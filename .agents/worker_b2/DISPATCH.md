# Dispatch: Worker M-B2 — 220-Scenario Stress Matrix Implementation

Your Working Directory: `c:\Users\arthu\Documents\Baleen-master\.agents\worker_b2`
Your Scope File: `c:\Users\arthu\Documents\Baleen-master\.agents\m_b2\SCOPE.md`
Your Test Infra File: `c:\Users\arthu\Documents\Baleen-master\.agents\TEST_INFRA.md`
Your Project File: `c:\Users\arthu\Documents\Baleen-master\.agents\PROJECT.md`
Your Request File: `c:\Users\arthu\Documents\Baleen-master\.agents\ORIGINAL_REQUEST.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Implement the 4 comprehensive scenario test suites using the infrastructure in `backend/tests/scenarios/`:
   - `backend/tests/scenarios/test_scenario_orderbook_extremes.py` (55 distinct parametric/functional scenarios)
   - `backend/tests/scenarios/test_scenario_network_timing.py` (55 distinct parametric/functional scenarios)
   - `backend/tests/scenarios/test_scenario_lifecycle_fifo.py` (55 distinct parametric/functional scenarios)
   - `backend/tests/scenarios/test_scenario_multitenancy_scaling.py` (55 distinct parametric/functional scenarios)
2. Ensure every scenario passes through `InvariantMonitor` assertions (Cash non-negativity, margin equality, HWM monotonicity, FIFO lot splitting conservation, fee bounds, zero orphaned lots, ghost sell prevention, IEEE numerical safety).
3. Execute the full scenario suite using:
   `& "backend/.venv/Scripts/python.exe" -m pytest backend/tests/scenarios/ -v`
4. Confirm all 220+ scenarios pass cleanly.
5. Write your handoff report to `c:\Users\arthu\Documents\Baleen-master\.agents\worker_b2\handoff.md` and send a message when complete.
