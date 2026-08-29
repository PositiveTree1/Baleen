# Code & Ingestion Pipeline Comprehensive Review and Adversarial Audit Report

**Working Directory**: `c:\Users\arthu\Documents\Baleen-master`  
**Agent Metadata Directory**: `c:\Users\arthu\Documents\Baleen-master\.agents\reviewer_code_and_pipeline\`  
**Author**: Reviewer 1 (Code & Ingestion Pipeline Reviewer & Adversarial Critic)  
**Timestamp**: 2026-08-29T11:20:00Z  
**Verdict**: **REQUEST_CHANGES** (Critical Integrity Violations & Simulation Defects)  

---

## 1. Review Summary

**Verdict**: **REQUEST_CHANGES**

An exhaustive, evidence-based audit and adversarial stress test of 100% of the backend Python codebase (`backend/app/`, `backend/*.py`), database layer (`db/schema.sql`, `backend/app/database.py`, `backend/app/models.py`), signal listener (`listener/src/`), and test suites (`backend/tests/`, `listener/tests/`) was completed.

The codebase features strong architectural design (FastAPI async architecture, Envio HyperSync client integration, continuous background valuation loops, and 2026 dynamic quadratic fee schedule). However, **multiple Critical integrity violations, severe paper trading simulation unrealisms, and high-impact runtime failure modes** were uncovered and verified against the source code.

### Core Integrity Violations & Findings Overview
1. **INTEGRITY VIOLATION (Mock Disconnects & Deceptive Tests)**: 5 backend test suites (`test_checkpoint.py`, `test_fee_calculation.py`, `test_idempotency.py`, `test_digest.py`, `test_ai_summary.py`) do not test production code. `test_ai_summary.py` contains a no-op loop (`for num in numbers: pass`) ensuring artificial 100% passing status without validation.
2. **INTEGRITY VIOLATION (Synthetic Equity Curve Fabrication)**: `backend/app/api/wallets.py` seeds MD5 hashes of wallet addresses to fabricate 45-day daily PnL curves when actual history is sparse, presenting pseudo-random data as authentic historical performance.
3. **CRITICAL SIMULATION DEFECT (Hardcoded Default $0.50 Fill Price)**: `listener/src/event-processor.ts#L83` hardcodes `price = '0'`, which triggers a fallback in `backend/app/services/live_poller.py#L425` setting execution price to $0.50 for all on-chain whale trades regardless of real market fill price.
4. **CRITICAL SIMULATION DEFECT (Inverted Trade Side & Asset ID Corruption)**: `listener/src/event-processor.ts#L71-L81` misidentifies CTF Exchange Maker/Taker trades, classifying outcome token BUY orders as SELLs and corrupting prediction outcome `assetId` to `"0"` (USDC).
5. **CRITICAL SIMULATION DEFECT (Adverse Slippage vs Favorable Discount Inversion)**: `backend/app/sizing/slippage.py#L8` uses `abs(current_price - whale_price)`, which rejects orders receiving favorable price improvements (e.g. buying at a discount or selling at a premium).
6. **CRITICAL RUNTIME HAZARD (Missing `import asyncio` in `database.py`)**: `backend/app/database.py#L123` executes `await asyncio.sleep(3)` inside the database connection retry loop without importing `asyncio`, crashing the startup sequence on transient pooler warmup.
7. **CRITICAL ACCOUNTING HAZARD (Double-Counting User Realized PnL)**: `backend/app/services/live_poller.py#L331-L353` records `realized_pnl_usd` on both the closed BUY row and the newly generated SELL row for user execution logs, doubling total user PnL on aggregation.
8. **CRITICAL DATA ISOLATION HAZARD (Global Sandbox Deletion on User Reset)**: `backend/app/api/users.py#L180-L182` executes unconstrained `delete(ExecutionLog)` and `delete(PortfolioSnapshot)` across the entire database whenever an individual user resets their sandbox.

---

## 2. Structured Review Findings

### Finding B1: Missing `import asyncio` in Database Connection Retry Loop
- **Severity**: **Critical / Stability**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/database.py#L1-L6` and `#L123`
- **What**: `import asyncio` is completely omitted from the module top-level imports.
- **Why**: When `init_db()` encounters any transient database connection exception (such as PgBouncer warmup or network latency), line 123 executes `await asyncio.sleep(3)`. This raises an immediate `NameError: name 'asyncio' is not defined`, crashing the startup lifecycle and preventing retries.
- **Suggestion**: Add `import asyncio` at line 1 of `backend/app/database.py`.

### Finding B2: Slippage Guard Treats Favorable Price Improvement as Adverse Slippage
- **Severity**: **Critical / Simulation Realism**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/sizing/slippage.py#L1-L16`
- **What**: `check_slippage(whale_price, current_price)` uses `diff = abs(current_price - whale_price) / whale_price` without accounting for trade side (`BUY` vs `SELL`).
- **Why**: 
  - For a BUY order, if `whale_price = 0.20` and `current_price = 0.18` (a 10% price improvement / discount), `diff = 0.10 > 0.012`, returning `'CANCEL_ORDER: SLIPPAGE_EXCEEDED'`.
  - For a SELL order, if `whale_price = 0.50` and `current_price = 0.55` (a 10% price improvement / higher proceeds), `diff = 0.10 > 0.02`, cancelling the order.
  - The model actively rejects profitable trades while only executing unfavorable or exact matches.
- **Suggestion**: Pass `side: str = 'BUY'` to `check_slippage`, and enforce one-sided adverse checks: `(current_price - whale_price) / whale_price` for BUYs, and `(whale_price - current_price) / whale_price` for SELLs.

### Finding B3: Production Bypass of Sizing, Order Book Depth Walking, and Slippage Models
- **Severity**: **Critical / Simulation Realism**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/services/live_poller.py#L184-L254` and `#L306`
- **What**: `live_poller.py` never invokes `size_trade()` (`app/sizing/dynamic_sizer.py`), `simulate_fill()` (`app/sizing/fill_simulator.py`), or `check_slippage()` (`app/sizing/slippage.py`).
- **Why**: `live_poller.py` hardcodes an inline heuristic clamp (`sys_notional = round(min(max(10.0, cash_usd * 0.1 * sizing_multiplier), 350.0), 2)`), checks slippage with an inline `(live_p - price) > 0.015`, and assumes instant fills at `effective_fill_price = live_p`. The production trading simulation completely bypasses the dynamic sizing and order book depth consumption models tested in unit tests.
- **Suggestion**: Integrate `size_trade()`, `check_slippage()`, and CLOB order book walking via `simulate_fill()` directly into `live_poller.py`.

### Finding B4: Unreachable Dead Code with Undefined Variables in Scanner
- **Severity**: **Major / Code Quality**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/discovery/scanner.py#L326-L350`
- **What**: Lines 327-350 in `calculate_authentic_wallet_stats` are positioned immediately after an unconditional `return` at line 325.
- **Why**: Lines 327-350 are unreachable dead code and reference undefined variables (`realized_pnl`, `total_trades_count`, `volume`, `avg_trades_per_day`, `trades_per_hour`, `is_hft`, `is_dormant`, `first_trade_dt`, `last_trade_dt`).
- **Suggestion**: Remove lines 326-350 from `backend/app/discovery/scanner.py`.

### Finding B5: Threshold Inconsistency Between Scanner, Scoring Engine, and Rescoring Worker
- **Severity**: **Major / Mathematical Consistency**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/scoring/engine.py#L22-L41`, `backend/app/discovery/scanner.py#L411-L448`, `backend/app/scoring/basket.py#L85-L105`
- **What**:
  - `engine.py` requires PnL >= $50,000, trades/day <= 300, and classifies Gold Sniper via `(win_rate >= 80.0 and max_drawdown <= 15.0) or (pnl >= 100000 and win_rate >= 70.0)`.
  - `scanner.py` admits wallets with PnL >= $25,000 and trades/day <= 100.
  - `basket.py` calls `score_wallet()` nightly, which rejects wallets with PnL < $50,000.
- **Why**: A candidate wallet with $35,000 PnL is admitted by `scanner.py` during discovery, but is rejected on the first nightly rescore by `basket.py`, causing basket membership churn and test suite failures in `test_scoring_filters.py`.
- **Suggestion**: Harmonize PnL threshold ($50,000), anti-HFT threshold (100 trades/day), and Gold Sniper tier criteria (`win_rate >= 85.0% and max_drawdown <= 10.0%`) across all three modules.

### Finding B6: MCP Server AttributeErrors on `User` Model
- **Severity**: **Major / API Stability**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/mcp_server.py#L269-L272`
- **What**: `handle_baleen_admin_users` accesses `u.role` and `u.live_trading_active`.
- **Why**: `User` in `backend/app/models.py` has no `role` attribute, and the active trading boolean is named `live_trading_enabled`. Calling `baleen_admin_users` via MCP raises `AttributeError: 'User' object has no attribute 'role'`.
- **Suggestion**: Remove `u.role` or provide a default string, and update `u.live_trading_active` to `u.live_trading_enabled`.

### Finding B7: `user_id` Parameter Ignored in Execution & Snapshot API Queries
- **Severity**: **Major / Multi-Tenancy & Data Isolation**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/api/execution_logs.py#L73`, `#L187`, `#L212`, `#L336`
- **What**: `get_execution_logs()`, `get_portfolio_summary()`, and `get_portfolio_snapshots()` declare `user_id: Optional[str] = Query(None, alias="userId")` but unconditionally filter `where(ExecutionLog.user_id.is_(None))` and `where(PortfolioSnapshot.user_id.is_(None))`.
- **Why**: When a specific user requests their execution logs or equity snapshots, the API returns the global platform logs instead of their user-specific portfolio data.
- **Suggestion**: Update queries to filter by `ExecutionLog.user_id == target_uuid` if `user_id` is provided, falling back to `is_(None)` when omitted.

### Finding B8: Mock Disconnects and Deceptive Tests in Backend Test Suite
- **Severity**: **Critical / INTEGRITY VIOLATION**
- **Location**:
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/test_checkpoint.py#L1-L16`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/test_fee_calculation.py#L1-L30`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/test_idempotency.py#L14-L55`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/test_digest.py#L3-L15`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/test_ai_summary.py#L20-L33`
- **What**: Five backend test files test local inline stubs and dummy variables instead of production service code:
  - `test_checkpoint.py`: Tests `saved_state = 100; assert saved_state == 100`.
  - `test_fee_calculation.py`: Tests a local inline `calculate_fee()` helper; zero tests for production `polymarket_fees.py`.
  - `test_idempotency.py`: Tests a local mock class `IdempotencyChecker` using a Python `set()`.
  - `test_digest.py`: Tests a local list comprehension `[u for u in users if u.daily_digest_opt_in]`.
  - `test_ai_summary.py`: Assertion loop executes `for num in numbers: pass`, making test failure impossible.
- **Why**: Inflates test pass rates while leaving critical production modules completely untested.
- **Suggestion**: Rewrite all test suites to import and assert against actual production services.

### Finding B9: Synthetic Timeline Synthesis in `wallets.py`
- **Severity**: **Critical / INTEGRITY VIOLATION & Realism**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/api/wallets.py#L318-L393`
- **What**: When trade history is sparse (<5 trades) and `cached_daily_pnl` is empty, `get_wallet()` fabricates a 45-day daily PnL timeline using MD5 hashes of the wallet address (`addr_seed = int(hashlib.md5(clean_addr.encode()).hexdigest()[:8], 16)`).
- **Why**: Fabricated equity curves are presented to the dashboard as historical performance data.
- **Suggestion**: Return genuine sparse historical data points without synthetic fabrication.

### Finding B10: Unrealized Gains Treated as Available Cash & Written to Realized Column
- **Severity**: **Major / Accounting Realism**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/services/mark_to_market.py#L180`, `#L212-L213`, `backend/app/services/live_poller.py#L232-L253`
- **What**: `mark_to_market.py` writes unrealized PnL of open positions directly into the `realized_pnl_usd` database column. `PortfolioSnapshot.balance` is computed as `$10,000 + sum(realized_pnl_usd)`, and `live_poller.py` uses `total_portfolio_equity - open_notional` to determine `free_cash`.
- **Why**: Unsettled paper gains on open prediction contracts immediately inflate available cash, allowing the paper trader to enter new trades using unrealized profits before positions settle.
- **Suggestion**: Maintain distinct columns/fields for `unrealized_pnl_usd` vs `realized_pnl_usd`, and calculate free cash strictly as `settled_cash_balance - open_positions_cost`.

### Finding B11: Double-Counting of Realized PnL on User Execution Logs
- **Severity**: **Major / Mathematical Bug**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/services/live_poller.py#L331-L353`
- **What**: When closing a position on a SELL order, `live_poller.py` sets `u_earliest_buy.realized_pnl_usd` (on the original BUY row) AND sets `user_log.realized_pnl_usd = u_realized_pnl_val` (on the newly created SELL row).
- **Why**: Any database aggregation querying `func.sum(ExecutionLog.realized_pnl_usd)` for a user sums the realized PnL twice (once on the BUY row, once on the SELL row).
- **Suggestion**: Set `user_log.realized_pnl_usd = None` (matching the platform log pattern in line 279) so PnL is tracked strictly on the closed BUY position.

### Finding B12: Global Sandbox Deletion on Individual User Reset
- **Severity**: **Major / Multi-Tenancy Hazard**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/api/users.py#L180-L183`
- **What**: In `reset_user_sandbox(user_id: str, ...)`, the route unconditionally executes `delete(ExecutionLog)`, `delete(PortfolioSnapshot)`, and `delete(SystemEvent)` without scoping to `user.id`.
- **Why**: When any user resets their individual sandbox balance, all execution logs, equity curves, and system events for all users and the platform are permanently deleted.
- **Suggestion**: Scope deletions to `ExecutionLog.user_id == user.id` and `PortfolioSnapshot.user_id == user.id`.

### Finding B13: On-Chain Signal Ingestion Leaves `market_condition_id` Empty
- **Severity**: **Major / Pipeline Continuity**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/services/live_poller.py#L40-L86`, `#L108-L117`, `#L432`
- **What**: `process_onchain_signal` passes `condition_id=""`. `_resolve_market_metadata` does not extract or return `condition_id` from Gamma market data.
- **Why**: All onchain signals are saved with `market_condition_id = ""`. Subsequent SELL orders cannot match open positions by `market_condition_id`, and UI trade chart links cannot navigate to Polymarket markets.
- **Suggestion**: Extract `conditionId` in `_resolve_market_metadata` and update `condition_id` in `process_trade_fill`.

---

## 3. Ingestion Listener Findings (`listener/src/`)

### Finding LST-01: Hardcoded Price `'0'` Forces 0.50 Synthetic Default Fill
- **Severity**: **Critical / Simulation Realism**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/listener/src/event-processor.ts#L83` & `backend/app/services/live_poller.py#L425`
- **What**: `matchesBasketWallet` sets `const price = '0'; // Placeholder`.
- **Why**: Backend `live_poller.py#L425` checks `float(price_str) > 0`. Because price is `"0"`, it defaults to `price = 0.50`. Every on-chain trade is ingested into simulation at exactly 50 cents regardless of whether the whale traded at $0.05 or $0.95.
- **Suggestion**: Calculate decimal price from `makerAmountFilled` and `takerAmountFilled` in `event-processor.ts`.

### Finding LST-02: Inverted Trade Side & Asset ID Corruption (Maker vs Taker)
- **Severity**: **Critical / Simulation Realism & Logic**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/listener/src/event-processor.ts#L71-L81`
- **What**: `matchesBasketWallet` assumes all Taker trades are `BUY` and Maker trades are `SELL`, and always assigns `assetId = event.makerAssetId`.
- **Why**: In Polymarket CTF Exchange:
  - If Maker offers USDC (`makerAssetId = 0`) to buy outcome tokens (`takerAssetId > 0`), the Maker is **BUYING** `takerAssetId`. The listener incorrectly flags side as `SELL` and passes `assetId = "0"`.
  - If Taker sells outcome tokens (`takerAssetId > 0`) for USDC (`makerAssetId = 0`), the Taker is **SELLING** `takerAssetId`. The listener incorrectly flags side as `BUY` and passes `assetId = "0"`.
  - Outcome tokens cannot be resolved when `assetId` is passed as `"0"`.
- **Suggestion**: Inspect whether `makerAssetId === '0'` or `takerAssetId === '0'` to dynamically assign trade side, execution price, and the non-zero prediction token `assetId`.

### Finding LST-03: System Wall-Clock `Date.now()` Assigned to Historical Block Trades
- **Severity**: **High / Latency & Lookahead Bias**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/listener/src/event-processor.ts#L94` & `backend/app/services/live_poller.py#L413-L417`
- **What**: `matchesBasketWallet` assigns `timestamp: Date.now()`.
- **Why**: When the listener catches up on past blocks, past trades are assigned the current system timestamp. In `live_poller.py`, `ts_sec < self.started_at` evaluates to `False`, causing historical trades from hours ago to execute as instantaneous live orders.
- **Suggestion**: Propagate block timestamps or estimate timestamp from block height (`blockNumber * 2.0 + genesisOffset`).

### Finding LST-04: 5,000 Block Silent Discard Window on Restart
- **Severity**: **High / Reliability**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/listener/src/index.ts#L43-L46`
- **What**: If `currentHeight - startBlock > 5000`, `startBlock` is clamped to `currentHeight - 500`.
- **Why**: After an outage or maintenance window > 2.7 hours, thousands of blockchain blocks are silently dropped without administrative logging or alerts.
- **Suggestion**: Log a warning with the exact skipped block range and allow configured max catch-up limits.

### Finding LST-05: Queue File Race Condition and Indefinite Disk Accumulation
- **Severity**: **High / Concurrency & Storage**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/listener/src/queue.ts#L20-L33`
- **What**: `dequeueSignals` performs a non-atomic read-slice-write cycle on `queue.jsonl`. Furthermore, `dequeueSignals` is never invoked in the codebase.
- **Why**: Concurrently appended signals are overwritten and lost. Uncalled dequeuing causes `queue.jsonl` to grow indefinitely.
- **Suggestion**: Implement an in-memory ring buffer or SQLite queue with transactional dequeueing.

### Finding LST-06: Unbounded Memory Leak in In-Memory Deduplication Set
- **Severity**: **Medium / Memory Leak**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/listener/src/queue.ts#L7-L15`
- **What**: `processedKeys = new Set<string>()` stores all transaction hash/log index pairs indefinitely.
- **Why**: Over long runtimes, memory usage grows monotonically, eventually exhausting Node.js heap memory.
- **Suggestion**: Replace `Set` with a bounded LRU cache (e.g. 50,000 entries).

### Finding LST-07: Non-Atomic Synchronous Checkpoint Persistence
- **Severity**: **Medium / Durability**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/listener/src/checkpoint.ts#L7-L13`
- **What**: `saveCheckpoint` writes directly to `checkpoint.json` with `fs.writeFileSync`.
- **Why**: Process termination mid-write corrupts JSON, causing resume block to reset to 0 on restart.
- **Suggestion**: Write to a temporary file (`checkpoint.json.tmp`) and atomically replace with `fs.renameSync`.

### Finding LST-08: Zero-Retry HTTP Forwarding to Backend
- **Severity**: **Medium / Fault Tolerance**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/listener/src/queue.ts#L35-L49`
- **What**: `postSignalToBackend` performs a single `fetch()` without retry logic.
- **Why**: Transient backend 500/503 errors or cold starts result in permanently lost whale trade signals.
- **Suggestion**: Implement exponential backoff retry (up to 3 attempts).

### Finding LST-09: Outdated Hardcoded Fallback Block Height (68,000,000)
- **Severity**: **Low / Configuration**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/listener/src/hypersync.ts#L28-L34`
- **What**: Fallback block height defaults to `68000000` on height fetch error.
- **Why**: Obsolete default for Polygon chain tip (>75M+).
- **Suggestion**: Fetch latest height from backup RPC or fail gracefully.

### Finding LST-10: 0% Unit Test Coverage on Core Ingestion Logic
- **Severity**: **Medium / Test Coverage**
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/listener/tests/envio.test.ts#L1-L38`
- **What**: Jest suite only tests basic query builder and checkpoint IO.
- **Why**: Zero tests exist for `parseOrderFilledLog`, `matchesBasketWallet`, pricing calculations, Maker/Taker sides, or webhook formatting.
- **Suggestion**: Add full unit test coverage for event parsing and whale basket matching.

---

## 4. Verified Claims Matrix

| Claim | Source / Finding | Verification Method | Status |
| :--- | :--- | :--- | :--- |
| Missing `asyncio` in `database.py` causes NameError | B1 | Inspected `backend/app/database.py#L1-L6` & `#L123` | **VERIFIED (FAIL)** |
| Slippage rejects price improvement | B2 | Inspected `backend/app/sizing/slippage.py#L8-L14` with test inputs | **VERIFIED (FAIL)** |
| Sizing, Fill Model, and Slippage bypassed in poller | B3 | Traced execution in `backend/app/services/live_poller.py#L188-L254` | **VERIFIED (FAIL)** |
| Dead code with undefined variables in `scanner.py` | B4 | Inspected `backend/app/discovery/scanner.py#L326-L350` | **VERIFIED (FAIL)** |
| Threshold mismatch between scanner, engine, rescore | B5 | Compared `engine.py#L22`, `scanner.py#L411`, `basket.py#L98` | **VERIFIED (FAIL)** |
| MCP server `User` model attribute error | B6 | Inspected `mcp_server.py#L269-L272` against `models.py#L79-L94` | **VERIFIED (FAIL)** |
| `userId` ignored in execution/snapshot queries | B7 | Inspected `execution_logs.py#L73`, `#L187`, `#L336` | **VERIFIED (FAIL)** |
| Mock disconnects & dummy tests in backend | B8 | Inspected `test_checkpoint.py`, `test_fee_calculation.py`, `test_ai_summary.py` | **VERIFIED (FAIL)** |
| Synthetic equity curve fabrication | B9 | Inspected `wallets.py#L318-L393` MD5 seed generator | **VERIFIED (FAIL)** |
| Unrealized gains inflate available cash | B10 | Traced MTM snapshot balance to poller free cash calculation | **VERIFIED (FAIL)** |
| Double-counting user realized PnL | B11 | Inspected `live_poller.py#L331-L353` PnL assignment | **VERIFIED (FAIL)** |
| Sandbox reset deletes global database | B12 | Inspected `users.py#L180-L183` unconstrained `delete` queries | **VERIFIED (FAIL)** |
| On-chain signals missing `condition_id` | B13 | Inspected `live_poller.py#L40-L86` and `#L432` | **VERIFIED (FAIL)** |
| Listener hardcoded `'0'` price -> 0.50 fallback | LST-01 | Inspected `event-processor.ts#L83` and `live_poller.py#L425` | **VERIFIED (FAIL)** |
| Listener inverted BUY/SELL and assetId '0' | LST-02 | Traced Maker/Taker logic in `event-processor.ts#L71-L81` | **VERIFIED (FAIL)** |
| Listener `Date.now()` on historical blocks | LST-03 | Inspected `event-processor.ts#L94` | **VERIFIED (FAIL)** |

---

## 5. Adversarial Challenge & Stress-Testing Report

### Challenge 1: Flash Crash & Gap Price Improvement (Slippage Model)
- **Assumption Challenged**: Price divergence between signal and market always represents adverse slippage.
- **Attack Scenario**: Whale buys outcome shares at $0.40. Before the copy order executes, market price drops to $0.30 due to liquidity influx.
- **Blast Radius**: Order is cancelled by `check_slippage` (`abs(0.30 - 0.40) / 0.40 = 0.25 > 0.02`), denying the user a 25% price discount.
- **Mitigation**: Implement directional slippage checking.

### Challenge 2: Bilateral CTF Maker/Taker Token Inversion (Listener Pipeline)
- **Assumption Challenged**: In Polymarket CTF Exchange, Takers always BUY and Makers always SELL.
- **Attack Scenario**: Whale posts a resting limit BUY order offering USDC (`makerAssetId = 0`) for outcome shares (`takerAssetId > 0`). When filled:
- **Blast Radius**: Listener marks the trade as a `SELL` of asset `"0"` (USDC). Backend cannot resolve the prediction market and simulates selling non-existent shares.
- **Mitigation**: Dynamically determine trade side and asset ID based on which side holds collateral (`0`).

### Challenge 3: Unrealized MTM Equity Cascade (Paper Trading Leverage)
- **Assumption Challenged**: Portfolio snapshot balance represents liquid capital available for margin.
- **Attack Scenario**: Whale holds open prediction position that spikes to 0.95. MTM service increases `PortfolioSnapshot.balance` by unrealized profit. Live poller uses `total_portfolio_equity` to calculate `free_cash` and opens large new positions. Market suddenly resolves to 0.00.
- **Blast Radius**: Unrealized gains vanish, leading to catastrophic paper liquidation and negative cash balance.
- **Mitigation**: Restrict `free_cash` strictly to settled cash balance.

---

## 6. Concrete Code Remediation Diffs

### Patch 1: Fix Missing `import asyncio` in `backend/app/database.py`
```diff
--- a/backend/app/database.py
+++ b/backend/app/database.py
@@ -1,3 +1,4 @@
+import asyncio
 import logging
 import os
 from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
```

### Patch 2: Fix Directional Slippage in `backend/app/sizing/slippage.py`
```diff
--- a/backend/app/sizing/slippage.py
+++ b/backend/app/sizing/slippage.py
@@ -1,14 +1,24 @@
-def check_slippage(whale_price: float, current_price: float) -> str:
+def check_slippage(whale_price: float, current_price: float, side: str = "BUY") -> str:
     """
-    Slippage check from spec.
+    Directional slippage check.
+    Allows favorable price improvements (lower BUY price / higher SELL price).
     """
-    if whale_price <= 0:
+    if whale_price <= 0 or current_price <= 0:
         return 'EXECUTE_ORDER'
         
-    diff = abs(current_price - whale_price) / whale_price
-    if whale_price <= 0.25 and diff > 0.012:
+    # Calculate adverse slippage only
+    if side.upper() == "BUY":
+        adverse_diff = (current_price - whale_price) / whale_price
+    else:
+        adverse_diff = (whale_price - current_price) / whale_price
+        
+    # If price improved in our favor, execute immediately
+    if adverse_diff <= 0:
+        return 'EXECUTE_ORDER'
+        
+    if whale_price <= 0.25 and adverse_diff > 0.012:
         return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
-    elif whale_price <= 0.50 and diff > 0.02:
+    elif whale_price <= 0.50 and adverse_diff > 0.02:
         return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
-    elif diff > 0.03:
+    elif adverse_diff > 0.03:
         return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
     return 'EXECUTE_ORDER'
```

### Patch 3: Fix CTF Maker/Taker Side, Asset ID, and Price in `listener/src/event-processor.ts`
```diff
--- a/listener/src/event-processor.ts
+++ b/listener/src/event-processor.ts
@@ -66,22 +66,41 @@ export function matchesBasketWallet(
   let side: 'BUY' | 'SELL';
   let walletAddress: string;
   let assetId: string;
   let amountFilled: string;
+  let calculatedPrice = '0.50';
+
+  const makerAssetIsCollateral = event.makerAssetId === '0';
+  const takerAssetIsCollateral = event.takerAssetId === '0';
 
   if (isTakerBasket) {
-    side = 'BUY';
     walletAddress = takerLower;
-    assetId = event.makerAssetId;
-    amountFilled = event.makerAmountFilled;
+    if (takerAssetIsCollateral) {
+      side = 'BUY';
+      assetId = event.makerAssetId;
+      amountFilled = event.makerAmountFilled;
+      const rawPrice = (parseFloat(event.takerAmountFilled) / 1e6) / (parseFloat(event.makerAmountFilled) / 1e6);
+      calculatedPrice = (!isNaN(rawPrice) && rawPrice > 0) ? rawPrice.toFixed(4) : '0.50';
+    } else {
+      side = 'SELL';
+      assetId = event.takerAssetId;
+      amountFilled = event.takerAmountFilled;
+      const rawPrice = (parseFloat(event.makerAmountFilled) / 1e6) / (parseFloat(event.takerAmountFilled) / 1e6);
+      calculatedPrice = (!isNaN(rawPrice) && rawPrice > 0) ? rawPrice.toFixed(4) : '0.50';
+    }
   } else {
-    side = 'SELL';
     walletAddress = makerLower;
-    assetId = event.makerAssetId;
-    amountFilled = event.makerAmountFilled;
+    if (makerAssetIsCollateral) {
+      side = 'BUY';
+      assetId = event.takerAssetId;
+      amountFilled = event.takerAmountFilled;
+      const rawPrice = (parseFloat(event.makerAmountFilled) / 1e6) / (parseFloat(event.takerAmountFilled) / 1e6);
+      calculatedPrice = (!isNaN(rawPrice) && rawPrice > 0) ? rawPrice.toFixed(4) : '0.50';
+    } else {
+      side = 'SELL';
+      assetId = event.makerAssetId;
+      amountFilled = event.makerAmountFilled;
+      const rawPrice = (parseFloat(event.takerAmountFilled) / 1e6) / (parseFloat(event.makerAmountFilled) / 1e6);
+      calculatedPrice = (!isNaN(rawPrice) && rawPrice > 0) ? rawPrice.toFixed(4) : '0.50';
+    }
   }
 
-  const price = '0'; // Placeholder
-
   return {
     walletAddress,
     side,
     assetId,
     amountFilled,
-    price,
+    price: calculatedPrice,
     transactionHash: event.transactionHash,
     logIndex: event.logIndex,
     blockNumber: event.blockNumber,
     timestamp: Date.now(),
   };
```

### Patch 4: Fix Anti-HFT and Gold Sniper Criteria in `backend/app/scoring/engine.py`
```diff
--- a/backend/app/scoring/engine.py
+++ b/backend/app/scoring/engine.py
@@ -23,8 +23,8 @@ def score_wallet(wallet_stats: dict) -> ScoringResult:
     if pnl < 50000:
         return ScoringResult("rejected", None, "PNL_BELOW_THRESHOLD", False)
 
-    # FILTER 2: Anti-HFT (only reject high-frequency automated market maker bots >300 trades/day)
-    if trades_per_day > 300:
+    # FILTER 2: Anti-HFT (reject high-frequency automated market maker bots >100 trades/day)
+    if trades_per_day > 100:
         return ScoringResult("rejected", None, "HFT_EXCEEDED", False)
 
     # FILTER 3: Outlier concentration (max_single_trade_profit/realized_pnl <= 0.35)
@@ -34,8 +34,8 @@ def score_wallet(wallet_stats: dict) -> ScoringResult:
     if win_rate < 55.0:
         return ScoringResult("rejected", None, "WIN_RATE_TOO_LOW", False)
 
-    # TIER: Gold Sniper if win_rate >= 80.0% OR (pnl >= $100,000 and win_rate >= 70.0%)
-    if (win_rate >= 80.0 and max_drawdown <= 15.0) or (pnl >= 100000 and win_rate >= 70.0):
+    # TIER: Gold Sniper requires both win_rate >= 85.0% AND max_drawdown <= 10.0%
+    if win_rate >= 85.0 and max_drawdown <= 10.0:
         tier = "gold_sniper"
     else:
         tier = "standard"
```

### Patch 5: Fix User Realized PnL Double-Counting in `backend/app/services/live_poller.py`
```diff
--- a/backend/app/services/live_poller.py
+++ b/backend/app/services/live_poller.py
@@ -330,8 +330,8 @@
                         u_ratio = ((effective_fill_price - u_orig_price) / u_orig_price) if u_orig_price > 0 else 0.0
                         
                         u_earliest_buy.status = "CLOSED"
-                        u_earliest_buy.realized_pnl_usd = round(u_orig_notional * u_ratio - float(u_earliest_buy.fee_usd or 0.0), 2)
-                        u_realized_pnl_val = round(u_notional * u_ratio - float(u_fee["fee_usd"]), 2)
+                        u_buy_fee = float(u_earliest_buy.fee_usd or 0.0)
+                        u_sell_fee = float(u_fee["fee_usd"] or 0.0)
+                        u_earliest_buy.realized_pnl_usd = round(u_orig_notional * u_ratio - (u_buy_fee + u_sell_fee), 2)
+                        u_realized_pnl_val = None
```

### Patch 6: Fix Multi-Tenant Sandbox Deletion in `backend/app/api/users.py`
```diff
--- a/backend/app/api/users.py
+++ b/backend/app/api/users.py
@@ -176,12 +176,14 @@ async def reset_user_sandbox(
     if user:
         user.sandbox_starting_balance_usd = new_bal
         user.sandbox_balance_usd = new_bal
         user.sandbox_high_water_mark_usd = new_bal
+        # Clear execution logs and snapshots for this user ONLY
+        await db.execute(delete(ExecutionLog).where(ExecutionLog.user_id == user.id))
+        await db.execute(delete(PortfolioSnapshot).where(PortfolioSnapshot.user_id == user.id))
+    else:
+        await db.execute(delete(ExecutionLog).where(ExecutionLog.user_id.is_(None)))
+        await db.execute(delete(PortfolioSnapshot).where(PortfolioSnapshot.user_id.is_(None)))
-    # Clear ALL execution logs, snapshots and system events across all users and global
-    await db.execute(delete(ExecutionLog))
-    await db.execute(delete(PortfolioSnapshot))
-    await db.execute(delete(SystemEvent))
```

### Patch 7: Fix User Attribute References in `backend/mcp_server.py`
```diff
--- a/backend/mcp_server.py
+++ b/backend/mcp_server.py
@@ -266,7 +266,7 @@ async def handle_baleen_admin_users(args):
         return [
             {
                 "id": str(u.id),
                 "email": u.email,
-                "role": u.role,
+                "risk_profile": u.risk_profile,
                 "sandbox_balance_usd": u.sandbox_balance_usd,
                 "high_water_mark_usd": u.sandbox_high_water_mark_usd,
-                "live_trading_active": u.live_trading_active,
+                "live_trading_enabled": u.live_trading_enabled,
                 "created_at": u.created_at.isoformat() if u.created_at else None
             }
             for u in users
```

---

## 7. Logic Chain

1. **Startup Stability**:
   - `init_db()` in `app/database.py` catches transient PostgreSQL connection errors and invokes `await asyncio.sleep(3)`.
   - Without `import asyncio`, Python encounters `NameError` on the first transient connection blip, aborting startup.

2. **Paper Trading Pricing & Execution Integrity**:
   - `event-processor.ts` sets `price: "0"`, causing `live_poller.py` to default execution price to 0.50.
   - `event-processor.ts` passes `assetId: "0"` for CTF Maker trades, corrupting the prediction token identifier.
   - `slippage.py` computes `abs(price_diff)`, aborting orders whenever market prices move favorably.
   - `live_poller.py` bypasses `fill_simulator.py` and `dynamic_sizer.py`, executing all trades at flat sizes with instant zero-slippage liquidity.
   - Result: The paper trading engine does not reflect Polymarket execution realities.

3. **Accounting & Multi-Tenancy**:
   - User SELL executions record PnL on both the BUY and SELL execution log rows, doubling calculated returns.
   - User sandbox reset erases all records from `execution_logs` and `portfolio_snapshots` across all tenants.

4. **Test Suite Validity**:
   - Backend tests pass at 90.9% only because 5 test suites evaluate local dummy stubs.
   - When real production logic is tested (e.g. `test_scoring_filters.py`), 3 tests fail due to parameter discrepancies in `engine.py`.

---

## 8. Caveats
1. **Live External Network Endpoints**: Polymarket Data API and Gamma API endpoints are subject to public rate limits and schema updates.
2. **AI Model Sandboxing**: Groq API tests require valid API keys in production; local test suites correctly return fallbacks when keys are absent.

---

## 9. Conclusion

The audit reveals significant divergence between the theoretical specifications and the actual running code in `backend/` and `listener/`. The codebase cannot be approved in its current state.

**Verdict**: **REQUEST_CHANGES**

Prior to production deployment, all 8 patches detailed in Section 6 must be applied and validated with full integration tests.

---

## 10. Verification Method

To independently verify these findings and reproduce test behaviors:

### 1. Reproduce Backend Test Failures
```powershell
cd c:\Users\arthu\Documents\Baleen-master\backend
c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\pytest.exe -v tests/test_scoring_filters.py
```
**Expected Outcome**: 3 test failures due to `engine.py` threshold mismatches.

### 2. Verify Database `asyncio` NameError
```python
# Inspect backend/app/database.py
import ast
with open("c:/Users/arthu/Documents/Baleen-master/backend/app/database.py") as f:
    tree = ast.parse(f.read())
imports = [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
assert "asyncio" not in imports, "asyncio is unexpectedly imported!"
```

### 3. Verify Directional Slippage Failure
```python
from app.sizing.slippage import check_slippage
# Whale bought at 0.20, market improved to 0.18 (10% discount)
result = check_slippage(0.20, 0.18)
assert result == 'CANCEL_ORDER: SLIPPAGE_EXCEEDED', "abs() bug reproduced"
```
