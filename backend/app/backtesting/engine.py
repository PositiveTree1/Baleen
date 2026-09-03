"""
Backtesting Simulation Engine
Coordinates chronological trade streaming, market resolution settlement,
execution fills, sleeve portfolio tracking, and final performance reporting.
"""
import logging
from typing import List, Optional, Dict, Any
from app.backtesting.config import BacktestConfig
from app.backtesting.models import TradeSignal, BacktestResult
from app.backtesting.data_loader import PolymarketDataLoader
from app.backtesting.execution import RealisticExecutionModel
from app.backtesting.portfolio import SimulatedPortfolio
from app.backtesting.strategies import BaseStrategy

logger = logging.getLogger(__name__)

class BacktestEngine:
    def __init__(
        self,
        config: BacktestConfig,
        strategy: BaseStrategy,
        data_loader: Optional[PolymarketDataLoader] = None
    ):
        self.config = config
        self.strategy = strategy
        self.data_loader = data_loader or PolymarketDataLoader(config)
        self.execution_model = RealisticExecutionModel(config)
        self.portfolio = SimulatedPortfolio(config)

    def run(
        self,
        start_ts: int,
        end_ts: int,
        whale_addresses: Optional[List[str]] = None,
        limit_trades: Optional[int] = None
    ) -> BacktestResult:
        """
        Executes a chronological event-driven backtest.
        """
        logger.info(f"Starting backtest '{self.strategy.name}' from {start_ts} to {end_ts}...")
        
        # 1. Preload market resolution metadata
        market_meta = self.data_loader.get_market_metadata()

        # 2. Discover whales if not provided
        if not whale_addresses:
            whales_qual = self.data_loader.find_qualified_whales(
                start_ts=start_ts,
                end_ts=end_ts,
                lookback_days=getattr(self.config, "lookback_days", 60),
                max_whales=10
            )
            whale_addresses = [q.address for q in whales_qual]
            if hasattr(self.strategy, "set_qualified_roster"):
                self.strategy.set_qualified_roster(whales_qual)

        self.portfolio.register_active_roster(whale_addresses)
        resolved_markets = set()
        last_snapshot_ts = start_ts
        snapshot_interval = 86400  # Daily equity snapshots

        # 3. Stream trades chronologically
        trade_stream = self.data_loader.stream_trades_in_window(
            start_ts=start_ts,
            end_ts=end_ts,
            whale_addresses=whale_addresses,
            limit_trades=limit_trades
        )

        for signal in trade_stream:
            curr_ts = signal.timestamp

            # Check daily equity snapshot
            if curr_ts - last_snapshot_ts >= snapshot_interval:
                self.portfolio.record_equity_snapshot(float(curr_ts))
                last_snapshot_ts = curr_ts

            # Check if this market was closed / resolved prior to this trade
            m_id = signal.market_id
            m_info = market_meta.get(m_id, {})
            if m_info.get("closed") and m_id not in resolved_markets:
                end_t = m_info.get("end_timestamp") or curr_ts
                if end_t <= curr_ts:
                    p1 = m_info.get("p1_payout")
                    p2 = m_info.get("p2_payout")
                    winning_tok = m_info.get("winning_token")
                    settled = self.portfolio.settle_market_resolution(
                        market_id=m_id,
                        winning_token=winning_tok,
                        resolution_timestamp=float(end_t),
                        p1_payout=p1,
                        p2_payout=p2
                    )
                    for t in settled:
                        self.strategy.on_trade_closed(t)
                    resolved_markets.add(m_id)

            # Process Signal
            if signal.side.upper() == "SELL":
                # Check if strategy or config wants to mirror whale exit or hold until resolution
                should_exit = getattr(self.strategy, "should_mirror_whale_exit", lambda s, p: True)(signal, self.portfolio)
                if should_exit and not self.config.hold_to_resolution:
                    clean_w = signal.whale_address.lower()
                    pos_key = f"{signal.market_id}_{signal.nonusdc_side}_{clean_w}"
                    if pos_key in self.portfolio.open_positions:
                        fill = self.execution_model.simulate_copy_execution(
                            signal=signal,
                            intended_size_usd=signal.whale_size_usd,
                            available_cash=self.portfolio.cash,
                            available_sleeve_cash=self.portfolio.get_available_sleeve_cash(clean_w)
                        )
                        closed_t = self.portfolio.close_position_on_whale_sell(signal, fill)
                        if closed_t:
                            self.strategy.on_trade_closed(closed_t)

            elif signal.side.upper() == "BUY":
                # Max open position guard
                if len(self.portfolio.open_positions) >= self.config.max_open_positions:
                    continue

                # Ask strategy for sizing
                intended_usd = self.strategy.evaluate_signal(signal, self.portfolio)
                if not intended_usd or intended_usd < self.config.min_trade_size_usd:
                    continue

                # Market concentration guard
                curr_market_notional = sum(
                    p.total_cost_usd for p in self.portfolio.open_positions.values() if p.market_id == signal.market_id
                )
                max_market_cap = self.portfolio.initial_capital * self.config.max_market_fraction
                if curr_market_notional + intended_usd > max_market_cap:
                    intended_usd = max(0.0, max_market_cap - curr_market_notional)
                    if intended_usd < self.config.min_trade_size_usd:
                        continue

                fill = self.execution_model.simulate_copy_execution(
                    signal=signal,
                    intended_size_usd=intended_usd,
                    available_cash=self.portfolio.cash,
                    available_sleeve_cash=self.portfolio.get_available_sleeve_cash(signal.whale_address)
                )

                if fill.status in ("FILLED", "PARTIALLY_FILLED"):
                    self.portfolio.open_position(fill)

        # 4. End of simulation settlement
        # Settle any remaining positions whose markets are closed in market_meta
        for m_id, m_info in market_meta.items():
            if m_info.get("closed") and m_id not in resolved_markets:
                p1 = m_info.get("p1_payout")
                p2 = m_info.get("p2_payout")
                winning_tok = m_info.get("winning_token")
                settled = self.portfolio.settle_market_resolution(
                    market_id=m_id,
                    winning_token=winning_tok,
                    resolution_timestamp=float(end_ts),
                    p1_payout=p1,
                    p2_payout=p2
                )
                for t in settled:
                    self.strategy.on_trade_closed(t)
                resolved_markets.add(m_id)

        self.portfolio.record_equity_snapshot(float(end_ts))
        return self.portfolio.compute_final_metrics(start_ts, end_ts, self.strategy.name)
