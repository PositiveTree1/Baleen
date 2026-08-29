# Baleen Backend & Database Architecture Audit Report

## 1. Observation

A comprehensive inspection of 100% of Python source files (`backend/app/`, `backend/*.py`), database files (`db/schema.sql`, `backend/app/database.py`), and test suites (`backend/tests/`) was conducted.

### 1.1 Backend & Database Inventory

| Path | Purpose / Description | Key Public Functions & Classes | Key Interactions / Dependencies |
| :--- | :--- | :--- | :--- |
| `db/schema.sql` | Canonical PostgreSQL schema reference for production database. | Tables: `wallets`, `wallet_snapshots`, `users`, `live_wallet_links`, `execution_logs`, `fee_charges`. Indexes: `idx_execution_logs_user_time`, `idx_wallets_status_tier`. | Referenced by PostgreSQL migrations; mirrors SQLAlchemy models in `app/models.py`. |
| `backend/app/config.py` | Pydantic v2 application settings, environment loader, and async database URL converter. | Class `Settings(BaseSettings)`; Property `async_database_url`; Global `settings`. | Reads `.env.local`; imported by `database.py`, `polymarket_client.py`, `main.py`. |
| `backend/app/database.py` | Async SQLAlchemy engine, session maker, connection pool management, and idempotent migration logic. | `engine`, `SessionLocal`, `AsyncSessionLocal`, `Base`, `get_db()`, `init_db()`, `NEW_COLS`. | Connects to PostgreSQL via `asyncpg` or fallback SQLite via `aiosqlite`. |
| `backend/app/models.py` | Declarative SQLAlchemy ORM models and cross-database GUID type decorator. | Classes `GUID`, `Wallet`, `WalletSnapshot`, `User`, `LiveWalletLink`, `ExecutionLog`, `FeeCharge`, `KeyValue`, `PortfolioSnapshot`, `SystemEvent`. | Defines database entity schema mapped by all API routers, workers, and background services. |
| `backend/app/main.py` | FastAPI application root, CORS/GZip middleware, startup lifecycle, APScheduler jobs, and core telemetry endpoints. | `app`, `startup_event()`, `shutdown_event()`, `keep_alive_job()`, `_auto_discovery_if_empty()`, `health_check()`, `get_stats()`, `diagnostics()`, `root()`. | Orchestrates API routers, `live_trade_mirror`, `mark_to_market_service`, `disk_backup_service`, and scheduled workers. |
| `backend/app/api/wallets.py` | Wallet leaderboard, copied whale metrics, detail inspection, AI summary on-demand generation, and daily PnL curve endpoint. | `router`, `wallet_to_response()`, `list_wallets()`, `get_copied_wallet_stats()`, `get_wallet()`. | Queries `Wallet`, `ExecutionLog`, `WalletSnapshot`; invokes `generate_summary()`. |
| `backend/app/api/execution_logs.py` | Execution audit trail, portfolio summary, equity curve snapshots, sandbox reset, and trade chart price history. | `router`, `slugify()`, `make_polymarket_url()`, `get_execution_logs()`, `get_portfolio_summary()`, `get_portfolio_snapshots()`, `reset_sandbox()`, `get_trade_price_chart()`. | Queries `ExecutionLog`, `PortfolioSnapshot`, `User`; calls `get_live_price()`, `get_consensus()`, `calculate_polymarket_fee()`. |
| `backend/app/api/users.py` | User authentication (login, signup, guest access), profile risk settings, and per-user/global sandbox reset. | `router`, `SignupRequest`, `LoginRequest`, `UpdateSettingsRequest`, `ResetSandboxRequest`, `hash_password()`, `verify_password()`, `login()`, `signup()`, `guest_login()`, `get_settings()`, `update_settings()`, `reset_user_sandbox()`, `reset_global_sandbox()`. | Manages `User`, `PortfolioSnapshot`, `ExecutionLog`, `SystemEvent`. |
| `backend/app/api/admin.py` | Admin telemetry dashboard, listener heartbeat ingestion, manual discovery trigger, full database wipe, CSV trade export, and AI portfolio analysis. | `router`, `listener_heartbeat()`, `trigger_discovery()`, `get_admin_status()`, `get_discovery_progress()`, `re_evaluate_wallets()`, `purge_and_rescan()`, `hard_wipe_all_database()`, `get_all_wallets()`, `export_trades_csv()`, `analyze_portfolio_ai()`. | Interacts with `discovery_state`, `scan_for_wallets()`, Groq client. |
| `backend/app/api/signals.py` | Webhook endpoint receiving on-chain `OrderFilled` events from Envio HyperSync listener. | `router`, `WhaleTradeSignalPayload`, `receive_whale_signal()`. | Dispatches background task to `live_trade_mirror.process_onchain_signal()`. |
| `backend/app/api/events.py` | System notification audit log endpoint with in-memory fallback. | `router`, `get_events()`. | Queries `SystemEvent` and falls back to `get_recent_events_from_memory()`. |
| `backend/app/api/copilot.py` | Natural language chat endpoint for Baleen AI quantitative copilot. | `router`, `ChatMessage`, `ChatRequest`, `chat_with_copilot()`. | Forwards messages to `execute_copilot_chat()`. |
| `backend/app/discovery/polymarket_client.py` | Asynchronous HTTP client for Polymarket Data, Gamma, and CLOB APIs with retry and token resolution. | `PolymarketClient`, `_to_decimal_token()`, `discover_candidates()`, `fetch_wallet_positions()`, `fetch_wallet_profile()`, `fetch_wallet_profile_pnl()`, `fetch_wallet_trades()`, `fetch_wallet_activity()`, `fetch_order_book()`, `fetch_market_info()`, `get_token_id_for_condition()`, `fetch_live_token_price()`, `fetch_batch_live_prices()`. | Low-level gateway for market scraping, order books, and price discovery. |
| `backend/app/discovery/scanner.py` | 2-stage whale discovery scanner, metrics calculation, and deep trade history auditor. | `discovery_state`, `_persist_discovery_state()`, `load_discovery_state_from_db()`, `calc_wilson_lower_bound()`, `calculate_authentic_wallet_stats()`, `evaluate_pending_wallets()`, `scan_for_wallets()`. | Fetches data via `PolymarketClient`; evaluates via `score_wallet()`, `compute_baleen_score()`, `generate_summary()`. |
| `backend/app/scoring/engine.py` | Pure evaluation engine applying 4 mandatory gating filters and tier qualification. | Class `ScoringResult`, `score_wallet()`. | Evaluates PnL, trades/day, outlier concentration, and win rate. |
| `backend/app/scoring/basket.py` | Baleen multi-horizon score calculation (0-100), active basket membership query, and scheduled basket rescoring. | `compute_baleen_score()`, `get_active_basket()`, `refresh_basket()`. | Computes 1d/3d/7d rolling win rate consistency; rescores wallets in DB. |
| `backend/app/scoring/dormancy.py` | Whale dormancy detection relative to individual trade cadence. | `check_dormancy()`. | Compares elapsed hours since last trade against $8 \times \text{median inter-trade gap}$. |
| `backend/app/services/polymarket_fees.py` | Official 2026 Polymarket dynamic quadratic taker fee calculator, banker's rounding, market classification, and EV net gate. | `classify_market_category()`, `calculate_polymarket_fee()`, `calculate_fee_aware_ev_gate()`. | Implements $\text{Fee} = \Theta \times \text{Notional} \times (1 - p)$ with category theta coefficients. |
| `backend/app/services/mark_to_market.py` | Continuous valuation background loop, multi-whale consensus tracker, and live price in-memory cache. | `MarkToMarketService`, `mark_to_market_service`, `get_live_price()`, `set_live_price()`, `get_consensus()`. | Periodically revalues open positions, updates `realized_pnl_usd` / `PortfolioSnapshot`. |
| `backend/app/services/live_poller.py` | Dual-ingestion live trade mirror polling Polymarket Data API and consuming Envio HyperSync signals. | `LiveTradeMirrorService`, `live_trade_mirror`, `process_trade_fill()`, `process_onchain_signal()`. | Performs live position opening/closing, fee deduction, and slippage guard. |
| `backend/app/services/event_logger.py` | Asynchronous system event logger writing to `SystemEvent` and bounded in-memory ring buffer. | `log_event()`, `get_recent_events_from_memory()`, `clear_recent_events_from_memory()`. | Thread-safe audit event pipeline. |
| `backend/app/services/disk_backup.py` | Periodic automated JSON/CSV disk backup service for all trade execution logs. | `DiskBackupService`, `disk_backup_service`, `export_all_trades_to_disk()`. | Background task executing every 15 minutes to persist data to `data/backups/`. |
| `backend/app/services/copilot.py` | Groq tool-calling reasoning agent with function schemas, database query tools, and fallback context injector. | `COPILOT_TOOLS`, `TOOL_HANDLERS`, `execute_copilot_chat()`, `_clean_response_text()`. | Integrates Groq LLM with live portfolio state and execution history. |
| `backend/app/analysis/ai_summary.py` | Groq API caller for trader style classification and executive summary generation with multi-key rotation and template fallback. | `get_groq_client()`, `generate_summary()`. | Invoked during discovery, rescoring, and on-demand wallet queries. |
| `backend/app/sizing/dynamic_sizer.py` | Proportional position sizer with risk caps and minimum order threshold. | `SizingResult`, `size_trade()`. | Implements $\text{Order} = (\text{Balance} / N_{\text{active}}) \times (\text{Whale Trade} / \text{Whale Portfolio})$. |
| `backend/app/sizing/fill_simulator.py` | Order book walking simulation across asks/bids with price-weighted averaging. | `FillResult`, `simulate_fill()`. | Walks CLOB depth levels to calculate simulated execution price. |
| `backend/app/sizing/slippage.py` | Tiered price slippage validator. | `check_slippage()`. | Checks maximum allowed price divergence based on entry price level. |
| `backend/app/workers/discovery_worker.py` | Scheduled task wrapper for autonomous discovery and initial basket scoring. | `run_discovery()`. | Scheduled by APScheduler every 20 minutes in `main.py`. |
| `backend/app/workers/scoring_worker.py` | Scheduled task wrapper for nightly wallet rescoring and snapshot creation. | `run_rescoring()`. | Scheduled by APScheduler every 24 hours in `main.py`. |
| `backend/app/workers/analysis_worker.py` | Scheduled task wrapper for batch AI summary generation across active wallets. | `run_analysis()`. | Scheduled by APScheduler every 24 hours in `main.py`. |
| `backend/mcp_server.py` | Model Context Protocol (MCP) stdio server exposing Baleen admin tools to external LLM agents. | `TOOLS`, `process_message()`, `handle_baleen_admin_*()`. | Exposes admin health, pipeline, wallets, trades, users, and deployment triggers. |
| `backend/test_apis.py`, `backend/test_integration.py` | Standalone API smoke test scripts verifying live Polymarket, Envio, CLOB, and Groq endpoints. | `test_polymarket_data_api()`, `test_groq_api()`, `test_envio_hypersync()`, etc. | Diagnostic scripts for development and deployment smoke testing. |
| `backend/add_whales.py`, `backend/cleanup_fake.py`, `backend/test_db.py`, `backend/test_real_whale.py`, `backend/test_users.py`, `backend/scratch_update_scanner.py`, `backend/search_titan.py`, `backend/search_wallet_titan.py` | Standalone maintenance, database inspection, and prototype scratch scripts. | Script entry points. | Developer utility scripts at the root of `backend/`. |

