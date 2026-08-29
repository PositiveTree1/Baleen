# Original User Request

## Initial Request — 2026-08-29T11:46:57Z

You are the Project Orchestrator (teamwork_preview_orchestrator) for the comprehensive scenario modeling, stress-testing, and logic exploration across the entire Baleen codebase at `c:\Users\arthu\Documents\Baleen-master`.

Your Working Directory: `c:\Users\arthu\Documents\Baleen-master\.agents\orchestrator_1`
Your Request File: `c:\Users\arthu\Documents\Baleen-master\.agents\ORIGINAL_REQUEST.md`
Integrity Mode: development

Core Mission & Requirements:
1. Multi-Scenario Simulation & Stress Engine:
   Construct and execute a systematic scenario matrix encompassing 200+ diverse edge-case scenarios:
   - Order Book & Liquidity Extremes (empty books, inverted books, micro-liquidity, whale orders, 0.99 to 0.01 price shocks, zero-price contracts)
   - Timing, Network & Settlement Dynamics (asynchronous block latency 1s-60s, out-of-order Envio HyperSync logs, duplicate transactions, WS reconnections, abrupt RPC downtime)
   - Complex Position & Lifecycle Sequences (multi-trade FIFO partial liquidations, interleaved BUY/SELL on same condition IDs, binary resolution payouts $1.00/$0.00, rapid rebalancing)
   - Multi-Tenancy & Portfolio Scaling (concurrent users with conservative/balanced/aggressive risk profiles, zero-balance/max-drawdown edge states, whale bursts)
2. State Machine Invariant Validation:
   - Cash & margin invariance (no negative cash, no inflation from unrealized MTM, free cash = settled cash - open margin)
   - High-water mark & fee invariance (non-decreasing HWM, quadratic Polymarket fee bounds across 6 asset classes)
   - Zero orphaned positions (exact lot/split accounting, no share leaks or PnL misallocations)
   - Numerical & error safety (zero-division guards on 0-price/0-volume, IEEE float bounds, zero unhandled exceptions)
3. Discovery of Ambiguities & Logic Improvements:
   - Forensic breakdown of failure modes and edge case responses
   - Concrete architectural & algorithmic recommendations
   - Automated scenario test suites added to the codebase for continuous regression prevention.

Acceptance Criteria:
- 200+ distinct operational and market scenarios programmatically tested against backend, execution engine, and listener pipeline.
- 100% of mathematical and cash invariants validated across all scenario runs.
- All edge case failures, edge leaks, and anomalies documented with exact file references and proposed fixes.
- Backend test suite passes 100% with newly added scenario regression suites.

Maintain `plan.md` and `progress.md` in your working directory. Decompose and dispatch to specialist subagents as appropriate. When complete, submit your final completion report.
