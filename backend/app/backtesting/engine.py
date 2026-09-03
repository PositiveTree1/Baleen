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
        latest_prices: Dict[str, float] = {}
        last_snapshot_ts = start_ts
        snapshot_interval = 3600  # Hourly periodic equity snapshots (or mark-to-market)
        trades_processed = 0

        # Initial equity snapshot at start of simulation
        self.portfolio.record_equity_snapshot(float(start_ts), latest_prices=latest_prices)

        # 3. Stream trades chronologically
        trade_stream = self.data_loader.stream_trades_in_window(
            start_ts=start_ts,
            end_ts=end_ts,
            whale_addresses=whale_addresses,
            limit_trades=limit_trades
        )

        for signal in trade_stream:
            trades_processed += 1
            curr_ts = signal.timestamp
            latest_prices[f"{signal.market_id}_{signal.nonusdc_side}"] = signal.whale_price
            latest_prices[signal.market_id] = signal.whale_price

            # Strategy signal hook
            if hasattr(self.strategy, "on_trade_signal"):
                self.strategy.on_trade_signal(signal)

            # Periodic mark-to-market snapshot: hourly or every 25 trades when holding positions
            if (curr_ts - last_snapshot_ts >= snapshot_interval) or (trades_processed % 25 == 0 and self.portfolio.open_positions):
                self.portfolio.record_equity_snapshot(float(curr_ts), latest_prices=latest_prices)
                last_snapshot_ts = curr_ts

            # In-stream market resolution: settle any open positions whose markets have reached resolution
            open_market_ids = {p.market_id for p in self.portfolio.open_positions.values()}
            for o_mid in open_market_ids:
                if o_mid not in resolved_markets:
                    m_info = market_meta.get(o_mid) or self.data_loader._market_resolutions_cache.get(o_mid)
                    if not m_info:
                        fetched = self.data_loader.get_market_metadata([o_mid])
                        m_info = fetched.get(o_mid, {})
                    if m_info.get("closed"):
                        end_t = m_info.get("end_timestamp") or 0.0
                        if end_t > 0 and end_t <= curr_ts:
                            p1 = m_info.get("p1_payout")
                            p2 = m_info.get("p2_payout")
                            winning_tok = m_info.get("winning_token")
                            settled = self.portfolio.settle_market_resolution(
                                market_id=o_mid,
                                winning_token=winning_tok,
                                resolution_timestamp=float(end_t),
                                p1_payout=p1,
                                p2_payout=p2
                            )
                            if settled:
                                for t in settled:
                                    self.strategy.on_trade_closed(t)
                                if hasattr(self.strategy, "on_market_resolved"):
                                    self.strategy.on_market_resolved(
                                        market_id=o_mid,
                                        winning_token=winning_tok,
                                        resolution_timestamp=float(end_t),
                                        p1_payout=p1,
                                        p2_payout=p2
                                    )
                                resolved_markets.add(o_mid)
                                # Record snapshot on resolution settlement
                                self.portfolio.record_equity_snapshot(float(curr_ts), latest_prices=latest_prices)

            # Process Signal
            if signal.side.upper() == "SELL":
                # Check if strategy or config wants to mirror whale exit or hold until resolution
                should_exit = getattr(self.strategy, "should_mirror_whale_exit", lambda s, p: True)(signal, self.portfolio)
                if should_exit and not self.config.hold_to_resolution:
                    clean_w = signal.whale_address.lower()
                    pos_key = f"{signal.market_id}_{signal.nonusdc_side}_{clean_w}"
                    if pos_key in self.portfolio.open_positions:
                        user_pos = self.portfolio.open_positions[pos_key]
                        user_sell_size = user_pos.shares * signal.whale_price
                        fill = self.execution_model.simulate_copy_execution(
                            signal=signal,
                            intended_size_usd=user_sell_size,
                            available_cash=self.portfolio.cash,
                            available_sleeve_cash=self.portfolio.get_available_sleeve_cash(clean_w)
                        )
                        closed_t = self.portfolio.close_position_on_whale_sell(signal, fill)
                        if closed_t:
                            self.strategy.on_trade_closed(closed_t)
                            # Record snapshot on sell fill
                            self.portfolio.record_equity_snapshot(float(curr_ts), latest_prices=latest_prices)

            elif signal.side.upper() == "BUY":
                # Ask strategy for sizing
                intended_usd = self.strategy.evaluate_signal(signal, self.portfolio)
                if not intended_usd or intended_usd < self.config.min_trade_size_usd:
                    continue

                # Max open position guard
                if len(self.portfolio.open_positions) >= self.config.max_open_positions:
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
                    new_pos = self.portfolio.open_position(fill)
                    if new_pos:
                        # Record snapshot on buy fill
                        self.portfolio.record_equity_snapshot(float(curr_ts), latest_prices=latest_prices)

        # 4. End of simulation settlement
        # STRICT ZERO LOOKAHEAD: Settle ONLY remaining open positions whose markets closed ON OR BEFORE end_ts
        remaining_open_market_ids = {p.market_id for p in self.portfolio.open_positions.values()}
        for m_id in remaining_open_market_ids:
            if m_id not in resolved_markets:
                m_info = market_meta.get(m_id) or self.data_loader._market_resolutions_cache.get(m_id)
                if not m_info:
                    fetched = self.data_loader.get_market_metadata([m_id])
                    m_info = fetched.get(m_id, {})
                if m_info.get("closed"):
                    end_t = m_info.get("end_timestamp") or 0.0
                    if end_t > 0 and end_t <= end_ts:
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
                        if settled:
                            for t in settled:
                                self.strategy.on_trade_closed(t)
                            if hasattr(self.strategy, "on_market_resolved"):
                                self.strategy.on_market_resolved(
                                    market_id=m_id,
                                    winning_token=winning_tok,
                                    resolution_timestamp=float(end_t),
                                    p1_payout=p1,
                                    p2_payout=p2
                                )
                            resolved_markets.add(m_id)
                            self.portfolio.record_equity_snapshot(float(end_t), latest_prices=latest_prices)

        self.portfolio.record_equity_snapshot(float(end_ts), latest_prices=latest_prices)
        return self.portfolio.compute_final_metrics(start_ts, end_ts, self.strategy.name)