---

### 1.2 Identified Code Defects & Logic Hazards

#### Finding B1 (High Severity): NameError `asyncio` in `app/database.py`
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/database.py#L123`
- **Verbatim Code**:
  ```python
  # Lines 1-6
  import logging
  import os
  from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
  from sqlalchemy.orm import declarative_base
  from sqlalchemy import text
  from app.config import settings

  # Line 123 (inside init_db retry loop)
  await asyncio.sleep(3)
  ```
- **Direct Observation**: `import asyncio` is completely omitted from `app/database.py`. If `init_db()` encounters any transient database connection failure during startup (e.g., Supabase/PgBouncer pooler warmup), execution hits line 123 and immediately raises `NameError: name 'asyncio' is not defined`, crashing the startup sequence and preventing retry attempts.

---

#### Finding B2 (High Severity): Slippage Logic Treats Favorable Price Improvement as Adverse Slippage
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/sizing/slippage.py#L8-L14`
- **Verbatim Code**:
  ```python
  diff = abs(current_price - whale_price) / whale_price
  if whale_price <= 0.25 and diff > 0.012:
      return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
  elif whale_price <= 0.50 and diff > 0.02:
      return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
  elif diff > 0.03:
      return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
  return 'EXECUTE_ORDER'
  ```
- **Direct Observation**: `check_slippage` computes `abs(current_price - whale_price)`. For a BUY order, if the market price decreases (e.g., whale entered at $0.20, market drops to $0.18), the buyer gets a 10% price improvement ($0.02 discount). However, because `abs(-0.02) / 0.20 = 0.10 > 0.012`, the order is incorrectly aborted with `'CANCEL_ORDER: SLIPPAGE_EXCEEDED'`. Similarly for SELL orders, favorable upward movement is rejected.

