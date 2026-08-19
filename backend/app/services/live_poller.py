import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import httpx
from sqlalchemy import select, func
from app.database import SessionLocal
from app.models import Wallet, ExecutionLog, User
from app.config import settings
from app.services.polymarket_fees import calculate_polymarket_fee

logger = logging.getLogger(__name__)

class LiveTradeMirrorService:
    def __init__(self):
        self.running = False
        self.data_api_url = settings.POLYMARKET_DATA_API_URL
        self.gamma_api_url = settings.GAMMA_API_URL
        self.seen_trade_keys = set()
        self.market_cache = {}
        self.client = None
        self.started_at = datetime.utcnow().timestamp()

    async def start(self):
        self.running = True
        self.client = httpx.AsyncClient(timeout=10.0)
        logger.info("Titan-style Polymarket Live Trade Mirror & Dual-Ingestion Pipeline started.")
        asyncio.create_task(self._poll_loop())

    async def stop(self):
        self.running = False
        if self.client:
            await self.client.aclose()

    async def _resolve_market_metadata(self, cid: str, asset: str = "") -> Dict[str, Any]:
        """Resolves market question, event_slug, icon, and outcome from Gamma API."""
        cache_key = cid or asset
        if cache_key in self.market_cache:
            return self.market_cache[cache_key]

        meta = {
            "title": "Polymarket Prediction",
            "event_slug": "",
            "icon": "",
            "outcome": "Yes"
        }

        if not self.client:
            return meta

        try:
            params = {}
            if cid:
                params["condition_ids"] = cid
            elif asset:
                params["clob_token_ids"] = asset
            
            if params:
                res = await self.client.get(f"{self.gamma_api_url}/markets", params=params)
                if res.status_code == 200:
                    data = res.json()
                    m = data[0] if (isinstance(data, list) and data) else (data if isinstance(data, dict) else None)
                    if m:
                        meta["title"] = m.get("question") or m.get("title") or meta["title"]
                        meta["event_slug"] = m.get("slug") or (m.get("events", [{}])[0].get("slug") if m.get("events") else "")
                        meta["icon"] = m.get("icon") or m.get("image") or ""
                        
                        import json
                        outcomes = m.get("outcomes") or "[]"
                        outcomes = json.loads(outcomes) if isinstance(outcomes, str) else list(outcomes)
                        tokens = m.get("clobTokenIds") or m.get("clob_token_ids") or "[]"
                        tokens = json.loads(tokens) if isinstance(tokens, str) else list(tokens)
                        
                        if asset and tokens:
                            for idx, tok in enumerate(tokens):
                                if str(tok) == str(asset) and idx < len(outcomes):
                                    meta["outcome"] = str(outcomes[idx])
                                    break

                        self.market_cache[cache_key] = meta
        except Exception as e:
            logger.debug(f"Metadata lookup note for {cache_key}: {e}")

        return meta

    async def process_trade_fill(
        self,
        wallet_address: str,
        condition_id: str,
        title: str,
        side: str,
        price: float,
        cash_usd: float,
        dt: datetime,
        outcome: str = "Yes",
        asset: str = "",
        event_slug: str = "",
        icon: str = "",
        tx_hash: Optional[str] = None,
        log_index: Optional[int] = None
    ):
        """Processes a validated whale trade and executes sandbox & user copy orders."""
        addr = wallet_address.lower()

        # If metadata is missing, resolve it from Gamma
        if not event_slug or not icon or title == "Polymarket Prediction":
            resolved = await self._resolve_market_metadata(condition_id, asset)
            if not event_slug:
                event_slug = resolved.get("event_slug", "")
            if not icon:
                icon = resolved.get("icon", "")
            if title == "Polymarket Prediction":
                title = resolved.get("title", title)
            if outcome == "Yes" and resolved.get("outcome") != "Yes":
                outcome = resolved["outcome"]

        async with SessionLocal() as db:
            # Query active basket wallets and users
            stmt_wallets = select(Wallet).where(
                Wallet.status == "active",
                Wallet.dormant == False,
                Wallet.is_hft == False
            )
            active_wallets = (await db.execute(stmt_wallets)).scalars().all()
            basket_addrs = {w.address.lower() for w in active_wallets}

            if addr not in basket_addrs:
                return

            stmt_users = select(User)
            users = (await db.execute(stmt_users)).scalars().all()

            # Check for sniper conviction weighting (e.g. Mr. Ozi / Gold snipers)
            source_whale = next((w for w in active_wallets if w.address.lower() == wallet_address.lower()), None)
            is_sniper = bool(source_whale and (
                source_whale.tier == "gold_sniper" or 
                ((source_whale.win_rate_pct or 0) >= 85.0 and (source_whale.avg_trades_per_day or 5.0) <= 5.0)
            ))
            sniper_multiplier = 1.35 if is_sniper else 1.0

            # Check for multi-whale consensus on this condition
            from app.services.mark_to_market import get_consensus, get_live_price
            consensus = get_consensus(condition_id)
            consensus_multiplier = 1.5 if consensus.get("is_consensus") else 1.0
            sizing_multiplier = consensus_multiplier * sniper_multiplier

            # Category & Fee Evaluation
            from app.services.polymarket_fees import calculate_polymarket_fee, calculate_fee_aware_ev_gate, classify_market_category
            category_name, _ = classify_market_category(title)

            # Rule 3: Category Filter - Require verified >65% win rate for Sports/Esports
            whale_win_rate = float(source_whale.win_rate_pct or 0.0) if source_whale else 0.0
            if category_name == "Sports" and whale_win_rate < 65.0:
                logger.info(f"🛑 Category Gate: Skipping Sports trade on '{title[:25]}' (whale win rate {whale_win_rate:.1f}% < 65% edge threshold).")
                return

            # Rule 2: Execution Delay / Anti-Frontrunning Guard (1.5 ticks / $0.015 max slippage)
            from app.services.mark_to_market import get_consensus, get_live_price
            live_p = get_live_price(condition_id, outcome=outcome, asset=asset or tx_hash or "", fallback=price)
            max_slippage = 0.015  # 1.5 cents ($0.015) max slippage tolerance
            if side == "BUY" and (live_p - price) > max_slippage:
                logger.info(f"⚠️ Anti-Frontrunning Guard: BUY on '{title[:25]}' live={live_p:.3f} > entry={price:.3f} + 0.015. Aborting slippage spike fill.")
                return
            elif side == "SELL" and (price - live_p) > max_slippage:
                logger.info(f"⚠️ Anti-Frontrunning Guard: SELL on '{title[:25]}' live={live_p:.3f} < entry={price:.3f} - 0.015. Aborting slippage spike fill.")
                return

            effective_fill_price = live_p if (0.01 <= live_p <= 0.99) else price

            # Rule 1: Fee-Aware Expected Value Gate (EV_net > 2.5 * Fee Rate)
            expected_edge = abs(effective_fill_price - 0.5)
            ev_pass, fee_rate, min_edge = calculate_fee_aware_ev_gate(effective_fill_price, title, expected_edge)
            if not ev_pass and expected_edge > 0.02:
                logger.info(f"🛑 Fee-Aware EV Gate: Skipping '{title[:25]}' - edge {expected_edge:.3f} < 2.5x fee rate ({min_edge:.3f}).")
                return

            sys_notional = round(min(max(10.0, cash_usd * 0.1 * sizing_multiplier), 350.0), 2)
            fee_calc = calculate_polymarket_fee(
                notional_usd=sys_notional,
                price=effective_fill_price,
                market_title=title,
                is_maker=False
            )

            # System execution log
            sys_log = ExecutionLog(
                source_wallet_address=wallet_address,
                market_condition_id=condition_id,
                market_question=title,
                event_slug=event_slug,
                icon=icon,
                side=side,
                whale_entry_price=price,
                user_fill_price=effective_fill_price,
                resolution_outcome=outcome,
                onchain_tx_hash=asset or tx_hash,
                notional_usd=sys_notional,
                fee_usd=fee_calc["fee_usd"],
                market_category=fee_calc["category"],
                active_basket_size_at_trade=len(active_wallets),
                is_sandbox=True,
                status="FILLED",
                executed_at=dt
            )
            db.add(sys_log)

            # Copy-trade for individual sandbox users
            for u in users:
                u_notional = round(min(max(5.0, cash_usd * 0.05 * sizing_multiplier), 150.0), 2)
                u_fee = calculate_polymarket_fee(
                    notional_usd=u_notional,
                    price=effective_fill_price,
                    market_title=title,
                    is_maker=False
                )
                user_log = ExecutionLog(
                    user_id=u.id,
                    source_wallet_address=wallet_address,
                    market_condition_id=condition_id,
                    market_question=title,
                    event_slug=event_slug,
                    icon=icon,
                    side=side,
                    whale_entry_price=price,
                    user_fill_price=effective_fill_price,
                    resolution_outcome=outcome,
                    onchain_tx_hash=asset or tx_hash,
                    notional_usd=u_notional,
                    fee_usd=u_fee["fee_usd"],
                    market_category=u_fee["category"],
                    active_basket_size_at_trade=len(active_wallets),
                    is_sandbox=True,
                    status="FILLED",
                    executed_at=dt
                )
                db.add(user_log)

            await db.commit()
            logger.info(f"🎯 COPIED WHALE TRADE: {addr[:10]}... {side} ${cash_usd:,.2f} on '{title[:30]}' @ {effective_fill_price:.3f} (Consensus: {consensus.get('is_consensus')})")

    async def process_onchain_signal(
        self,
        wallet_address: str,
        side: str,
        asset_id: str,
        amount_filled: str,
        price_str: str,
        tx_hash: str,
        log_index: int,
        block_number: int,
        timestamp_ms: Optional[int] = None
    ):
        """Handler for on-chain Envio HyperSync events."""
        ts_sec = (timestamp_ms / 1000.0) if timestamp_ms else datetime.utcnow().timestamp()
        
        # Real-time guard
        if ts_sec < self.started_at:
            return

        trade_key = f"{wallet_address.lower()}:{asset_id}:{tx_hash}:{log_index}"
        if trade_key in self.seen_trade_keys:
            return
        self.seen_trade_keys.add(trade_key)

        try:
            price = float(price_str) if price_str and float(price_str) > 0 else 0.5
            amount = float(amount_filled) / 1e6 if float(amount_filled) > 1e10 else float(amount_filled)
            cash_usd = max(amount * price, 20.0)
            dt = datetime.fromtimestamp(ts_sec, timezone.utc).replace(tzinfo=None)

            await self.process_trade_fill(
                wallet_address=wallet_address,
                condition_id="", # will resolve from asset_id
                title="Polymarket Prediction",
                side=side.upper(),
                price=price,
                cash_usd=cash_usd,
                dt=dt,
                asset=asset_id,
                tx_hash=tx_hash,
                log_index=log_index
            )
        except Exception as e:
            logger.error(f"Error executing on-chain signal: {e}", exc_info=True)

    async def _poll_loop(self):
        while self.running:
            try:
                await self._poll_active_whales()
            except Exception as e:
                logger.error(f"Error in live whale polling loop: {e}", exc_info=True)
            await asyncio.sleep(2.5)

    async def _poll_active_whales(self):
        async with SessionLocal() as db:
            stmt = select(Wallet).where(
                Wallet.status == "active",
                Wallet.dormant == False,
                Wallet.is_hft == False
            )
            active_wallets = (await db.execute(stmt)).scalars().all()
            
            if not active_wallets:
                return

            for w in active_wallets:
                addr = w.address.lower()
                try:
                    res = await self.client.get(
                        f"{self.data_api_url}/trades",
                        params={"user": addr, "limit": 50}
                    )
                    if res.status_code != 200:
                        continue
                    trades = res.json()
                    if not isinstance(trades, list) or not trades:
                        continue

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
                        tx_hash = str(t.get("transactionHash") or t.get("id") or "")

                        trade_key = f"{addr}:{cid}:{side}:{ts_sec}:{price:.4f}:{size:.2f}:{tx_hash}"

                        # 1. Real-time Live Guard: Skip trades that occurred before server start
                        if ts_sec < self.started_at:
                            self.seen_trade_keys.add(trade_key)
                            continue

                        # 2. Strict Price Boundary Guard (0.04 <= price <= 0.96)
                        if price < 0.04 or price > 0.96:
                            self.seen_trade_keys.add(trade_key)
                            continue

                        if trade_key in self.seen_trade_keys:
                            continue
                        self.seen_trade_keys.add(trade_key)

                        trade_dt = datetime.fromtimestamp(ts_sec, timezone.utc).replace(tzinfo=None)

                        if not w.last_trade_at or trade_dt > w.last_trade_at:
                            w.last_trade_at = trade_dt
                            w.dormant = False

                        await self.process_trade_fill(
                            wallet_address=w.address,
                            condition_id=cid,
                            title=str(t.get("title") or t.get("slug") or "Polymarket Prediction"),
                            side=side,
                            price=price,
                            cash_usd=cash,
                            dt=trade_dt,
                            outcome=outcome,
                            asset=asset,
                            event_slug=str(t.get("eventSlug") or t.get("event_slug") or t.get("slug") or ""),
                            icon=str(t.get("icon") or t.get("image") or ""),
                            tx_hash=tx_hash
                        )

                except Exception as w_err:
                    logger.error(f"Error polling live trades for {addr}: {w_err}", exc_info=True)
                    continue
                
                await asyncio.sleep(0.05)

live_trade_mirror = LiveTradeMirrorService()
