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

            # Sells are ALWAYS permitted if we hold an open position from this whale (even if whale was later demoted/blacklisted)
            target_open_buys = []
            if side == "SELL":
                stmt_open_buys = select(ExecutionLog).where(
                    ExecutionLog.market_condition_id == condition_id,
                    ExecutionLog.resolution_outcome == outcome,
                    ExecutionLog.source_wallet_address.ilike(wallet_address),
                    ExecutionLog.side == "BUY",
                    ExecutionLog.status == "FILLED"
                ).order_by(ExecutionLog.executed_at.asc())
                target_open_buys = (await db.execute(stmt_open_buys)).scalars().all()
                
                if not target_open_buys:
                    logger.info(f"🛡️ Position Guard: Whale {addr[:8]} sold '{title[:25]}', but sandbox holds 0 open positions from this whale. Skipping.")
                    return
            else:
                # BUY: Must be an active, approved basket whale
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
                from app.services.event_logger import log_event
                asyncio.create_task(log_event(
                    "TRADE_SKIPPED_CATEGORY",
                    f"Sports trade skipped: {title[:50]}",
                    detail=f"Whale {addr[:10]}... win rate {whale_win_rate:.1f}% < 65% required for Sports category.",
                    severity="warning",
                    related_address=wallet_address,
                    related_market=title,
                ))
                return

            # Rule 2: Execution Delay / Anti-Frontrunning Guard with Directional Slippage Check
            live_p = get_live_price(condition_id, outcome=outcome, asset=asset or tx_hash or "", fallback=price)
            from app.sizing.slippage import check_slippage
            from app.sizing.dynamic_sizer import size_trade
            
            slippage_decision = check_slippage(price, live_p, side=side)
            if slippage_decision != 'EXECUTE_ORDER':
                logger.info(f"⚠️ Slippage Guard: {side} on '{title[:25]}' entry={price:.3f} -> live={live_p:.3f}. Aborting ({slippage_decision}).")
                from app.services.event_logger import log_event
                asyncio.create_task(log_event(
                    "TRADE_SKIPPED_SLIPPAGE",
                    f"Slippage guard: {side} {title[:50]}",
                    detail=f"Live price {live_p:.4f} vs entry {price:.4f} triggered slippage threshold for {side}.",
                    severity="warning",
                    related_address=wallet_address,
                    related_market=title,
                ))
                return

            # For SELLs: Always execute the exit at live market price to guarantee position closure and unlock capital
            effective_fill_price = live_p if (0.001 <= live_p <= 0.999) else price

            # Rule 1: Fee-Aware Expected Value Gate (EV_net > 2.5 * Fee Rate)
            source_whale = next((w for w in active_wallets if w.address.lower() == wallet_address.lower()), None)
            whale_expected_p = (float(source_whale.wilson_lb or source_whale.win_rate_pct or 60.0) / 100.0) if source_whale else 0.60
            expected_edge = max(0.0, whale_expected_p - effective_fill_price) if side == "BUY" else max(0.0, effective_fill_price - (1.0 - whale_expected_p))
            ev_pass, fee_rate, min_edge = calculate_fee_aware_ev_gate(effective_fill_price, title, expected_edge)
            if not ev_pass and expected_edge > 0.02 and side == "BUY":
                logger.info(f"🛑 Fee-Aware EV Gate: Skipping '{title[:25]}' - edge {expected_edge:.3f} < 2.5x fee rate ({min_edge:.3f}).")
                from app.services.event_logger import log_event
                asyncio.create_task(log_event(
                    "TRADE_SKIPPED_EV",
                    f"EV gate: {title[:50]}",
                    detail=f"Edge {expected_edge:.4f} < 2.5× fee rate ({min_edge:.4f}). Category: {category_name}.",
                    severity="warning",
                    related_address=wallet_address,
                    related_market=title,
                ))
                return

            sys_notional = round(min(max(10.0, cash_usd * 0.1 * sizing_multiplier), 350.0), 2)

            # Rule 3: Strict Cash Ceiling Guard (Max Active Open Exposure <= Settled Cash Balance)
            if side == "BUY":
                stmt_active_notional = select(func.sum(ExecutionLog.notional_usd)).where(
                    ExecutionLog.user_id.is_(None),
                    ExecutionLog.status == "FILLED",
                    ExecutionLog.side == "BUY"
                )
                current_open_notional = float((await db.execute(stmt_active_notional)).scalar() or 0.0)
                
                # Fetch settled cash: starting balance + cumulative realized PnL
                stmt_realized_pnl = select(func.sum(ExecutionLog.realized_pnl_usd)).where(
                    ExecutionLog.user_id.is_(None),
                    ExecutionLog.status == "CLOSED"
                )
                total_realized_pnl = float((await db.execute(stmt_realized_pnl)).scalar() or 0.0)
                settled_cash = 10000.0 + total_realized_pnl
                
                free_cash = max(0.0, settled_cash - current_open_notional)
                
                if free_cash < 10.0:
                    logger.info(f"🛑 Cash Limit Guard: Skipping BUY on '{title[:25]}' - Active exposure ${current_open_notional:,.2f} >= Settled Cash ${settled_cash:,.2f} (Free cash: ${free_cash:,.2f}).")
                    from app.services.event_logger import log_event
                    asyncio.create_task(log_event(
                        "TRADE_SKIPPED_CASH_LIMIT",
                        f"Cash limit: {title[:50]}",
                        detail=f"Active capital deployed (${current_open_notional:,.2f}) at 100% capacity of settled cash (${settled_cash:,.2f}). Free cash: ${free_cash:,.2f}.",
                        severity="warning",
                        related_address=wallet_address,
                        related_market=title,
                    ))
                    return
                
                # Adjust sizing to not exceed available free cash
                sys_notional = round(min(sys_notional, free_cash), 2)

            fee_calc = calculate_polymarket_fee(
                notional_usd=sys_notional,
                price=effective_fill_price,
                market_title=title,
                is_maker=False
            )

            # FIFO matching loop for SELL orders
            sys_realized_pnl_val = None
            if side == "SELL" and target_open_buys:
                remaining_sell_notional = sys_notional
                sell_fee_total = float(fee_calc["fee_usd"] or 0.0)
                sell_fee_rate = sell_fee_total / sys_notional if sys_notional > 0 else 0.0
                
                for open_buy in target_open_buys:
                    if remaining_sell_notional <= 0:
                        break
                    buy_notional = float(open_buy.notional_usd or 0.0)
                    orig_buy_price = float(open_buy.user_fill_price or open_buy.whale_entry_price or 0.5)
                    price_ratio = ((effective_fill_price - orig_buy_price) / orig_buy_price) if orig_buy_price > 0 else 0.0
                    
                    if buy_notional <= remaining_sell_notional + 0.01:
                        open_buy.status = "CLOSED"
                        buy_fee = float(open_buy.fee_usd or 0.0)
                        allocated_sell_fee = buy_notional * sell_fee_rate
                        open_buy.realized_pnl_usd = round(buy_notional * price_ratio - (buy_fee + allocated_sell_fee), 2)
                        remaining_sell_notional -= buy_notional
                    else:
                        closed_portion = remaining_sell_notional
                        remaining_portion = round(buy_notional - closed_portion, 2)
                        buy_fee_rate = float(open_buy.fee_usd or 0.0) / buy_notional if buy_notional > 0 else 0.0
                        closed_buy_fee = closed_portion * buy_fee_rate
                        allocated_sell_fee = closed_portion * sell_fee_rate
                        
                        open_buy.status = "CLOSED"
                        open_buy.notional_usd = closed_portion
                        open_buy.fee_usd = round(closed_buy_fee, 4)
                        open_buy.realized_pnl_usd = round(closed_portion * price_ratio - (closed_buy_fee + allocated_sell_fee), 2)
                        
                        split_buy = ExecutionLog(
                            user_id=None,
                            source_wallet_address=open_buy.source_wallet_address,
                            market_condition_id=open_buy.market_condition_id,
                            market_question=open_buy.market_question,
                            event_slug=open_buy.event_slug,
                            icon=open_buy.icon,
                            side="BUY",
                            whale_entry_price=open_buy.whale_entry_price,
                            user_fill_price=open_buy.user_fill_price,
                            resolution_outcome=open_buy.resolution_outcome,
                            onchain_tx_hash=open_buy.onchain_tx_hash,
                            notional_usd=remaining_portion,
                            fee_usd=round(float(open_buy.fee_usd or 0.0) - closed_buy_fee, 4),
                            market_category=open_buy.market_category,
                            active_basket_size_at_trade=open_buy.active_basket_size_at_trade,
                            is_sandbox=True,
                            status="FILLED",
                            realized_pnl_usd=None,
                            executed_at=open_buy.executed_at
                        )
                        db.add(split_buy)
                        remaining_sell_notional = 0.0
                        break

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
                status="CLOSED" if side == "SELL" else "FILLED",
                realized_pnl_usd=sys_realized_pnl_val,
                executed_at=dt
            )
            db.add(sys_log)

            # Copy-trade for individual sandbox users
            for u in users:
                whale_port_val = float(source_whale.all_time_pnl_usd or 50000.0) if source_whale else 50000.0
                whale_trade_val = float(price * notional if notional > 0 else 500.0)
                sizing_res = size_trade(
                    user_balance=float(u.sandbox_balance_usd or 10000.0),
                    risk_profile=str(u.risk_profile or "balanced"),
                    n_active=max(1, len(active_wallets)),
                    whale_trade_value=whale_trade_val,
                    whale_portfolio_value=max(1000.0, whale_port_val),
                    min_order_usd=5.0
                )
                if sizing_res.status == 'SUCCESS':
                    u_notional = sizing_res.value
                else:
                    u_notional = round(min(max(5.0, cash_usd * 0.05 * sizing_multiplier), 150.0), 2)

                u_fee = calculate_polymarket_fee(
                    notional_usd=u_notional,
                    price=effective_fill_price,
                    market_title=title,
                    is_maker=False
                )
                
                u_realized_pnl_val = None
                if side == "SELL":
                    stmt_u_buys = select(ExecutionLog).where(
                        ExecutionLog.user_id == u.id,
                        ExecutionLog.market_condition_id == condition_id,
                        ExecutionLog.resolution_outcome == outcome,
                        ExecutionLog.source_wallet_address.ilike(wallet_address),
                        ExecutionLog.side == "BUY",
                        ExecutionLog.status == "FILLED"
                    ).order_by(ExecutionLog.executed_at.asc())
                    u_open_buys = (await db.execute(stmt_u_buys)).scalars().all()
                    if u_open_buys:
                        remaining_u_sell_notional = u_notional
                        u_sell_fee_total = float(u_fee["fee_usd"] or 0.0)
                        u_sell_fee_rate = u_sell_fee_total / u_notional if u_notional > 0 else 0.0
                        
                        for u_buy in u_open_buys:
                            if remaining_u_sell_notional <= 0:
                                break
                            u_buy_notional = float(u_buy.notional_usd or 0.0)
                            u_orig_price = float(u_buy.user_fill_price or 0.5)
                            u_ratio = ((effective_fill_price - u_orig_price) / u_orig_price) if u_orig_price > 0 else 0.0
                            
                            if u_buy_notional <= remaining_u_sell_notional + 0.01:
                                u_buy.status = "CLOSED"
                                u_buy_fee = float(u_buy.fee_usd or 0.0)
                                u_allocated_sell_fee = u_buy_notional * u_sell_fee_rate
                                u_buy.realized_pnl_usd = round(u_buy_notional * u_ratio - (u_buy_fee + u_allocated_sell_fee), 2)
                                remaining_u_sell_notional -= u_buy_notional
                            else:
                                closed_part = remaining_u_sell_notional
                                rem_part = round(u_buy_notional - closed_part, 2)
                                u_buy_fee_rate = float(u_buy.fee_usd or 0.0) / u_buy_notional if u_buy_notional > 0 else 0.0
                                closed_u_buy_fee = closed_part * u_buy_fee_rate
                                u_allocated_sell_fee = closed_part * u_sell_fee_rate
                                
                                u_buy.status = "CLOSED"
                                u_buy.notional_usd = closed_part
                                u_buy.fee_usd = round(closed_u_buy_fee, 4)
                                u_buy.realized_pnl_usd = round(closed_part * u_ratio - (closed_u_buy_fee + u_allocated_sell_fee), 2)
                                
                                u_split_buy = ExecutionLog(
                                    user_id=u.id,
                                    source_wallet_address=u_buy.source_wallet_address,
                                    market_condition_id=u_buy.market_condition_id,
                                    market_question=u_buy.market_question,
                                    event_slug=u_buy.event_slug,
                                    icon=u_buy.icon,
                                    side="BUY",
                                    whale_entry_price=u_buy.whale_entry_price,
                                    user_fill_price=u_buy.user_fill_price,
                                    resolution_outcome=u_buy.resolution_outcome,
                                    onchain_tx_hash=u_buy.onchain_tx_hash,
                                    notional_usd=rem_part,
                                    fee_usd=round(float(u_buy.fee_usd or 0.0) - closed_u_buy_fee, 4),
                                    market_category=u_buy.market_category,
                                    active_basket_size_at_trade=u_buy.active_basket_size_at_trade,
                                    is_sandbox=True,
                                    status="FILLED",
                                    realized_pnl_usd=None,
                                    executed_at=u_buy.executed_at
                                )
                                db.add(u_split_buy)
                                remaining_u_sell_notional = 0.0
                                break

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
                    status="CLOSED" if side == "SELL" else "FILLED",
                    realized_pnl_usd=u_realized_pnl_val,
                    executed_at=dt
                )
                db.add(user_log)

            # Record running snapshot directly from live poller
            try:
                from app.models import PortfolioSnapshot
                from sqlalchemy import func
                stmt_latest = select(PortfolioSnapshot).where(PortfolioSnapshot.user_id.is_(None)).order_by(PortfolioSnapshot.timestamp.desc()).limit(1)
                latest_snap = (await db.execute(stmt_latest)).scalar_one_or_none()
                
                cur_bal = float(latest_snap.balance) if latest_snap and latest_snap.balance else 10000.0
                cur_pnl = float(latest_snap.total_pnl) if latest_snap and latest_snap.total_pnl is not None else 0.0
                
                if sys_realized_pnl_val is not None:
                    cur_pnl = round(cur_pnl + float(sys_realized_pnl_val), 2)
                    cur_bal = round(cur_bal + float(sys_realized_pnl_val), 2)
                
                stmt_count = select(func.count(ExecutionLog.id)).where(ExecutionLog.user_id.is_(None))
                cur_count = int((await db.execute(stmt_count)).scalar() or 0)

                db.add(PortfolioSnapshot(
                    user_id=None,
                    timestamp=dt,
                    balance=cur_bal,
                    total_pnl=cur_pnl,
                    active_trades_count=cur_count
                ))
                await db.commit()
            except Exception as snap_err:
                logger.debug(f"Poller snapshot note: {snap_err}")

            whale_name = source_whale.name or source_whale.pseudonym or addr[:10] if source_whale else addr[:10]
            logger.info(f"🎯 COPIED WHALE TRADE: {addr[:10]}... {side} ${cash_usd:,.2f} on '{title[:30]}' @ {effective_fill_price:.3f} (Consensus: {consensus.get('is_consensus')})")

            # Log successful trade copy event
            from app.services.event_logger import log_event
            asyncio.create_task(log_event(
                "TRADE_COPIED",
                f"Copied {side} from {whale_name}: {title[:50]}",
                detail=f"${sys_notional:,.2f} @ {effective_fill_price:.4f}. Whale: {whale_name}. Consensus: {'Yes' if consensus.get('is_consensus') else 'No'}. Sniper: {'Yes' if is_sniper else 'No'}.",
                severity="success",
                related_address=wallet_address,
                related_market=title,
            ))

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
