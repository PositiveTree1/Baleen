import asyncio
import logging
import uuid
from datetime import datetime, timezone
import httpx
from sqlalchemy import select, func
from app.database import SessionLocal
from app.models import Wallet, ExecutionLog, User
from app.config import settings

logger = logging.getLogger(__name__)

class LiveTradeMirrorService:
    def __init__(self):
        self.running = False
        self.data_api_url = settings.POLYMARKET_DATA_API_URL
        self.seen_trade_keys = set()
        self.client = None

    async def start(self):
        self.running = True
        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info("Titan-style Polymarket Live Trade Mirror started.")
        asyncio.create_task(self._poll_loop())

    async def stop(self):
        self.running = False
        if self.client:
            await self.client.aclose()

    async def _poll_loop(self):
        while self.running:
            try:
                await self._poll_active_whales()
            except Exception as e:
                logger.error(f"Error in live whale polling loop: {e}", exc_info=True)
            await asyncio.sleep(8.0)

    async def _poll_active_whales(self):
        async with SessionLocal() as db:
            # Query all active non-dormant, non-HFT wallets in basket
            stmt = select(Wallet).where(
                Wallet.status == "active",
                Wallet.dormant == False,
                Wallet.is_hft == False
            )
            active_wallets = (await db.execute(stmt)).scalars().all()
            
            if not active_wallets:
                return

            # Also get active users for sandbox mirroring
            user_stmt = select(User)
            users = (await db.execute(user_stmt)).scalars().all()

            for w in active_wallets:
                addr = w.address.lower()
                try:
                    res = await self.client.get(
                        f"{self.data_api_url}/trades",
                        params={"user": addr, "limit": 6}
                    )
                    if res.status_code != 200:
                        continue
                    trades = res.json()
                    if not isinstance(trades, list) or not trades:
                        continue

                    new_trades = []
                    for t in trades:
                        if not isinstance(t, dict):
                            continue
                        ts_raw = t.get("timestamp") or t.get("match_time") or t.get("created_at")
                        if not ts_raw:
                            continue
                        try:
                            ts_sec = float(ts_raw) / 1000.0 if float(ts_raw) > 1e11 else float(ts_raw)
                        except Exception:
                            continue

                        cid = str(t.get("conditionId") or t.get("condition_id") or "")
                        side = str(t.get("side") or "BUY").upper()
                        price = float(t.get("price") or 0.5)
                        size = float(t.get("size") or 0.0)
                        cash = float(t.get("usdcSize") or 0.0) or (size * price)
                        outcome = str(t.get("outcome") or "Yes")
                        asset = str(t.get("asset") or "")
                        trade_key = f"{addr}:{cid}:{side}:{ts_sec}:{price}:{size}"

                        if trade_key in self.seen_trade_keys:
                            continue

                        self.seen_trade_keys.add(trade_key)
                        trade_dt = datetime.fromtimestamp(ts_sec, timezone.utc).replace(tzinfo=None)

                        # If trade is new (occurred recently or after wallet's last recorded trade)
                        if not w.last_trade_at or trade_dt > w.last_trade_at:
                            w.last_trade_at = trade_dt
                            w.dormant = False
                            new_trades.append({
                                "cid": cid,
                                "title": str(t.get("title") or t.get("slug") or "Polymarket Prediction"),
                                "side": side,
                                "price": price,
                                "size": size,
                                "cash": cash,
                                "dt": trade_dt,
                                "outcome": outcome,
                                "asset": asset
                            })

                    # Mirror new trades into ExecutionLogs
                    if new_trades:
                        for nt in new_trades:
                            logger.info(f"🎯 NEW WHALE TRADE DETECTED: {addr[:10]}... {nt['side']} ${nt['cash']:,.2f} @ {nt['price']}")
                            
                            # Create system execution log
                            log = ExecutionLog(
                                source_wallet_address=w.address,
                                market_condition_id=nt["cid"],
                                market_question=nt["title"],
                                side=nt["side"],
                                whale_entry_price=nt["price"],
                                user_fill_price=nt["price"],
                                resolution_outcome=nt["outcome"],
                                onchain_tx_hash=nt["asset"],
                                notional_usd=min(nt["cash"], 500.0),
                                active_basket_size_at_trade=len(active_wallets),
                                is_sandbox=True,
                                status="FILLED",
                                executed_at=nt["dt"]
                            )
                            db.add(log)

                            # If users exist, record copy-trade execution
                            for u in users:
                                user_log = ExecutionLog(
                                    user_id=u.id,
                                    source_wallet_address=w.address,
                                    market_condition_id=nt["cid"],
                                    market_question=nt["title"],
                                    side=nt["side"],
                                    whale_entry_price=nt["price"],
                                    user_fill_price=nt["price"],
                                    resolution_outcome=nt["outcome"],
                                    onchain_tx_hash=nt["asset"],
                                    notional_usd=min(nt["cash"] * 0.05, 100.0),
                                    active_basket_size_at_trade=len(active_wallets),
                                    is_sandbox=True,
                                    status="FILLED",
                                    executed_at=nt["dt"]
                                )
                                db.add(user_log)

                        await db.commit()

                except Exception as w_err:
                    logger.error(f"Error polling live trades for {addr}: {w_err}", exc_info=True)
                    continue
                
                await asyncio.sleep(0.1)

live_trade_mirror = LiveTradeMirrorService()
