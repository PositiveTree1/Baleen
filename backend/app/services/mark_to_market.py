import asyncio
import logging
import time
from sqlalchemy import select, func
from app.database import SessionLocal
from app.models import ExecutionLog, User, Wallet
from app.discovery.polymarket_client import PolymarketClient

logger = logging.getLogger(__name__)

# In-memory live price cache: condition_id -> {price, ts}
_live_price_cache: dict[str, dict] = {}
# Consensus cache: condition_id -> {whale_count, total_cash}
_consensus_cache: dict[str, dict] = {}

# Snapshot throttle: track last snapshot write time and balance
_last_snapshot_time: float = 0.0
_last_snapshot_balance: float = 0.0
_SNAPSHOT_MIN_INTERVAL_SECS = 60  # Write at most 1 snapshot per minute unless balance changes significantly

class MarkToMarketService:
    def __init__(self):
        self.running = False

    async def start(self):
        self.running = True
        logger.info("Mark-to-Market Live Valuation & Consensus Service started.")
        asyncio.create_task(self._valuation_loop())

    async def stop(self):
        self.running = False

    async def _valuation_loop(self):
        while self.running:
            try:
                await self.update_valuations_and_consensus()
            except Exception as e:
                logger.error(f"Error in Mark-to-Market loop: {e}", exc_info=True)
            await asyncio.sleep(3.5)

    async def update_valuations_and_consensus(self):
        global _last_snapshot_time, _last_snapshot_balance
        client = PolymarketClient()
        try:
            async with SessionLocal() as db:
                # 1. Update consensus across recent active whale trades
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

                # 2. Fetch live prices for ALL distinct open market positions (no 30 limit)
                stmt_active_pairs = select(
                    ExecutionLog.market_condition_id,
                    ExecutionLog.resolution_outcome,
                    ExecutionLog.onchain_tx_hash
                ).where(
                    ExecutionLog.status == "FILLED",
                    ExecutionLog.market_condition_id.is_not(None)
                ).distinct()
                all_active_rows = (await db.execute(stmt_active_pairs)).all()
                pairs_to_price = list(set(
                    (row[0], row[1] or "Yes", row[2] or "")
                    for row in all_active_rows if row[0]
                ))

                # Concurrently price in bounded chunks with strict rate-limit protection
                sem = asyncio.Semaphore(4)

                async def _price_pair(cid: str, outc: str, asset_id: str):
                    async with sem:
                        cache_key = f"{cid.lower().strip()}:{outc.lower().strip()}"
                        # If cached less than 15s ago, reuse to save API quota
                        existing = _live_price_cache.get(cache_key)
                        if existing and (time.time() - existing.get("ts", 0)) < 15.0:
                            return
                        try:
                            live_p = await client.fetch_live_token_price(condition_id=cid, asset=asset_id, outcome=outc)
                            if live_p is not None and 0.005 <= live_p <= 0.995:
                                entry = {"price": live_p, "ts": time.time()}
                                _live_price_cache[cache_key] = entry
                                if asset_id:
                                    _live_price_cache[asset_id] = entry
                        except Exception as e:
                            logger.debug(f"Live price fetch note for {cid}: {e}")
                        await asyncio.sleep(0.05)

                # Rotating window: refresh up to 40 distinct active positions per 4s cycle
                tasks = [_price_pair(c, o, a) for c, o, a in pairs_to_price[:40]]
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                # 3. Update PnL on all execution logs (system feed + user copy trades)
                # Use a single query and reuse these objects for the snapshot calculation below
                stmt_all_logs = select(ExecutionLog).where(ExecutionLog.status == "FILLED")
                all_logs = (await db.execute(stmt_all_logs)).scalars().all()
                from app.services.polymarket_fees import calculate_polymarket_fee
                for elog in all_logs:
                    cid = elog.market_condition_id or ""
                    outc = elog.resolution_outcome or "Yes"
                    asset_id = elog.onchain_tx_hash or ""
                    fill_p = float(elog.user_fill_price or elog.whale_entry_price or 0.5)
                    notional = float(elog.notional_usd or 0.0)

                    # Ensure fee is calculated and cached
                    if (elog.fee_usd is None or elog.fee_usd == 0.0) and notional > 0:
                        fee_info = calculate_polymarket_fee(
                            notional_usd=notional,
                            price=fill_p,
                            market_title=elog.market_question or ""
                        )
                        elog.fee_usd = fee_info["fee_usd"]
                        elog.market_category = fee_info["category"]

                    fee = float(elog.fee_usd or 0.0)
                    cur_p = get_live_price(cid, outcome=outc, asset=asset_id, fallback=fill_p)
                    if cur_p > 0 and fill_p > 0:
                        if elog.side == "BUY":
                            gross_pnl = notional * ((cur_p - fill_p) / fill_p)
                        else:
                            gross_pnl = notional * ((fill_p - cur_p) / fill_p)
                        # Net PnL after Polymarket trading fee
                        net_pnl = gross_pnl - fee
                        elog.realized_pnl_usd = round(net_pnl, 2)

                # 4. Synchronize authoritative sandbox balance & snapshots
                # IMPORTANT: Reuse `all_logs` from step 3 — do NOT re-query, as the
                # realized_pnl_usd values were just updated in-memory above.
                from app.models import PortfolioSnapshot
                from datetime import datetime

                now_dt = datetime.utcnow()
                total_portfolio_pnl = sum(float(l.realized_pnl_usd or 0.0) for l in all_logs)
                trades_count = len(all_logs)

                # Guard: If total PnL is exactly 0 and we have trades, live prices
                # likely failed. Preserve the last known good balance instead of
                # collapsing to $10,000.
                if trades_count > 0 and total_portfolio_pnl == 0.0:
                    logger.warning(
                        f"⚠️ MTM: {trades_count} filled trades but total PnL = $0.00. "
                        f"Live prices likely unavailable. Preserving last known balance ${_last_snapshot_balance:,.2f}."
                    )
                    canonical_balance = _last_snapshot_balance if _last_snapshot_balance > 0 else 10000.0
                else:
                    canonical_balance = round(10000.0 + total_portfolio_pnl, 2)

                # Update all users to authoritative canonical balance
                try:
                    stmt_users = select(User)
                    users = (await db.execute(stmt_users)).scalars().all()
                    for u in users:
                        u.sandbox_balance_usd = canonical_balance
                        if canonical_balance > float(u.sandbox_high_water_mark_usd or 10000.0):
                            u.sandbox_high_water_mark_usd = canonical_balance

                    # Snapshot throttle: Only write if balance changed meaningfully or enough time passed
                    time_since_last = time.time() - _last_snapshot_time
                    balance_changed = abs(canonical_balance - _last_snapshot_balance) > 0.50
                    should_snapshot = balance_changed or time_since_last >= _SNAPSHOT_MIN_INTERVAL_SECS

                    if should_snapshot:
                        for u in users:
                            db.add(PortfolioSnapshot(
                                user_id=u.id,
                                timestamp=now_dt,
                                balance=canonical_balance,
                                total_pnl=round(total_portfolio_pnl, 2),
                                active_trades_count=trades_count
                            ))

                        # Global platform sandbox snapshot
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

def get_consensus(cid: str) -> dict:
    return _consensus_cache.get(cid, {
        "whale_count": 1,
        "total_cash": 0.0,
        "is_consensus": False,
        "multiplier": 1.0,
        "whales": [],
        "detail": ""
    })