---

#### Finding B3 (High Severity): Production Bypass of Core Sizing, Book-Walking, and Slippage Modules
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/services/live_poller.py#L188-L220`
- **Direct Observation**:
  1. `size_trade()` in `app/sizing/dynamic_sizer.py` is never called in `live_poller.py`. Instead, `live_poller.py` hardcodes an ad-hoc heuristic formula:
     ```python
     sys_notional = round(min(max(10.0, cash_usd * 0.1 * sizing_multiplier), 350.0), 2)
     # and for users:
     u_notional = round(min(max(5.0, cash_usd * 0.05 * sizing_multiplier), 150.0), 2)
     ```
  2. `simulate_fill()` in `app/sizing/fill_simulator.py` (which implements order book depth walking) is never invoked during live signal ingestion or poller execution.
  3. `check_slippage()` in `app/sizing/slippage.py` is completely bypassed. `live_poller.py` instead uses an inline absolute price difference check `(live_p - price) > 0.015`.
  - **Impact**: The paper trading execution diverges significantly from the quantitative sizing and order book walking models tested in unit tests.

---

#### Finding B4 (High Severity): Unreachable Dead Code with Undefined Variables in `app/discovery/scanner.py`
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/discovery/scanner.py#L326-L350`
- **Verbatim Code**:
  ```python
  320:         "today_pnl": round(today_pnl, 2),
  321:         "today_trades_count": today_trades,
  322:         "daily_pnl_history": daily_pnl_history,
  323:         "first_trade_at": None,
  324:         "last_trade_at": datetime.utcnow()
  325:     }
  326:     
  327:     # Drawdown calculation
  328:     max_drawdown = round(max(3.0, min(16.0, 18.0 - (win_rate * 0.12))), 1)
  329:     outlier_pct = 0.14
  330:     alpha_per_trade = round(realized_pnl / total_trades_count, 2) if total_trades_count > 0 else 0.0
  331:     profit_factor = round(max(1.2, 1.0 + (realized_pnl / max(1000.0, volume * 0.35))), 2)
  332: 
  333:     return {
  334:         'all_time_pnl_usd': round(realized_pnl, 2),
  335:         ...
  349:         'trades_count': total_trades_count
  350:     }
  ```
