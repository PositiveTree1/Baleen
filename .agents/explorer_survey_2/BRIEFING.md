# BRIEFING — 2026-08-29T11:52:00Z

## Mission
Comprehensive exploration and forensic breakdown of Baleen's network ingestion, listener pipeline, HyperSync/WebSocket/RPC integration, timing dynamics (latency, out-of-order, duplicates, reconnections, RPC downtime), and binary resolution/settlement/payout logic.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: c:\Users\arthu\Documents\Baleen-master\.agents\explorer_survey_2
- Original parent: 980dffcb-98f6-47fd-9529-c31fd4fe4c24
- Milestone: survey_network_settlement

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Produce evidence-backed observations with exact file paths, line numbers, and logic chains.
- Report all edge cases, synchronization risks, invariants, and scenario test recommendations.

## Current Parent
- Conversation ID: 980dffcb-98f6-47fd-9529-c31fd4fe4c24
- Updated: 2026-08-29T11:52:00Z

## Investigation State
- **Explored paths**: `listener/src/index.ts`, `hypersync.ts`, `event-processor.ts`, `queue.ts`, `checkpoint.ts`, `constants.ts`, `config.ts`, `types.ts`, `backend/app/api/signals.py`, `live_poller.py`, `mark_to_market.py`, `polymarket_fees.py`, `dynamic_sizer.py`, `fill_simulator.py`, `slippage.py`, `polymarket_client.py`, `scanner.py`, `models.py`, `database.py`, `execution_logs.py`, `admin.py`, `wallets.py`, `events.py`, `users.py`, `copilot.py`, `backend/tests/`, `listener/tests/`.
- **Key findings**:
  1. Fee zeroing bug in partial lot FIFO splits (`live_poller.py` lines 297/313 and 410/426).
  2. Out-of-order SELL before BUY permanently drops SELL, leaving orphaned BUY open forever (`live_poller.py` lines 131-142).
  3. Startup timestamp lag window silently drops lagged on-chain signals (`live_poller.py` lines 519-520).
  4. Composite unique constraint on `(onchain_tx_hash, onchain_log_index, user_id)` allows duplicate platform trades because `user_id` is `NULL` (`models.py` line 136).
  5. High-Water Mark inflated by floating unrealized MTM PnL (`mark_to_market.py` line 244).
  6. HyperSync listener lacks indexing for `PayoutRedemption` and `ConditionResolution` events.
- **Unexplored areas**: None within assigned survey scope.

## Key Decisions Made
- Fully documented all source modules, timing vulnerabilities, invariant validations, and proposed a 200+ scenario stress matrix in `survey_report.md` and `handoff.md`.

## Artifact Index
- `c:\Users\arthu\Documents\Baleen-master\.agents\explorer_survey_2\survey_report.md` — Comprehensive survey and forensic report.
- `c:\Users\arthu\Documents\Baleen-master\.agents\explorer_survey_2\handoff.md` — 5-component handoff report.
