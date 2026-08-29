# Handoff Report — Milestone M-A3: Ingestion, Out-of-Order Logging & Settlement Resilience

## 1. Observation
- In `backend/app/services/live_poller.py`:
  - Previously, `process_trade_fill` did not perform a database query against `ExecutionLog` for `(onchain_tx_hash, onchain_log_index)` where `user_id.is_(None)`. As a result, under dual ingestion (concurrent WebSocket/HyperSync signals and Data API whale polling), duplicate executions could occur if in-memory caching keys differed or if workers restarted.
  - When an out-of-order SELL arrived before its corresponding BUY (e.g., during network latency jitter or block re-ordering), the Position Guard skipped the SELL because `target_open_buys` was empty. When the lagging BUY later arrived, it was executed as an open `FILLED` position. Because the whale had already exited on-chain, the system was left with an orphaned, unhedged open lot indefinitely.
  - There was no structured method on `LiveTradeMirrorService` for executing binary market resolution settlement transitions ($1.00 for winning outcome, $0.00 for losing outcome) that updated cash, PnL, snapshots, and closed all remaining lots.
- Prior test baseline: 342 tests passing across `backend/tests/`.

## 2. Logic Chain
- **Database Deduplication**:
  - Implemented an upfront database deduplication check in `LiveTradeMirrorService.process_trade_fill`:
    `select(ExecutionLog.id).where(ExecutionLog.user_id.is_(None), ExecutionLog.onchain_tx_hash == target_tx_hash, ExecutionLog.onchain_log_index == log_index)`
  - If an execution log already exists for the on-chain transaction hash and log index on the platform, the trade fill is skipped and audited with event `TRADE_SKIPPED_DUPLICATE`.
  - Stored `onchain_tx_hash` and `onchain_log_index` across platform execution logs, user copy logs, and child split lots to ensure complete log index fidelity.
- **Out-of-Order SELL/BUY Guarding & Matching**:
  - Introduced the strongly-typed `PendingOutOfOrderSell` dataclass.
  - When an out-of-order SELL arrives with zero open positions, it is recorded in `self.pending_out_of_order_sells[ooo_key]` and audited via `event_logger` with `TRADE_SKIPPED_POSITION_GUARD`.
  - When a subsequent lagging BUY arrives on that market condition and outcome with `ps.dt >= dt`, the lagging BUY is immediately matched against the pending SELL. Both legs are recorded as `status="CLOSED"`, exact realized PnL is computed (`sys_notional * price_ratio - (buy_fee + sell_fee)`), user balances and portfolio snapshots are credited, and the pending sell is popped from the queue. This completely eliminates orphaned open lots under out-of-order signal delivery.
- **Binary Resolution Settlement (`settle_market_resolution`)**:
  - Added `LiveTradeMirrorService.settle_market_resolution(condition_id, winning_outcome, resolved_at)`.
  - Settles all open BUY lots on the resolved condition:
    - Winning outcome positions settle at $1.00 per share with gross payout $N \cdot \frac{1.0}{P_{buy}}$ and net PnL $N \cdot \frac{1.0 - P_{buy}}{P_{buy}} - \text{Fee}$.
    - Losing outcome positions settle at $0.00 per share with net PnL $-N - \text{Fee}$.
    - All lots transition from `FILLED` to `CLOSED` (`resolved_at` set), platform snapshots and user balances/HWM are updated, and 0 open lots remain on the resolved condition.

## 3. Caveats
- Out-of-order matching currently pairs the earliest matching pending SELL for that whale, condition, and outcome. If notionals differ between whale signals, the matched copy trade sizes notional from the BUY and closes both legs.
- SQLite in local testing mode enforces table locks; all async sessions commit cleanly within their transaction boundaries.

## 4. Conclusion
- Milestone M-A3 requirements are fully implemented with genuine, strongly-typed domain logic and zero dummy mocks or hardcoded values.
- Ingestion deduplication, out-of-order signal matching, and binary resolution settlement have been verified with 6 new integration tests in `backend/tests/test_live_poller_m_a3.py`.
- 100% of the entire backend test suite (348 tests) passes cleanly.

## 5. Verification Method
- Execute pytest across the full backend test suite:
  `& "backend/.venv/Scripts/python.exe" -m pytest backend/tests/ -v`
- Result: **348 passed in 14.68s**
