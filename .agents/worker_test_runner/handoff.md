# Test Suite Execution & Baseline Evaluation Report (Milestone M1)

**Working Directory**: `c:\Users\arthu\Documents\Baleen-master`  
**Metadata Directory**: `c:\Users\arthu\Documents\Baleen-master\.agents\worker_test_runner\`  
**Timestamp**: 2026-08-29T11:09:00Z  
**Author**: Test Execution Worker (`worker_test_runner`)  
**Milestone**: M1 — Codebase Audit & Baseline Verification  

---

## 1. Observation

### 1.1 Environment Configuration & Toolchains
- **OS**: Windows 11 (x86_64)
- **Python Runtime**: Python 3.11.16 via isolated virtual environment (`backend/.venv/`)
- **Pytest Version**: `pytest 9.1.1` (`pluggy 1.6.0`, `anyio 4.14.2`, `pytest-asyncio 1.4.0`)
- **Node.js Runtime**: Node.js `v20.18.0`, npm `10.8.2` (`.tools/node/`)
- **Jest Version**: `jest 29.7.0`, `ts-jest 29.1.0`

---

### 1.2 Backend Test Suite Execution (`backend/tests/`)

#### Global Suite Command & Summary
- **Command**: `c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\pytest.exe -v --tb=short tests/`
- **Working Directory**: `c:\Users\arthu\Documents\Baleen-master\backend`
- **Exit Code**: `1`
- **Total Tests Collected**: 33 tests across 12 test files
- **Passed**: 30 (90.9%)
- **Failed**: 3 (9.1%)
- **Duration**: 10.69 seconds

#### Verbatim Global Pytest Console Output
```text
============================= test session starts =============================
platform win32 -- Python 3.11.16, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\arthu\Documents\Baleen-master\backend
configfile: pytest.ini
plugins: anyio-4.14.2, asyncio-1.4.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 33 items

tests/test_ai_summary.py::test_summary_does_not_introduce_unlisted_numbers PASSED [  3%]
tests/test_checkpoint.py::test_save_and_resume_checkpoint PASSED         [  6%]
tests/test_checkpoint.py::test_default_checkpoint_is_zero PASSED         [  9%]
tests/test_digest.py::test_digest_includes_only_opted_in_users PASSED    [ 12%]
tests/test_dormancy.py::test_dormancy_is_relative_to_own_median_gap PASSED [ 15%]
tests/test_dormancy.py::test_daily_trader_dormant_after_8x_gap PASSED    [ 18%]
tests/test_dormancy.py::test_weekly_trader_not_dormant_at_same_hours PASSED [ 21%]
tests/test_dynamic_sizing.py::test_sizing_scales_with_active_basket_size PASSED [ 24%]
tests/test_dynamic_sizing.py::test_risk_cap_overrides_raw_calculation PASSED [ 27%]
tests/test_dynamic_sizing.py::test_below_minimum_is_skipped_not_failed PASSED [ 30%]
tests/test_dynamic_sizing.py::test_dormant_wallets_excluded_from_denominator PASSED [ 33%]
tests/test_dynamic_sizing.py::test_equal_weight_across_active_members PASSED [ 36%]
tests/test_fee_calculation.py::test_no_fee_when_recovering_past_losses PASSED [ 39%]
tests/test_fee_calculation.py::test_fee_only_on_profit_above_hwm PASSED  [ 42%]
tests/test_fee_calculation.py::test_hwm_ratchets_up_only PASSED          [ 45%]
tests/test_fill_model.py::test_fill_walks_order_book_not_exact_whale_price PASSED [ 48%]
tests/test_fill_model.py::test_larger_order_gets_worse_price PASSED      [ 51%]
tests/test_fill_model.py::test_insufficient_liquidity PASSED             [ 54%]
tests/test_idempotency.py::test_first_event_processed PASSED             [ 57%]
tests/test_idempotency.py::test_duplicate_event_skipped PASSED           [ 60%]
tests/test_idempotency.py::test_same_tx_different_log_index_processed PASSED [ 63%]
tests/test_idempotency.py::test_same_tx_same_log_different_user_processed PASSED [ 66%]
tests/test_scoring_filters.py::test_pnl_threshold_rejects_below_50k PASSED [ 69%]
tests/test_scoring_filters.py::test_hft_screen_rejects_over_100_trades_per_day FAILED [ 72%]
tests/test_scoring_filters.py::test_outlier_concentration_rejects_single_trade_over_35pct PASSED [ 75%]
tests/test_scoring_filters.py::test_gold_tier_requires_both_winrate_and_drawdown FAILED [ 78%]
tests/test_scoring_filters.py::test_gold_tier_accepts_qualifying_wallet PASSED [ 81%]
tests/test_scoring_filters.py::test_wallet_above_all_thresholds_but_failing_drawdown FAILED [ 84%]
tests/test_signals_and_drawer.py::test_signals_and_trade_endpoints PASSED [ 87%]
tests/test_slippage.py::test_high_slippage_at_low_price_cancels PASSED   [ 90%]
tests/test_slippage.py::test_low_slippage_at_mid_price_executes PASSED   [ 93%]
tests/test_slippage.py::test_reasonable_slippage_executes PASSED         [ 96%]
tests/test_wallet_api.py::test_get_wallet_detail_and_snapshots PASSED    [100%]

