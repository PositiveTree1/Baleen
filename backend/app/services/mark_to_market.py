import asyncio
import logging
import time
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
_SNAPSHOT_MIN_INTERVAL_SECS = 25  # Write at most 1 snapshot per 25s unless balance changes significantly

_price_cycle_index: int = 0

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
        """Self-healing snapshot watchdog: fills time gaps but never overwrites balance with cold-cache values."""
        try:
            async with SessionLocal() as db:
                from app.models import PortfolioSnapshot
                stmt = select(PortfolioSnapshot).where(PortfolioSnapshot.user_id.is_(None)).order_by(PortfolioSnapshot.timestamp.desc()).limit(1)
                latest = (await db.execute(stmt)).scalars().first()
                now = datetime.utcnow()
                if latest and latest.timestamp and (now - latest.timestamp) > timedelta(minutes=30):
                    # Gap detected — carry forward the LAST KNOWN GOOD balance, not a recomputed one
                    last_bal = float(latest.balance) if latest.balance else 10000.0
                    last_pnl = float(latest.total_pnl) if latest.total_pnl is not None else 0.0
                    logger.info(
                        f"🛡️ Watchdog: {(now - latest.timestamp).total_seconds()/60:.0f}m snapshot gap. "
                        f"Carrying forward last known balance ${last_bal:,.2f} (not recomputing from cold cache)."
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
            await asyncio.sleep(3.5)

    async def update_valuations_and_consensus(self):
        global _last_snapshot_time, _last_snapshot_balance, _price_cycle_index
        client = PolymarketClient()
        try:
            async with SessionLocal() as db:
                # 1. Update Consensus State for top recent active markets
                stmt_recent = select(ExecutionLog).where(
                    ExecutionLog.status == "FILLED"
                ).order_by(ExecutionLog.executed_at.desc()).limit(100)
                recent_logs = (await db.execute(stmt_recent)).scalars().all()

                mkt_wallets: dict[str, set[str]] = {}
                mkt_cash: dict[str, float] = {}
                mkt_outcomes: dict[str, str] = {}
                for log in recent_logs:
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

                # 2. Batch fetch live prices across active markets from Gamma API
                active_cids_stmt = select(ExecutionLog.market_condition_id).where(
                    ExecutionLog.status == "FILLED",
                    ExecutionLog.market_condition_id.is_not(None)
                ).distinct()
                all_active_rows = (await db.execute(active_cids_stmt)).all()
                all_cids = list({str(row[0]).strip() for row in all_active_rows if row[0] and len(str(row[0]).strip()) > 5})
                if all_cids:
                    try:
                        batch_prices = await client.fetch_batch_live_prices(all_cids[:150])
                        now_ts = time.time()
                        for cid_key, outcome_dict in batch_prices.items():
                            if cid_key.startswith("token:"):
                                tok_id = cid_key.replace("token:", "")
                                _live_price_cache[tok_id] = {"price": outcome_dict.get("price", 0.5), "ts": now_ts}
                            else:
                                for outc_name, p_val in outcome_dict.items():
                                    cache_key = f"{cid_key}:{outc_name}"
                                    _live_price_cache[cache_key] = {"price": p_val, "ts": now_ts}
                    except Exception as batch_err:
                        logger.debug(f"MTM batch price fetch note: {batch_err}")

                # 3. Update PnL on all execution logs (FILLED + CLOSED + RESOLVED)
                # Use a single query and reuse these objects for the snapshot calculation below
                stmt_all_logs = select(ExecutionLog).where(ExecutionLog.status.in_(["FILLED", "CLOSED", "RESOLVED"]))
                all_logs = (await db.execute(stmt_all_logs)).scalars().all()
                from app.services.polymarket_fees import calculate_polymarket_fee
                for elog in all_logs:
                    # Closed/resolved trades already have their final realized PnL locked in
                    if elog.status != "FILLED":
                        continue

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

                    # Detect if we have a valid cached price (within last hour)
                    cache_key = f"{cid.lower().strip()}:{outc.lower().strip()}"
                    price_entry = None
                    if asset_id and asset_id in _live_price_cache:
                        price_entry = _live_price_cache[asset_id]
                    elif cid and cache_key in _live_price_cache:
                        price_entry = _live_price_cache.get(cache_key)

                    price_is_fresh = (price_entry is not None and (time.time() - price_entry.get("ts", 0)) < 3600.0)

                    if price_is_fresh:
                        cur_p = price_entry["price"]
                        if cur_p > 0 and fill_p > 0:
                            if elog.side == "BUY":
                                gross_pnl = notional * ((cur_p - fill_p) / fill_p)
                            else:
                                gross_pnl = notional * ((fill_p - cur_p) / fill_p)
                            net_pnl = gross_pnl - fee
                            elog.realized_pnl_usd = round(net_pnl, 2)
                            _last_known_pnl[str(elog.id)] = elog.realized_pnl_usd
                    else:
                        # Use last known PnL to avoid oscillation from stale/fill prices
                        last_pnl = _last_known_pnl.get(str(elog.id))
                        if last_pnl is not None:
                            elog.realized_pnl_usd = last_pnl
                        elif elog.realized_pnl_usd is None:
                            elog.realized_pnl_usd = round(-fee, 2)

                # 4. Synchronize authoritative sandbox balance & snapshots
                from app.models import PortfolioSnapshot
                from datetime import datetime

                now_dt = datetime.utcnow()
                # Deduplicate: only sum platform logs (user_id IS NULL) for global balance
                platform_logs = [l for l in all_logs if l.user_id is None]
                if not platform_logs:
                    platform_logs = all_logs

                # --- STRUCTURAL FIX: Track price cache warmth before computing balance ---
                # Count how many open positions actually got a fresh live price this cycle
                open_positions = [l for l in platform_logs if l.status == "FILLED"]
                closed_positions = [l for l in platform_logs if l.status in ("CLOSED", "RESOLVED")]
                
                positions_with_fresh_price = 0
                for elog in open_positions:
                    cid = (elog.market_condition_id or "").lower().strip()
                    outc = (elog.resolution_outcome or "Yes").lower().strip()
                    asset_id = elog.onchain_tx_hash or ""
                    cache_key = f"{cid}:{outc}"
                    
                    entry = _live_price_cache.get(asset_id) or _live_price_cache.get(cache_key)
                    if entry and (time.time() - entry.get("ts", 0)) < 3600.0:
                        positions_with_fresh_price += 1

                total_open = len(open_positions)
                cache_warmth_pct = (positions_with_fresh_price / total_open * 100.0) if total_open > 0 else 0.0
                
                # Fetch the last known good balance from database
                stmt_latest_snap = select(PortfolioSnapshot.balance).where(
                    PortfolioSnapshot.user_id.is_(None)
                ).order_by(PortfolioSnapshot.timestamp.desc()).limit(1)
                last_db_bal = float((await db.execute(stmt_latest_snap)).scalar() or _last_snapshot_balance or 10000.0)

                # Sum PnL from all platform logs
                total_portfolio_pnl = sum(float(l.realized_pnl_usd or 0.0) for l in platform_logs)
                computed_bal = round(10000.0 + total_portfolio_pnl, 2)
                trades_count = len(platform_logs)

                # DECISION: Only trust the computed balance if the price cache is warm enough
                # If <30% of open positions have fresh prices, the computed balance is unreliable
                if total_open > 10 and cache_warmth_pct < 30.0:
                    logger.warning(
                        f"⚠️ MTM: Price cache cold ({cache_warmth_pct:.0f}% warm, {positions_with_fresh_price}/{total_open} open positions priced). "
                        f"Computed ${computed_bal:,.2f} vs last known ${last_db_bal:,.2f}. "
                        f"REFUSING to write snapshot — preserving last known balance."
                    )
                    canonical_balance = last_db_bal
                    total_portfolio_pnl = round(last_db_bal - 10000.0, 2)
                    # Skip snapshot write entirely when cache is cold
                    should_snapshot = False
                elif computed_bal < (last_db_bal - 500.0) and last_db_bal > 12000.0:
                    # Even with warm cache, guard against sudden >$500 drops (likely partial pricing)
                    logger.warning(
                        f"⚠️ MTM: Suspicious drop: computed ${computed_bal:,.2f} vs last ${last_db_bal:,.2f} "
                        f"(cache {cache_warmth_pct:.0f}% warm). Preserving last known balance."
                    )
                    canonical_balance = last_db_bal
                    total_portfolio_pnl = round(last_db_bal - 10000.0, 2)
                    should_snapshot = False
                else:
                    canonical_balance = computed_bal
                    # Snapshot throttle: Only write if balance changed meaningfully or enough time passed
                    time_since_last = time.time() - _last_snapshot_time
                    balance_changed = abs(canonical_balance - _last_snapshot_balance) > 2.0
                    should_snapshot = balance_changed or time_since_last >= _SNAPSHOT_MIN_INTERVAL_SECS

                logger.debug(
                    f"MTM cycle: cache={cache_warmth_pct:.0f}% warm ({positions_with_fresh_price}/{total_open}), "
                    f"computed=${computed_bal:,.2f}, canonical=${canonical_balance:,.2f}, write={should_snapshot}"
                )

                # Update all users to their authoritative balance
                try:
                    stmt_users = select(User)
                    users = (await db.execute(stmt_users)).scalars().all()
                    for u in users:
                        u_logs = [l for l in all_logs if l.user_id == u.id]
                        if not u_logs:
                            u_logs = platform_logs
                        u_pnl = sum(float(l.realized_pnl_usd or 0.0) for l in u_logs)
                        u_start = float(u.sandbox_starting_balance_usd or 10000.0)
                        u_bal = round(u_start + u_pnl, 2)
                        u.sandbox_balance_usd = u_bal
                        if u_bal > float(u.sandbox_high_water_mark_usd or u_start):
                            u.sandbox_high_water_mark_usd = u_bal

                    if should_snapshot:
                        # Global platform sandbox snapshot (no per-user snapshots)
                        db.add(PortfolioSnapshot(
                            user_id=None,
                            timestamp=now_dt,
                            balance=canonical_balance,
                            total_pnl=round(total_portfolio_pnl, 2),
                            active_trades_count=trades_count
                        ))

                        _last_snapshot_time = time.time()
                        _last_snapshot_balance = canonical_balance

                    await db.commit()
                except Exception as snap_err:
                    logger.error(f"❌ MTM snapshot write failed: {snap_err}", exc_info=True)
                    # Still try to commit the PnL updates even if snapshot failed
                    try:
                        await db.commit()
                    except Exception:
                        pass
        finally:
            await client.close()

mark_to_market_service = MarkToMarketService()

def get_live_price(cid: str = "", outcome: str = "Yes", asset: str = "", fallback: float = 0.5) -> float:
    if asset and asset in _live_price_cache:
        return _live_price_cache[asset]["price"]
    if cid:
        cache_key = f"{cid.lower().strip()}:{outcome.lower().strip()}"
        if cache_key in _live_price_cache:
            return _live_price_cache[cache_key]["price"]
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