- **Direct Observation**: Lines 327-350 in `calculate_authentic_wallet_stats` are positioned immediately after an unconditional `return` statement at line 325. Furthermore, variables `realized_pnl`, `total_trades_count`, `volume`, `trades_per_hour`, `is_hft`, `is_dormant`, `first_trade_dt`, and `last_trade_dt` referenced in lines 328-350 are undefined in the function scope.

---

#### Finding B5 (Medium Severity): Threshold Inconsistency Between Scanner, Scoring Engine, and Rescoring Worker
- **Location**:
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/scoring/engine.py#L22-L27`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/discovery/scanner.py#L411-L425`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/scoring/basket.py#L75-L105`
- **Direct Observation**:
  - `app/scoring/engine.py`: Requires `pnl >= 50000` (Filter 1) and `trades_per_day <= 300` (Filter 2).
  - `app/discovery/scanner.py`: In `evaluate_pending_wallets` line 411, rejects if `pnl < 25000.0` or `pnl > 22000000.0`, and line 421 rejects if `is_hft` (`avg_trades_per_day > 100.0`).
  - `app/scoring/basket.py`: In `refresh_basket` line 98, calls `score_wallet(stats)` which enforces the $50,000 threshold.
  - **Mechanism**: A candidate wallet with $35,000 PnL and 150 trades/day is marked `active` during discovery (`scanner.py`), but during nightly rescore (`scoring_worker.py` -> `refresh_basket`), `score_wallet` rejects it due to `pnl < 50000`, causing unexpected basket membership churn.

---

#### Finding B6 (Medium Severity): `mcp_server.py` AttributeErrors on `User` Model
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/mcp_server.py#L269-L272`
- **Verbatim Code**:
  ```python
  return [
      {
          "id": str(u.id),
          "email": u.email,
          "role": u.role,
          "sandbox_balance_usd": u.sandbox_balance_usd,
          "high_water_mark_usd": u.sandbox_high_water_mark_usd,
          "live_trading_active": u.live_trading_active,
          "created_at": u.created_at.isoformat() if u.created_at else None
      }
      for u in users
  ]
  ```
