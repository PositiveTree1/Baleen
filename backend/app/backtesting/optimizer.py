"""
Strategy Optimization, Multi-Capital Sweeps, and Head-to-Head Comparison Engine
Evaluates all distinct strategy approaches:
  - Fixed $100 Entry
  - Baseline Proportional (2%)
  - High-Conviction Gold Snipers Only
  - Consensus / Multi-Whale Confirmation (2+ Whales)
  - Top 5 Whales by Sharpe (Dynamic Half-Kelly)
  - Resolution Hold ("Diamond Hands")
  - Anti-Conflict Gated
  - Flagship Baleen Adaptive Production
"""
import copy
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.backtesting.config import BacktestConfig
from app.backtesting.models import BacktestResult
from app.backtesting.data_loader import PolymarketDataLoader, get_predefined_window
from app.backtesting.engine import BacktestEngine
from app.backtesting.strategies import (
    BaseStrategy,
    FixedAmountEntryStrategy,
    FixedProportionalStrategy,
    GoldSniperStrategy,
    ConsensusConfirmationStrategy,
    TopSharpeKellyStrategy,
    ResolutionHoldStrategy,
    WhaleExitMirroringStrategy,
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

    def get_standard_strategy_suite(self, entry_usd: float = 100.0) -> List[BaseStrategy]:
        """Returns the full suite of distinct strategy architectures."""
        return [
            FixedAmountEntryStrategy(entry_usd=entry_usd, name=f"FixedEntry_${int(entry_usd)}"),
            FixedProportionalStrategy(fraction=0.02, name="Baseline_Proportional_2%"),
            GoldSniperStrategy(min_conviction=0.70, name="HighConviction_GoldSnipers"),
            ConsensusConfirmationStrategy(min_whales=2, window_sec=86400.0, name="Consensus_2Whales_Confirm"),
            TopSharpeKellyStrategy(top_n=5, name="Top5_Whales_Sharpe_Kelly"),
            ResolutionHoldStrategy(fraction=0.03, name="Resolution_Hold_DiamondHands"),
            AntiConflictGatedStrategy(max_conflict_tolerance=0.15, name="AntiConflict_Gated"),
            AdaptiveProductionStrategy(ev_multiplier=2.5, max_conflict_ratio=0.15, name="Baleen_Adaptive_Production")
        ]

    def compare_strategies(
        self,
        start_ts: int,
        end_ts: int,
        whale_addresses: Optional[List[str]] = None,
        limit_trades: Optional[int] = None,
        entry_usd: float = 100.0
    ) -> List[BacktestResult]:
        """
        Runs all distinct strategy architectures on the exact same market events and compares them.
        """
        whales_qual = self.data_loader.find_qualified_whales(
            start_ts=start_ts,
            end_ts=end_ts,
            lookback_days=getattr(self.base_config, "lookback_days", 60),
            max_whales=12
        )

        if not whale_addresses:
            whale_addresses = [q.address for q in whales_qual]

        strategies = self.get_standard_strategy_suite(entry_usd=entry_usd)
        for s in strategies:
            if hasattr(s, "set_qualified_roster"):
                s.set_qualified_roster(whales_qual)

        results = []
        for strat in strategies:
            cfg = copy.deepcopy(self.base_config)
            cfg.fixed_entry_usd = entry_usd
            engine = BacktestEngine(config=cfg, strategy=strat, data_loader=self.data_loader)
            res = engine.run(
                start_ts=start_ts,
                end_ts=end_ts,
                whale_addresses=whale_addresses,
                limit_trades=limit_trades
            )
            results.append(res)

        # Sort by Net PnL, Sortino/Sharpe, and Profit Factor
        results.sort(
            key=lambda r: (
                r.total_net_pnl,
                r.sortino_ratio if r.sortino_ratio > 0 else -r.max_drawdown_pct,
                r.profit_factor
            ),
            reverse=True
        )
        return results

    def sweep_capital(
        self,
        start_ts: int,
        end_ts: int,
        capitals: Optional[List[float]] = None,
        whale_addresses: Optional[List[str]] = None,
        limit_trades: Optional[int] = None,
        entry_usd: float = 100.0,
        strategy_type: str = "fixed"
    ) -> List[Dict[str, Any]]:
        """
        Runs the specified strategy across varied starting investment levels ($1,000, $5,000, $10,000).
        """
        capitals = capitals or [1000.0, 5000.0, 10000.0]

        whales_qual = self.data_loader.find_qualified_whales(
            start_ts=start_ts,
            end_ts=end_ts,
            lookback_days=getattr(self.base_config, "lookback_days", 60),
            max_whales=10
        )
        if not whale_addresses:
            whale_addresses = [q.address for q in whales_qual]

        records = []
        for cap in capitals:
            cfg = copy.deepcopy(self.base_config)
            cfg.initial_capital = cap
            # Respect safe max single-trade sizing limit
            eff_entry = min(entry_usd, cap * 0.10)
            cfg.fixed_entry_usd = eff_entry

            if strategy_type == "fixed":
                strat = FixedAmountEntryStrategy(entry_usd=eff_entry, name=f"FixedEntry_${int(eff_entry)}")
            elif strategy_type == "proportional":
                strat = FixedProportionalStrategy(fraction=0.02, name=f"Proportional_2pct_Cap${int(cap)}")
            else:
                strat = AdaptiveProductionStrategy(
                    ev_multiplier=2.5,
                    max_conflict_ratio=0.15,
                    name=f"AdaptiveProd_Cap${int(cap)}"
                )

            if hasattr(strat, "set_qualified_roster"):
                strat.set_qualified_roster(whales_qual)

            engine = BacktestEngine(config=cfg, strategy=strat, data_loader=self.data_loader)
            res = engine.run(
                start_ts=start_ts,
                end_ts=end_ts,
                whale_addresses=whale_addresses,
                limit_trades=limit_trades
            )
            records.append({
                "capital": cap,
                "strategy": strat.name,
                "entry_usd": eff_entry,
                "net_pnl": res.total_net_pnl,
                "roi_pct": res.roi_pct,
                "annualized_roi_pct": res.annualized_roi_pct,
                "sharpe_ratio": res.sharpe_ratio,
                "max_drawdown_pct": res.max_drawdown_pct,
                "win_rate_pct": res.win_rate_pct,
                "profit_factor": res.profit_factor,
                "total_trades": res.total_trades,
                "total_fees_usd": res.total_fees_usd
            })
        return records

    def sweep_windows(
        self,
        windows: Optional[List[Tuple[str, int, int]]] = None,
        capital: float = 10000.0,
        entry_usd: float = 100.0,
        limit_trades: Optional[int] = None,
        strategy_type: str = "fixed"
    ) -> List[Dict[str, Any]]:
        """
        Compares strategy performance across extended historical windows (1-Month, 3-Month, 6-Month).
        """
        if not windows:
            w1 = get_predefined_window("1m")
            w3 = get_predefined_window("3m")
            w6 = get_predefined_window("6m")
            windows = [
                (w1[2], w1[0], w1[1]),
                (w3[2], w3[0], w3[1]),
                (w6[2], w6[0], w6[1])
            ]

        records = []
        for label, s_ts, e_ts in windows:
            cfg = copy.deepcopy(self.base_config)
            cfg.initial_capital = capital
            cfg.fixed_entry_usd = entry_usd

            whales_qual = self.data_loader.find_qualified_whales(
                start_ts=s_ts,
                end_ts=e_ts,
                lookback_days=getattr(cfg, "lookback_days", 60),
                max_whales=10
            )
            whales = [q.address for q in whales_qual]

            if strategy_type == "fixed":
                strat = FixedAmountEntryStrategy(entry_usd=entry_usd, name=f"FixedEntry_${int(entry_usd)}_{label[:6]}")
            elif strategy_type == "proportional":
                strat = FixedProportionalStrategy(fraction=0.02, name=f"Proportional_2pct_{label[:6]}")
            else:
                strat = AdaptiveProductionStrategy(
                    ev_multiplier=2.5,
                    max_conflict_ratio=0.15,
                    name=f"AdaptiveProd_{label[:10]}"
                )

            if hasattr(strat, "set_qualified_roster"):
                strat.set_qualified_roster(whales_qual)

            engine = BacktestEngine(config=cfg, strategy=strat, data_loader=self.data_loader)
            res = engine.run(
                start_ts=s_ts,
                end_ts=e_ts,
                whale_addresses=whales,
                limit_trades=limit_trades
            )
            records.append({
                "window": label,
                "start_ts": s_ts,
                "end_ts": e_ts,
                "duration_days": res.duration_days,
                "net_pnl": res.total_net_pnl,
                "roi_pct": res.roi_pct,
                "sharpe_ratio": res.sharpe_ratio,
                "max_drawdown_pct": res.max_drawdown_pct,
                "win_rate_pct": res.win_rate_pct,
                "total_trades": res.total_trades,
                "whales_count": len(whales)
            })
        return records

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
            whales_qual = self.data_loader.find_qualified_whales(
                start_ts=start_ts,
                end_ts=end_ts,
                lookback_days=getattr(self.base_config, "lookback_days", 60),
                max_whales=10
            )
            whale_addresses = [q.address for q in whales_qual]

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
