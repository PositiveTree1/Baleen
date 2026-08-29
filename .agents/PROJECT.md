# Project: Baleen Comprehensive Scenario Modeling & Invariant Stress-Testing

## Architecture
Baleen is an automated copy-trading and market discovery platform for Polymarket prediction markets.
- **Core Engine & Execution**: `backend/app/services/live_poller.py`, `backend/app/sizing/fill_simulator.py`, `backend/app/sizing/dynamic_sizing.py`, `backend/app/services/polymarket_fees.py`.
- **Valuation & MTM State Machine**: `backend/app/services/mark_to_market.py`, `backend/app/models.py`.
- **Ingestion & Network Pipeline**: `listener/src/hypersync.ts`, `listener/src/poller.ts`, `backend/app/api/endpoints/webhooks.py`.
- **Scoring & Discovery**: `backend/app/scoring/`, `backend/app/discovery/`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Order Book & Liquidity Extremes | Empty books, inverted books, micro-liquidity, whale orders, 0.99 to 0.01 shocks, zero-price contracts | M-A1, M-B2 | Survey |
| 2 | Dynamic Sizing & Slippage Model | Multi-tier book depth consumption, non-mutating sort, case-insensitive side matching, zero-division guards | M-A1, M-B2 | Survey |
| 3 | 2026 Quadratic Polymarket Fees | $\Theta \in [0.00, 0.072]$ across 6 asset classes with exact zero-price clamp ($p=0.0 \to 0.001$) | M-A1, M-B2 | Survey |
| 4 | State Machine Cash Invariance | `Free Cash = Settled Cash - Open Margin`, non-negative cash, no unearned MTM inflation | M-A2, M-B2 | Survey |
| 5 | FIFO Lot Splitting & Conservation | Partial trade closures with exact notional, share, and transaction fee conservation | M-A2, M-B2 | Survey |
| 6 | Ghost Sell Fill & Leak Prevention | Ensure users with 0 open positions do not log phantom SELL fills or deduct unearned fees | M-A2, M-B2 | Survey |
| 7 | Non-Decreasing High-Water Mark | HWM strictly monotonic, ratcheting on verified equity without floating phantom inflation | M-A2, M-B2 | Survey |
| 8 | Timing & Async Latency Dynamics | Asynchronous block latency (1s-60s), out-of-order Envio logs, duplicate transaction idempotency | M-A3, M-B2 | Survey |
| 9 | Out-of-Order SELL/BUY Guarding | Prevent dropped SELLs and orphaned open BUY positions when log arrivals invert | M-A3, M-B2 | Survey |
| 10 | Binary Resolution & Payout Logic | Settlement at $1.00/$0.00, condition ID redemption, and lot closure | M-A3, M-B2 | Survey |
| 11 | Multi-Tenancy & Risk Profiles | Concurrent users (Conservative 5%, Balanced 10%, Aggressive 20%), zero-balance/drawdown edge states | M-A2, M-B2 | Survey |
| 12 | 220-Scenario Automated Test Matrix | Programmatic stress engine executing 220+ edge cases across all 4 operational domains | M-B1, M-B2, M-B3 | Survey |

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M-A1 | Core Execution & Order Book Robustness | Fix `fill_simulator.py` mutation/case/zero-division, `polymarket_fees.py` zero-price bug, `live_poller.py:351` notional bug | None | PLANNED |
| M-A2 | FIFO Lot Splitting, Cash Invariance & Ghost Sells | Fix `live_poller.py` partial split fee zeroing, ghost user SELLs, MTM HWM inflation, cash bounds | M-A1 | PLANNED |
| M-A3 | Ingestion, Out-of-Order Logging & Settlement | Fix out-of-order SELL/BUY race condition, platform log deduplication, binary resolution lifecycle | M-A2 | PLANNED |
| M-B1 | Scenario Test Infrastructure & Invariant Monitor | Create scenario runner, mock book/event generators, and 10-invariant assertion engine | None | PLANNED |
| M-B2 | 220-Scenario Stress Matrix Implementation | Implement 220 distinct scenarios (55 Order Book, 55 Network/Timing, 55 Lifecycle/FIFO, 55 Multi-Tenancy) | M-B1, M-A1, M-A2, M-A3 | PLANNED |
| M-B3 | Final Invariant Verification & E2E Validation | Run full 220-scenario suite, verify 100% invariant satisfaction and 100% pytest pass rate | M-B2 | PLANNED |

## Interface Contracts
### Order Book Simulator ↔ Sizing Engine
- `simulate_fill(order_book: dict, side: str, target_value: float) -> tuple[float, float, float]`
  - `side` accepted in any case (`"BUY"`, `"buy"`, `"SELL"`, `"sell"`)
  - Input `order_book` is treated as immutable (no in-place modification)
  - Returns `(effective_price, total_shares, slippage_pct)` safely bounded against zero division.

### Fee Calculation Contract
- `calculate_fee(category: str, price: float, notional: float) -> Decimal`
  - $p$ strictly clamped in $[0.001, 0.999]$; $p=0.0$ evaluates to $0.001$, NOT $0.50$.

### FIFO Lot Split Contract
- For partial fill $V_{\text{closed}} < V_{\text{open}}$:
  - $\text{Original Lot: } V' = V_{\text{closed}}, \quad \text{Fee}' = \text{round}(\text{Fee}_{\text{orig}} \cdot \frac{V_{\text{closed}}}{V_{\text{open}}}, 4), \quad \text{Status} = \text{"CLOSED"}$
  - $\text{Split Lot: } V'' = V_{\text{open}} - V_{\text{closed}}, \quad \text{Fee}'' = \text{Fee}_{\text{orig}} - \text{Fee}', \quad \text{Status} = \text{"FILLED"}$
  - Invariant: $V' + V'' = V_{\text{open}}$ and $\text{Fee}' + \text{Fee}'' = \text{Fee}_{\text{orig}}$.

## Code Layout
- `backend/app/sizing/fill_simulator.py`: Non-mutating order book matching and slippage simulation.
- `backend/app/services/polymarket_fees.py`: 2026 Quadratic Polymarket fee curves with zero-price clamping.
- `backend/app/services/live_poller.py`: Core trade copy execution, FIFO partial liquidation, user sizing, and position guards.
- `backend/app/services/mark_to_market.py`: MTM valuation, PnL calculations, and monotonic HWM tracking.
- `backend/app/models.py`: Database models, unique constraints, and schema definitions.
- `backend/tests/scenarios/`: Scenario test engine, invariant checkers, and 220-scenario regression suites.
