"""
Baleen High-Fidelity Quantitative Backtesting System
 realistic copy-trading backtesting on Polymarket historical parquet datasets.
"""
from app.backtesting.config import BacktestConfig
from app.backtesting.models import TradeSignal, ExecutionFill, PortfolioPosition, ClosedTrade, BacktestResult
from app.backtesting.execution import RealisticExecutionModel
from app.backtesting.portfolio import SimulatedPortfolio
from app.backtesting.engine import BacktestEngine
from app.backtesting.strategies import (
    BaseStrategy,
    FixedProportionalStrategy,
    SleeveConvictionStrategy,
    FeeAwareGatedStrategy,
    AntiConflictGatedStrategy,
    AdaptiveProductionStrategy,
)
from app.backtesting.optimizer import StrategyOptimizer

__all__ = [
    "BacktestConfig",
    "TradeSignal",
    "ExecutionFill",
    "PortfolioPosition",
    "ClosedTrade",
    "BacktestResult",
    "RealisticExecutionModel",
    "SimulatedPortfolio",
    "BacktestEngine",
    "BaseStrategy",
    "FixedProportionalStrategy",
    "SleeveConvictionStrategy",
    "FeeAwareGatedStrategy",
    "AntiConflictGatedStrategy",
    "AdaptiveProductionStrategy",
    "StrategyOptimizer",
]