- **Direct Observation**: In `app/models.py`, `User` defines `risk_profile`, `live_trading_enabled`, etc., but has NO `role` or `live_trading_active` attributes. Invoking `baleen_admin_users` via MCP raises `AttributeError: 'User' object has no attribute 'role'`.

---

#### Finding B7 (Medium Severity): `user_id` Parameter Ignored in Execution & Snapshot API Queries
- **Location**:
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/api/execution_logs.py#L73`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/api/execution_logs.py#L188`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/api/execution_logs.py#L336`
- **Direct Observation**: In `get_execution_logs()`, `get_portfolio_summary()`, and `get_portfolio_snapshots()`, the FastAPI route declares `user_id: Optional[str] = Query(None, alias="userId")`, but the SQL queries unconditionally execute:
  `stmt.where(ExecutionLog.user_id.is_(None))` and `PortfolioSnapshot.user_id.is_(None)`.
  Any query requesting user-specific execution logs or snapshots receives global sandbox data instead.

---

#### Finding B8 (Medium Severity): Test Suite Disconnect & Mocking Real Logic
- **Location**:
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/test_fee_calculation.py#L1-L8`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/test_idempotency.py#L14-L26`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/test_checkpoint.py#L1-L16`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/tests/test_scoring_filters.py#L9-L45`
- **Direct Observation**:
  1. `test_fee_calculation.py` defines a local inline function `calculate_fee(hwm, current_value)` for 20% performance fees; it does NOT import or test `app/services/polymarket_fees.py` (which contains the 2026 quadratic fee formula).
  2. `test_idempotency.py` tests a dummy in-memory class `IdempotencyChecker` declared in the test file, rather than testing the real deduplication logic in `live_poller.py` or database constraints.
  3. `test_checkpoint.py` tests `assert saved_state == 100`.
  4. In `test_scoring_filters.py`, `test_hft_screen_rejects_over_100_trades_per_day` expects rejection at 101 trades/day, but `engine.py` allows up to 300 trades/day. Similarly, `test_gold_tier_requires_both_winrate_and_drawdown` passes a default `pnl=100000.0`, triggering the alternate gold tier branch `pnl >= 100000 and win_rate >= 70.0`, causing test assertion failure.

---

#### Finding B9 (Paper Trading Realism / Math Edge): Synthetic Timeline Synthesis in `wallets.py`
- **Location**: `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/api/wallets.py#L317-L393`
- **Direct Observation**: When actual trade history is sparse (<5 trades) and `cached_daily_pnl` is empty, `get_wallet()` generates a 45-day continuous daily PnL timeline by seeding MD5 hashes of the wallet address (`addr_seed = int(hashlib.md5(clean_addr.encode()).hexdigest()[:8], 16)`) and scaling the pseudo-random daily steps so that their sum matches `wallet.all_time_pnl_usd`. While deterministic for UI rendering, this presents synthetic equity trajectories as historical performance.

---

#### Finding B10 (Paper Trading Realism / Math Edge): Unrealized Gains Treated as Available Cash
- **Location**:
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/services/mark_to_market.py#L174-L213`
  - `file:///c:/Users/arthu/Documents/Baleen-master/backend/app/services/live_poller.py#L232-L253`
- **Direct Observation**:
  - In `mark_to_market.py`, `PortfolioSnapshot.balance` is computed as $\text{Starting Balance (\$10,000)} + \sum(\text{Realized \& Unrealized MTM PnL})$.
  - In `live_poller.py`, `free_cash` is calculated as $\text{total\_portfolio\_equity} - \text{current\_open\_notional}$.
  - Because `total_portfolio_equity` incorporates unrealized mark-to-market appreciation of open prediction contracts, paper trading immediately allows buying new positions using unrealized paper gains before positions are closed and settled.

---

## 2. Logic Chain

1. **Startup Failure Chain (Finding B1)**:
   - `app/database.py` defines `init_db()` which contains a 5-attempt retry loop for connecting to PostgreSQL.
   - Line 123 calls `await asyncio.sleep(3)`.
   - `asyncio` is not imported in `app/database.py`.
   - Therefore, any database connection exception during startup crashes immediately with `NameError` instead of completing retry attempts.

2. **Slippage Cancellation Chain (Finding B2)**:
   - In `app/sizing/slippage.py`, `diff = abs(current_price - whale_price) / whale_price`.
   - When `current_price < whale_price` on a BUY order, the user receives a discount (favorable price improvement).
   - Because `abs()` is applied, `diff` is positive and exceeds the threshold (1.2% / 2% / 3%), returning `CANCEL_ORDER: SLIPPAGE_EXCEEDED`.
   - Therefore, the system systematically cancels orders when favorable entry prices occur.

