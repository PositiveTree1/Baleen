# Scope: Milestone M-B1 — Scenario Test Infrastructure & Invariant Monitor

## Objective
Build the foundational scenario testing framework, mock generators, and invariant monitoring harness in `backend/tests/scenarios/`:
1. `backend/tests/scenarios/__init__.py`
2. `backend/tests/scenarios/invariant_monitor.py`:
   - State machine monitor checking all 10 core invariants:
     * Cash non-negativity: $\text{Cash} \ge 0$
     * Margin equation: $\text{Free Cash} = \max(0, \text{Settled Cash} - \text{Open Margin})$
     * High-Water Mark monotonicity: $\text{HWM}_{t+1} \ge \text{HWM}_t$
     * FIFO Lot splitting dollar & fee conservation: $\sum V_{\text{split}} = V_{\text{orig}}$ and $\sum \text{Fee}_{\text{split}} = \text{Fee}_{\text{orig}}$
     * 2026 Quadratic Polymarket fee bounds: $0 \le \text{Fee} \le 0.072 \times \text{Notional}$
     * Zero orphaned positions
     * Ghost sell fill prevention
     * Numerical / IEEE float bounds & zero-division safety
3. `backend/tests/scenarios/mock_market_factory.py`:
   - Helpers to generate synthetic order books (empty, inverted, micro-liquidity, whale depth, price shocks, zero-price contracts).
   - Helpers to generate mock Envio logs, out-of-order event streams, latency delays, and WebSocket reconnect events.
4. `backend/tests/scenarios/runner.py`:
   - Unified scenario test runner executing defined scenario matrices with invariant checks before, during, and after execution.

## Verification Method
- Execute pytest on `backend/tests/scenarios/test_infra.py`.
- Run full pytest suite across `backend/tests`.
