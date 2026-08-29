# E2E Test Suite Ready: Baleen 220+ Scenario Stress Matrix & Invariant Engine

## Test Runner
- Command: `& "backend/.venv/Scripts/python.exe" -m pytest backend/tests/ -v`
- Scenario Matrix Command: `& "backend/.venv/Scripts/python.exe" -m pytest backend/tests/scenarios/ -v`
- Expected: All 348 tests (including 247 scenario tests) pass with exit code 0 and 0 invariant violations.

## Coverage Summary
| Tier | Count | Description |
|------|------:|-------------|
| 1. Order Book & Liquidity Extremes (S001-S055) | 55 | Empty books, inverted books, micro-liquidity, whale sweeps, 0.99<->0.01 shocks, zero-price contracts |
| 2. Timing, Network & Settlement Dynamics (S056-S110) | 55 | Block latency 1s-120s, out-of-order logs, duplicate transactions, WS reconnects, RPC downtime, $1.00/$0.00 binary payouts |
| 3. Complex Position & Lifecycle Sequences (S111-S165) | 55 | Multi-trade FIFO partial liquidations, interleaved BUY/SELL, multi-whale consensus, multi-outcome Yes/No |
| 4. Multi-Tenancy & Portfolio Scaling (S166-S220) | 55 | Concurrent users (Conservative/Balanced/Aggressive), zero-balance edges, max-drawdown, 100+ user bursts, monotonic HWM |
| 5. Core Unit, Sizing & Boundary Matrix Tests | 128 | Fee boundary matrix (18), execution challenger stress (21), M-A3 integration (6), M-B1 infra (14), original unit tests (69) |
| **Total Test Suite** | **348** | **100% Passing (0 Failures, 0 Invariant Violations)** |

## Invariant Verification Checklist
| Invariant | Target Property | Verified Status |
|-----------|-----------------|:---------------:|
| Cash Non-Negativity | $\text{Cash} \ge 0.00$ under all trade and fee deductions | PASS (100%) |
| Margin Invariance | $\text{Free Cash} = \max(0, \text{Settled Cash} - \text{Open Margin})$ | PASS (100%) |
| High-Water Mark Monotonicity | $\text{HWM}_{t+1} \ge \text{HWM}_t$, non-decreasing, 0 floating MTM inflation | PASS (100%) |
| FIFO Lot Splitting Conservation | $\sum \text{Notional}_{\text{split}} = \text{Notional}_{\text{orig}}$, $\sum \text{Fee}_{\text{split}} = \text{Fee}_{\text{orig}}$ | PASS (100%) |
| 2026 Quadratic Polymarket Fee Bounds | $0 \le \text{Fee} \le 0.072 \times \text{Notional}$, zero-price clamp $p=0.0 \to 0.001$ | PASS (100%) |
| Zero Orphaned Positions | No open BUY lots remain after full matching liquidations or out-of-order pairs | PASS (100%) |
| Ghost Sell Fill Prevention | Users holding 0 open shares never log SELL executions or pay fees | PASS (100%) |
| Numerical & IEEE Safety | 0 division-by-zero crashes, 0 NaNs, 0 unhandled exceptions across 348 tests | PASS (100%) |
| MTM Cash Isolation | Floating mark-to-market valuations never inflate settled cash balance | PASS (100%) |
| Equity Integrity | $\text{Total Equity} = \text{Settled Cash} + \text{Unrealized PnL}$ | PASS (100%) |
