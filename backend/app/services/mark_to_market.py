import asyncio
import logging
import time
from typing import Any
from datetime import datetime, timedelta
from sqlalchemy import select, func, text
from app.database import SessionLocal
from app.models import ExecutionLog, User, Wallet
from app.discovery.polymarket_client import PolymarketClient

logger = logging.getLogger(__name__)

# In-memory live price cache: condition_id -> {price, ts}
_live_price_cache: dict[str, dict] = {}
# Consensus cache: condition_id -> {whale_count, total_cash}
_consensus_cache: dict[str, dict] = {}
# Per-trade last-known PnL: trade_id -> last computed PnL (avoids oscillation from stale prices)
_last_known_pnl: dict[str, float] = {}

# Snapshot throttle: track last snapshot write time and balance
_last_snapshot_time: float = 0.0
_last_snapshot_balance: float = 0.0
_SNAPSHOT_MIN_INTERVAL_SECS = 60  # Write at most 1 snapshot per 60s unless balance changes significantly

_price_cycle_index: int = 0

# Cached aggregates for closed trades: prevents loading thousands of closed logs every 5s over WAN
_closed_trades_cache: dict[str, Any] = {
    "ts": 0.0,
    "platform_realized_pnl": 0.0,
    "platform_closed_count": 0,
    "user_realized_pnls": {}
}

