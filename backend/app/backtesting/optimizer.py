"""
Strategy Optimization and Comparison Engine
Sweeps multiple strategy architectures, latency parameters, EV gate hurdles,
and adverse pricing models to find THE optimal money-making strategy.
"""
import copy
import logging
from typing import List, Dict, Any, Optional
from app.backtesting.config import BacktestConfig
from app.backtesting.models import BacktestResult
from app.backtesting.data_loader import PolymarketDataLoader
from app.backtesting.engine import BacktestEngine
from app.backtesting.strategies import (
    BaseStrategy,
    FixedProportionalStrategy,
    SleeveConvictionStrategy,
    FeeAwareGatedStrategy,
    AntiConflictGatedStrategy,
    AdaptiveProductionStrategy,
)

logger = logging.getLogger(__name__)

class StrategyOptimizer:
    def __init__(self, base_config: BacktestConfig):
        self.base_config = base_config
        self.data_loader = PolymarketDataLoader(base_config)

    def compare_strategies(
        self,
        start_ts: int,
        end_ts: int,
        whale_addresses: Optional[List[str]] = None,
        limit_trades: Optional[int] = None
    ) -> List[BacktestResult]:
        """
        Runs all strategy architectures on the exact same market events and compares them.
        """
        if not whale_addresses:
            whale_addresses = self.data_loader.find_top_whales_in_window(
                start_ts=start_ts,
                end_ts=end_ts,
                min_volume_usd=50000.0,
                min_trades=20,
                max_whales=10
            )

        strategies: List[BaseStrategy] = [
            FixedProportionalStrategy(fraction=0.03, name="Baseline_Fixed_3%"),
            SleeveConvictionStrategy(name="Sleeve_Conviction_Only"),
            FeeAwareGatedStrategy(ev_multiplier=2.5, name="FeeAware_EV_Gate_2.5x"),
            AntiConflictGatedStrategy(max_conflict_tolerance=0.15, name="AntiConflict_Gated"),
            AdaptiveProductionStrategy(ev_multiplier=2.5, max_conflict_ratio=0.15, name="Baleen_Adaptive_Production")
        ]

        results = []
        for strat in strategies:
            cfg = copy.deepcopy(self.base_config)
            engine = BacktestEngine(config=cfg, strategy=strat, data_loader=self.data_loader)
            res = engine.run(
                start_ts=start_ts,
                end_ts=end_ts,
                whale_addresses=whale_addresses,
                limit_trades=limit_trades
            )
            results.append(res)

        # Sort by risk-adjusted performance: Net PnL first, then Sortino/Sharpe, with drawdown protection
        results.sort(
            key=lambda r: (
                r.total_net_pnl,
                r.sortino_ratio if r.sortino_ratio > 0 else -r.max_drawdown_pct,
                r.profit_factor
            ),
            reverse=True
        )
        return results

    def sweep_parameters(
        self,
        start_ts: int,
        end_ts: int,
        whale_addresses: Optional[List[str]] = None,
        limit_trades: Optional[int] = None,
        ev_multipliers: Optional[List[float]] = None,
        latencies_ms: Optional[List[float]] = None,
        adverse_biases_bps: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Parameter grid search over latency, adverse fill bias, and EV hurdle multipliers.
        """
        ev_multipliers = ev_multipliers or [1.5, 2.0, 2.5, 3.0]
        latencies_ms = latencies_ms or [150.0, 350.0, 750.0]
        adverse_biases_bps = adverse_biases_bps or [0.0, 5.0, 15.0]

        if not whale_addresses:
            whale_addresses = self.data_loader.find_top_whales_in_window(
                start_ts=start_ts,
                end_ts=end_ts,
                min_volume_usd=50000.0,
                min_trades=20,
                max_whales=10
            )

        sweep_records = []
        for lat in latencies_ms:
            for bias in adverse_biases_bps:
                for ev in ev_multipliers:
                    cfg = copy.deepcopy(self.base_config)
                    cfg.latency_ms = lat
                    cfg.adverse_bias_bps = bias
                    strat = AdaptiveProductionStrategy(
                        ev_multiplier=ev,
                        max_conflict_ratio=0.15,
                        name=f"Adaptive_lat{int(lat)}_bias{int(bias)}_ev{ev}"
                    )
                    engine = BacktestEngine(config=cfg, strategy=strat, data_loader=self.data_loader)
                    res = engine.run(
                        start_ts=start_ts,
                        end_ts=end_ts,
                        whale_addresses=whale_addresses,
                        limit_trades=limit_trades
                    )
                    score = (res.sharpe_ratio * res.profit_factor) / max(1.0, res.max_drawdown_pct)
                    sweep_records.append({
                        "latency_ms": lat,
                        "adverse_bias_bps": bias,
                        "ev_multiplier": ev,
                        "net_pnl": res.total_net_pnl,
                        "roi_pct": res.roi_pct,
                        "sharpe_ratio": res.sharpe_ratio,
                        "max_drawdown_pct": res.max_drawdown_pct,
                        "profit_factor": res.profit_factor,
                        "win_rate_pct": res.win_rate_pct,
                        "total_fees_usd": res.total_fees_usd,
                        "composite_score": round(score, 3)
                    })

        sweep_records.sort(key=lambda x: x["composite_score"], reverse=True)
        return sweep_records

    def close(self):
        self.data_loader.close()
