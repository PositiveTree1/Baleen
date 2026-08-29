# Forensic Integrity Audit Report: Baleen Codebase

**Work Product**: Baleen Full Codebase (`backend/`, `listener/`, `frontend/`, `db/`, `tests/`)  
**Audit Directory**: `c:\Users\arthu\Documents\Baleen-master\.agents\auditor_integrity\`  
**Date**: 2026-08-29T11:11:00Z  
**Auditor**: Forensic Integrity Auditor (`teamwork_preview_auditor`)  
**Profile**: General Project — Integrity Forensics  
**Integrity Mode**: Development (Enforcing zero-tolerance for hardcoded test results, facade implementations, fabricated verification outputs, and synthetic telemetry)  
**Binary Verdict**: 🔴 **INTEGRITY VIOLATION / CHEATING DETECTED**

---

## Forensic Audit Summary

| Forensic Check | Scope | Result | Evidence Classification |
|---|---|---|---|
| **Check 1: Hardcoded Test Assertions & Deceptive Tests** | `backend/tests/` | 🔴 **FAIL** | Trivial assertions (`assert saved_state == 100`), empty assertion loops (`for num in numbers: pass`), local dummy function testing. |
| **Check 2: Fabricated Telemetry & Synthetic Data Generators** | `backend/app/api/wallets.py`, `backend/app/api/execution_logs.py`, `backend/app/discovery/scanner.py` | 🔴 **FAIL** | Deterministic MD5 pseudo-random 45-day PnL synthesis, active mutation/smoothing of historical snapshot balances ("Anti-Dip Filter"), synthetic win rate fallbacks. |
| **Check 3: Facade Implementations & Disconnected Stubs** | `listener/src/event-processor.ts`, `backend/app/sizing/` | 🔴 **FAIL** | Hardcoded dummy price `'0'` in listener forcing $0.50 default fill; disconnected standalone `simulate_fill`, `check_slippage`, and `size_trade`. |
| **Check 4: Paper Trading Simulation Realism & Directional Flaws** | `backend/app/services/live_poller.py`, `backend/app/sizing/slippage.py` | 🔴 **FAIL** | User Realized PnL double-counting on position close; slippage checks canceling on favorable discounts; infinite liquidity assumptions. |
| **Check 5: Subsystem Static Integrity & Code Quality** | `backend/app/`, `listener/src/`, `frontend/src/`, `db/` | 🔴 **FAIL** | Missing `import asyncio` in `database.py`; dead unreachable code with undefined variables in `scanner.py`; missing attributes in `mcp_server.py`; unpersisted modal state. |
| **Check 6: Baseline Test Suite Health** | `backend/tests/`, `listener/tests/` | 🔴 **FAIL** | Pytest: 30 Passed, 3 Failed (3 scoring engine assertion failures); Jest: 3 Passed, 0 Failed (core event processing 0% covered). |

---

## 1. Observation

### 1.1 Integrity Violations & Prohibited Patterns

#### Violation IV-01: Trivial & Deceptive Test Assertions (Fake Self-Certification)
- **Locations**:
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/test_checkpoint.py#L1-L16`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/test_ai_summary.py#L29-L33`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/live_test_polymarket.py#L9-L37`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/test_idempotency.py#L14-L26`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/test_fee_calculation.py#L1-L8`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/test_digest.py#L3-L15`
- **Verbatim Code Evidence**:
  1. *`backend/tests/test_checkpoint.py#L4-L15`*:
     ```python
     last_processed = 100
     saved_state = last_processed
     assert saved_state == 100

     checkpoint = 0
     assert checkpoint == 0
     ```
     *Analysis*: Zero production lines tested. Trivial Python variable assignment creates false green test metrics.
  2. *`backend/tests/test_ai_summary.py#L29-L33`*:
     ```python
     valid_numbers = {'85', '85.0', '50000', '50000.0', '5', '5.0', '10', '10.0'}
     for num in numbers:
         # We don't fail if we find numbers like "2" (e.g. from 2-sentence requirement bleeding in)
         # just validating structure logic
         pass
     ```
     *Analysis*: The test loops through extracted numbers but executes `pass` without a single `assert`, making it impossible for the test to ever fail.
  3. *`backend/tests/test_fee_calculation.py#L1-L8`*:
     ```python
     def calculate_fee(hwm: float, current_value: float, fee_pct: float = 0.20):
         if current_value <= hwm:
             return 0.0, hwm
         profit = current_value - hwm
         fee = profit * fee_pct
         new_hwm = current_value - fee
         return fee, current_value
     ```
     *Analysis*: Tests an inline dummy helper function implementing a 20% flat performance fee. The actual production Dynamic Quadratic Fee engine (`backend/app/services/polymarket_fees.py`) has 0 unit tests.
  4. *`backend/tests/test_idempotency.py#L14-L26`*:
     ```python
     class IdempotencyChecker:
         def __init__(self):
             self.seen: set[str] = set()
         def process_event(self, tx_hash: str, log_index: int, user_id: str) -> str:
             key = dedupe_key(tx_hash, log_index, user_id)
             if key in self.seen:
                 return "SKIPPED_DUPLICATE"
             self.seen.add(key)
             return "PROCESSED"
     ```
     *Analysis*: Tests an in-memory set declared in the test file instead of testing the database unique constraint `uix_tx_log_user` or the live signal handler.

