# Dispatch: Worker M-B1 — Scenario Test Infrastructure & Invariant Monitor

Your Working Directory: `c:\Users\arthu\Documents\Baleen-master\.agents\worker_b1`
Your Scope File: `c:\Users\arthu\Documents\Baleen-master\.agents\m_b1\SCOPE.md`
Your Test Infra File: `c:\Users\arthu\Documents\Baleen-master\.agents\TEST_INFRA.md`
Your Project File: `c:\Users\arthu\Documents\Baleen-master\.agents\PROJECT.md`
Your Request File: `c:\Users\arthu\Documents\Baleen-master\.agents\ORIGINAL_REQUEST.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Create `backend/tests/scenarios/__init__.py`.
2. Create `backend/tests/scenarios/invariant_monitor.py`:
   - State machine monitor checking all 10 core invariants:
     * Cash non-negativity: `Cash >= 0`
     * Margin equation: `Free Cash == max(0.0, Settled Cash - Open Margin)`
     * High-Water Mark monotonicity: `HWM_{t+1} >= HWM_t`
     * FIFO Lot splitting dollar & fee conservation: `sum(V_split) == V_orig` and `sum(Fee_split) == Fee_orig`
     * 2026 Quadratic Polymarket fee bounds: `0.0 <= Fee <= 0.072 * Notional` across 6 asset classes
     * Zero orphaned positions (no unhedged BUYs after complete SELL closes)
     * Ghost sell fill prevention (users with 0 positions never get SELL fills)
     * Numerical / IEEE float bounds & zero-division safety
3. Create `backend/tests/scenarios/mock_market_factory.py`:
   - Synthetic order book generators: empty, inverted, micro-liquidity, whale depth, price shocks, zero-price contracts.
   - Synthetic event streams: out-of-order Envio logs, block latency simulator (1s-60s), WebSocket reconnect bursts.
4. Create `backend/tests/scenarios/runner.py` with parametric test runner harness.
5. Create `backend/tests/scenarios/test_scenario_infra.py` to unit test the infrastructure itself.
6. Run pytest using: `& "backend/.venv/Scripts/python.exe" -m pytest backend/tests/scenarios/test_scenario_infra.py`
7. Write your handoff report to `c:\Users\arthu\Documents\Baleen-master\.agents\worker_b1\handoff.md` and send a message when done.