class MarkToMarketService:
    def __init__(self):
        self.running = False

    async def start(self):
        self.running = True
        logger.info("Mark-to-Market Live Valuation & Consensus Service started.")
        asyncio.create_task(self._ensure_snapshot_continuity())
        asyncio.create_task(self._valuation_loop())

    async def stop(self):
        self.running = False

    async def _ensure_snapshot_continuity(self):
        # A gap is missing evidence; do not manufacture a new valuation timestamp.
        return

    async def _valuation_loop(self):
        while self.running:
            try:
                await self.update_valuations_and_consensus()
            except Exception as e:
                logger.error(f"Error in Mark-to-Market loop: {e}", exc_info=True)
            await asyncio.sleep(5.0)

    async def update_valuations_and_consensus(self):
        global _last_snapshot_time, _last_snapshot_balance, _price_cycle_index, _closed_trades_cache
        client = PolymarketClient()
        try:
            async with SessionLocal() as db:
                if db.bind.dialect.name == 'postgresql':
                    await db.execute(text('SELECT pg_advisory_xact_lock(20260909, 1)'))
                # 1. Refresh closed trades summary aggregate periodically (saves megabytes of bandwidth)
                now_ts = time.time()
                if True:  # Read under the same financial lock; stale aggregates can overwrite settlement.
                    stmt_closed_platform = select(
                        func.coalesce(func.sum(ExecutionLog.realized_pnl_usd), 0.0),
                        func.count(ExecutionLog.id)
                    ).where(
                        ExecutionLog.user_id.is_(None),
                        ExecutionLog.is_sandbox.is_(True),
                        ExecutionLog.side == "BUY",
                        ExecutionLog.status.in_(["CLOSED", "RESOLVED"])
                    )
                    closed_row = (await db.execute(stmt_closed_platform)).first()
                    _closed_trades_cache["platform_realized_pnl"] = float(closed_row[0] or 0.0) if closed_row else 0.0
                    _closed_trades_cache["platform_closed_count"] = int(closed_row[1] or 0) if closed_row else 0

                    stmt_closed_users = select(
                        ExecutionLog.user_id,
                        func.coalesce(func.sum(ExecutionLog.realized_pnl_usd), 0.0)
                    ).where(
                        ExecutionLog.user_id.is_not(None),
                        ExecutionLog.is_sandbox.is_(True),
                        ExecutionLog.side == "BUY",
                        ExecutionLog.status.in_(["CLOSED", "RESOLVED"])
                    ).group_by(ExecutionLog.user_id)
                    user_rows = (await db.execute(stmt_closed_users)).all()
                    _closed_trades_cache["user_realized_pnls"] = {str(r[0]): float(r[1] or 0.0) for r in user_rows if r[0]}
                    _closed_trades_cache["ts"] = now_ts

                # 2. Fetch ONLY open active positions for real-time MTM evaluation
                stmt_open_logs = select(ExecutionLog).where(
                    ExecutionLog.status == "FILLED", ExecutionLog.is_sandbox.is_(True), ExecutionLog.side == "BUY"
                ).order_by(ExecutionLog.executed_at.desc())
                open_logs = (await db.execute(stmt_open_logs)).scalars().all()

                # 3. Update Consensus State for active open markets
                mkt_wallets: dict[str, set[str]] = {}
                mkt_cash: dict[str, float] = {}
                mkt_outcomes: dict[str, str] = {}
                for log in open_logs:
                    cid = log.market_condition_id
                    if not cid:
                        continue
                    if cid not in mkt_wallets:
                        mkt_wallets[cid] = set()
                        mkt_cash[cid] = 0.0
                    mkt_wallets[cid].add(log.source_wallet_address.lower())
                    mkt_cash[cid] += float(log.notional_usd or 0.0)
                    mkt_outcomes[cid] = log.resolution_outcome or "Yes"

                for cid, w_set in mkt_wallets.items():
                    cnt = len(w_set)
                    is_con = cnt >= 2
                    _consensus_cache[cid] = {
                        "whale_count": cnt,
                        "total_cash": round(mkt_cash.get(cid, 0.0), 2),
                        "is_consensus": is_con,
                        "multiplier": 1.5 if is_con else 1.0,
                        "whales": list(w_set)[:4],
                        "detail": f"{cnt} distinct whales took aligned {mkt_outcomes.get(cid, 'Yes')} positions with ${mkt_cash.get(cid, 0.0):,.0f} aggregate capital." if is_con else ""
                    }

                # 4. Batch fetch live prices across open markets from Gamma API
                all_cids = list({str(l.market_condition_id).strip() for l in open_logs if l.market_condition_id and len(str(l.market_condition_id).strip()) > 5})
                # The read set is complete and the session uses
                # expire_on_commit=False. Do not pin a database connection
                # while Gamma responds; this loop runs every five seconds.
                await db.commit()
                if all_cids:
                    try:
                        batch_prices = await client.fetch_batch_live_prices(all_cids[:150])
                        fetch_ts = time.time()
                        for cid_key, outcome_dict in batch_prices.items():
                            if cid_key.startswith("token:"):
                                tok_id = cid_key.replace("token:", "")
                                _live_price_cache[tok_id] = {"price": outcome_dict.get("price"), "ts": fetch_ts}
                            else:
                                for outc_name, p_val in outcome_dict.items():
                                    cache_key = f"{cid_key}:{outc_name.lower().strip()}"
                                    _live_price_cache[cache_key] = {"price": p_val, "ts": fetch_ts}
                    except Exception as batch_err:
                        logger.debug(f"MTM batch price fetch note: {batch_err}")

                # Revalue only from actual fresh marks; zero is a valid observed price.
                from app.services.execution_valuation import execution_valuation
                unavailable = set()
                for elog in open_logs:
                    valuation = execution_valuation(elog)
                    if valuation['pnl'] is None:
                        unavailable.add(elog.id)
                        _last_known_pnl.pop(str(elog.id), None)
                    else:
                        _last_known_pnl[str(elog.id)] = valuation['pnl']

                # 6. Authoritative sandbox balance & snapshot synchronization
                from app.models import PortfolioSnapshot
                if db.bind.dialect.name == 'postgresql':
                    # Serialize the write phase only. The prior read lock was
                    # deliberately released before the external price fetch.
                    await db.execute(text('SELECT pg_advisory_xact_lock(20260909, 1)'))
                now_dt = datetime.utcnow()
                platform_open = [l for l in open_logs if l.user_id is None]

                platform_open_unrealized = sum(_last_known_pnl.get(str(l.id), 0.0) for l in platform_open)
                platform_closed_realized = float(_closed_trades_cache.get("platform_realized_pnl", 0.0))
                total_portfolio_pnl = round(platform_closed_realized + platform_open_unrealized, 2)
                computed_bal = round(10000.0 + total_portfolio_pnl, 2)
                trades_count = int(_closed_trades_cache.get("platform_closed_count", 0)) + len(platform_open)

                stmt_latest_snap = select(PortfolioSnapshot.balance).where(
                    PortfolioSnapshot.user_id.is_(None)
                ).order_by(PortfolioSnapshot.timestamp.desc()).limit(1)
                last_db_bal = float((await db.execute(stmt_latest_snap)).scalar() or _last_snapshot_balance or 10000.0)

                canonical_balance = computed_bal
                time_since_last = time.time() - _last_snapshot_time
                balance_changed = abs(canonical_balance - _last_snapshot_balance) > 2.00
                should_snapshot = balance_changed or time_since_last >= 60.0

                if should_snapshot and not any(l.id in unavailable for l in platform_open):
                    db.add(PortfolioSnapshot(
                        user_id=None,
                        timestamp=now_dt,
                        balance=canonical_balance,
                        total_pnl=round(total_portfolio_pnl, 2),
                        active_trades_count=trades_count
                    ))
                    _last_snapshot_time = time.time()
                    _last_snapshot_balance = canonical_balance

                # 7. User balance sync & continuous portfolio snapshot writing (strictly isolated per user)
                try:
                    stmt_users = select(User)
                    users = (await db.execute(stmt_users)).scalars().all()
                    for u in users:
                        u_open = [l for l in open_logs if l.user_id == u.id]
                        u_open_unrealized = sum(
                            _last_known_pnl.get(str(l.id), -float(l.fee_usd or 0.0) if l.side == "BUY" else 0.0)
                            for l in u_open
                        )
                        u_closed_realized = float(_closed_trades_cache.get("user_realized_pnls", {}).get(str(u.id), 0.0))
                        u_total_pnl = round(u_closed_realized + u_open_unrealized, 2)
                        u_start = float(u.sandbox_starting_balance_usd or 10000.0)
                        u_bal = round(u_start + u_total_pnl, 2)
                        u.sandbox_balance_usd = u_bal
                        current_hwm = float(u.sandbox_high_water_mark_usd or u_start)
                        u.sandbox_high_water_mark_usd = max(current_hwm, u_bal)

                        # Write periodic continuous snapshot for the user (at most once every 60s or if balance moved > $1.00)
                        stmt_user_snap = select(PortfolioSnapshot.balance, PortfolioSnapshot.timestamp).where(
                            PortfolioSnapshot.user_id == u.id
                        ).order_by(PortfolioSnapshot.timestamp.desc()).limit(1)
                        last_snap_row = (await db.execute(stmt_user_snap)).first()
                        last_u_bal = float(last_snap_row[0]) if last_snap_row else u_start
                        last_u_time = last_snap_row[1].timestamp() if (last_snap_row and last_snap_row[1]) else 0.0

                        u_time_since_snap = time.time() - last_u_time
                        u_bal_changed = abs(u_bal - last_u_bal) > 1.00
                        u_should_snap = u_bal_changed or (u_time_since_snap >= 60.0 and len(u_open) > 0)

                        if u_should_snap:
                            stmt_closed_count = select(func.count(ExecutionLog.id)).where(
                                ExecutionLog.user_id == u.id,
                                ExecutionLog.status.in_(["CLOSED", "RESOLVED"]),
                                ExecutionLog.side == "BUY"
                            )
                            u_closed_cnt = int((await db.execute(stmt_closed_count)).scalar() or 0)
                            db.add(PortfolioSnapshot(
                                user_id=u.id,
                                timestamp=now_dt,
                                balance=u_bal,
                                total_pnl=round(u_total_pnl, 2),
                                active_trades_count=len(u_open) + u_closed_cnt
                            ))
                except Exception as user_sync_err:
                    logger.debug(f"User sync note: {user_sync_err}")

                try:
                    await db.commit()
                except Exception as snap_err:
                    logger.error(f"❌ MTM snapshot write failed: {snap_err}", exc_info=True)
                    try:
                        await db.rollback()
                    except Exception:
                        pass
        finally:
            await client.close()

