# Scope: Milestone M-B2 — 220-Scenario Stress Matrix Implementation

## Objective
Implement the complete 220-scenario stress testing matrix across 4 dedicated test suites under `backend/tests/scenarios/`:
1. `backend/tests/scenarios/test_scenario_orderbook_extremes.py` (55 Scenarios):
   - Empty books, one-sided books, inverted books, crossed spreads, zero-spread top of book.
   - Micro-liquidity ($0.01 depth), sub-penny ticks, massive whale order depth exhaustion ($1M+ sweeps).
   - Price shocks (0.99 to 0.01 flash collapse, 0.01 to 0.99 parabolic spike, binary extremes).
   - Zero-price contracts ($p=0.00$), ceiling contracts ($p=1.00$), and boundary fee quantization.
2. `backend/tests/scenarios/test_scenario_network_timing.py` (55 Scenarios):
   - Asynchronous block latency sweeps (1s to 120s lag).
   - Out-of-order Envio HyperSync log delivery (SELL before BUY, inverted split log index).
   - Duplicate transaction ingestion and idempotency locks.
   - WebSocket disconnect/reconnect bursts, offline queue replay.
   - Abrupt RPC downtime, rate-limiting HTTP 429 retries, and binary resolution payouts ($1.00/$0.00).
3. `backend/tests/scenarios/test_scenario_lifecycle_fifo.py` (55 Scenarios):
   - Multi-trade FIFO partial liquidations across fractional splits (10%, 25%, 33.3%, 50%, 75%, 90%).
   - Interleaved BUY and SELL sequences on identical condition IDs across multiple whales.
   - Multi-whale consensus triggers, tier upgrades (Gold Sniper vs Standard), and sizing multipliers.
   - Multi-outcome opposing positions (Yes vs No lot conservation).
   - Rapid rebalancing and lot redemption state transitions.
4. `backend/tests/scenarios/test_scenario_multitenancy_scaling.py` (55 Scenarios):
   - Concurrent user executions across Conservative (5%), Balanced (10%), and Aggressive (20%) risk caps.
   - Zero-balance and near-zero balance boundary states (graceful trade skips without crashes).
   - Maximum drawdown limit enforcement and margin exhaustion.
   - Large-scale concurrent user bursts (100+ simulated users executing simultaneously).
   - High-Water Mark monotonic tracking across volatile win/loss sequences and fee deductions.

## Verification Method
- Execute pytest across all 4 scenario test files:
  `& "backend/.venv/Scripts/python.exe" -m pytest backend/tests/scenarios/ -v`
- Verify that all 220+ scenario tests run and 100% pass with zero invariant violations.
