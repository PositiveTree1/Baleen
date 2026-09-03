"""
Backtest Reporting and Visualization Formatter
Generates clean markdown comparison tables, trade distributions, and risk summaries.
"""
from typing import List, Dict, Any
from app.backtesting.models import BacktestResult

def format_comparison_table(results: List[BacktestResult]) -> str:
    """Generates a markdown table comparing multiple backtest strategy results."""
    lines = [
        "| Strategy | Net PnL ($) | ROI (%) | Ann. ROI (%) | Sharpe | Max DD (%) | Win Rate (%) | Profit Factor | Trades | Fees ($) | Slippage ($) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    for r in results:
        lines.append(
            f"| **{r.strategy_name}** | ${r.total_net_pnl:+,.2f} | {r.roi_pct:+.2f}% | {r.annualized_roi_pct:+.1f}% | "
            f"{r.sharpe_ratio:.2f} | {r.max_drawdown_pct:.1f}% | {r.win_rate_pct:.1f}% | {r.profit_factor:.2f} | "
            f"{r.total_trades} | ${r.total_fees_usd:,.2f} | ${r.total_slippage_usd:,.2f} |"
        )
    return "\n".join(lines)


def format_parameter_sweep_table(sweep_records: List[Dict[str, Any]]) -> str:
    """Generates a markdown table of parameter optimization sweep results."""
    lines = [
        "| Rank | Latency | Adverse Bias | EV Hurdle | Net PnL ($) | ROI (%) | Sharpe | Max DD (%) | Win Rate (%) | Profit Factor | Composite Score |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    for idx, s in enumerate(sweep_records[:15], 1):
        lines.append(
            f"| #{idx} | {int(s['latency_ms'])}ms | {int(s['adverse_bias_bps'])} bps | {s['ev_multiplier']}x | "
            f"${s['net_pnl']:+,.2f} | {s['roi_pct']:+.2f}% | {s['sharpe_ratio']:.2f} | {s['max_drawdown_pct']:.1f}% | "
            f"{s['win_rate_pct']:.1f}% | {s['profit_factor']:.2f} | **{s['composite_score']:.3f}** |"
        )
    return "\n".join(lines)


def format_capital_sweep_table(records: List[Dict[str, Any]]) -> str:
    """Generates a markdown table of multi-capital simulation results."""
    lines = [
        "| Starting Capital | Entry Sizing | Net PnL ($) | ROI (%) | Ann. ROI (%) | Sharpe | Max DD (%) | Win Rate (%) | Profit Factor | Trades | Fees ($) |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    for r in records:
        lines.append(
            f"| **${r['capital']:,.0f}** | ${r['entry_usd']:.0f} | ${r['net_pnl']:+,.2f} | {r['roi_pct']:+.2f}% | "
            f"{r['annualized_roi_pct']:+.1f}% | {r['sharpe_ratio']:.2f} | {r['max_drawdown_pct']:.1f}% | "
            f"{r['win_rate_pct']:.1f}% | {r['profit_factor']:.2f} | {r['total_trades']} | ${r['total_fees_usd']:,.2f} |"
        )
    return "\n".join(lines)


def format_window_sweep_table(records: List[Dict[str, Any]]) -> str:
    """Generates a markdown table of multi-window simulation results."""
    lines = [
        "| Time Window | Duration | Whales | Trades | Net PnL ($) | ROI (%) | Sharpe | Max DD (%) | Win Rate (%) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    for r in records:
        lines.append(
            f"| **{r['window']}** | {r['duration_days']:.0f} days | {r['whales_count']} | {r['total_trades']} | "
            f"${r['net_pnl']:+,.2f} | {r['roi_pct']:+.2f}% | {r['sharpe_ratio']:.2f} | {r['max_drawdown_pct']:.1f}% | {r['win_rate_pct']:.1f}% |"
        )
    return "\n".join(lines)

