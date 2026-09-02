"""
Backtest Command Line Interface & Execution Script
Executes backtesting sweeps and optimizations against E:/polymarket_data.
"""
import sys
import os
import argparse
import logging
from datetime import datetime, timezone

# Ensure project root is on sys.path
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.backtesting.config import BacktestConfig
from app.backtesting.optimizer import StrategyOptimizer
from app.backtesting.report import format_comparison_table, format_parameter_sweep_table

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backtest_runner")

def main():
    parser = argparse.ArgumentParser(description="Baleen Quantitative Backtesting System")
    parser.add_argument("--start-ts", type=int, default=1770000000, help="Start unix timestamp (default 1770000000)")
    parser.add_argument("--end-ts", type=int, default=1770604800, help="End unix timestamp (default 7 days later)")
    parser.add_argument("--limit-trades", type=int, default=5000, help="Max trades to process per strategy")
    parser.add_argument("--sweep", action="store_true", help="Run multi-parameter optimization sweep")
    parser.add_argument("--capital", type=float, default=10000.0, help="Initial portfolio capital")
    parser.add_argument("--latency", type=float, default=350.0, help="Copy latency in ms")
    parser.add_argument("--adverse-bps", type=float, default=5.0, help="Adverse bias in bps")

    args = parser.parse_args()

    config = BacktestConfig(
        initial_capital=args.capital,
        latency_ms=args.latency,
        adverse_bias_bps=args.adverse_bps
    )

    logger.info(f"=== Initializing Baleen Backtesting Engine on {config.data_dir} ===")
    logger.info(f"Time Window: {args.start_ts} -> {args.end_ts} (Limit: {args.limit_trades} trades)")

    optimizer = StrategyOptimizer(config)

    try:
        if args.sweep:
            logger.info("Running Multi-Variable Parameter Optimization Sweep...")
            sweep_results = optimizer.sweep_parameters(
                start_ts=args.start_ts,
                end_ts=args.end_ts,
                limit_trades=args.limit_trades
            )
            print("\n=== PARAMETER OPTIMIZATION SWEEP RESULTS ===")
            print(format_parameter_sweep_table(sweep_results))
        else:
            logger.info("Running Head-to-Head Strategy Comparison...")
            results = optimizer.compare_strategies(
                start_ts=args.start_ts,
                end_ts=args.end_ts,
                limit_trades=args.limit_trades
            )
            print("\n=== STRATEGY COMPARISON RESULTS ===")
            print(format_comparison_table(results))

            best = results[0]
            print(f"\n>>> THE BEST STRATEGY IS: {best.strategy_name} <<<")
            print(f"Net PnL: ${best.total_net_pnl:+,.2f} | ROI: {best.roi_pct:+.2f}% | Sharpe: {best.sharpe_ratio:.2f} | Max DD: {best.max_drawdown_pct:.1f}% | Win Rate: {best.win_rate_pct:.1f}%")

    finally:
        optimizer.close()

if __name__ == "__main__":
    main()
