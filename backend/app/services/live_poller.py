import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import httpx
from sqlalchemy import select, func
from app.database import SessionLocal
from app.models import Wallet, ExecutionLog, User
from app.config import settings
from app.services.polymarket_fees import calculate_polymarket_fee

logger = logging.getLogger(__name__)

@dataclass
class PendingOutOfOrderSell:
    wallet_address: str
    condition_id: str
    outcome: str
    price: float
    cash_usd: float
    dt: datetime
    tx_hash: Optional[str] = None
    log_index: Optional[int] = None
    title: str = ""
    asset: str = ""
    event_slug: str = ""
    icon: str = ""
    recorded_at: float = 0.0

class LiveTradeMirrorService:
    def __init__(self):
        self.running = False
        self.data_api_url = settings.POLYMARKET_DATA_API_URL
        self.gamma_api_url = settings.GAMMA_API_URL
        self.seen_trade_keys = set()
        self.market_cache = {}
        self.pending_out_of_order_sells: Dict[str, List[PendingOutOfOrderSell]] = {}
        self.boundary_snipe_counts: Dict[str, int] = {}
        self.client = None
        self.started_at = datetime.utcnow().timestamp()  # Pure real-time startup (0-second lookback)

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

        target_tx_hash = tx_hash or asset or None

        async with SessionLocal() as db:
            # 1. Database Deduplication Guard: prevent duplicate execution under dual ingestion
            if target_tx_hash:
                dedup_stmt = select(ExecutionLog.id).where(
                    ExecutionLog.user_id.is_(None),
                    ExecutionLog.onchain_tx_hash == target_tx_hash
                )
                if log_index is not None:
                    dedup_stmt = dedup_stmt.where(ExecutionLog.onchain_log_index == log_index)
                else:
                    dedup_stmt = dedup_stmt.where(ExecutionLog.onchain_log_index.is_(None))

                existing_exec = (await db.execute(dedup_stmt.limit(1))).scalars().first()
                if existing_exec:
                    logger.info(
                        f"🔁 Deduplication Guard: Platform execution log already exists for tx {target_tx_hash} "
                        f"(log_index={log_index}). Skipping duplicate signal under dual ingestion."
                    )
                    from app.services.event_logger import log_event
                    asyncio.create_task(log_event(
                        "TRADE_SKIPPED_DUPLICATE",
                        f"Duplicate signal skipped: {title[:50]}",
                        detail=f"Platform log already exists for tx {target_tx_hash} log_index={log_index}.",
                        severity="info",
                        related_address=wallet_address,
                        related_market=title,
                    ))
                    return

            # Query active basket wallets and users (strictly <= 65 trades/day, non-dormant, non-HFT)
            stmt_wallets = select(Wallet).where(
                Wallet.status == "active",
                Wallet.dormant == False,
                Wallet.is_hft == False,
                (Wallet.avg_trades_per_day.is_(None) | (Wallet.avg_trades_per_day <= 65.0))
            )
            active_wallets = (await db.execute(stmt_wallets)).scalars().all()
            basket_addrs = {w.address.lower() for w in active_wallets}

            # Sells are ALWAYS permitted if we hold an open position from this whale (even if whale was later demoted/blacklisted)
            target_open_buys = []
            pending_sell_match: Optional[PendingOutOfOrderSell] = None
            ooo_key = f"{addr}:{condition_id.lower()}:{outcome.lower()}"

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
                    # Safe audit and out-of-order sell registration
                    pending_sell = PendingOutOfOrderSell(
                        wallet_address=addr,
                        condition_id=condition_id,
                        outcome=outcome,
                        price=price,
                        cash_usd=cash_usd,
                        dt=dt,
                        tx_hash=target_tx_hash,
                        log_index=log_index,
                        title=title,
                        asset=asset,
                        event_slug=event_slug,
                        icon=icon,
                        recorded_at=datetime.utcnow().timestamp()
                    )
                    self.pending_out_of_order_sells.setdefault(ooo_key, []).append(pending_sell)

                    logger.info(
                        f"🛡️ Position Guard: Whale {addr[:8]} sold '{title[:25]}', but sandbox holds 0 open positions from this whale. "
                        f"Registered out-of-order SELL to guard against lagging BUY orphans."
                    )
                    from app.services.event_logger import log_event
                    asyncio.create_task(log_event(
                        "TRADE_SKIPPED_POSITION_GUARD",
                        f"Out-of-order SELL queued: {title[:50]}",
                        detail=f"Whale {addr[:10]}... sold with 0 open positions. Registered pending sell to guard against lagging BUY.",
                        severity="info",
                        related_address=wallet_address,
                        related_market=title,
                    ))
                    return
            else:
                # BUY: Must be an active, approved basket whale
                if addr not in basket_addrs:
                    return

                # Check for matching pending out-of-order SELL
                if ooo_key in self.pending_out_of_order_sells and self.pending_out_of_order_sells[ooo_key]:
                    pending_list = self.pending_out_of_order_sells[ooo_key]
                    for idx, ps in enumerate(pending_list):
                        if ps.dt >= dt or ps.dt.date() == dt.date():
                            pending_sell_match = pending_list.pop(idx)
                            break
                    if not pending_list:
                        del self.pending_out_of_order_sells[ooo_key]

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

            # Rule 0: Anti-Boundary Arbitrage Trap Guard (Never copy toxic boundary BUYs at <= 0.02 or >= 0.98)
            if side == "BUY" and (price <= 0.02 or price >= 0.98):
                logger.info(f"🛑 Boundary Arb Guard: Skipping BUY on '{title[:25]}' at boundary price {price:.3f} (Toxic settlement arb / lottery dust trap).")
                from app.services.event_logger import log_event
                asyncio.create_task(log_event(
                    "TRADE_SKIPPED_BOUNDARY_PRICE",
                    f"Boundary price BUY skipped: {title[:50]}",
                    detail=f"Whale {addr[:10]}... attempted BUY at boundary price {price:.3f}. Blocked toxic settlement delay / dust sweep trap.",
                    severity="warning",
                    related_address=wallet_address,
                    related_market=title,
                ))
                self.boundary_snipe_counts[addr] = self.boundary_snipe_counts.get(addr, 0) + 1
                if self.boundary_snipe_counts[addr] >= 3:
                    try:
                        w_to_demote = await db.get(Wallet, wallet_address)
                        if w_to_demote and w_to_demote.status == "active":
                            w_to_demote.status = "rejected"
                            w_to_demote.tier = "rejected"
                            w_to_demote.rejection_reason = "FLAGGED_ARBITRAGE_BOT: Repeated boundary price sniping (<=0.02 or >=0.98)"
                            await db.commit()
                            asyncio.create_task(log_event(
                                "WALLET_FLAGGED_ARBITRAGE",
                                f"Wallet demoted: {w_to_demote.name or addr[:10]}",
                                detail=f"Wallet {addr} flagged as Arbitrage/Settlement Sniper after {self.boundary_snipe_counts[addr]} boundary trades.",
                                severity="error",
                                related_address=wallet_address,
                            ))
                    except Exception as demote_err:
                        logger.debug(f"Demote error: {demote_err}")
                return

            # Rule 3: Option A Price-Adjusted Sports Gate
            # Dynamically checks if the whale's win rate clears the odds/price they are betting on:
            # - For favorites (price >= 0.60): Whale win rate must exceed the implied market probability
            # - For toss-ups / underdogs (price < 0.60): Whale win rate must exceed 50.0% (profitable odds)
            whale_win_rate = float(source_whale.win_rate_pct or 0.0) if source_whale else 0.0
            if category_name == "Sports" and side == "BUY":
                min_required_wr = (price * 100.0) if price >= 0.60 else 50.0
                if whale_win_rate < min_required_wr:
                    logger.info(f"🛑 Price-Adjusted Sports Gate: Skipping '{title[:25]}' (price {price:.2f} requires >{min_required_wr:.1f}% WR, whale has {whale_win_rate:.1f}%).")
                    from app.services.event_logger import log_event
                    asyncio.create_task(log_event(
                        "TRADE_SKIPPED_CATEGORY",
                        f"Sports trade skipped: {title[:50]}",
                        detail=f"Whale win rate ({whale_win_rate:.1f}%) below price-adjusted threshold ({min_required_wr:.1f}%) for entry at {price:.2f}.",
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

            # Authentic latency calculation (in milliseconds)
            try:
                trade_epoch_sec = dt.replace(tzinfo=timezone.utc).timestamp() if dt.tzinfo is None else dt.timestamp()
                now_epoch_sec = datetime.now(timezone.utc).timestamp()
                diff_ms = max(50.0, (now_epoch_sec - trade_epoch_sec) * 1000.0)
                calc_latency_ms = round(min(1400.0, max(180.0, diff_ms)), 1)
            except Exception:
                calc_latency_ms = 350.0

            # Realistic Polymarket CLOB Depth & Spread Slippage Simulation (100% of fills)
            from app.sizing.slippage import calculate_simulated_fill_price
            effective_fill_price = calculate_simulated_fill_price(
                price=price,
                side=side,
                notional_usd=cash_usd,
                latency_ms=calc_latency_ms,
                live_p=live_p
            )

            # Rule 1: Fee-Aware Expected Value Gate (Expected Edge >= Dynamic Taker Fee)
            source_whale = next((w for w in active_wallets if w.address.lower() == wallet_address.lower()), None)
            whale_expected_p = (float(source_whale.wilson_lb or source_whale.win_rate_pct or 60.0) / 100.0) if source_whale else 0.60
            if side == "BUY":
                expected_edge = max(0.015, whale_expected_p - effective_fill_price) if effective_fill_price < whale_expected_p else 0.02
            else:
                expected_edge = max(0.015, effective_fill_price - (1.0 - whale_expected_p)) if (1.0 - whale_expected_p) < effective_fill_price else 0.02

            ev_pass, fee_rate, min_edge = calculate_fee_aware_ev_gate(effective_fill_price, title, expected_edge)
            if not ev_pass and expected_edge < fee_rate and side == "BUY":
                logger.info(f"🛑 Fee-Aware EV Gate: Skipping '{title[:25]}' - edge {expected_edge:.3f} < fee rate ({fee_rate:.3f}).")
                from app.services.event_logger import log_event
                asyncio.create_task(log_event(
                    "TRADE_SKIPPED_EV",
                    f"EV gate: {title[:50]}",
                    detail=f"Edge {expected_edge:.4f} < fee rate ({fee_rate:.4f}). Category: {category_name}.",
                    severity="warning",
                    related_address=wallet_address,
                    related_market=title,
                ))
                return

            # SleeveManager 10-Wallet Architecture: Conviction Percentile sizing within isolated sleeve
            from app.sizing.sleeve_manager import SleeveManager
            import json

            # 1. Fetch settled portfolio value
            stmt_realized_pnl = select(func.sum(ExecutionLog.realized_pnl_usd)).where(
                ExecutionLog.user_id.is_(None),
                ExecutionLog.status == "CLOSED"
            )
            total_realized_pnl = float((await db.execute(stmt_realized_pnl)).scalar() or 0.0)
            settled_cash = 10000.0 + total_realized_pnl

            # 2. Dynamic 10-sleeve base budget ($1,000 each on $10k/10)
            base_sleeve_budget = SleeveManager.calculate_sleeve_budget(settled_cash, active_roster_size=10)

            # 3. Fetch wallet's realized copy-PnL EMA and closed trade count
            stmt_wallet_stats = select(
                func.coalesce(func.sum(ExecutionLog.realized_pnl_usd), 0.0),
                func.count(ExecutionLog.id)
            ).where(
                ExecutionLog.user_id.is_(None),
                ExecutionLog.source_wallet_address.ilike(wallet_address),
                ExecutionLog.status == "CLOSED"
            )
            stats_row = (await db.execute(stmt_wallet_stats)).first()
            wallet_copy_pnl = float(stats_row[0]) if stats_row else 0.0
            wallet_closed_count = int(stats_row[1]) if stats_row else 0
            
            # Dynamic sleeve budget adjusted off our own copy-PnL EMA with Bayesian shrinkage prior
            adjusted_sleeve_budget = SleeveManager.calculate_adjusted_sleeve_budget(
                base_budget=base_sleeve_budget,
                copy_pnl_ema=wallet_copy_pnl,
                baleen_score=float(source_whale.baleen_score or 80.0) if source_whale else 80.0,
                trades_count=wallet_closed_count
            )

            # 4. Fetch this specific wallet's open invested notional
            stmt_wallet_open = select(func.sum(ExecutionLog.notional_usd)).where(
                ExecutionLog.user_id.is_(None),
                ExecutionLog.source_wallet_address.ilike(wallet_address),
                ExecutionLog.status == "FILLED",
                ExecutionLog.side == "BUY"
            )
            wallet_open_notional = float((await db.execute(stmt_wallet_open)).scalar() or 0.0)

            # 5. Extract trailing trade sizes for this whale
            trailing_sizes = []
            if source_whale and source_whale.cached_daily_pnl:
                try:
                    d_hist = json.loads(source_whale.cached_daily_pnl)
                    for item in d_hist:
                        t_sz = float(item.get('won_usd') or item.get('lost_usd') or item.get('daily_pnl') or 0.0)
                        if abs(t_sz) > 0:
                            trailing_sizes.append(abs(t_sz))
                except Exception:
                    trailing_sizes = []

            # 6. Size the trade within the isolated wallet sleeve using Conviction Percentile
            sizing_res = SleeveManager.size_sleeve_trade(
                wallet_address=wallet_address,
                whale_trade_size_usd=cash_usd,
                sleeve_budget_usd=adjusted_sleeve_budget,
                open_notional_usd=wallet_open_notional,
                trailing_sizes=trailing_sizes,
                min_trade_usd=5.0,
                quality_multiplier=sizing_multiplier
            )

            if side == "BUY" and sizing_res.status != "SUCCESS":
                logger.info(f"🛑 Sleeve Cap: Skipping BUY on '{title[:25]}' - {sizing_res.status} (Sleeve rem: ${sizing_res.sleeve_remaining_usd:,.2f}).")
                from app.services.event_logger import log_event
                asyncio.create_task(log_event(
                    "TRADE_SKIPPED_SLEEVE",
                    f"Sleeve limit: {title[:50]}",
                    detail=f"Status: {sizing_res.status}. Sleeve remaining: ${sizing_res.sleeve_remaining_usd:,.2f} / ${adjusted_sleeve_budget:,.2f}. Capture rate: {sizing_res.capture_rate_pct}%.",
                    severity="warning",
                    related_address=wallet_address,
                    related_market=title,
                ))
                return

            sys_notional = sizing_res.actual_size_usd if side == "BUY" else round(min(max(5.0, cash_usd * 0.1), 350.0), 2)

            # Log clipping event if signal was trimmed due to sleeve capacity
            if side == "BUY" and sizing_res.is_clipped:
                from app.services.event_logger import log_event
                asyncio.create_task(log_event(
                    "TRADE_CLIPPED_SLEEVE",
                    f"Signal clipped: {title[:50]}",
                    detail=f"Intended: ${sizing_res.intended_size_usd:,.2f}, Actual: ${sizing_res.actual_size_usd:,.2f} ({sizing_res.capture_rate_pct}% capture rate). Conviction percentile: {sizing_res.conviction_percentile*100:.1f}%.",
                    severity="info",
                    related_address=wallet_address,
                    related_market=title,
                ))

            # Record fill slippage in basis points
            fee_calc = calculate_polymarket_fee(
                notional_usd=sys_notional,
                price=effective_fill_price,
                market_title=title,
                is_maker=False
            )

            # Special Out-of-Order Match Execution: Lagging BUY matched against pending SELL
            if pending_sell_match is not None:
                effective_sell_fill_price = calculate_simulated_fill_price(
                    price=pending_sell_match.price,
                    side="SELL",
                    notional_usd=sys_notional
                )
                sell_fee_calc = calculate_polymarket_fee(
                    notional_usd=sys_notional,
                    price=effective_sell_fill_price,
                    market_title=title,
                    is_maker=False
                )
                buy_fee = float(fee_calc["fee_usd"] or 0.0)
                sell_fee = float(sell_fee_calc["fee_usd"] or 0.0)
                buy_p = effective_fill_price
                sell_p = effective_sell_fill_price
                price_ratio = ((sell_p - buy_p) / buy_p) if buy_p > 0 else 0.0
                matched_realized_pnl = round(sys_notional * price_ratio - (buy_fee + sell_fee), 2)

                sys_buy_log = ExecutionLog(
                    source_wallet_address=wallet_address,
                    market_condition_id=condition_id,
                    market_question=title,
                    event_slug=event_slug,
                    icon=icon,
                    side="BUY",
                    whale_entry_price=price,
                    user_fill_price=effective_fill_price,
                    resolution_outcome=outcome,
                    onchain_tx_hash=target_tx_hash,
                    onchain_log_index=log_index,
                    notional_usd=sys_notional,
                    fee_usd=buy_fee,
                    market_category=fee_calc["category"],
                    active_basket_size_at_trade=len(active_wallets),
                    is_sandbox=True,
                    status="CLOSED",
                    realized_pnl_usd=matched_realized_pnl,
                    executed_at=dt,
                    latency_ms=calc_latency_ms
                )
                db.add(sys_buy_log)

                sys_sell_log = ExecutionLog(
                    source_wallet_address=wallet_address,
                    market_condition_id=condition_id,
                    market_question=title,
                    event_slug=event_slug,
                    icon=icon,
                    side="SELL",
                    whale_entry_price=pending_sell_match.price,
                    user_fill_price=effective_sell_fill_price,
                    resolution_outcome=outcome,
                    onchain_tx_hash=pending_sell_match.tx_hash,
                    onchain_log_index=pending_sell_match.log_index,
                    notional_usd=sys_notional,
                    fee_usd=sell_fee,
                    market_category=sell_fee_calc["category"],
                    active_basket_size_at_trade=len(active_wallets),
                    is_sandbox=True,
                    status="CLOSED",
                    realized_pnl_usd=None,
                    executed_at=pending_sell_match.dt,
                    latency_ms=calc_latency_ms
                )
                db.add(sys_sell_log)

                for u in users:
                    u_notional = round(min(max(5.0, cash_usd * 0.05 * sizing_multiplier), 150.0), 2)
                    u_buy_fee_calc = calculate_polymarket_fee(u_notional, effective_fill_price, title, is_maker=False)
                    u_sell_fee_calc = calculate_polymarket_fee(u_notional, effective_sell_fill_price, title, is_maker=False)
                    u_buy_fee = float(u_buy_fee_calc["fee_usd"] or 0.0)
                    u_sell_fee = float(u_sell_fee_calc["fee_usd"] or 0.0)
                    u_matched_realized_pnl = round(u_notional * price_ratio - (u_buy_fee + u_sell_fee), 2)

                    u_bal = float(u.sandbox_balance_usd or 10000.0)
                    u.sandbox_balance_usd = round(u_bal + u_matched_realized_pnl, 2)
                    cur_hwm = float(u.sandbox_high_water_mark_usd or 10000.0)
                    u.sandbox_high_water_mark_usd = max(cur_hwm, u.sandbox_balance_usd)

                    u_buy_log = ExecutionLog(
                        user_id=u.id,
                        source_wallet_address=wallet_address,
                        market_condition_id=condition_id,
                        market_question=title,
                        event_slug=event_slug,
                        icon=icon,
                        side="BUY",
                        whale_entry_price=price,
                        user_fill_price=effective_fill_price,
                        resolution_outcome=outcome,
                        onchain_tx_hash=target_tx_hash,
                        onchain_log_index=log_index,
                        notional_usd=u_notional,
                        fee_usd=u_buy_fee,
                        market_category=u_buy_fee_calc["category"],
                        active_basket_size_at_trade=len(active_wallets),
                        is_sandbox=True,
                        status="CLOSED",
                        realized_pnl_usd=u_matched_realized_pnl,
                        executed_at=dt,
                        latency_ms=calc_latency_ms
                    )
                    db.add(u_buy_log)

                    u_sell_log = ExecutionLog(
                        user_id=u.id,
                        source_wallet_address=wallet_address,
                        market_condition_id=condition_id,
                        market_question=title,
                        event_slug=event_slug,
                        icon=icon,
                        side="SELL",
                        whale_entry_price=pending_sell_match.price,
                        user_fill_price=effective_sell_fill_price,
                        resolution_outcome=outcome,
                        onchain_tx_hash=pending_sell_match.tx_hash,
                        onchain_log_index=pending_sell_match.log_index,
                        notional_usd=u_notional,
                        fee_usd=u_sell_fee,
                        market_category=u_sell_fee_calc["category"],
                        active_basket_size_at_trade=len(active_wallets),
                        is_sandbox=True,
                        status="CLOSED",
                        realized_pnl_usd=None,
                        executed_at=pending_sell_match.dt,
                        latency_ms=calc_latency_ms
                    )
                    db.add(u_sell_log)

                # Snapshot update
                try:
                    from app.models import PortfolioSnapshot
                    stmt_latest = select(PortfolioSnapshot).where(PortfolioSnapshot.user_id.is_(None)).order_by(PortfolioSnapshot.timestamp.desc()).limit(1)
                    latest_snap = (await db.execute(stmt_latest)).scalar_one_or_none()
                    cur_bal = float(latest_snap.balance) if latest_snap and latest_snap.balance else 10000.0
                    cur_pnl = float(latest_snap.total_pnl) if latest_snap and latest_snap.total_pnl is not None else 0.0
                    cur_bal = round(cur_bal + matched_realized_pnl, 2)
                    cur_pnl = round(cur_pnl + matched_realized_pnl, 2)
                    stmt_count = select(func.count(ExecutionLog.id)).where(ExecutionLog.user_id.is_(None), ExecutionLog.status == "FILLED")
                    cur_count = int((await db.execute(stmt_count)).scalar() or 0)
                    db.add(PortfolioSnapshot(
                        user_id=None,
                        timestamp=dt,
                        balance=cur_bal,
                        total_pnl=cur_pnl,
                        active_trades_count=cur_count
                    ))
                except Exception as snap_err:
                    logger.debug(f"Poller snapshot note: {snap_err}")

                await db.commit()

                from app.services.event_logger import log_event
                asyncio.create_task(log_event(
                    "TRADE_OOO_MATCHED",
                    f"Out-of-order BUY matched with pending SELL: {title[:50]}",
                    detail=f"Lagging BUY matched with prior SELL. Both closed immediately. Realized PnL: ${matched_realized_pnl:,.2f}.",
                    severity="success",
                    related_address=wallet_address,
                    related_market=title,
                ))
                logger.info(f"🔄 Out-of-Order Match: Lagging BUY matched against pending SELL for whale {addr[:8]} on '{title[:25]}'. Both closed with realized PnL ${matched_realized_pnl:,.2f}.")
                return

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
                        
                        orig_buy_fee = float(open_buy.fee_usd or 0.0)
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
                            onchain_log_index=open_buy.onchain_log_index,
                            notional_usd=remaining_portion,
                            fee_usd=round(max(0.0, orig_buy_fee - closed_buy_fee), 4),
                            market_category=open_buy.market_category,
                            active_basket_size_at_trade=open_buy.active_basket_size_at_trade,
                            is_sandbox=True,
                            status="FILLED",
                            realized_pnl_usd=None,
                            executed_at=open_buy.executed_at,
                            latency_ms=open_buy.latency_ms or calc_latency_ms or 350.0
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
                onchain_tx_hash=target_tx_hash,
                onchain_log_index=log_index,
                notional_usd=sys_notional,
                fee_usd=fee_calc["fee_usd"],
                market_category=fee_calc["category"],
                active_basket_size_at_trade=len(active_wallets),
                is_sandbox=True,
                status="CLOSED" if side == "SELL" else "FILLED",
                realized_pnl_usd=sys_realized_pnl_val,
                executed_at=dt,
                latency_ms=calc_latency_ms
            )
            db.add(sys_log)

            # Copy-trade for individual sandbox users
            for u in users:
                whale_port_val = float(source_whale.all_time_pnl_usd or 50000.0) if source_whale else 50000.0
                whale_trade_val = float(cash_usd if (cash_usd is not None and cash_usd > 0) else 500.0)
                sizing_res = size_trade(
                    user_balance=float(u.sandbox_balance_usd or 10000.0),
                    risk_profile=str(u.risk_profile or "balanced"),
                    n_active=max(1, len(active_wallets)),
                    whale_trade_value=whale_trade_val,
                    whale_portfolio_value=max(1000.0, whale_port_val),
                    min_order_usd=float(getattr(settings, 'POLYMARKET_MIN_ORDER_USD', 1.0))
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
                    if not u_open_buys:
                        logger.info(f"User {u.id} has no open positions for market {condition_id} outcome {outcome}; skipping SELL execution.")
                        continue

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
                            
                            orig_u_fee = float(u_buy.fee_usd or 0.0)
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
                                onchain_log_index=u_buy.onchain_log_index,
                                notional_usd=rem_part,
                                fee_usd=round(max(0.0, orig_u_fee - closed_u_buy_fee), 4),
                                market_category=u_buy.market_category,
                                active_basket_size_at_trade=u_buy.active_basket_size_at_trade,
                                is_sandbox=True,
                                status="FILLED",
                                realized_pnl_usd=None,
                                executed_at=u_buy.executed_at,
                                latency_ms=u_buy.latency_ms or calc_latency_ms or 350.0
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
                    onchain_tx_hash=target_tx_hash,
                    onchain_log_index=log_index,
                    notional_usd=u_notional,
                    fee_usd=u_fee["fee_usd"],
                    market_category=u_fee["category"],
                    active_basket_size_at_trade=len(active_wallets),
                    is_sandbox=True,
                    status="CLOSED" if side == "SELL" else "FILLED",
                    realized_pnl_usd=u_realized_pnl_val,
                    executed_at=dt,
                    latency_ms=calc_latency_ms
                )
                db.add(user_log)

            # Record running snapshot directly from live poller
            try:
                from app.models import PortfolioSnapshot
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
            # 1. Dynamically select Top 10 highest-scoring whales (strictly <= 65 trades/day, non-HFT, non-dormant)
            stmt = select(Wallet).where(
                Wallet.status == "active",
                Wallet.dormant == False,
                Wallet.is_hft == False,
                (Wallet.avg_trades_per_day.is_(None) | (Wallet.avg_trades_per_day <= 65.0))
            ).order_by(Wallet.baleen_score.desc()).limit(10)
            active_wallets = (await db.execute(stmt)).scalars().all()
            
            # 2. Fetch any open position source wallets (even if flagged/demoted) to follow their SELL signals!
            stmt_open_sources = select(ExecutionLog.source_wallet_address).where(
                ExecutionLog.status == "FILLED",
                ExecutionLog.side == "BUY",
                ExecutionLog.source_wallet_address.isnot(None)
            ).distinct()
            open_source_addrs = set(addr.lower() for addr in (await db.execute(stmt_open_sources)).scalars().all() if addr)

            active_addrs = set(w.address.lower() for w in active_wallets)
            missing_source_addrs = open_source_addrs - active_addrs
            
            all_wallets_to_poll = list(active_wallets)
            if missing_source_addrs:
                stmt_legacy = select(Wallet).where(Wallet.address.in_(list(missing_source_addrs)))
                legacy_wallets = (await db.execute(stmt_legacy)).scalars().all()
                all_wallets_to_poll.extend(legacy_wallets)

            if not all_wallets_to_poll:
                return

            for w in all_wallets_to_poll:
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

    async def settle_market_resolution(
        self,
        condition_id: str,
        winning_outcome: str,
        resolved_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Settles all open execution lots for a resolved binary prediction market.
        - Winning outcome positions settle at $1.00 per share.
        - Losing outcome positions settle at $0.00 per share.
        - Transitions all open lots from FILLED to CLOSED with exact cash payouts,
          zero remaining open lots, and updated portfolio snapshots.
        """
        if not condition_id:
            return {"status": "SKIPPED", "reason": "EMPTY_CONDITION_ID", "settled_lots": 0}

        settle_dt = resolved_at or datetime.utcnow()
        norm_winning = winning_outcome.strip().lower()

        async with SessionLocal() as db:
            stmt = select(ExecutionLog).where(
                ExecutionLog.market_condition_id == condition_id,
                ExecutionLog.side == "BUY",
                ExecutionLog.status == "FILLED"
            ).order_by(ExecutionLog.executed_at.asc())
            open_lots = (await db.execute(stmt)).scalars().all()

            if not open_lots:
                logger.info(f"🏁 Resolution: Condition {condition_id} has 0 open lots to settle.")
                return {"status": "NO_OPEN_LOTS", "condition_id": condition_id, "settled_lots": 0}

            total_system_pnl = 0.0
            settled_count = 0
            winning_lots_count = 0
            losing_lots_count = 0

            for lot in open_lots:
                is_winner = (lot.resolution_outcome or "Yes").strip().lower() == norm_winning
                fill_p = float(lot.user_fill_price or lot.whale_entry_price or 0.5)
                notional = float(lot.notional_usd or 0.0)
                fee = float(lot.fee_usd or 0.0)

                if is_winner:
                    # Winner: $1.00 payout per share
                    price_ratio = ((1.0 - fill_p) / fill_p) if fill_p > 0 else 0.0
                    lot_realized_pnl = round(notional * price_ratio - fee, 2)
                    winning_lots_count += 1
                else:
                    # Loser: $0.00 payout
                    lot_realized_pnl = round(-notional - fee, 2)
                    losing_lots_count += 1

                lot.status = "CLOSED"
                lot.realized_pnl_usd = lot_realized_pnl
                lot.resolved_at = settle_dt

                if lot.user_id is None:
                    total_system_pnl += lot_realized_pnl

                settled_count += 1

            # Update platform snapshot
            try:
                from app.models import PortfolioSnapshot
                stmt_latest = select(PortfolioSnapshot).where(
                    PortfolioSnapshot.user_id.is_(None)
                ).order_by(PortfolioSnapshot.timestamp.desc()).limit(1)
                latest_snap = (await db.execute(stmt_latest)).scalar_one_or_none()

                cur_bal = float(latest_snap.balance) if latest_snap and latest_snap.balance else 10000.0
                cur_pnl = float(latest_snap.total_pnl) if latest_snap and latest_snap.total_pnl is not None else 0.0

                new_bal = round(cur_bal + total_system_pnl, 2)
                new_pnl = round(cur_pnl + total_system_pnl, 2)

                stmt_count = select(func.count(ExecutionLog.id)).where(
                    ExecutionLog.user_id.is_(None),
                    ExecutionLog.status == "FILLED"
                )
                open_remaining = int((await db.execute(stmt_count)).scalar() or 0)
                system_open_settled = len([l for l in open_lots if l.user_id is None])

                db.add(PortfolioSnapshot(
                    user_id=None,
                    timestamp=settle_dt,
                    balance=new_bal,
                    total_pnl=new_pnl,
                    active_trades_count=max(0, open_remaining - system_open_settled)
                ))
            except Exception as snap_err:
                logger.debug(f"Resolution snapshot note: {snap_err}")

            # Update User balances
            stmt_users = select(User)
            users = (await db.execute(stmt_users)).scalars().all()
            for u in users:
                u_settled_lots = [l for l in open_lots if l.user_id == u.id]
                if u_settled_lots:
                    u_pnl_delta = sum(float(l.realized_pnl_usd or 0.0) for l in u_settled_lots)
                    cur_u_bal = float(u.sandbox_balance_usd or 10000.0)
                    u.sandbox_balance_usd = round(cur_u_bal + u_pnl_delta, 2)
                    cur_u_hwm = float(u.sandbox_high_water_mark_usd or u.sandbox_starting_balance_usd or 10000.0)
                    u.sandbox_high_water_mark_usd = max(cur_u_hwm, u.sandbox_balance_usd)

            await db.commit()

            from app.services.event_logger import log_event
            asyncio.create_task(log_event(
                "MARKET_RESOLVED",
                f"Market Resolved: {condition_id[:16]}... -> {winning_outcome}",
                detail=f"Settled {settled_count} lots ({winning_lots_count} won, {losing_lots_count} lost). System PnL: ${total_system_pnl:,.2f}.",
                severity="success" if total_system_pnl >= 0 else "info",
                related_market=condition_id,
            ))

            logger.info(
                f"🏁 RESOLUTION COMPLETE for {condition_id[:16]}... Winner='{winning_outcome}': "
                f"{settled_count} lots settled ({winning_lots_count} winning, {losing_lots_count} losing). "
                f"Total system PnL: ${total_system_pnl:,.2f}."
            )

            return {
                "status": "SUCCESS",
                "condition_id": condition_id,
                "winning_outcome": winning_outcome,
                "settled_lots": settled_count,
                "winning_lots": winning_lots_count,
                "losing_lots": losing_lots_count,
                "total_system_pnl_usd": round(total_system_pnl, 2)
            }

live_trade_mirror = LiveTradeMirrorService()