mark_to_market_service = MarkToMarketService()

def get_observed_price(cid: str = '', outcome: str = '', asset: str = '', max_age_seconds: float = 60.0):
    """An actual fresh cached observation, or None. Never an entry-price substitute."""
    import math
    keys = ([asset] if asset else []) + ([f'{cid.lower().strip()}:{outcome.lower().strip()}'] if cid and outcome else [])
    now = time.time()
    for key in keys:
        entry = _live_price_cache.get(key)
        if not entry:
            continue
        price, observed = entry.get('price'), entry.get('ts')
        if (isinstance(price, (float, int)) and not isinstance(price, bool) and math.isfinite(price)
                and 0 <= price <= 1 and isinstance(observed, (float, int)) and math.isfinite(observed)
                and 0 <= now - observed <= max_age_seconds):
            return {'price': price, 'observed_at': observed, 'source': 'provider_cache'}

    # Binary complementary inversion if direct outcome key is not found
    if cid and outcome:
        cid_clean = cid.lower().strip()
        outc_clean = outcome.lower().strip()
        comp_key = None
        if outc_clean in ('no', '0'):
            comp_key = f'{cid_clean}:yes'
        elif outc_clean in ('yes', '1'):
            comp_key = f'{cid_clean}:no'
        elif outc_clean == 'under':
            comp_key = f'{cid_clean}:over'
        elif outc_clean == 'over':
            comp_key = f'{cid_clean}:under'

        if comp_key and comp_key in _live_price_cache:
            entry = _live_price_cache[comp_key]
            price, observed = entry.get('price'), entry.get('ts')
            if (isinstance(price, (float, int)) and not isinstance(price, bool) and math.isfinite(price)
                    and 0 <= price <= 1 and isinstance(observed, (float, int)) and math.isfinite(observed)
                    and 0 <= now - observed <= max_age_seconds):
                inv_price = round(max(0.0001, min(0.9999, 1.0 - price)), 4)
                return {'price': inv_price, 'observed_at': observed, 'source': 'provider_cache_complement'}

    return None

