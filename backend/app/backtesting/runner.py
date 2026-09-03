"""
Baleen Quantitative Backtesting Command Line Interface & Runner
Executes comprehensive backtests, multi-strategy head-to-head comparisons,
multi-capital sweeps ($1k, $5k, $10k), multi-window sweeps (1m, 3m, 6m),
and parameter optimization sweeps against E:/polymarket_data.
"""
import sys
import os
import argparse
import logging
from datetime import datetime, timezone

# Ensure backend directory is on sys.path
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.backtesting.config import BacktestConfig
from app.backtesting.data_loader import get_predefined_window
from app.backtesting.optimizer import StrategyOptimizer
from app.backtesting.report import (
    format_comparison_table,
    format_parameter_sweep_table,
    format_capital_sweep_table,
    format_window_sweep_table,
    format_30_sweep_table,
    generate_comparison_charts,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backtest_runner")

def main():
    parser = argparse.ArgumentParser(description="Baleen Quantitative Backtesting System")
    parser.add_argument("--period", type=str, default="1m", choices=["1m", "3m", "6m", "election", "custom"],
                        help="Predefined historical period (1m: 1-Month Oct 2024, 3m: 3-Month Aug-Oct 2024, 6m: 6-Month May-Oct 2024, election: Oct-Nov 2024)")
    parser.add_argument("--start-ts", type=int, default=None, help="Custom start unix timestamp (seconds)")
    parser.add_argument("--end-ts", type=int, default=None, help="Custom end unix timestamp (seconds)")
    parser.add_argument("--limit-trades", type=int, default=10000, help="Max trades to process per strategy")
    parser.add_argument("--capital", type=float, default=10000.0, help="Initial portfolio capital ($1000, $5000, $10000)")
    parser.add_argument("--entry-usd", type=float, default=100.0, help="Fixed trade entry size in USD (default $100)")
    parser.add_argument("--lookback-days", type=int, default=60, help="Pre-qualification lookback window for zero-lookahead bias (default 60 days)")
    parser.add_argument("--latency", type=float, default=350.0, help="Copy latency in ms")
    parser.add_argument("--adverse-bps", type=float, default=5.0, help="Adverse bias in bps")
    parser.add_argument("--sweep-capital", action="store_true", help="Run multi-capital sweep ($1,000, $5,000, $10,000)")
    parser.add_argument("--sweep-windows", action="store_true", help="Run multi-window duration sweep (1-Month, 3-Month, 6-Month)")
    parser.add_argument("--sweep-params", action="store_true", help="Run parameter optimization grid sweep")
    parser.add_argument("--sweep-30", action="store_true", help="Run 30-configuration structural parameter sweep")
    parser.add_argument("--all", action="store_true", help="Run full comprehensive suite (strategies, capital sweep, window sweep, 30-sweep)")

    args = parser.parse_args()

    # Determine time window
    if args.period != "custom":
        s_ts, e_ts, period_label = get_predefined_window(args.period)
    else:
        s_ts = args.start_ts or 1727740800
        e_ts = args.end_ts or 1730419200
        period_label = f"Custom ({s_ts} -> {e_ts})"

    config = BacktestConfig(
        initial_capital=args.capital,
        fixed_entry_usd=args.entry_usd,
        lookback_days=args.lookback_days,
        latency_ms=args.latency,
        adverse_bias_bps=args.adverse_bps
    )

    print("\n" + "=" * 80)
    print("      BALEEN INSTITUTIONAL QUANTITATIVE BACKTESTING SYSTEM")
    print("=" * 80)
    print(f"Data Directory     : {config.data_dir}")
    print(f"Historical Window  : {period_label} [{s_ts} -> {e_ts}]")
    print(f"Starting Capital   : ${args.capital:,.2f}")
    print(f"Fixed Entry Size   : ${args.entry_usd:.2f}")
    print(f"Lookback Window    : {args.lookback_days} days (Zero Lookahead Bias)")
    print(f"Execution Latency  : {args.latency:.1f}ms | Adverse Bias: {args.adverse_bps:.1f} bps")
    print(f"Polymarket Dynamic : Fees Enabled (Classified taker schedule) | Adverse Slippage Enabled")
    print("=" * 80 + "\n")

    optimizer = StrategyOptimizer(config)

    try:
        # 1. Strategy Comparison
        print(">>> [1/4] RUNNING HEAD-TO-HEAD STRATEGY COMPARISON <<<")
        logger.info(f"Evaluating key strategy architectures on {period_label}...")
        results = optimizer.compare_strategies(
            start_ts=s_ts,
            end_ts=e_ts,
            limit_trades=args.limit_trades,
            entry_usd=args.entry_usd
        )
        print("\n=== HEAD-TO-HEAD STRATEGY PERFORMANCE ===")
        print(format_comparison_table(results))

        best = results[0]
        print(f"\n[+] THE BEST PERFORMING STRATEGY IS: {best.strategy_name}")
        print(f"   Net PnL: ${best.total_net_pnl:+,.2f} | ROI: {best.roi_pct:+.2f}% | Sharpe: {best.sharpe_ratio:.2f} | Max DD: {best.max_drawdown_pct:.1f}% | Win Rate: {best.win_rate_pct:.1f}%\n")

        # Generate & save comparison charts
        data_dir = os.path.join(backend_root, "data")
        extra_dirs = []
        for cid in [
            "46b2eeba-fcaa-448d-b531-53aab065f8a0",
            "3558f49c-622a-4113-ae69-0a73aba3f6a5",
            "6ea603d6-3089-42fa-9408-e2af7a110866"
        ]:
            p = os.path.join("C:/Users/arthu/.gemini/antigravity/brain", cid)
            if os.path.exists(p) and p not in extra_dirs:
                extra_dirs.append(p)
        chart_files = generate_comparison_charts(results, output_dir=data_dir, extra_output_dirs=extra_dirs)
        print("[+] Generated strategy comparison graphs:")
        for k, p in chart_files.items():
            print(f"    - {k}: {p}")

        # 2. 30-Configuration Structural Parameter Sweep
        if args.sweep_30 or args.all:
            print("\n>>> [2/4] RUNNING 30-CONFIGURATION STRUCTURAL PARAMETER SWEEP <<<")
            sweep_30_records, best_30_cfg, top_30_results = optimizer.sweep_30_configurations(
                start_ts=s_ts,
                end_ts=e_ts,
                limit_trades=args.limit_trades,
                initial_capital=args.capital
            )
            print("\n=== 30-CONFIGURATION STRUCTURAL PARAMETER SWEEP RESULTS ===")
            print(format_30_sweep_table(sweep_30_records))
            print(f"\n[+] OPTIMAL CONFIGURATION: Config #{best_30_cfg['config_id']:02d} ({best_30_cfg['description']})")
            print(f"    Net PnL: ${best_30_cfg['net_pnl']:+,.2f} | ROI: {best_30_cfg['roi_pct']:+.2f}% | Sharpe: {best_30_cfg['sharpe_ratio']:.2f} | Win Rate: {best_30_cfg['win_rate_pct']:.1f}% | Composite Score: {best_30_cfg['composite_score']:.3f}\n")

            # Update charts with top performing configurations
            generate_comparison_charts(top_30_results, output_dir=data_dir, extra_output_dirs=extra_dirs)

        # 3. Multi-Capital Sweep
        if args.sweep_capital or args.all:
            print("\n>>> [3/4] RUNNING MULTI-CAPITAL SIZING SWEEP ($1,000, $5,000, $10,000) <<<")
            cap_records = optimizer.sweep_capital(
                start_ts=s_ts,
                end_ts=e_ts,
                capitals=[1000.0, 5000.0, 10000.0],
                limit_trades=args.limit_trades,
                entry_usd=args.entry_usd
            )
            print("\n=== MULTI-CAPITAL SCALING RESULTS ===")
            print(format_capital_sweep_table(cap_records))

        # 4. Multi-Window Sweep
        if args.sweep_windows or args.all:
            print("\n>>> [4/4] RUNNING MULTI-WINDOW EXTENDED DURATION SWEEP <<<")
            win_records = optimizer.sweep_windows(
                capital=args.capital,
                entry_usd=args.entry_usd,
                limit_trades=args.limit_trades
            )
            print("\n=== MULTI-WINDOW EXTENDED DURATION RESULTS ===")
            print(format_window_sweep_table(win_records))

        # 5. Parameter Grid Sweep (if requested)
        if args.sweep_params:
            print("\n>>> RUNNING PARAMETER OPTIMIZATION GRID SWEEP <<<")
            param_records = optimizer.sweep_parameters(
                start_ts=s_ts,
                end_ts=e_ts,
                limit_trades=args.limit_trades
            )
            print("\n=== PARAMETER OPTIMIZATION GRID RESULTS ===")
            print(format_parameter_sweep_table(param_records))

    finally:
        optimizer.close()

if __name__ == "__main__":
    main()
