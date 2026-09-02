"""
Backtesting Configuration Module
Defines execution constraints, latency parameters, slippage models, and fee settings.
"""
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class BacktestConfig:
    # Portfolio Capital & Limits
    initial_capital: float = 10000.0
    min_trade_size_usd: float = 5.0
    max_trade_size_usd: float = 1500.0
    max_sleeve_fraction: float = 0.10  # Max 10% of total capital allocated to any single whale sleeve
    max_market_fraction: float = 0.05  # Max 5% of total capital in any single market
    max_open_positions: int = 30

    # Execution Realism & Adverse Pricing
    # Whale trades at T, copy arrives at T + latency_ms
    latency_ms: float = 350.0
    # Intentional adverse bias in basis points to ensure zero optimistic bias:
    # Simulated copy fill will be shifted slightly worse than the whale's price
    adverse_bias_bps: float = 5.0
    # Maximum volume participation rate (e.g. 20% of whale order size or book depth)
    liquidity_participation_cap: float = 0.20

    # Feature Toggles
    enable_fees: bool = True
    enable_slippage: bool = True
    enable_ev_gate: bool = True
    ev_gate_multiplier: float = 2.5  # Edge must exceed multiplier * taker_fee

    # Data Source
    data_dir: str = "E:/polymarket_data"
    trades_file: str = "trades.parquet"
    markets_file: str = "markets.parquet"
    quant_file: str = "quant.parquet"

    # Time Window Filter (Unix timestamps in seconds)
    start_timestamp: Optional[int] = None
    end_timestamp: Optional[int] = None
