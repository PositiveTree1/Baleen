# Handoff Report — Survey Explorer 2 (Network Ingestion & Settlement Dynamics)

**Agent:** `explorer_survey_2`  
**Timestamp:** 2026-08-29T11:52:00Z  
**Type:** Hard Handoff (Task Complete)  
**Deliverable File:** `c:\Users\arthu\Documents\Baleen-master\.agents\explorer_survey_2\survey_report.md`

---

## 1. Observation

1. **Fee Zeroing on FIFO Partial Split:**
   In `backend/app/services/live_poller.py` lines 296–313:
   ```python
   open_buy.status = "CLOSED"
   open_buy.notional_usd = closed_portion
   open_buy.fee_usd = round(closed_buy_fee, 4) # Line 297 sets open_buy.fee_usd
   ...
   split_buy = ExecutionLog(
       ...
       fee_usd=round(float(open_buy.fee_usd or 0.0) - closed_buy_fee, 4), # Line 313 evaluates to closed_buy_fee - closed_buy_fee = 0.0
       ...
   )
   ```
   Identical defect on lines 410 and 426 for user copy trade execution logs.

2. **Out-of-Order SELL Before BUY Position Dropping:**
   In `backend/app/services/live_poller.py` lines 131–142:
   ```python
   stmt_open_buys = select(ExecutionLog).where(
       ExecutionLog.market_condition_id == condition_id,
       ExecutionLog.resolution_outcome == outcome,
       ExecutionLog.source_wallet_address.ilike(wallet_address),
       ExecutionLog.side == "BUY",
       ExecutionLog.status == "FILLED"
   )
   target_open_buys = (await db.execute(stmt_open_buys)).scalars().all()
   if not target_open_buys:
       logger.info(f"Position Guard: Whale sold ..., but sandbox holds 0 open positions. Skipping.")
       return
   ```
   If a network reorg or latency delivers a `SELL` before the `BUY`, the `SELL` is dropped immediately. When the `BUY` arrives, it opens a position that is never closed, becoming an orphaned open position.

3. **Startup Lag Drop Window:**
   In `backend/app/services/live_poller.py` lines 519–520:
   ```python
   ts_sec = (timestamp_ms / 1000.0) if timestamp_ms else datetime.utcnow().timestamp()
   if ts_sec < self.started_at:
       return
   ```
   On-chain signals mined 5–60 seconds prior to server startup but delivered during startup/lag catchup are silently dropped.

4. **Composite Unique Constraint `NULL` Semantics for Platform Logs:**
   In `backend/app/models.py` lines 135–138:
   ```python
   __table_args__ = (
       UniqueConstraint('onchain_tx_hash', 'onchain_log_index', 'user_id', name='uix_tx_log_user'),
   )
   ```
   For platform-level execution logs where `user_id` is `None` (`NULL`), ANSI SQL treats `NULL` as distinct, permitting duplicate rows with identical `(tx_hash, log_index, NULL)`.

5. **Dangling Disk Queue Without Replayer:**
   In `listener/src/queue.ts`, `enqueueSignal` appends offline signals to `queue.jsonl`, but `dequeueSignals()` is never invoked anywhere in the codebase.

6. **Test Suite Verification Commands & Results:**
   - Pytest execution: `& "backend/.venv/Scripts/python.exe" -m pytest backend/tests`
     Result: **56 passed in 3.98s** (100% pass rate).
   - Listener Jest execution: `& "C:\Program Files\nodejs\node.exe" node_modules/jest/bin/jest.js` in `listener/`
     Result: **3 passed in 5.17s** (100% pass rate).

---

## 2. Logic Chain

1. **Fee Accounting:** Mutating `open_buy.fee_usd` on line 297 alters the object in place before line 313 reads `open_buy.fee_usd`. The arithmetic `closed_buy_fee - closed_buy_fee` yields `0.0`, resulting in zero transaction fee recorded for the split child.
2. **Signal Inversion:** In an asynchronous distributed system, network latency causes out-of-order packet arrival. Because `live_poller.py` does not buffer unmatched `SELL` signals, premature `SELL` arrivals are permanently dropped. When the lagging `BUY` arrives, it leaves an unhedged, open position.
3. **Deduplication:** The in-memory cache `seen_trade_keys` resets on server reboot. While the database has a unique constraint, the `NULL` `user_id` on platform sandbox trades bypasses standard SQL uniqueness checks, allowing dual ingestion (Envio + REST poller) to create duplicate executions.
4. **Resolution Mechanics:** Binary resolution contracts on Polymarket settle to $1.00 or $0.00. Because HyperSync listener only filters for `ORDER_FILLED_TOPIC` and not `PayoutRedemption` or `ConditionResolution`, redemption at expiry relies entirely on Gamma API price polling.

---

## 3. Caveats

1. **External Network API Availability:** Live testing against production Polymarket endpoints (`clob.polymarket.com`, `gamma-api.polymarket.com`, `polygon.hypersync.xyz`) is subject to network rate limits (429) and network mode policies.
2. **Phase 2 Custody:** Live execution (§9 of spec) requiring Magic/Privy delegated signing and EIP-712 order construction was reviewed for interface compatibility but is not active in the Phase 1 Sandbox.

---

## 4. Conclusion

The Baleen ingestion, networking, and settlement engine is structurally sound, featuring a high-performance dual-ingestion architecture, 2026 quadratic fee curves, and robust directional slippage guards. The critical findings documented in `survey_report.md` (partial lot fee zeroing, out-of-order SELL/BUY races, and SQL NULL uniqueness loopholes) have been pinpointed with exact file references and remediation strategies.

The recommended 200+ scenario stress matrix provides a systematic framework to validate cash/margin invariance, zero orphaned positions, and mathematical consistency.

---

## 5. Verification Method

To independently verify all findings and test suite health:

1. **Run Backend Pytest Suite:**
   ```powershell
   & "c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\python.exe" -m pytest backend/tests
   ```
2. **Run Listener Jest Suite:**
   ```powershell
   cd "c:\Users\arthu\Documents\Baleen-master\listener"
   & "C:\Program Files\nodejs\node.exe" node_modules/jest/bin/jest.js
   ```
3. **Inspect Key Vulnerability Locations:**
   - `backend/app/services/live_poller.py`: Lines 296–313 (partial fee mutation), Lines 131–142 (out-of-order SELL drop), Lines 519–520 (startup drop window).
   - `backend/app/models.py`: Line 136 (composite unique constraint).
   - `backend/app/services/mark_to_market.py`: Lines 244–246 (floating MTM HWM inflation).
