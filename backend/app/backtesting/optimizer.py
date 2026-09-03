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
    BaleenDynamicSizerStrategy,
    ProportionalSleeveStrategy,
    IntuitiveProportionalStrategy,
)

logger = logging.getLogger(__name__)

class StrategyOptimizer:
    def __init__(self, base_config: BacktestConfig):
        self.base_config = base_config
        self.data_loader = PolymarketDataLoader(base_config)

    def get_key_comparison_strategies(self, entry_usd: float = 100.0) -> List[BaseStrategy]:
        """Returns the core suite of key strategies for institutional head-to-head comparison."""
        return [
            ProportionalSleeveStrategy(sizing_mode="pure_proportional", enable_anti_conflict=True, name="Proportional_Sleeve_Base"),
            ProportionalSleeveStrategy(sizing_mode="conviction_scaled", enable_anti_conflict=True, name="Proportional_Sleeve_Conviction"),
            ProportionalSleeveStrategy(sizing_mode="fee_aware", enable_anti_conflict=True, name="Proportional_Sleeve_FeeAware"),
            BaleenDynamicSizerStrategy(enable_anti_conflict=True, name="Baleen_DynamicSizer_AntiConflict"),
            FixedAmountEntryStrategy(entry_usd=entry_usd, name=f"FixedEntry_${int(entry_usd)}"),
            GoldSniperStrategy(min_conviction=0.70, name="HighConviction_GoldSnipers"),
            ResolutionHoldStrategy(fraction=0.03, name="Resolution_Hold_DiamondHands"),
            ConsensusConfirmationStrategy(min_whales=2, window_sec=86400.0, name="Consensus_2Whales_Confirm"),
        ]

    def get_standard_strategy_suite(self, entry_usd: float = 100.0) -> List[BaseStrategy]:
        """Returns the full suite of distinct strategy architectures."""
        return [
            BaleenDynamicSizerStrategy(enable_anti_conflict=False, name="Baleen_DynamicSizer_NetWorth"),
            BaleenDynamicSizerStrategy(enable_anti_conflict=True, name="Baleen_DynamicSizer_AntiConflict"),
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
        entry_usd: float = 100.0,
        strategies: Optional[List[BaseStrategy]] = None,
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

        if strategies is None:
            strategies = self.get_key_comparison_strategies(entry_usd=entry_usd)

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
            elif strategy_type in ("dynamic", "baleen"):
                strat = BaleenDynamicSizerStrategy(enable_anti_conflict=True, name=f"Baleen_DynamicSizer_Cap${int(cap)}")
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
            elif strategy_type in ("dynamic", "baleen"):
                strat = BaleenDynamicSizerStrategy(enable_anti_conflict=True, name=f"Baleen_DynamicSizer_{label[:10]}")
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

    def sweep_30_configurations(
        self,
        start_ts: int,
        end_ts: int,
        limit_trades: Optional[int] = None,
        initial_capital: float = 10000.0,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[BacktestResult]]:
        """
        Executes a 30-configuration parameter sweep across structural settings:
          - Active wallets count (N in [3, 5, 8, 10, 12, 15])
          - Min whale win rate ([60%, 65%, 70%, 75%, 80%])
          - Min whale historical PnL ([$25k, $50k, $100k])
          - Sizing modes (pure proportional, conviction scaled, fee-aware EV gated)
          - Anti-conflict gating (strict per-market blocking vs un-gated)
          - Exit modes (whale mirror vs resolution hold)
        Ranks all 30 runs, identifies the optimal configuration, and returns top results.
        """
        configs = [
            # Group 1: Min Whale Win Rate variation (60%, 65%, 70%, 75%, 80%) [Runs 1-5]
            {"id": 1, "n_wallets": 10, "min_wr": 60.0, "min_pnl": 25000.0, "sizing_mode": "pure_proportional", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=10 | WR>=60% | PnL>=$25k | PureProp | AntiConflict | WhaleMirror"},
            {"id": 2, "n_wallets": 10, "min_wr": 65.0, "min_pnl": 50000.0, "sizing_mode": "pure_proportional", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=10 | WR>=65% | PnL>=$50k | PureProp | AntiConflict | WhaleMirror"},
            {"id": 3, "n_wallets": 10, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "pure_proportional", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=10 | WR>=70% | PnL>=$50k | PureProp | AntiConflict | WhaleMirror"},
            {"id": 4, "n_wallets": 10, "min_wr": 75.0, "min_pnl": 50000.0, "sizing_mode": "pure_proportional", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=10 | WR>=75% | PnL>=$50k | PureProp | AntiConflict | WhaleMirror"},
            {"id": 5, "n_wallets": 10, "min_wr": 80.0, "min_pnl": 50000.0, "sizing_mode": "pure_proportional", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=10 | WR>=80% | PnL>=$50k | PureProp | AntiConflict | WhaleMirror (GoldSnipers)"},

            # Group 2: Active Wallets Count N variation (N=3, 5, 8, 12, 15) [Runs 6-10]
            {"id": 6, "n_wallets": 3, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "pure_proportional", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=3  | WR>=70% | PnL>=$50k | PureProp | AntiConflict | WhaleMirror"},
            {"id": 7, "n_wallets": 5, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "pure_proportional", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=5  | WR>=70% | PnL>=$50k | PureProp | AntiConflict | WhaleMirror"},
            {"id": 8, "n_wallets": 8, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "pure_proportional", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=8  | WR>=70% | PnL>=$50k | PureProp | AntiConflict | WhaleMirror"},
            {"id": 9, "n_wallets": 12, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "pure_proportional", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=12 | WR>=70% | PnL>=$50k | PureProp | AntiConflict | WhaleMirror"},
            {"id": 10, "n_wallets": 15, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "pure_proportional", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=15 | WR>=70% | PnL>=$50k | PureProp | AntiConflict | WhaleMirror"},

            # Group 3: Min Whale Historical PnL variation ($25k, $50k, $100k) [Runs 11-13]
            {"id": 11, "n_wallets": 8, "min_wr": 70.0, "min_pnl": 25000.0, "sizing_mode": "pure_proportional", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=8  | WR>=70% | PnL>=$25k | PureProp | AntiConflict | WhaleMirror"},
            {"id": 12, "n_wallets": 8, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "pure_proportional", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=8  | WR>=70% | PnL>=$50k | PureProp | AntiConflict | WhaleMirror"},
            {"id": 13, "n_wallets": 8, "min_wr": 70.0, "min_pnl": 100000.0, "sizing_mode": "pure_proportional", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=8  | WR>=70% | PnL>=$100k| PureProp | AntiConflict | WhaleMirror"},

            # Group 4: Conviction Scaled Sizing across wallet counts & win rates [Runs 14-18]
            {"id": 14, "n_wallets": 5, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "conviction_scaled", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=5  | WR>=70% | PnL>=$50k | ConvictionProp | AntiConflict | WhaleMirror"},
            {"id": 15, "n_wallets": 8, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "conviction_scaled", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=8  | WR>=70% | PnL>=$50k | ConvictionProp | AntiConflict | WhaleMirror"},
            {"id": 16, "n_wallets": 10, "min_wr": 75.0, "min_pnl": 50000.0, "sizing_mode": "conviction_scaled", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=10 | WR>=75% | PnL>=$50k | ConvictionProp | AntiConflict | WhaleMirror"},
            {"id": 17, "n_wallets": 12, "min_wr": 75.0, "min_pnl": 50000.0, "sizing_mode": "conviction_scaled", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=12 | WR>=75% | PnL>=$50k | ConvictionProp | AntiConflict | WhaleMirror"},
            {"id": 18, "n_wallets": 15, "min_wr": 80.0, "min_pnl": 50000.0, "sizing_mode": "conviction_scaled", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=15 | WR>=80% | PnL>=$50k | ConvictionProp | AntiConflict | WhaleMirror"},

            # Group 5: Fee-Aware EV Gated Sizing across wallet counts & win rates [Runs 19-23]
            {"id": 19, "n_wallets": 5, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "fee_aware", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=5  | WR>=70% | PnL>=$50k | FeeAwareProp | AntiConflict | WhaleMirror"},
            {"id": 20, "n_wallets": 8, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "fee_aware", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=8  | WR>=70% | PnL>=$50k | FeeAwareProp | AntiConflict | WhaleMirror"},
            {"id": 21, "n_wallets": 10, "min_wr": 75.0, "min_pnl": 50000.0, "sizing_mode": "fee_aware", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=10 | WR>=75% | PnL>=$50k | FeeAwareProp | AntiConflict | WhaleMirror"},
            {"id": 22, "n_wallets": 12, "min_wr": 75.0, "min_pnl": 100000.0, "sizing_mode": "fee_aware", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=12 | WR>=75% | PnL>=$100k| FeeAwareProp | AntiConflict | WhaleMirror"},
            {"id": 23, "n_wallets": 15, "min_wr": 80.0, "min_pnl": 100000.0, "sizing_mode": "fee_aware", "anti_conflict": True, "hold_to_resolution": False, "desc": "N=15 | WR>=80% | PnL>=$100k| FeeAwareProp | AntiConflict | WhaleMirror"},

            # Group 6: Anti-Conflict Gating Comparison (Un-gated vs Gated) [Runs 24-26]
            {"id": 24, "n_wallets": 10, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "pure_proportional", "anti_conflict": False, "hold_to_resolution": False, "desc": "N=10 | WR>=70% | PnL>=$50k | PureProp | Ungated | WhaleMirror"},
            {"id": 25, "n_wallets": 10, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "conviction_scaled", "anti_conflict": False, "hold_to_resolution": False, "desc": "N=10 | WR>=70% | PnL>=$50k | ConvictionProp | Ungated | WhaleMirror"},
            {"id": 26, "n_wallets": 10, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "fee_aware", "anti_conflict": False, "hold_to_resolution": False, "desc": "N=10 | WR>=70% | PnL>=$50k | FeeAwareProp | Ungated | WhaleMirror"},

            # Group 7: Exit Modes Comparison (Resolution Hold 'Diamond Hands' vs Whale Mirror) [Runs 27-30]
            {"id": 27, "n_wallets": 10, "min_wr": 70.0, "min_pnl": 50000.0, "sizing_mode": "pure_proportional", "anti_conflict": True, "hold_to_resolution": True, "desc": "N=10 | WR>=70% | PnL>=$50k | PureProp | AntiConflict | DiamondHands"},
            {"id": 28, "n_wallets": 5, "min_wr": 75.0, "min_pnl": 50000.0, "sizing_mode": "conviction_scaled", "anti_conflict": True, "hold_to_resolution": True, "desc": "N=5  | WR>=75% | PnL>=$50k | ConvictionProp | AntiConflict | DiamondHands"},
            {"id": 29, "n_wallets": 10, "min_wr": 75.0, "min_pnl": 50000.0, "sizing_mode": "fee_aware", "anti_conflict": True, "hold_to_resolution": True, "desc": "N=10 | WR>=75% | PnL>=$50k | FeeAwareProp | AntiConflict | DiamondHands"},
            {"id": 30, "n_wallets": 12, "min_wr": 80.0, "min_pnl": 100000.0, "sizing_mode": "conviction_scaled", "anti_conflict": True, "hold_to_resolution": True, "desc": "N=12 | WR>=80% | PnL>=$100k| ConvictionProp | AntiConflict | DiamondHands"}
        ]

        whales_cache = {}
        records = []
        results_map = {}

        logger.info(f"Executing 30-configuration parameter sweep from {start_ts} to {end_ts}...")
        for c in configs:
            cache_key = (c["min_pnl"], c["min_wr"], c["n_wallets"])
            if cache_key not in whales_cache:
                whales_qual = self.data_loader.find_qualified_whales(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    lookback_days=getattr(self.base_config, "lookback_days", 60),
                    min_pnl=c["min_pnl"],
                    min_win_rate=c["min_wr"],
                    max_whales=c["n_wallets"]
                )
                whales_cache[cache_key] = whales_qual
            else:
                whales_qual = whales_cache[cache_key]

            whale_addrs = [q.address for q in whales_qual]

            strat = ProportionalSleeveStrategy(
                sizing_mode=c["sizing_mode"],
                enable_anti_conflict=c["anti_conflict"],
                hold_to_resolution=c["hold_to_resolution"],
                n_active=c["n_wallets"],
                name=f"Config_{c['id']:02d}_{c['desc'].split(' | ')[3]}"
            )
            strat.set_qualified_roster(whales_qual)

            cfg = copy.deepcopy(self.base_config)
            cfg.initial_capital = initial_capital
            cfg.hold_to_resolution = c["hold_to_resolution"]
            cfg.min_trade_size_usd = 1.0
            cfg.max_sleeve_fraction = max(self.base_config.max_sleeve_fraction, 1.0 / c["n_wallets"])

            engine = BacktestEngine(config=cfg, strategy=strat, data_loader=self.data_loader)
            res = engine.run(
                start_ts=start_ts,
                end_ts=end_ts,
                whale_addresses=whale_addrs,
                limit_trades=limit_trades
            )
            results_map[c["id"]] = res

            score = (res.sharpe_ratio * res.profit_factor) / max(1.0, res.max_drawdown_pct)
            records.append({
                "config_id": c["id"],
                "description": c["desc"],
                "n_wallets": c["n_wallets"],
                "min_wr": c["min_wr"],
                "min_pnl": c["min_pnl"],
                "sizing_mode": c["sizing_mode"],
                "anti_conflict": c["anti_conflict"],
                "exit_mode": "DiamondHands" if c["hold_to_resolution"] else "WhaleMirror",
                "net_pnl": res.total_net_pnl,
                "roi_pct": res.roi_pct,
                "annualized_roi_pct": res.annualized_roi_pct,
                "sharpe_ratio": res.sharpe_ratio,
                "sortino_ratio": res.sortino_ratio,
                "max_drawdown_pct": res.max_drawdown_pct,
                "win_rate_pct": res.win_rate_pct,
                "profit_factor": res.profit_factor,
                "total_trades": res.total_trades,
                "total_fees_usd": res.total_fees_usd,
                "composite_score": round(score, 3)
            })

        # Rank all 30 configurations by composite score and net PnL
        records.sort(key=lambda r: (r["composite_score"], r["net_pnl"]), reverse=True)
        for rank, r in enumerate(records, 1):
            r["rank"] = rank

        best_cfg = records[0]
        # Return top 6 distinct BacktestResult objects for chart rendering
        top_results = [results_map[r["config_id"]] for r in records[:6]]

        return records, best_cfg, top_results

    def close(self):
        self.data_loader.close()

