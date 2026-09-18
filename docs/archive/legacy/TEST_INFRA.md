# E2E Test Infra: Baleen Whale Copy-Trading Platform

## Test Philosophy
- Opaque-box, requirement-driven testing directly derived from `ORIGINAL_REQUEST.md`.
- Multi-tier testing hierarchy across all 14 features in the Feature Inventory.

## Feature Inventory & Test Coverage Mapping
| # | Feature | Requirement | Tier 1 (Coverage) | Tier 2 (Boundary) | Tier 3 (Cross-Feature) | Tier 4 (Real-World) |
|---|---------|-------------|:-----------------:|:-----------------:|:----------------------:|:-------------------:|
| 1 | Polymarket Data Ingestion | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 2 | Trade History & PnL Separation | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 3 | Whale Classification & Scoring | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 4 | Dual-Column Win/Loss Bar Chart | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 5 | Chart Responsiveness & Tooltips | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 6 | Frontend Build & Type Safety | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 7 | Live Continuous Polling Loop | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 8 | Isolated Sleeve Sizing | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 9 | 2026 Quadratic Polymarket Fee Engine | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 10 | Directional Slippage & Boundary Screening | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 11 | Out-of-Order Sell Matching & Invariance | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 12 | 24/7 Resilience & State Persistence | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |

## Test Architecture & Execution
- **Backend Test Runner**: `& "C:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\pytest.exe"`
  - Target: 100% pass across all test modules (403+ unit, integration, and scenario tests).
- **Frontend Test & Build Runner**: `npm.cmd run build` inside `c:\Users\arthu\Documents\Baleen-master\frontend`
  - Target: Exit code 0, 0 TypeScript errors, Next.js production build succeeds with all 10 routes compiled.

## Test Tiers Breakdown
- **Tier 1: Feature Coverage (>=5 per feature)**: Unit and isolated integration tests for each service, model, and component.
- **Tier 2: Boundary & Corner Cases (>=5 per feature)**: Boundary price screening ($0.04 / $0.96), $0.01 / $0.99 sniper disqualification, extreme slippage, capacity exhaustion, zero trades, empty date ranges.
- **Tier 3: Cross-Feature Interactions**: Out-of-order SELL matching with fee computation, sleeve capacity updates upon binary market resolution, dynamic roster updates during continuous polling.
- **Tier 4: Real-World Workload Scenarios**: Overnight continuous 24/7 operation simulations, live wallet discovery and tracking, multi-wallet parallel execution with zero negative balances.
- **Tier 5: Adversarial Hardening**: 220-scenario adversarial stress matrix testing all 10 state machine invariants under arbitrary event interleavings.

## Thresholds
- Total Backend Tests: ≥400 passing
- Frontend TypeScript / Lint Errors: 0
- State Machine Violations / Negative Balances: 0