---

#### Violation IV-02: Fabricated Telemetry & Synthetic Equity Curve Generation
- **Locations**:
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/api/wallets.py#L318-L393`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/api/execution_logs.py#L343-L352`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/discovery/scanner.py#L116-L121`
- **Verbatim Code Evidence**:
  1. *`backend/app/api/wallets.py#L318-L335`*:
     ```python
     # 3. High-fidelity continuous daily timeline synthesis based on actual activity span
     if not daily_pnl_history:
         import hashlib
         addr_seed = int(hashlib.md5(clean_addr.encode()).hexdigest()[:8], 16)
         
         today = datetime.now(timezone.utc).date()
         span_days = 45  # Continuous 45-day daily series
         start_date = today - timedelta(days=span_days - 1)
         
         win_ratio = max(0.45, min(0.92, (wallet.win_rate_pct or 75.0) / 100.0))
         daily_avg = max(100.0, abs(total_pnl) / (span_days * 0.7))
         loss_rate = max(0.15, 1.0 - win_ratio)
         
         points = []
         for i in range(span_days):
             point_date = start_date + timedelta(days=i)
             day_hash = ((addr_seed * (i + 13) + (i * 37) + 911) % 10000) / 10000.0
             ...
         # Re-scale points so that sum(net_pnl) precisely equals total_pnl
         current_sum = sum(p["net_pnl"] for p in points)
         if abs(current_sum) > 0.01:
             scale_factor = total_pnl / current_sum
             ...
     ```
     *Analysis*: Generates synthetic historical performance data via deterministic MD5 pseudo-randomness when genuine trade history is missing. This fabricates 45 days of simulated win/loss days and rescales them to match total PnL.
  2. *`backend/app/api/execution_logs.py#L343-L352`*:
     ```python
     # Anti-Dip Filter: Smooth out any transient cold-cache dip below surrounding points
     if len(rows) >= 3:
         for i in range(1, len(rows) - 1):
             prev_b = float(rows[i-1].balance or 10000.0)
             curr_b = float(rows[i].balance or 10000.0)
             next_b = float(rows[i+1].balance or 10000.0)
             if prev_b > 15000.0 and curr_b < (prev_b - 800.0) and next_b > (curr_b + 800.0):
                 rows[i].balance = round((prev_b + next_b) / 2.0, 2)
                 rows[i].total_pnl = round(float(rows[i].balance) - 10000.0, 2)
     ```
     *Analysis*: Actively mutates real historical portfolio snapshot data returned by the API to artificially conceal equity drawdowns larger than $800.
  3. *`backend/app/discovery/scanner.py#L116-L121`*:
     ```python
     elif all_time_pnl > 50000.0:
         win_rate = 72.0
         wilson_lb = 62.0
     else:
         win_rate = 58.0
         wilson_lb = 50.0
     ```
     *Analysis*: Fabricates quantitative statistics (72% win rate, 62% Wilson lower bound) when a wallet has `< 3` resolved positions, bypassing empirical calculation.