================================== FAILURES ===================================
_______________ test_hft_screen_rejects_over_100_trades_per_day _______________
tests\test_scoring_filters.py:12: in test_hft_screen_rejects_over_100_trades_per_day
    assert res.status == "rejected"
E   AssertionError: assert 'active' == 'rejected'
E     
E     - rejected
E     + active
______________ test_gold_tier_requires_both_winrate_and_drawdown ______________
tests\test_scoring_filters.py:26: in test_gold_tier_requires_both_winrate_and_drawdown
    assert res.tier.lower() == "standard"
E   AssertionError: assert 'gold_sniper' == 'standard'
E     
E     - standard
E     + gold_sniper
____________ test_wallet_above_all_thresholds_but_failing_drawdown ____________
tests\test_scoring_filters.py:44: in test_wallet_above_all_thresholds_but_failing_drawdown
    assert res.tier.lower() == "standard"
E   AssertionError: assert 'gold_sniper' == 'standard'
E     
E     - standard
E     + gold_sniper
=========================== short test summary info ===========================
FAILED tests/test_scoring_filters.py::test_hft_screen_rejects_over_100_trades_per_day
FAILED tests/test_scoring_filters.py::test_gold_tier_requires_both_winrate_and_drawdown
FAILED tests/test_scoring_filters.py::test_wallet_above_all_thresholds_but_failing_drawdown
======================== 3 failed, 30 passed in 10.69s ========================
```

---

### 1.3 Granular Per-File Breakdown of Required Backend Test Files

| # | Test File Path | Tests | Passed | Failed | Exit Code | Duration | Status |
|---|---|---|---|---|---|---|---|
| 1 | `tests/test_checkpoint.py` | 2 | 2 | 0 | 0 | 0.09s | PASSED (Dummy/Mock) |
| 2 | `tests/test_dynamic_sizing.py` | 5 | 5 | 0 | 0 | 0.09s | PASSED |
| 3 | `tests/test_fee_calculation.py` | 3 | 3 | 0 | 0 | 0.08s | PASSED (Dummy/Mock) |
| 4 | `tests/test_fill_model.py` | 3 | 3 | 0 | 0 | 0.08s | PASSED |
| 5 | `tests/test_idempotency.py` | 4 | 4 | 0 | 0 | 0.09s | PASSED (Dummy/Mock) |
| 6 | `tests/test_scoring_filters.py` | 6 | 3 | 3 | 1 | 0.62s | **FAILED (3 Failures)** |
| 7 | `tests/test_signals_and_drawer.py` | 1 | 1 | 0 | 0 | 4.14s | PASSED |
| 8 | `tests/test_slippage.py` | 3 | 3 | 0 | 0 | 0.11s | PASSED |
| 9 | `tests/test_wallet_api.py` | 1 | 1 | 0 | 0 | 4.37s | PASSED |
| 10 | `tests/test_ai_summary.py` | 1 | 1 | 0 | 0 | 1.10s | PASSED (Incomplete Assertions) |
| 11 | `tests/test_digest.py` | 1 | 1 | 0 | 0 | 1.90s | PASSED (Dummy/Mock) |
| 12 | `tests/test_dormancy.py` | 3 | 3 | 0 | 0 | 0.09s | PASSED |

---

### 1.4 Listener Test Suite Execution (`listener/tests/`)

- **Command**: `npm test` (`jest`)
- **Working Directory**: `c:\Users\arthu\Documents\Baleen-master\listener`
- **Exit Code**: `0`
- **Total Test Suites**: 1 suite (`tests/envio.test.ts`)
- **Total Tests**: 3 tests
- **Passed**: 3 (100%)
- **Failed**: 0 (0%)
- **Duration**: 45.115s (startup/transpilation), 1.394s execution

#### Verbatim Listener Jest Output
```text
> baleen-listener@0.1.0 test
> jest

