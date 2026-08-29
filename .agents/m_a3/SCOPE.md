# Scope: Milestone M-A3 — Ingestion, Out-of-Order Logging & Settlement Resilience

## Objective
Implement and verify all fixes for:
1. `backend/app/services/live_poller.py`:
   - Out-of-order SELL before BUY handling:
     When a SELL arrives and no open BUY is found, record the pending sell or handle the race gracefully, or in the position guard when a subsequent lagging BUY arrives with an earlier or equal on-chain timestamp/hash, match and close to prevent orphaned open positions.
   - Platform execution log idempotency: ensure duplicate signals with matching `tx_hash` and `log_index` (even when `user_id` is None/NULL) are deduplicated cleanly.
2. Binary resolution and settlement verification:
   - Ensure binary resolution payouts ($1.00 / $0.00) properly close out remaining lots and compute exact final equity.

## Verification Method
- Execute pytest across `backend/tests/scenarios/test_scenario_network_timing.py` and full backend test suite:
  `& "backend/.venv/Scripts/python.exe" -m pytest backend/tests/ -v`