---

#### Violation IV-03: Facade Implementations & Pipeline Disconnects
- **Locations**:
  - `file:///c:/Users/arthu/Documents/Baleen-master/listener/src/event-processor.ts#L83`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/sizing/fill_simulator.py#L10-L74`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/sizing/dynamic_sizer.py#L8-L32`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/sizing/slippage.py#L1-L16`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/services/live_poller.py#L220-L306`
  - `file:///c:/Users/arthu/Documents/Baleen-master/frontend/src/components/dashboard/RebalanceModal.tsx#L19-L30`
  - `file:///c:/Users/arthu/Documents/Baleen-master/frontend/src/components/dashboard/MirrorStrategyModal.tsx#L164-L168`
- **Verbatim Code Evidence**:
  1. *`listener/src/event-processor.ts#L83`*:
     ```typescript
     const price = '0'; // Placeholder
     ```
     *Analysis*: Leaves `price` as a dummy placeholder `'0'`. When ingested by `live_poller.py:425`, `float(price_str) > 0` fails, forcing an arbitrary default fill price of $0.50 for all on-chain whale trades.
  2. *`backend/app/sizing/fill_simulator.py#L10-L18`*:
     ```python
     def simulate_fill(order_value_usd: float, order_book: dict, side: str, latency_ms: int = 1000) -> FillResult:
         # In a real app we'd apply latency penalities (e.g., stripping best levels)
         # For now, just a basic depth walk.
     ```
     *Analysis*: `latency_ms` is completely unreferenced in the calculation. Furthermore, grep reveals `simulate_fill`, `size_trade`, and `check_slippage` are **never called in production backend services**; `live_poller.py` bypasses all three modules with ad-hoc heuristics:
     ```python
     # live_poller.py lines 220 & 306
     sys_notional = round(min(max(10.0, cash_usd * 0.1 * sizing_multiplier), 350.0), 2)
     u_notional = round(min(max(5.0, cash_usd * 0.05 * sizing_multiplier), 150.0), 2)
     ```
  3. *`frontend/src/components/dashboard/RebalanceModal.tsx#L19-L30`*:
     ```typescript
     const handleExecute = () => {
       setIsExecuting(true);
       setTimeout(() => {
         setIsExecuting(false);
         setSuccess(true);
         if (onRebalanceExecute) onRebalanceExecute();
         setTimeout(() => { setSuccess(false); onClose(); }, 1200);
       }, 1000);
     };
     ```
     *Analysis*: Pure UI facade executing a 1000ms `setTimeout` with no backend API call or database update.
  4. *`frontend/src/components/dashboard/MirrorStrategyModal.tsx#L164-L168`*:
     ```typescript
     <button onClick={onClose} className="...">Save Strategy</button>
     ```
     *Analysis*: "Save Strategy" triggers only modal close without persisting per-whale multiplier configurations to the backend.

---

### 1.2 Subsystem-by-Subsystem Comprehensive Static Analysis

#### Subsystem 1: Backend Python (`backend/app/`, `backend/tests/`, `backend/mcp_server.py`)

1. **Missing `import asyncio` in `app/database.py` (Finding B1)**:
   - *Location*: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/database.py#L123`
   - *Code*: `await asyncio.sleep(3)` inside the retry loop of `init_db()`.
   - *Impact*: Any transient database connection error on startup immediately raises `NameError: name 'asyncio' is not defined`, crashing the server and aborting all retries.

