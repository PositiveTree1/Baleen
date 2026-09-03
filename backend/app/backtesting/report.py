"""
Backtest Reporting and Visualization Formatter
Generates clean markdown comparison tables, trade distributions, and risk summaries.
"""
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
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


def format_30_sweep_table(records: List[Dict[str, Any]]) -> str:
    """Generates a comprehensive markdown table of the 30-configuration parameter sweep."""
    lines = [
        "| Rank | Config | Description | Net PnL ($) | ROI (%) | Sharpe | Sortino | Max DD (%) | Win Rate (%) | Profit Factor | Trades | Fees ($) | Composite Score |",
        "| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    for r in records:
        lines.append(
            f"| #{r['rank']} | #{r['config_id']:02d} | {r['description']} | ${r['net_pnl']:+,.2f} | {r['roi_pct']:+.2f}% | "
            f"{r['sharpe_ratio']:.2f} | {r['sortino_ratio']:.2f} | {r['max_drawdown_pct']:.1f}% | {r['win_rate_pct']:.1f}% | "
            f"{r['profit_factor']:.2f} | {r['total_trades']} | ${r['total_fees_usd']:,.2f} | **{r['composite_score']:.3f}** |"
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


def generate_comparison_charts(
    results: List[BacktestResult],
    output_dir: str = "backend/data",
    extra_output_dirs: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Renders clean, institutional matplotlib charts comparing backtested strategies:
      1. strategy_equity_curves.png - Multi-strategy cumulative equity trajectories over time
      2. strategy_cumulative_pnl.png - Cumulative net PnL progression over time
      3. strategy_performance_metrics.png - Multi-metric comparative bar charts (PnL, ROI, Win Rate, Sharpe)
    Saves to output_dir and any extra_output_dirs (e.g. brain artifacts folder).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    all_dirs = [output_dir] + (extra_output_dirs or [])
    for d in all_dirs:
        os.makedirs(d, exist_ok=True)

    color_palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]

    saved_files = {}

    # 1. Equity Curves
    fig, ax = plt.subplots(figsize=(12, 6.5))
    for idx, r in enumerate(results):
        color = color_palette[idx % len(color_palette)]
        if r.equity_curve:
            dates = [datetime.fromtimestamp(p.timestamp, tz=timezone.utc) for p in r.equity_curve]
            equities = [p.total_equity for p in r.equity_curve]
        else:
            dates = [datetime.fromtimestamp(r.start_timestamp, tz=timezone.utc), datetime.fromtimestamp(r.end_timestamp, tz=timezone.utc)]
            equities = [r.initial_capital, r.final_equity]

        clean_name = r.strategy_name.replace("$", "")
        lbl = f"{clean_name} (${r.final_equity:,.0f} | {r.roi_pct:+.1f}%)"
        ax.plot(dates, equities, label=lbl, color=color, linewidth=2.0, alpha=0.9)

    ax.axhline(results[0].initial_capital if results else 10000.0, color="gray", linestyle="--", alpha=0.6, label="Starting Capital")
    ax.set_title("Baleen Institutional Backtest — Strategy Cumulative Equity Curves", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("Portfolio Total Equity ($)", fontsize=11)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.legend(loc="upper left", framealpha=0.9, fontsize=9.5)
    plt.tight_layout()

    for d in all_dirs:
        eq_path = os.path.join(d, "strategy_equity_curves.png")
        fig.savefig(eq_path, dpi=150)
        saved_files[f"equity_curves_{d}"] = eq_path
    plt.close(fig)

    # 2. Cumulative Net PnL Over Time
    fig, ax = plt.subplots(figsize=(12, 6.5))
    for idx, r in enumerate(results):
        color = color_palette[idx % len(color_palette)]
        if r.equity_curve:
            dates = [datetime.fromtimestamp(p.timestamp, tz=timezone.utc) for p in r.equity_curve]
            pnls = [p.total_equity - r.initial_capital for p in r.equity_curve]
        else:
            dates = [datetime.fromtimestamp(r.start_timestamp, tz=timezone.utc), datetime.fromtimestamp(r.end_timestamp, tz=timezone.utc)]
            pnls = [0.0, r.total_net_pnl]

        clean_name = r.strategy_name.replace("$", "")
        lbl = f"{clean_name} (${r.total_net_pnl:+,.0f} | Sharpe {r.sharpe_ratio:.2f})"
        ax.plot(dates, pnls, label=lbl, color=color, linewidth=2.0, alpha=0.9)

    ax.axhline(0.0, color="black", linestyle="-", linewidth=1.0, alpha=0.7)
    ax.set_title("Baleen Quantitative Backtest — Cumulative Net PnL ($) Over Time", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("Cumulative Net PnL ($)", fontsize=11)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.legend(loc="upper left", framealpha=0.9, fontsize=9.5)
    plt.tight_layout()

    for d in all_dirs:
        pnl_path = os.path.join(d, "strategy_cumulative_pnl.png")
        fig.savefig(pnl_path, dpi=150)
        saved_files[f"cumulative_pnl_{d}"] = pnl_path
    plt.close(fig)

    # 3. Multi-Metric Performance Comparison (2x2 Bar Chart)
    fig, axes = plt.subplots(2, 2, figsize=(14, 9.5))
    strat_names = [r.strategy_name.replace("Baleen_", "").replace("_", "\n") for r in results]

    # Net PnL ($)
    pnls = [r.total_net_pnl for r in results]
    p_min = min(min(pnls), 0.0)
    p_max = max(max(pnls), 0.0)
    p_span = max(100.0, p_max - p_min)
    bar_colors = ["#2ca02c" if p >= 0 else "#d62728" for p in pnls]
    axes[0, 0].bar(strat_names, pnls, color=bar_colors, alpha=0.85)
    axes[0, 0].axhline(0, color="gray", linestyle="--", alpha=0.5)
    axes[0, 0].set_title("Net PnL ($)", fontsize=12, fontweight="bold")
    axes[0, 0].set_ylabel("USD ($)")
    axes[0, 0].set_ylim(p_min - p_span * 0.15, p_max + p_span * 0.15)
    axes[0, 0].grid(True, axis="y", linestyle=":", alpha=0.6)
    for i, v in enumerate(pnls):
        offset = p_span * 0.03 if v >= 0 else -p_span * 0.07
        axes[0, 0].text(i, v + offset, f"${v:+,.0f}", ha="center", fontsize=9, fontweight="bold")

    # Annualized ROI (%)
    rois = [r.roi_pct for r in results]
    r_min = min(min(rois), 0.0)
    r_max = max(max(rois), 0.0)
    r_span = max(5.0, r_max - r_min)
    axes[0, 1].bar(strat_names, rois, color="#1f77b4", alpha=0.85)
    axes[0, 1].axhline(0, color="gray", linestyle="--", alpha=0.5)
    axes[0, 1].set_title("Total ROI (%)", fontsize=12, fontweight="bold")
    axes[0, 1].set_ylabel("ROI (%)")
    axes[0, 1].set_ylim(r_min - r_span * 0.15, r_max + r_span * 0.15)
    axes[0, 1].grid(True, axis="y", linestyle=":", alpha=0.6)
    for i, v in enumerate(rois):
        offset = r_span * 0.03 if v >= 0 else -r_span * 0.07
        axes[0, 1].text(i, v + offset, f"{v:+.1f}%", ha="center", fontsize=9, fontweight="bold")

    # Win Rate (%)
    win_rates = [r.win_rate_pct for r in results]
    axes[1, 0].bar(strat_names, win_rates, color="#ff7f0e", alpha=0.85)
    axes[1, 0].axhline(50.0, color="red", linestyle=":", alpha=0.7, label="50% Breakeven")
    axes[1, 0].set_title("Win Rate (%)", fontsize=12, fontweight="bold")
    axes[1, 0].set_ylabel("Win Rate (%)")
    axes[1, 0].set_ylim(0, 115)
    axes[1, 0].grid(True, axis="y", linestyle=":", alpha=0.6)
    for i, v in enumerate(win_rates):
        axes[1, 0].text(i, v + 2.5, f"{v:.1f}%", ha="center", fontsize=9, fontweight="bold")

    # Sharpe Ratio
    sharpes = [r.sharpe_ratio for r in results]
    s_min = min(min(sharpes), 0.0)
    s_max = max(max(sharpes), 0.0)
    s_span = max(5.0, s_max - s_min)
    axes[1, 1].bar(strat_names, sharpes, color="#9467bd", alpha=0.85)
    axes[1, 1].axhline(0, color="gray", linestyle="--", alpha=0.5)
    axes[1, 1].set_title("Sharpe Ratio", fontsize=12, fontweight="bold")
    axes[1, 1].set_ylabel("Sharpe")
    axes[1, 1].set_ylim(s_min - s_span * 0.15, s_max + s_span * 0.15)
    axes[1, 1].grid(True, axis="y", linestyle=":", alpha=0.6)
    for i, v in enumerate(sharpes):
        offset = s_span * 0.03 if v >= 0 else -s_span * 0.07
        axes[1, 1].text(i, v + offset, f"{v:.2f}", ha="center", fontsize=9, fontweight="bold")

    fig.suptitle("Baleen Quantitative Strategy Suite — Institutional Performance Matrix", fontsize=15, fontweight="bold", y=0.99)
    plt.tight_layout()

    for d in all_dirs:
        matrix_path = os.path.join(d, "strategy_performance_metrics.png")
        fig.savefig(matrix_path, dpi=150)
        saved_files[f"metrics_matrix_{d}"] = matrix_path
    plt.close(fig)

    return saved_files