def get_live_price(cid: str = "", outcome: str = "Yes", asset: str = "", fallback: float = 0.5) -> float:
    """Resolves live market price with binary outcome (1 - p) complementary inversion and fresh cache validation."""
    now_sec = time.time()
    if asset and asset in _live_price_cache:
        entry = _live_price_cache[asset]
        if (now_sec - entry.get("ts", 0)) < 3600.0:
            return entry["price"]
            
    if cid:
        cid_clean = cid.lower().strip()
        outc_clean = outcome.lower().strip()
        cache_key = f"{cid_clean}:{outc_clean}"
        if cache_key in _live_price_cache:
            entry = _live_price_cache[cache_key]
            if (now_sec - entry.get("ts", 0)) < 3600.0:
                return entry["price"]

        # Binary market complementary inversion (1 - p)
        if outc_clean in ["no", "0"]:
            yes_key = f"{cid_clean}:yes"
            if yes_key in _live_price_cache:
                entry = _live_price_cache[yes_key]
                if (now_sec - entry.get("ts", 0)) < 3600.0:
                    return round(max(0.001, min(0.999, 1.0 - entry["price"])), 4)
        elif outc_clean in ["yes", "1"]:
            no_key = f"{cid_clean}:no"
            if no_key in _live_price_cache:
                entry = _live_price_cache[no_key]
                if (now_sec - entry.get("ts", 0)) < 3600.0:
                    return round(max(0.001, min(0.999, 1.0 - entry["price"])), 4)

    return fallback

def set_live_price(cid: str = "", outcome: str = "Yes", price: float = 0.5, asset: str = ""):
    global _live_price_cache
    if not (0.0 <= price <= 1.0):
        return
    entry = {"price": price, "ts": time.time()}
    if cid:
        cache_key = f"{cid.lower().strip()}:{outcome.lower().strip()}"
        _live_price_cache[cache_key] = entry
    if asset:
        _live_price_cache[asset] = entry

def get_consensus(cid: str) -> dict:
    return _consensus_cache.get(cid, {
        "whale_count": 1,
        "total_cash": 0.0,
        "is_consensus": False,
        "multiplier": 1.0,
        "whales": [],
        "detail": ""
    })