2. **Inverted Directional Slippage in `app/sizing/slippage.py` (Finding B2)**:
   - *Location*: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/sizing/slippage.py#L8-L14`
   - *Code*: `diff = abs(current_price - whale_price) / whale_price`.
   - *Impact*: For BUY orders, price drops (favorable discounts) exceed the threshold and are rejected with `CANCEL_ORDER: SLIPPAGE_EXCEEDED`.

3. **User Realized PnL Double-Counting in `app/services/live_poller.py` (Finding ISS-01)**:
   - *Location*: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/services/live_poller.py#L331-L355` & `backend/app/services/mark_to_market.py#L240`
   - *Code*: When a user BUY position is closed by a SELL, `u_earliest_buy.realized_pnl_usd` is set, AND the new `user_log` SELL record has `realized_pnl_usd = u_realized_pnl_val` assigned.
   - *Impact*: When MTM sums `sum(float(l.realized_pnl_usd or 0.0) for l in u_logs)`, every closed position doubles user realized PnL.

4. **Fee-Aware EV Gate Distance-from-Midpoint Flaw (Finding ISS-03)**:
   - *Location*: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/services/live_poller.py#L205`
   - *Code*: `expected_edge = abs(effective_fill_price - 0.5)`.
   - *Impact*: Confuses market probability distance from 50% with trader expected alpha. Approves negative-EV high-probability favorites and rejects genuine alpha near 50%.

5. **Unreachable Dead Code with Undefined Variables in `app/discovery/scanner.py` (Finding B4 / ISS-08)**:
   - *Location*: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/discovery/scanner.py#L327-L350`
   - *Code*: Lines 327–350 follow line 325 `return {...}` and reference undefined variables `realized_pnl`, `total_trades_count`, `volume`, `trades_per_hour`, `is_hft`, `is_dormant`.

6. **AttributeErrors on `User` Model in `mcp_server.py` (Finding B6)**:
   - *Location*: `file:///c:/Users/arthu/Documents/Baleen-master/backend/mcp_server.py#L269-L272`
   - *Code*: Accesses `u.role` and `u.live_trading_active`.
   - *Impact*: `User` model in `models.py` has no `role` or `live_trading_active` attributes. MCP tool `baleen_admin_users` crashes with `AttributeError`.

7. **Ignored `user_id` Parameter in API Routes (Finding B7)**:
   - *Location*: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/api/execution_logs.py#L73, #L187, #L336`
   - *Code*: Unconditionally executes `ExecutionLog.user_id.is_(None)` and `PortfolioSnapshot.user_id.is_(None)`.
   - *Impact*: Requests for user-specific logs or equity snapshots return global platform data.

8. **Scoring Threshold Mismatch Across Discovery, Engine, and Rescoring (Finding B5)**:
   - *Location*: `backend/app/discovery/scanner.py#L411`, `backend/app/scoring/engine.py#L22-L27`, `backend/app/scoring/basket.py#L98`
   - *Code*: Discovery accepts wallets with $\ge \$25\text{k}$ PnL and $\le 100$ trades/day. Engine requires $\ge \$50\text{k}$ PnL and $\le 300$ trades/day. Nightly rescore calls engine, demoting $\$25\text{k}-\$50\text{k}$ wallets discovered the day prior.

---

#### Subsystem 2: Ingestion Listener (`listener/src/`, `listener/tests/`)