3. **Paper Trading Divergence Chain (Finding B3)**:
   - The spec defines dynamic Kelly-style position sizing (`dynamic_sizer.py`), order book depth walking (`fill_simulator.py`), and slippage checking (`slippage.py`).
   - In `live_poller.py`, `process_trade_fill()` bypasses all three modules, instead using hardcoded bounds `[10.0, 350.0]` and filling instantly at `effective_fill_price = live_p`.
   - Therefore, live paper trading outcomes do not reflect the book-walking slippage or dynamic sizing algorithms tested in unit tests.

4. **Scoring Inconsistency Chain (Finding B5)**:
   - Candidate discovery in `scanner.py` accepts wallets with $\ge \$25,000$ PnL and $\le 100$ trades/day.
   - Nightly scoring worker in `scoring_worker.py` runs `refresh_basket()` which calls `score_wallet()` in `engine.py`.
   - `engine.py` rejects wallets with $<\$50,000$ PnL and allows up to 300 trades/day.
   - Therefore, wallets discovered in the $\$25\text{k}-\$50\text{k}$ range are admitted to the basket on day 1, but silently demoted to `rejected` during the first nightly rescore.

5. **MCP API Crash Chain (Finding B6)**:
   - `mcp_server.py` queries `User` model and accesses `u.role` and `u.live_trading_active`.
   - `app/models.py` defines `User` without those two fields (`role` does not exist; `live_trading_enabled` is the boolean field).
   - When an LLM client or admin tool calls `baleen_admin_users`, Python raises `AttributeError`.

---

## 3. Caveats

1. **External Network Calls**: Live API tests against Polymarket Data API, Gamma API, and CLOB API depend on external rate limits (HTTP 429) and network reachability.
2. **Environment Variable Configurations**: Supabase PostgreSQL connection strings in production Render/Supabase environments use asyncpg driver options (`statement_cache_size=0`) to accommodate PgBouncer transaction pooling.
3. **Database Dialect Discrepancies**: While SQLite is supported for local development via `aiosqlite` and `GUID` TypeDecorator, PostgreSQL in production uses native `gen_random_uuid()` and `UUID` columns.

---

## 4. Conclusion

The Baleen backend demonstrates a well-architected asynchronous structure (FastAPI + Asyncpg/SQLAlchemy + Envio HyperSync webhook + continuous MTM background services), but contains several critical and high-severity logic issues that affect paper trading realism, startup resilience, and scoring consistency:

1. **Immediate Runtime Fixes Needed**:
   - Add `import asyncio` to `app/database.py`.
   - Fix `User` model attribute references in `mcp_server.py`.
   - Delete dead unreachable code in `app/discovery/scanner.py` (lines 326-350).
2. **Paper Trading Realism Adjustments**:
   - Fix directional slippage in `app/sizing/slippage.py` (distinguish BUY adverse slippage from favorable discounts).
   - Integrate `simulate_fill()` and `size_trade()` directly into `live_poller.py` instead of hardcoded sizing bounds.
   - Separate settled cash balance accounting from mark-to-market unrealized equity.
3. **Scoring & Threshold Harmonization**:
   - Standardize PnL and HFT thresholds between `engine.py`, `scanner.py`, and `basket.py`.
   - Update unit test assertions in `test_scoring_filters.py` to match unified engine thresholds.

---

## 5. Verification Method

To independently verify all findings and test suite behavior:

1. **Verify Missing Import in `database.py`**:
   - Inspect `backend/app/database.py` lines 1-6 and line 123.
   - Confirm `asyncio` is referenced on line 123 without a top-level import.

2. **Verify Slippage Logic in `slippage.py`**:
   - Inspect `backend/app/sizing/slippage.py` line 8.
   - Run a test case: `check_slippage(whale_price=0.20, current_price=0.18)` -> observed return `'CANCEL_ORDER: SLIPPAGE_EXCEEDED'`.

3. **Verify Dead Code in `scanner.py`**:
   - Inspect `backend/app/discovery/scanner.py` lines 324-350.
   - Confirm lines 327-350 follow line 325 `return {...}` and reference undefined variables.

4. **Verify MCP Server Attribute Errors**:
   - Inspect `backend/mcp_server.py` lines 269-272 against `backend/app/models.py` lines 79-94 (`User` class).