PASS tests/envio.test.ts (39.241 s)
  HyperSync and Checkpoint Tests
    √ should build a valid query (7 ms)
    √ should save and resume checkpoint (45 ms)
    √ should create client (87 ms)

Test Suites: 1 passed, 1 total
Tests:       3 passed, 3 total
Snapshots:   0 total
Time:        45.115 s
Ran all test suites.
```

---

## 2. Logic Chain & Root Cause Analysis

### 2.1 Deep Diagnostic of Failing Tests in `backend/app/scoring/engine.py`

#### Failure 1: `test_hft_screen_rejects_over_100_trades_per_day`
- **Test Code** (`backend/tests/test_scoring_filters.py#L9-L13`):
  ```python
  def test_hft_screen_rejects_over_100_trades_per_day(make_wallet_stats):
      stats = make_wallet_stats(trades_per_day=101.0)
      res = score_wallet(stats)
      assert res.status == "rejected"
      assert res.rejection_reason == "HFT_EXCEEDED"
  ```
- **Observed Failure**: `AssertionError: assert 'active' == 'rejected'`
- **Root Cause in Source Code** (`backend/app/scoring/engine.py#L25-L27`):
  ```python
  # FILTER 2: Anti-HFT (only reject high-frequency automated market maker bots >300 trades/day)
  if trades_per_day > 300:
      return ScoringResult("rejected", None, "HFT_EXCEEDED", False)
  ```
- **Inference**: The implementation hardcoded a 300 trades/day threshold instead of the 100 trades/day threshold defined in the system specification §4. When `trades_per_day = 101.0` is scored, `101 > 300` evaluates to `False`, bypassing the anti-HFT filter and returning `status="active"`.

#### Failure 2: `test_gold_tier_requires_both_winrate_and_drawdown`
- **Test Code** (`backend/tests/test_scoring_filters.py#L21-L27`):
  ```python
  def test_gold_tier_requires_both_winrate_and_drawdown(make_wallet_stats):
      # High win rate (90.0%), bad drawdown (15.0%)
      stats = make_wallet_stats(win_rate=90.0, max_drawdown=15.0)
      res = score_wallet(stats)
      assert res.status == "active"
      assert res.tier.lower() == "standard"
  ```
- **Observed Failure**: `AssertionError: assert 'gold_sniper' == 'standard'`
- **Root Cause in Source Code** (`backend/app/scoring/engine.py#L37-L41`):
  ```python
  # TIER: Gold Sniper if win_rate >= 80.0% OR (pnl >= $100,000 and win_rate >= 70.0%)
  if (win_rate >= 80.0 and max_drawdown <= 15.0) or (pnl >= 100000 and win_rate >= 70.0):
      tier = "gold_sniper"
  else:
      tier = "standard"
  ```
- **Inference**:
  1. `make_wallet_stats` fixture in `conftest.py#L22` provides default `pnl = 100000.0`.
  2. The right-hand OR operand `(pnl >= 100000 and win_rate >= 70.0)` evaluates to `100000 >= 100000 and 90.0 >= 70.0` -> `True`.
  3. This completely bypasses the max drawdown constraint on high-PnL wallets.
  4. Even without the right-hand operand, the left-hand operand used `max_drawdown <= 15.0` instead of `<= 10.0%` (allowing a 15.0% drawdown to qualify as gold sniper).

#### Failure 3: `test_wallet_above_all_thresholds_but_failing_drawdown`
- **Test Code** (`backend/tests/test_scoring_filters.py#L40-L45`):
  ```python
  def test_wallet_above_all_thresholds_but_failing_drawdown(make_wallet_stats):
      stats = make_wallet_stats(win_rate=90.0, max_drawdown=11.0)
      res = score_wallet(stats)
      assert res.status == "active"
      assert res.tier.lower() == "standard"
  ```