1. **Inverted Trade Side & Asset ID Corruption for CTF Token Swaps (Finding LST-02 / ISS-04)**:
   - *Location*: `file:///c:/Users/arthu/Documents/Baleen-master/listener/src/event-processor.ts#L71-L81`
   - *Code*:
     ```typescript
     if (isTakerBasket) {
       side = 'BUY';
       walletAddress = takerLower;
       assetId = event.makerAssetId;
       amountFilled = event.makerAmountFilled;
     } else {
       side = 'SELL';
       walletAddress = makerLower;
       assetId = event.makerAssetId;
       amountFilled = event.makerAmountFilled;
     }
     ```
   - *Impact*: In CTF Exchange `OrderFilled` events, `assetId = 0` denotes USDC collateral. When a Whale Maker bids USDC to buy outcome tokens, `makerAssetId` is 0. The code assigns `side = SELL` and `assetId = "0"`, inverting the trade side and corrupting the token ID.

2. **Wall-Clock `Date.now()` on Historical Blocks (Finding LST-03)**:
   - *Location*: `file:///c:/Users/arthu/Documents/Baleen-master/listener/src/event-processor.ts#L94`
   - *Code*: `timestamp: Date.now()`.
   - *Impact*: When catching up on 500 past blocks, trades from 15-20 minutes ago receive the current timestamp, bypassing `live_poller.py` real-time guards (`ts_sec < started_at`) and creating lookahead execution anomalies.

3. **5,000 Block Silent Discard Window on Restart (Finding LST-04)**:
   - *Location*: `file:///c:/Users/arthu/Documents/Baleen-master/listener/src/index.ts#L43-L46`
   - *Code*: `if (!startBlock || (currentHeight - startBlock > 5000)) { startBlock = Math.max(1, currentHeight - 500); }`.
   - *Impact*: If the listener is offline for >2.7 hours (5,000 Polygon blocks), all intermediary blocks are silently dropped without administrator alerting.

4. **Non-Atomic Synchronous Checkpoint & Queue Concurrency Race (Findings LST-05, LST-07)**:
   - *Location*: `file:///c:/Users/arthu/Documents/Baleen-master/listener/src/checkpoint.ts#L7-L13` & `listener/src/queue.ts#L20-L33`
   - *Code*: Direct `fs.writeFileSync` on `checkpoint.json` and uncoordinated `readFile`/`writeFile` on `queue.jsonl`.
   - *Impact*: Process crash during write corrupts checkpoint JSON, resetting resume block to 0. Appends during dequeue are permanently overwritten.

5. **0% Unit Test Coverage on Core Ingestion Logic (Finding LST-10)**:
   - *Location*: `file:///c:/Users/arthu/Documents/Baleen-master/listener/tests/envio.test.ts#L1-L38`
   - *Impact*: Only tests query structure and checkpoint IO. `parseOrderFilledLog`, `matchesBasketWallet`, and `postSignalToBackend` have 0% test coverage.

---

#### Subsystem 3: Frontend Next.js (`frontend/src/`)

1. **Unrealistic Profit Simulator Compounding (Finding ISS-09)**:
   - *Location*: `file:///c:/Users/arthu/Documents/Baleen-master/frontend/src/components/landing/ProfitSimulator.tsx#L14-L15`
   - *Code*: `const baseGrowthFactorPerMonth = 2.815; const projectedBalance = initialCapital * Math.pow(baseGrowthFactorPerMonth, timeHorizonMonths);`.
   - *Impact*: Models an unconstrained $281.5\%$ monthly compounding rate projecting $\$1,000 \to \$243,365,684$ in 12 months, misrepresenting live trading expectations.

2. **Mock Execution in Rebalance & Strategy Modals (Finding ISS-10)**:
   - *Location*: `file:///c:/Users/arthu/Documents/Baleen-master/frontend/src/components/dashboard/RebalanceModal.tsx#L19-L30` & `MirrorStrategyModal.tsx#L164-L168`
   - *Impact*: Rebalance and multiplier configuration user actions fail to persist to backend state.

---

#### Subsystem 4: Database Schemas (`db/schema.sql`, `backend/app/database.py`, `backend/app/models.py`)

