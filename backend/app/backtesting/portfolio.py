"""
Simulated Portfolio and Risk Accounting Module
Maintains cash balance, isolated wallet sleeves, open position tracking,
settlement closures, equity snapshots, and risk-adjusted metrics.
"""
import math
import uuid
from typing import Dict, List, Optional, Any
from app.backtesting.config import BacktestConfig
from app.backtesting.models import (
    TradeSignal,
    ExecutionFill,
    PortfolioPosition,
    ClosedTrade,
    EquityPoint,
    BacktestResult,
)
from app.sizing.sleeve_manager import SleeveManager
from app.services.polymarket_fees import calculate_polymarket_fee

class SimulatedPortfolio:
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.cash = float(config.initial_capital)
        self.initial_capital = float(config.initial_capital)
        self.sleeve_budgets: Dict[str, float] = {}
        self.sleeve_open_notional: Dict[str, float] = {}
        self.open_positions: Dict[str, PortfolioPosition] = {}
        self.closed_trades: List[ClosedTrade] = []
        self.equity_curve: List[EquityPoint] = []
        self.peak_equity = float(config.initial_capital)
        self.max_drawdown_dollars = 0.0
        self.max_drawdown_pct = 0.0
        self.total_fees_paid = 0.0
        self.total_slippage_dollars = 0.0
        self.last_snapshot_time = 0.0

    def register_active_roster(self, whale_addresses: List[str]):
        """Sets up isolated sleeve budgets evenly across tracked whales."""
        active_count = max(1, len(whale_addresses))
        per_sleeve = min(
            self.config.initial_capital * self.config.max_sleeve_fraction,
            self.config.initial_capital / active_count
        )
        for addr in whale_addresses:
            clean = addr.lower()
            self.sleeve_budgets[clean] = round(per_sleeve, 2)
            self.sleeve_open_notional.setdefault(clean, 0.0)

    def get_available_sleeve_cash(self, whale_address: str) -> float:
        """Returns free remaining capital inside a whale's dedicated sleeve."""
        clean = whale_address.lower()
        budget = self.sleeve_budgets.get(clean, self.config.initial_capital * self.config.max_sleeve_fraction)
        deployed = self.sleeve_open_notional.get(clean, 0.0)
        return max(0.0, budget - deployed)

    def open_position(self, fill: ExecutionFill) -> Optional[PortfolioPosition]:
        """Deducts capital and opens/augments a position."""
        if fill.status not in ("FILLED", "PARTIALLY_FILLED") or fill.filled_size_usd <= 0:
            return None

        total_debit = fill.filled_size_usd + fill.fee_usd
        if total_debit > self.cash:
            excess = total_debit - self.cash
            if fill.filled_size_usd - excess >= self.config.min_trade_size_usd:
                fill.filled_size_usd = round(fill.filled_size_usd - excess, 2)
                fill.filled_shares = round(fill.filled_size_usd / fill.fill_price, 4) if fill.fill_price > 0 else 0.0
                total_debit = fill.filled_size_usd + fill.fee_usd
            else:
                return None

        clean_whale = fill.signal.whale_address.lower()
        self.cash -= total_debit
        self.total_fees_paid += fill.fee_usd
        self.total_slippage_dollars += fill.filled_shares * abs(fill.fill_price - fill.signal.whale_price)
        self.sleeve_open_notional[clean_whale] = self.sleeve_open_notional.get(clean_whale, 0.0) + fill.filled_size_usd

        pos_key = f"{fill.signal.market_id}_{fill.signal.nonusdc_side}_{clean_whale}"
        if pos_key in self.open_positions:
            existing = self.open_positions[pos_key]
            new_shares = existing.shares + fill.filled_shares
            new_cost = existing.total_cost_usd + fill.filled_size_usd
            new_avg_price = new_cost / new_shares if new_shares > 0 else fill.fill_price
            existing.shares = new_shares
            existing.total_cost_usd = new_cost
            existing.avg_fill_price = round(new_avg_price, 4)
            existing.fees_paid_usd += fill.fee_usd
            return existing
        else:
            new_pos = PortfolioPosition(
                position_id=str(uuid.uuid4())[:8],
                market_id=fill.signal.market_id,
                condition_id=fill.signal.condition_id,
                token_id=fill.signal.token_id,
                outcome_token=fill.signal.nonusdc_side,
                side="BUY",
                shares=fill.filled_shares,
                avg_fill_price=fill.fill_price,
                total_cost_usd=fill.filled_size_usd,
                fees_paid_usd=fill.fee_usd,
                opened_at=fill.executed_at,
                whale_address=clean_whale,
                category=fill.signal.category,
                market_title=fill.signal.market_title
            )
            self.open_positions[pos_key] = new_pos
            return new_pos

    def close_position_on_whale_sell(self, signal: TradeSignal, fill: ExecutionFill) -> Optional[ClosedTrade]:
        """Exits position partially or fully when whale sells."""
        clean_whale = signal.whale_address.lower()
        pos_key = f"{signal.market_id}_{signal.nonusdc_side}_{clean_whale}"
        if pos_key not in self.open_positions:
            return None

        pos = self.open_positions[pos_key]
        shares_to_sell = min(pos.shares, fill.filled_shares if fill.filled_shares > 0 else pos.shares)
        if shares_to_sell <= 0:
            return None

        fraction = shares_to_sell / pos.shares if pos.shares > 0 else 1.0
        cost_basis = pos.total_cost_usd * fraction
        entry_fees = pos.fees_paid_usd * fraction

        gross_proceeds = shares_to_sell * fill.fill_price
        exit_fee = fill.fee_usd
        self.cash += (gross_proceeds - exit_fee)
        self.total_fees_paid += exit_fee

        gross_pnl = gross_proceeds - cost_basis
        net_pnl = gross_pnl - entry_fees - exit_fee
        roi_pct = (net_pnl / cost_basis * 100.0) if cost_basis > 0 else 0.0

        closed_trade = ClosedTrade(
            trade_id=str(uuid.uuid4())[:8],
            whale_address=clean_whale,
            market_id=pos.market_id,
            condition_id=pos.condition_id,
            token_id=pos.token_id,
            outcome_token=pos.outcome_token,
            category=pos.category,
            entry_price=pos.avg_fill_price,
            exit_price=fill.fill_price,
            shares=shares_to_sell,
            total_invested=cost_basis,
            gross_pnl=round(gross_pnl, 2),
            entry_fee_usd=round(entry_fees, 2),
            exit_fee_usd=round(exit_fee, 2),
            total_fees_usd=round(entry_fees + exit_fee, 2),
            net_pnl=round(net_pnl, 2),
            roi_pct=round(roi_pct, 2),
            opened_at=pos.opened_at,
            closed_at=fill.executed_at,
            hold_duration_sec=max(0.0, fill.executed_at - pos.opened_at),
            exit_reason="WHALE_SELL_EXIT"
        )
        self.closed_trades.append(closed_trade)

        # Update remaining position
        pos.shares -= shares_to_sell
        pos.total_cost_usd -= cost_basis
        pos.fees_paid_usd -= entry_fees
        self.sleeve_open_notional[clean_whale] = max(0.0, self.sleeve_open_notional.get(clean_whale, 0.0) - cost_basis)

        if pos.shares <= 0.0001:
            del self.open_positions[pos_key]

        return closed_trade

    def settle_market_resolution(
        self,
        market_id: str,
        winning_token: Optional[str],
        resolution_timestamp: float,
        p1_payout: Optional[float] = None,
        p2_payout: Optional[float] = None
    ) -> List[ClosedTrade]:
        """Settles all open positions on this market using authentic contract payout (win, loss, split refund)."""
        settled_trades = []
        matching_keys = [k for k in list(self.open_positions.keys()) if k.startswith(f"{market_id}_")]

        for key in matching_keys:
            pos = self.open_positions.pop(key)
            if p1_payout is not None and p2_payout is not None:
                payout_price = p1_payout if pos.outcome_token == "token1" else p2_payout
            elif winning_token:
                payout_price = 1.00 if pos.outcome_token == winning_token else 0.00
            else:
                payout_price = 0.50

            gross_proceeds = pos.shares * payout_price

            # Exit redemption fee (Polymarket does not charge fee on 0 payout, standard fee on winning redemption if applicable)
            exit_fee = 0.0
            if payout_price > 0.50 and self.config.enable_fees:
                fee_calc = calculate_polymarket_fee(
                    notional_usd=gross_proceeds,
                    price=min(0.999, payout_price),
                    market_title=pos.market_title or pos.category,
                    is_maker=False
                )
                exit_fee = float(fee_calc.get("fee_usd", 0.0))

            self.cash += (gross_proceeds - exit_fee)
            self.total_fees_paid += exit_fee

            gross_pnl = gross_proceeds - pos.total_cost_usd
            net_pnl = gross_pnl - pos.fees_paid_usd - exit_fee
            roi_pct = (net_pnl / pos.total_cost_usd * 100.0) if pos.total_cost_usd > 0 else -100.0

            clean_whale = pos.whale_address.lower()
            self.sleeve_open_notional[clean_whale] = max(0.0, self.sleeve_open_notional.get(clean_whale, 0.0) - pos.total_cost_usd)

            if payout_price > pos.avg_fill_price:
                reason = "RESOLUTION_WIN"
            elif math.isclose(payout_price, 0.50) and math.isclose(pos.avg_fill_price, 0.50):
                reason = "RESOLUTION_SPLIT"
            else:
                reason = "RESOLUTION_LOSS"

            trade = ClosedTrade(
                trade_id=str(uuid.uuid4())[:8],
                whale_address=clean_whale,
                market_id=pos.market_id,
                condition_id=pos.condition_id,
                token_id=pos.token_id,
                outcome_token=pos.outcome_token,
                category=pos.category,
                entry_price=pos.avg_fill_price,
                exit_price=round(payout_price, 4),
                shares=pos.shares,
                total_invested=pos.total_cost_usd,
                gross_pnl=round(gross_pnl, 2),
                entry_fee_usd=round(pos.fees_paid_usd, 2),
                exit_fee_usd=round(exit_fee, 2),
                total_fees_usd=round(pos.fees_paid_usd + exit_fee, 2),
                net_pnl=round(net_pnl, 2),
                roi_pct=round(roi_pct, 2),
                opened_at=pos.opened_at,
                closed_at=resolution_timestamp,
                hold_duration_sec=max(0.0, resolution_timestamp - pos.opened_at),
                exit_reason=reason
            )
            self.closed_trades.append(trade)
            settled_trades.append(trade)

        return settled_trades

    def record_equity_snapshot(
        self,
        current_timestamp: float,
        latest_prices: Optional[Dict[str, float]] = None
    ):
        """Computes current mark-to-market equity and updates drawdown."""
        latest_prices = latest_prices or {}
        invested_notional = 0.0
        unrealized_pnl = 0.0

        for pos in self.open_positions.values():
            m_key = f"{pos.market_id}_{pos.outcome_token}"
            curr_p = latest_prices.get(m_key, pos.avg_fill_price)
            curr_val = pos.shares * curr_p
            invested_notional += pos.total_cost_usd
            unrealized_pnl += (curr_val - pos.total_cost_usd)

        total_equity = self.cash + invested_notional + unrealized_pnl
        realized_pnl = sum(t.net_pnl for t in self.closed_trades)

        ts = max(float(current_timestamp), self.last_snapshot_time)

        # Avoid redundant duplicate points if timestamp and equity have not changed
        if self.equity_curve:
            last = self.equity_curve[-1]
            if math.isclose(last.timestamp, ts, abs_tol=1e-3) and math.isclose(last.total_equity, total_equity, abs_tol=1e-2):
                return

        if total_equity > self.peak_equity:
            self.peak_equity = total_equity

        dd_dollars = max(0.0, self.peak_equity - total_equity)
        dd_pct = (dd_dollars / self.peak_equity * 100.0) if self.peak_equity > 0 else 0.0

        if dd_dollars > self.max_drawdown_dollars:
            self.max_drawdown_dollars = dd_dollars
        if dd_pct > self.max_drawdown_pct:
            self.max_drawdown_pct = dd_pct

        point = EquityPoint(
            timestamp=ts,
            cash_balance=round(self.cash, 2),
            invested_notional=round(invested_notional, 2),
            total_equity=round(total_equity, 2),
            realized_pnl=round(realized_pnl, 2),
            unrealized_pnl=round(unrealized_pnl, 2),
            drawdown_pct=round(dd_pct, 2)
        )
        self.equity_curve.append(point)
        self.last_snapshot_time = ts

    def compute_final_metrics(
        self,
        start_ts: int,
        end_ts: int,
        strategy_name: str
    ) -> BacktestResult:
        """Calculates comprehensive quantitative backtest metrics."""
        duration_sec = max(1.0, float(end_ts - start_ts))
        duration_days = max(1.0, duration_sec / 86400.0)

        # Ensure a final snapshot exists
        if not self.equity_curve:
            self.record_equity_snapshot(float(end_ts))

        # Sort snapshots chronologically
        self.equity_curve.sort(key=lambda p: p.timestamp)

        final_equity = self.equity_curve[-1].total_equity
        total_net_pnl = final_equity - self.initial_capital
        roi_pct = (total_net_pnl / self.initial_capital) * 100.0
        annualized_roi_pct = roi_pct * (365.0 / duration_days)

        wins = [t for t in self.closed_trades if t.net_pnl > 0]
        losses = [t for t in self.closed_trades if t.net_pnl < 0]
        total_trades = len(self.closed_trades)
        win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_wins = sum(t.net_pnl for t in wins)
        gross_losses = abs(sum(t.net_pnl for t in losses))
        profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else (99.0 if gross_wins > 0 else 1.0)
        profit_factor = min(99.0, round(profit_factor, 2))

        # True Daily Return Sharpe & Sortino
        daily_equities = {}
        for p in self.equity_curve:
            day_idx = int(p.timestamp // 86400)
            daily_equities[day_idx] = p.total_equity

        sorted_days = sorted(daily_equities.keys())
        daily_returns = []
        if len(sorted_days) >= 2:
            for i in range(1, len(sorted_days)):
                e_prev = daily_equities[sorted_days[i-1]]
                e_curr = daily_equities[sorted_days[i]]
                if e_prev > 0:
                    daily_returns.append((e_curr - e_prev) / e_prev)
        else:
            # For intraday or sparse windows, compute step returns across equity curve
            for i in range(1, len(self.equity_curve)):
                e_prev = self.equity_curve[i-1].total_equity
                e_curr = self.equity_curve[i].total_equity
                if e_prev > 0 and not math.isclose(e_prev, e_curr, abs_tol=1e-4):
                    daily_returns.append((e_curr - e_prev) / e_prev)

        if daily_returns and len(daily_returns) >= 2:
            mean_r = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_r) ** 2 for r in daily_returns) / len(daily_returns)
            stdev = math.sqrt(variance)
            downside_returns = [r for r in daily_returns if r < 0]
            downside_var = sum(r ** 2 for r in downside_returns) / max(1, len(downside_returns))
            downside_stdev = math.sqrt(downside_var)

            # Annualized Sharpe with 0% risk free rate
            sharpe = (mean_r / (stdev + 1e-6)) * math.sqrt(365) if stdev > 0 else 0.0
            sortino = (mean_r / (downside_stdev + 1e-6)) * math.sqrt(365) if downside_stdev > 0 else 0.0
        else:
            sharpe = 1.0 if total_net_pnl > 0 else 0.0
            sortino = 1.0 if total_net_pnl > 0 else 0.0

        # Wallet Breakdown
        wallet_perf = {}
        for t in self.closed_trades:
            w = t.whale_address
            if w not in wallet_perf:
                wallet_perf[w] = {"trades": 0, "net_pnl": 0.0, "wins": 0, "fees": 0.0}
            wallet_perf[w]["trades"] += 1
            wallet_perf[w]["net_pnl"] += t.net_pnl
            wallet_perf[w]["fees"] += t.total_fees_usd
            if t.net_pnl > 0:
                wallet_perf[w]["wins"] += 1

        # Category Breakdown
        cat_perf = {}
        for t in self.closed_trades:
            c = t.category
            if c not in cat_perf:
                cat_perf[c] = {"trades": 0, "net_pnl": 0.0, "wins": 0}
            cat_perf[c]["trades"] += 1
            cat_perf[c]["net_pnl"] += t.net_pnl
            if t.net_pnl > 0:
                cat_perf[c]["wins"] += 1

        avg_trade_pnl = (total_net_pnl / total_trades) if total_trades > 0 else 0.0

        return BacktestResult(
            strategy_name=strategy_name,
            config=self.config,
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            duration_days=round(duration_days, 1),
            initial_capital=self.initial_capital,
            final_equity=round(final_equity, 2),
            total_net_pnl=round(total_net_pnl, 2),
            roi_pct=round(roi_pct, 2),
            annualized_roi_pct=round(annualized_roi_pct, 2),
            sharpe_ratio=round(max(-10.0, min(20.0, sharpe)), 3),
            sortino_ratio=round(max(-10.0, min(30.0, sortino)), 3),
            max_drawdown_pct=round(self.max_drawdown_pct, 2),
            max_drawdown_usd=round(self.max_drawdown_dollars, 2),
            win_rate_pct=round(win_rate, 1),
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=len(wins),
            losing_trades=len(losses),
            total_fees_usd=round(self.total_fees_paid, 2),
            total_slippage_usd=round(self.total_slippage_dollars, 2),
            avg_trade_pnl=round(avg_trade_pnl, 2),
            equity_curve=self.equity_curve,
            closed_trades=self.closed_trades,
            wallet_performance=wallet_perf,
            category_performance=cat_perf
        )
