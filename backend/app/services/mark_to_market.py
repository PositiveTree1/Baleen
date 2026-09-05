import asyncio
import logging
import time
from typing import Any
from datetime import datetime, timedelta
from sqlalchemy import select, func
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
        """Self-healing snapshot watchdog: reconciles historical dip anomalies and fills time gaps."""
        try:
            async with SessionLocal() as db:
                from app.models import PortfolioSnapshot
                
                # 1. Self-healing watchdog: check for time gaps and carry forward last known good balance
                stmt = select(PortfolioSnapshot).where(PortfolioSnapshot.user_id.is_(None)).order_by(PortfolioSnapshot.timestamp.desc()).limit(1)
                latest = (await db.execute(stmt)).scalars().first()
                now = datetime.utcnow()
                if latest and latest.timestamp and (now - latest.timestamp) > timedelta(minutes=30):
                    last_bal = float(latest.balance) if latest.balance else 10000.0
                    last_pnl = float(latest.total_pnl) if latest.total_pnl is not None else 0.0
                    logger.info(
                        f"🛡️ Watchdog: {(now - latest.timestamp).total_seconds()/60:.0f}m snapshot gap. "
                        f"Carrying forward last known balance ${last_bal:,.2f}."
                    )
                    db.add(PortfolioSnapshot(
                        user_id=None,
                        timestamp=now,
                        balance=last_bal,
                        total_pnl=last_pnl,
                        active_trades_count=int(latest.active_trades_count or 0)
                    ))
                    await db.commit()
                    logger.info(f"✅ Watchdog recovery snapshot written: Balance ${last_bal:,.2f}.")
        except Exception as e:
            logger.error(f"Watchdog recovery check note: {e}")

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
                # 1. Refresh closed trades summary aggregate periodically (saves megabytes of bandwidth)
                now_ts = time.time()
                if (now_ts - _closed_trades_cache.get("ts", 0.0)) > 60.0 or _closed_trades_cache.get("ts", 0.0) == 0.0:
                    stmt_closed_platform = select(
                        func.coalesce(func.sum(ExecutionLog.realized_pnl_usd), 0.0),
                        func.count(ExecutionLog.id)
                    ).where(
                        ExecutionLog.user_id.is_(None),
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
                        ExecutionLog.side == "BUY",
                        ExecutionLog.status.in_(["CLOSED", "RESOLVED"])
                    ).group_by(ExecutionLog.user_id)
                    user_rows = (await db.execute(stmt_closed_users)).all()
                    _closed_trades_cache["user_realized_pnls"] = {str(r[0]): float(r[1] or 0.0) for r in user_rows if r[0]}
                    _closed_trades_cache["ts"] = now_ts

                # 2. Fetch ONLY open active positions for real-time MTM evaluation
                stmt_open_logs = select(ExecutionLog).where(
                    ExecutionLog.status == "FILLED"
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
                if all_cids:
                    try:
                        batch_prices = await client.fetch_batch_live_prices(all_cids[:150])
                        fetch_ts = time.time()
                        for cid_key, outcome_dict in batch_prices.items():
                            if cid_key.startswith("token:"):
                                tok_id = cid_key.replace("token:", "")
                                _live_price_cache[tok_id] = {"price": outcome_dict.get("price", 0.5), "ts": fetch_ts}
                            else:
                                for outc_name, p_val in outcome_dict.items():
                                    cache_key = f"{cid_key}:{outc_name.lower().strip()}"
                                    _live_price_cache[cache_key] = {"price": p_val, "ts": fetch_ts}
                    except Exception as batch_err:
                        logger.debug(f"MTM batch price fetch note: {batch_err}")

                # 5. Price open lots with binary outcome inversion & cost-basis protection
                from app.services.polymarket_fees import calculate_polymarket_fee
                for elog in open_logs:
                    cid = elog.market_condition_id or ""
                    outc = elog.resolution_outcome or "Yes"
                    asset_id = elog.onchain_tx_hash or ""
                    fill_p = float(elog.user_fill_price or elog.whale_entry_price or 0.5)
                    notional = float(elog.notional_usd or 0.0)

                    # Ensure fee is calculated and cached
                    fee = float(elog.fee_usd or 0.0)
                    if fee == 0.0 and notional > 0:
                        fee_info = calculate_polymarket_fee(
                            notional_usd=notional,
                            price=fill_p,
                            market_title=elog.market_question or ""
                        )
                        fee = float(fee_info["fee_usd"])
                        elog.fee_usd = fee
                        elog.market_category = fee_info["category"]

                    # Obtain live price with cost-basis fallback (so missing prices NEVER cause cliff drops)
                    cur_p = get_live_price(cid=cid, outcome=outc, asset=asset_id, fallback=fill_p)
                    if cur_p > 0 and fill_p > 0:
                        if elog.side == "BUY":
                            gross_pnl = notional * ((cur_p - fill_p) / fill_p)
                        else:
                            gross_pnl = notional * ((fill_p - cur_p) / fill_p)
                        net_pnl = gross_pnl - fee
                        _last_known_pnl[str(elog.id)] = round(net_pnl, 2)
                    else:
                        _last_known_pnl[str(elog.id)] = round(-fee, 2)

                # 6. Authoritative sandbox balance & snapshot synchronization
                from app.models import PortfolioSnapshot
                now_dt = datetime.utcnow()
                platform_open = [l for l in open_logs if l.user_id is None]
                if not platform_open and open_logs:
                    platform_open = open_logs

                platform_open_unrealized = sum(_last_known_pnl.get(str(l.id), 0.0) for l in platform_open)
                platform_closed_realized = float(_closed_trades_cache.get("platform_realized_pnl", 0.0))
                total_portfolio_pnl = round(platform_closed_realized + platform_open_unrealized, 2)
                computed_bal = round(10000.0 + total_portfolio_pnl, 2)
                trades_count = int(_closed_trades_cache.get("platform_closed_count", 0)) + len(platform_open)

                stmt_latest_snap = select(PortfolioSnapshot.balance).where(
                    PortfolioSnapshot.user_id.is_(None)
                ).order_by(PortfolioSnapshot.timestamp.desc()).limit(1)
                last_db_bal = float((await db.execute(stmt_latest_snap)).scalar() or _last_snapshot_balance or 10000.0)

                # Guard against uninitialized database collapse
                if computed_bal < 5000.0 and last_db_bal > 12000.0:
                    logger.warning(f"⚠️ MTM: Suspicious collapse: computed ${computed_bal:,.2f} vs last ${last_db_bal:,.2f}. Preserving last balance.")
                    canonical_balance = last_db_bal
                    total_portfolio_pnl = round(last_db_bal - 10000.0, 2)
                    should_snapshot = False
                else:
                    canonical_balance = computed_bal
                    time_since_last = time.time() - _last_snapshot_time
                    balance_changed = abs(canonical_balance - _last_snapshot_balance) > 2.00
                    should_snapshot = balance_changed or time_since_last >= 60.0

                if should_snapshot:
                    db.add(PortfolioSnapshot(
                        user_id=None,
                        timestamp=now_dt,
                        balance=canonical_balance,
                        total_pnl=round(total_portfolio_pnl, 2),
                        active_trades_count=trades_count
                    ))
                    _last_snapshot_time = time.time()
                    _last_snapshot_balance = canonical_balance

                # 7. User balance sync
                try:
                    stmt_users = select(User)
                    users = (await db.execute(stmt_users)).scalars().all()
                    for u in users:
                        u_open = [l for l in open_logs if l.user_id == u.id]
                        if not u_open:
                            u_open = platform_open
                        u_open_unrealized = sum(_last_known_pnl.get(str(l.id), 0.0) for l in u_open)
                        u_closed_realized = float(_closed_trades_cache.get("user_realized_pnls", {}).get(str(u.id), platform_closed_realized))
                        u_total_pnl = round(u_closed_realized + u_open_unrealized, 2)
                        u_start = float(u.sandbox_starting_balance_usd or 10000.0)
                        u_bal = round(u_start + u_total_pnl, 2)
                        u.sandbox_balance_usd = u_bal
                        current_hwm = float(u.sandbox_high_water_mark_usd or u_start)
                        u.sandbox_high_water_mark_usd = max(current_hwm, u_bal)
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
    if not (0.001 <= price <= 0.999):
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

