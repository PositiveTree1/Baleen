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
            await asyncio.sleep(25.0)

    async def update_valuations_and_consensus(self):
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
                for log in recent_logs:
                    cid = log.market_condition_id
                    if not cid:
                        continue
                    if cid not in mkt_wallets:
                        mkt_wallets[cid] = set()
                        mkt_cash[cid] = 0.0
                    mkt_wallets[cid].add(log.source_wallet_address.lower())
                    mkt_cash[cid] += float(log.notional_usd or 0.0)

                for cid, w_set in mkt_wallets.items():
                    _consensus_cache[cid] = {
                        "whale_count": len(w_set),
                        "total_cash": mkt_cash.get(cid, 0.0),
                        "is_consensus": len(w_set) >= 2
                    }

                # 2. Fetch live prices for distinct (condition_id, outcome, asset) pairs
                pairs_to_price = list(set((log.market_condition_id, log.resolution_outcome or "Yes", log.onchain_tx_hash or "") for log in recent_logs if log.market_condition_id))
                for cid, outc, asset_id in pairs_to_price[:30]:
                    cache_key = f"{cid}:{outc.lower().strip()}"
                    try:
                        live_p = await client.fetch_live_token_price(condition_id=cid, asset=asset_id, outcome=outc)
                        if live_p is not None and 0.005 <= live_p <= 0.995:
                            entry = {"price": live_p, "ts": time.time()}
                            _live_price_cache[cache_key] = entry
                            _live_price_cache[cid] = entry
                            if asset_id:
                                _live_price_cache[asset_id] = entry
                    except Exception as e:
                        logger.debug(f"Live price fetch note for {cid}: {e}")
                    await asyncio.sleep(0.04)

                # 3. Update PnL on all execution logs (system feed + user copy trades)
                stmt_all_logs = select(ExecutionLog).where(ExecutionLog.status == "FILLED")
                all_logs = (await db.execute(stmt_all_logs)).scalars().all()
                for elog in all_logs:
                    cid = elog.market_condition_id or ""
                    outc = elog.resolution_outcome or "Yes"
                    asset_id = elog.onchain_tx_hash or ""
                    fill_p = float(elog.user_fill_price or elog.whale_entry_price or 0.5)
                    notional = float(elog.notional_usd or 0.0)

                    cur_p = get_live_price(cid, outcome=outc, asset=asset_id, fallback=fill_p)
                    if cur_p > 0 and fill_p > 0:
                        if elog.side == "BUY":
                            trade_pnl = notional * ((cur_p - fill_p) / fill_p)
                        else:
                            trade_pnl = notional * ((fill_p - cur_p) / fill_p)
                        elog.realized_pnl_usd = round(trade_pnl, 2)

                # 4. Update user sandbox balances based on their active filled trades
                stmt_users = select(User)
                users = (await db.execute(stmt_users)).scalars().all()

                for u in users:
                    stmt_user_logs = select(ExecutionLog).where(
                        ExecutionLog.user_id == u.id,
                        ExecutionLog.status == "FILLED"
                    )
                    user_logs = (await db.execute(stmt_user_logs)).scalars().all()

                    total_pnl = sum(float(ulog.realized_pnl_usd or 0.0) for ulog in user_logs)
                    base_balance = float(u.sandbox_starting_balance_usd or 10000.0)
                    u.sandbox_balance_usd = round(base_balance + total_pnl, 2)
                    if u.sandbox_balance_usd > (u.sandbox_high_water_mark_usd or base_balance):
                        u.sandbox_high_water_mark_usd = u.sandbox_balance_usd

                await db.commit()
        finally:
            await client.close()

mark_to_market_service = MarkToMarketService()

def get_live_price(cid: str = "", outcome: str = "Yes", asset: str = "", fallback: float = 0.5) -> float:
    if asset and asset in _live_price_cache:
        return _live_price_cache[asset]["price"]
    if cid:
        cache_key = f"{cid}:{outcome.lower().strip()}"
        if cache_key in _live_price_cache:
            return _live_price_cache[cache_key]["price"]
        if cid in _live_price_cache:
            return _live_price_cache[cid]["price"]
    return fallback

def get_consensus(cid: str) -> dict:
    return _consensus_cache.get(cid, {"whale_count": 1, "total_cash": 0.0, "is_consensus": False})
