"""
Baleen Scenario Test Infrastructure & Invariant Stress Matrix Package.

Provides state machine invariant monitors, synthetic market factories, and
a parametric test runner harness for 220+ edge-case scenarios across:
  - Tier 1: Order Book & Liquidity Extremes
  - Tier 2: Timing, Network & Settlement Dynamics
  - Tier 3: Complex Position & Lifecycle Sequences
  - Tier 4: Multi-Tenancy & Portfolio Scaling
"""

from tests.scenarios.invariant_monitor import (
    InvariantMonitor,
    InvariantResult,
    InvariantViolation,
    InvariantSeverity,
    InvariantCheckType,
    PortfolioState,
    PositionLot,
    TradeExecution,
)
from tests.scenarios.mock_market_factory import (
    MockMarketFactory,
    OrderBookLevel,
    OrderBookSnapshot,
    SyntheticEvent,
    EventStreamGenerator,
)
from tests.scenarios.runner import (
    ScenarioRunner,
    ScenarioDefinition,
    ScenarioStep,
    ScenarioResult,
    ScenarioReport,
)

__all__ = [
    "InvariantMonitor",
    "InvariantResult",
    "InvariantViolation",
    "InvariantSeverity",
    "InvariantCheckType",
    "PortfolioState",
    "PositionLot",
    "TradeExecution",
    "MockMarketFactory",
    "OrderBookLevel",
    "OrderBookSnapshot",
    "SyntheticEvent",
    "EventStreamGenerator",
    "ScenarioRunner",
    "ScenarioDefinition",
    "ScenarioStep",
    "ScenarioResult",
    "ScenarioReport",
]