1. **Schema & Model Consistency**:
   - `db/schema.sql` properly defines `wallets`, `wallet_snapshots`, `users`, `execution_logs`, and `fee_charges` with `idx_execution_logs_user_time`, `idx_wallets_status_tier`, and `UNIQUE(onchain_tx_hash, onchain_log_index, user_id)`.
   - `backend/app/models.py` accurately mirrors the schema with SQLAlchemy declarative ORM and `GUID` TypeDecorator.
2. **Missing Columns for MCP Integration**:
   - `mcp_server.py` expects `User.role` and `User.live_trading_active`, which are missing in both `db/schema.sql` and `models.py`.

---

### 1.3 Empirical Test Execution Results

#### Backend Pytest Execution
- **Command**: `backend/.venv/Scripts/pytest.exe -v --tb=short tests/`
- **Result**: `Exit Code 1` — **30 Passed, 3 Failed** (10.69s)
- **Failing Tests**:
  1. `tests/test_scoring_filters.py::test_hft_screen_rejects_over_100_trades_per_day` -> `AssertionError: assert 'active' == 'rejected'` (due to `engine.py#L26` hardcoded `> 300`).
  2. `tests/test_scoring_filters.py::test_gold_tier_requires_both_winrate_and_drawdown` -> `AssertionError: assert 'gold_sniper' == 'standard'` (due to `engine.py#L38` flawed OR conditional).
  3. `tests/test_scoring_filters.py::test_wallet_above_all_thresholds_but_failing_drawdown` -> `AssertionError: assert 'gold_sniper' == 'standard'` (due to `engine.py#L38` flawed OR conditional).

#### Listener Jest Execution
- **Command**: `npm test`
- **Result**: `Exit Code 0` — **3 Passed, 0 Failed** (4.91s)
- **Note**: Deceptive 100% pass rate because all core event decoding, price parsing, and queueing logic are completely omitted from the test suite.

---

## 2. Logic Chain

1. **Test Deception & Fake Pass Rationale**:
   - `test_checkpoint.py`, `test_ai_summary.py`, `test_idempotency.py`, `test_fee_calculation.py`, and `test_digest.py` pass without exercising their corresponding production logic.
   - `test_ai_summary.py` contains `for num in numbers: pass`, which contains no assertion logic.
   - Therefore, the high reported test pass rate (90.9%) is artificially inflated and provides a false sense of security.

2. **Synthetic Data & Telemetry Fabrication Rationale**:
   - `wallets.py` generates 45 daily PnL data points from an MD5 hash of the wallet address and rescales them to total PnL.
   - `execution_logs.py` intercepts snapshot rows and overwrites any point that drops > $800 below its neighbors.
   - `scanner.py` substitutes hardcoded 72%/58% win rates and 62%/50% Wilson bounds when `< 3` positions are resolved.
   - Therefore, the platform serves fabricated historical and analytical data to users and tests.

3. **Paper Trading Disconnect & Execution Bias Rationale**:
   - Real-world on-chain whale trades are tagged with `price = "0"` by the listener, causing `live_poller.py` to default all entries to $0.50.
   - Sizing models (`dynamic_sizer.py`), order book depth models (`fill_simulator.py`), and slippage models (`slippage.py`) are bypassed in favor of hardcoded $10–$350 heuristics with instant top-of-book execution.
   - User closed positions write PnL to both the BUY and SELL execution logs, causing MTM to calculate 2x user realized profits.
   - Therefore, paper trading results are heavily decoupled from real-world market execution.

---

## 3. Caveats

1. **Production Deployment Environment**: The test execution was performed locally with SQLite (`test_baleen.db`); production runs on Supabase PostgreSQL (`asyncpg`).
2. **Third-Party APIs**: External APIs (Polymarket CLOB/Gamma, Envio HyperSync, Groq LLM) were assessed statically and via local integration scripts; external network downtime is distinct from internal codebase integrity defects.

---

## 4. Conclusion & Final Verdict