- **Observed Failure**: `AssertionError: assert 'gold_sniper' == 'standard'`
- **Root Cause**: Identical to Failure 2. Because `pnl = 100000.0` and `win_rate = 90.0% >= 70.0%`, the wallet is classified as `gold_sniper` regardless of having `max_drawdown = 11.0% > 10.0%`.

---

### 2.2 Mock Disconnects & Dummy Function Implementations

A critical finding from this test audit is that **five backend test suites do not test production service code**, instead testing local dummy functions or in-memory stubs defined inside the test files:

1. **`tests/test_checkpoint.py`** (`backend/tests/test_checkpoint.py#L1-L16`):
   - **Observation**:
     ```python
     def test_save_and_resume_checkpoint():
         last_processed = 100
         saved_state = last_processed
         assert saved_state == 100
     def test_default_checkpoint_is_zero():
         checkpoint = 0
         assert checkpoint == 0
     ```
   - **Impact**: Zero lines of production backend or listener checkpoint code are exercised. Tests trivial Python variable assignment.

2. **`tests/test_fee_calculation.py`** (`backend/tests/test_fee_calculation.py#L1-L8`):
   - **Observation**: Defines a local Python helper `calculate_fee(hwm, current_value, fee_pct=0.20)` and tests only that helper.
   - **Impact**: The actual production Dynamic Fee module in `backend/app/services/polymarket_fees.py` (which contains `calculate_polymarket_fee`, category Theta coefficients 0.000–0.072, Banker's Rounding, and `calculate_fee_aware_ev_gate`) has **zero tests**.

3. **`tests/test_idempotency.py`** (`backend/tests/test_idempotency.py#L9-L26`):
   - **Observation**: Defines a custom mock class `IdempotencyChecker` utilizing a Python `set()` in memory.
   - **Impact**: Does not test the actual database constraint `UniqueConstraint('onchain_tx_hash', 'onchain_log_index', 'user_id')` on `ExecutionLog` (`app/models.py#L136`) or the live signal handler `app/api/signals.py`.

4. **`tests/test_digest.py`** (`backend/tests/test_digest.py#L3-L15`):
   - **Observation**: Instantiates a Python list of `User(email=..., daily_digest_opt_in=...)` objects and filters them with a Python list comprehension `[u for u in users if u.daily_digest_opt_in]`.
   - **Impact**: Does not test database queries, SQLAlchemy session execution, digest worker tasks (`app/workers/`), or SMTP email dispatch logic.

5. **`tests/test_ai_summary.py`** (`backend/tests/test_ai_summary.py#L20-L33`):
   - **Observation**: Executes `generate_summary(stats)`. If the summary is returned, it extracts numbers with regex but then executes a no-op `pass` inside the assertion loop (`for num in numbers: pass`).
   - **Impact**: The test cannot fail under any circumstances, providing deceptive 100% pass status without validating output integrity.

6. **`tests/live_test_polymarket.py`** (`backend/tests/live_test_polymarket.py#L9-L37`):
   - **Observation**: Wraps HTTP requests to Polymarket data API in `try: ... except Exception as e: print(...)` without any assertion statements.
   - **Impact**: Never fails during pytest collection, even if external endpoints are unreachable or data schema is corrupted.

---

### 2.3 Test Coverage Gaps Across Subsystems

#### Listener Gaps (`listener/src/`)
- `src/event-processor.ts`: **0% Coverage**. No tests for `OrderFilled` ABI decoding, topic hash matching, Maker/Taker address extraction, binary outcome side normalization (`side = BUY/SELL`), token decimal conversion (`amountFilled`), or webhook payload generation.
- `src/queue.ts`: **0% Coverage**. No tests for local disk queue persistence, FIFO message ordering, retry backoff on backend 500/503 errors, or queue recovery on restart.
- `src/index.ts`: **0% Coverage**. No tests for polling intervals, process signal trapping (`SIGINT`/`SIGTERM`), or websocket disconnection reconnection.
- `src/config.ts` & `src/constants.ts`: **0% Coverage**. No tests verifying contract addresses (CTF Exchange `0x4bFb...`, Neg Risk CTF Exchange `0xC5d5...`) or topic hashes.

#### Backend Gaps (`backend/app/`)
- **Dynamic Quadratic Taker Fees** (`app/services/polymarket_fees.py`): Missing tests for category keyword classification (Crypto, Economics, Politics, Sports, Culture, Geopolitics), Theta rate calculations, maker 0% fee exemption, and the EV gate condition `Expected Edge >= 2.5 * [Theta * (1 - p)]`.
- **Autonomous Workers** (`app/workers/`): Missing tests for the 20-minute Whale Discovery worker, 24-hour Rescoring worker, and 24-hour Analysis worker.
- **Mark-to-Market Revaluation Engine** (`app/services/mark_to_market.py`): Missing unit and stress tests for unrealized PnL mark-to-market valuations, drawdown tracking, and High Water Mark updates.
- **MCP Admin Server** (`backend/mcp_server.py`): Missing tests for Model Context Protocol stdio tool handlers (`list_wallets`, `get_wallet`, `update_risk_profile`, `trigger_discovery`, `reset_sandbox`).
- **API Error Handling**: Missing tests for 404 Not Found, 422 Unprocessable Entity, invalid payload shapes, and negative number edge cases across all FastAPI routers (`/api/wallets`, `/api/executions`, `/api/signals`, `/api/auth`).

---

## 3. Caveats

1. **Database Dialect Discrepancy**: Backend unit tests execute against SQLite via `aiosqlite` (`sqlite+aiosqlite:///test_baleen.db`) as configured in `conftest.py`. Production runtime is configured for PostgreSQL (`asyncpg`). Dialect-specific behaviors—such as UUID indexing semantics, `ON CONFLICT DO NOTHING` row-level locks, and strict datetime timezone parsing—were not tested against a live PostgreSQL instance during unit test runs.
2. **AI Provider Sandbox Isolation**: The Groq API key (`GROQ_API_KEY`) is not present in local test execution environments; `app/analysis/ai_summary.py` gracefully returns `(None, None)` under missing credentials.
3. **Live External Network Endpoints**: `live_test_polymarket.py` depends directly on public Polymarket endpoints (`https://data-api.polymarket.com/trades`). Network latency or rate-limiting from public endpoints is external to the codebase logic.

---

## 4. Conclusion

1. **Baseline Execution Health**:
   - Backend pytest suite: **30 passed, 3 failed (90.9% pass rate)**.
   - Listener jest suite: **3 passed, 0 failed (100% pass rate)**.
2. **Defect Concentration**: All 3 test failures originate exclusively from `backend/app/scoring/engine.py` due to hardcoded parameter deviations from the specification:
   - Anti-HFT threshold set to `> 300` instead of `> 100`.
   - Gold Sniper tier max drawdown set to `<= 15.0%` instead of `<= 10.0%`.
   - Flawed OR conditional `(pnl >= 100000 and win_rate >= 70.0)` that bypasses drawdown rules for high-PnL wallets.
3. **False Security from Mock Disconnects**: Passing test numbers are artificially inflated because 5 backend test files test local mock functions and variables rather than actual production code (`test_checkpoint.py`, `test_fee_calculation.py`, `test_idempotency.py`, `test_digest.py`, `test_ai_summary.py`).
4. **Listener Test Deficiency**: The listener test suite covers only basic config/checkpoint IO, leaving the core streaming, parsing, and queueing pipeline completely untested.

---

## 5. Verification Method

To independently reproduce and verify these test execution results:

### Step 1: Backend Pytest Suite
```powershell
# Set working directory
cd c:\Users\arthu\Documents\Baleen-master\backend

# Execute full backend test suite
c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\pytest.exe -v --tb=short tests/

# Execute only the failing scoring tests
c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\pytest.exe -v tests/test_scoring_filters.py
```
**Expected Invalidation Condition**: If `test_scoring_filters.py` passes without modifications to `backend/app/scoring/engine.py`, the test environment has been corrupted or modified.

### Step 2: Listener Jest Suite
```powershell
# Set working directory
cd c:\Users\arthu\Documents\Baleen-master\listener

# Set PATH to include node toolchain
$env:PATH = "C:\Users\arthu\.tools\node;$env:PATH"

# Run listener tests
npm test
```
**Expected Outcome**: 1 test suite passed (`tests/envio.test.ts`), 3 tests passed.
