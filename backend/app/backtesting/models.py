"""
Backtesting Data Models
Typed structures for signals, execution fills, positions, closed trades, and summary metrics.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class TradeSignal:
    timestamp: int
    whale_address: str
    market_id: str
    condition_id: str
    token_id: str
    side: str  # "BUY" or "SELL"
    whale_price: float
    whale_size_usd: float
    whale_shares: float
    market_title: str = ""
    category: str = "General"
    nonusdc_side: str = "token1"  # "token1" or "token2"

@dataclass
class ExecutionFill:
    order_id: str
    signal: TradeSignal
    intended_size_usd: float
    fill_price: float
    filled_size_usd: float
    filled_shares: float
    slippage_bps: float
    fee_usd: float
    latency_ms: float
    status: str  # "FILLED", "PARTIALLY_FILLED", "REJECTED_SLIPPAGE", "SKIPPED_CAPITAL", "SKIPPED_EV_GATE"
    executed_at: float
    rejection_reason: Optional[str] = None

@dataclass
class PortfolioPosition:
    position_id: str
    market_id: str
    condition_id: str
    token_id: str
    outcome_token: str  # "token1" or "token2"
    side: str  # "BUY"
    shares: float
    avg_fill_price: float
    total_cost_usd: float
    fees_paid_usd: float
    opened_at: float
    whale_address: str
    category: str = "General"
    market_title: str = ""

@dataclass
class ClosedTrade:
    trade_id: str
    whale_address: str
    market_id: str
    condition_id: str
    token_id: str
    outcome_token: str
    category: str
    entry_price: float
    exit_price: float
    shares: float
    total_invested: float
    gross_pnl: float
    entry_fee_usd: float
    exit_fee_usd: float
    total_fees_usd: float
    net_pnl: float
    roi_pct: float
    opened_at: float
    closed_at: float
    hold_duration_sec: float
    exit_reason: str  # "RESOLUTION_WIN", "RESOLUTION_LOSS", "WHALE_SELL_EXIT"

@dataclass
class EquityPoint:
    timestamp: float
    cash_balance: float
    invested_notional: float
    total_equity: float
    realized_pnl: float
    unrealized_pnl: float
    drawdown_pct: float

@dataclass
class BacktestResult:
    strategy_name: str
    config: Any
    start_timestamp: int
    end_timestamp: int
    duration_days: float
    initial_capital: float
    final_equity: float
    total_net_pnl: float
    roi_pct: float
    annualized_roi_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    max_drawdown_usd: float
    win_rate_pct: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_fees_usd: float
    total_slippage_usd: float
    avg_trade_pnl: float
    equity_curve: List[EquityPoint] = field(default_factory=list)
    closed_trades: List[ClosedTrade] = field(default_factory=list)
    wallet_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    category_performance: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy_name,
            "initial_capital": self.initial_capital,
            "final_equity": round(self.final_equity, 2),
            "net_pnl": round(self.total_net_pnl, 2),
            "roi_pct": round(self.roi_pct, 2),
            "annualized_roi_pct": round(self.annualized_roi_pct, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 3),
            "sortino_ratio": round(self.sortino_ratio, 3),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "win_rate_pct": round(self.win_rate_pct, 1),
            "profit_factor": round(self.profit_factor, 2),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_fees_usd": round(self.total_fees_usd, 2),
            "total_slippage_usd": round(self.total_slippage_usd, 2),
            "avg_trade_pnl": round(self.avg_trade_pnl, 2),
        }