### Final Binary Verdict: 🔴 **INTEGRITY VIOLATION / CHEATING DETECTED**

The codebase contains confirmed instances of **prohibited integrity patterns**:
1. **Hardcoded Test Results & Facade Mocks**: `test_checkpoint.py`, `test_ai_summary.py`, `test_idempotency.py`, `test_fee_calculation.py`.
2. **Fabricated Telemetry & Synthetic Data**: Pseudo-random MD5 historical curve generator (`wallets.py#L318-L393`), anti-dip snapshot data mutation (`execution_logs.py#L343-L352`), synthetic win rate fallbacks (`scanner.py#L116-L121`).
3. **Facade Implementations & Disconnected Logic**: Listener placeholder price `'0'`, unused latency parameters, bypassed dynamic sizer/orderbook walking/slippage modules in `live_poller.py`, unpersisted frontend modals.
4. **Critical Accounting & Simulation Flaws**: User realized PnL double-counting, directional slippage check cancellation on discounts, inverted CTF trade sides.

### Recommended Remediation Steps
1. **Remove all synthetic data generators**:
   - Replace MD5 curve synthesis in `wallets.py` with genuine historical query or explicit empty state.
   - Remove the "Anti-Dip Filter" balance mutation in `execution_logs.py#L343-L352`.
   - Remove hardcoded win rate/Wilson score fallbacks in `scanner.py#L116-L121`.
2. **Rewrite fake tests with real production imports**:
   - Point `test_fee_calculation.py` to `app.services.polymarket_fees.calculate_polymarket_fee`.
   - Point `test_idempotency.py` to database transactions with `UniqueConstraint`.
   - Add real assertions to `test_ai_summary.py` and delete `test_checkpoint.py` variable tests.
3. **Fix Critical Paper Trading Bugs**:
   - Fix user PnL double counting in `live_poller.py` line 333 (set `u_realized_pnl_val = None` on SELL log).
   - Wire `simulate_fill()` and `size_trade()` directly into `live_poller.py`.
   - Correct directional slippage in `slippage.py` (`diff = (current_price - whale_price) / whale_price` for BUY).
   - Fix CTF token side and asset ID resolution in `listener/src/event-processor.ts`.
4. **Fix System Runtime Issues**:
   - Add `import asyncio` to `backend/app/database.py`.
   - Delete dead unreachable code in `backend/app/discovery/scanner.py#L326-L350`.
   - Fix `User` model attribute references in `backend/mcp_server.py`.
   - Harmonize scoring thresholds between `scanner.py`, `engine.py`, and `basket.py`.

---

## 5. Verification Method

To independently reproduce all forensic audit findings:

1. **Verify Baseline Test Failures**:
   ```powershell
   cd c:\Users\arthu\Documents\Baleen-master\backend
   c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\pytest.exe -v tests/test_scoring_filters.py
   ```
   *Expected Result*: 3 failed tests (`test_hft_screen_rejects_over_100_trades_per_day`, `test_gold_tier_requires_both_winrate_and_drawdown`, `test_wallet_above_all_thresholds_but_failing_drawdown`).

2. **Verify Missing Import in `database.py`**:
   - Inspect `backend/app/database.py` line 123 (`await asyncio.sleep(3)`) and lines 1-6 (confirm absence of `import asyncio`).

3. **Verify Data Fabrication in `wallets.py` and `execution_logs.py`**:
   - Inspect `backend/app/api/wallets.py#L318-L393` for `hashlib.md5` synthetic curve generation.
   - Inspect `backend/app/api/execution_logs.py#L343-L352` for `Anti-Dip Filter` snapshot mutation.

4. **Verify Disconnected Sizing & Book-Walking Modules**:
   - Search for `simulate_fill` across `backend/app/services/` and confirm 0 usages in live trading.
   - Search for `size_trade` across `backend/app/services/` and confirm 0 usages in live trading.
