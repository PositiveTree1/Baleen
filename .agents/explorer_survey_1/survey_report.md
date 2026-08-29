# Baleen — Comprehensive Codebase Survey & Scenario Stress-Testing Architecture Report

**Author:** Survey Explorer 1  
**Target Codebase:** `c:\Users\arthu\Documents\Baleen-master`  
**Date:** 2026-08-29  
**Status:** Completed Investigation  

---

## 1. Executive Summary

Baleen is an automated copy-trading, whale-index, and predictive intelligence engine for Polymarket prediction markets. It continuously ingests on-chain `OrderFilled` events from the Polygon CTF Exchange via Envio HyperSync, dynamically filters and scores elite prediction market traders (Gold Snipers), dynamically sizes mirrored copy-trades based on live portfolio equity, simulates order book execution across the Polymarket CLOB, enforces 2026 official quadratic dynamic taker fees, and continuously revalues open and closed positions via Mark-to-Market (MTM) pricing.

This comprehensive exploration audited all backend modules (`backend/app/`), data models (`models.py`), services (`live_poller.py`, `mark_to_market.py`, `polymarket_fees.py`), sizing and execution algorithms (`fill_simulator.py`, `slippage.py`, `dynamic_sizer.py`), quantitative scoring algorithms (`scanner.py`, `engine.py`, `basket.py`, `dormancy.py`), database schemas and migrations, listener ingestion pipelines (`listener/src/`), and existing test suites (`backend/tests/`).

### Core Findings Summary
1. **Critical Runtime Bug (`NameError: name 'notional' is not defined`):** In `backend/app/services/live_poller.py` line 351, user copy-trade sizing references an undeclared variable `notional`, triggering a fatal runtime `NameError` whenever sandbox users exist in the database.
2. **Order Book Simulator In-Place Mutation & Case Sensitivity:** `simulate_fill` in `fill_simulator.py` mutates the caller's order book dictionary list in place via `levels.sort()`, and fails on lowercase `"buy"`, executing against bids instead of asks.
3. **Zero-Price Contract / Boundary Logic Trap:** In `polymarket_fees.py` lines 117 & 147, `float(price or 0.5)` evaluates `0.0 or 0.5` to `0.5`, causing 0-price resolution contracts to calculate fees based on a 50% midpoint rather than 0%. Furthermore, in `fill_simulator.py` line 49, `shares_taken = remaining_value / price` causes a potential `ZeroDivisionError` if an ask/bid level has price $0.00.
4. **Phantom Free Cash Inflation from Unrealized MTM:** In `live_poller.py` line 243, free cash is computed as `settled_cash - current_open_notional`, but `settled_cash` is calculated from `10000.0 + total_realized_pnl` where `status == "CLOSED"`. In `mark_to_market.py`, `realized_pnl_usd` is actively overwritten on open `FILLED` orders as floating MTM PnL, risking accounting confusion between settled cash and floating unrealized equity.
5. **Ghost SELL Execution on Zero-Position Users:** In `live_poller.py` lines 373–459, when system holds an open position and closes it, any user with 0 open positions still gets a SELL execution log and fee charged.

---

## 2. Codebase & Source File Inventory

| File Path | Primary Class / Functions | Architectural Responsibility |
|---|---|---|
| `backend/app/sizing/fill_simulator.py` | `FillResult`, `simulate_fill(order_value_usd, order_book, side)` | Walks CLOB order book depth (asks for BUY, bids for SELL), calculates VWAP fill price, total filled USD, slippage %, and consumed levels. |
| `backend/app/sizing/slippage.py` | `check_slippage(whale_price, current_price, side)` | Asymmetric directional slippage validator. Allows favorable price discounts/premiums, enforces regime thresholds (1.2% for $\le 0.25$, 2.0% for $\le 0.50$, 3.0% for $> 0.50$). |
| `backend/app/sizing/dynamic_sizer.py` | `SizingResult`, `size_trade(user_balance, risk_profile, n_active, ...)` | Dynamically sizes copy-trades based on active basket size $N$, whale trade risk %, and user risk profile caps (5% conservative, 10% balanced, 20% aggressive). |
| `backend/app/services/polymarket_fees.py` | `classify_market_category`, `calculate_polymarket_fee`, `calculate_fee_aware_ev_gate` | Official 2026 Polymarket dynamic quadratic taker fee engine ($\text{Fee} = \theta \cdot \text{Notional} \cdot (1-p)$) across 6 categories (Crypto, Finance, Tech, Politics, Sports, Geopolitics). |
| `backend/app/services/live_poller.py` | `LiveTradeMirrorService`, `process_trade_fill`, `process_onchain_signal`, `_poll_active_whales` | Main trade mirroring and execution coordinator. Consumes on-chain HyperSync signals and Data API trades, applies guards, executes FIFO lot splitting, updates snapshots. |
| `backend/app/services/mark_to_market.py` | `MarkToMarketService`, `update_valuations_and_consensus`, `get_live_price`, `get_consensus` | Continuous 5s MTM valuation loop. Batch fetches live prices via Gamma API, computes open floating PnL, consensus multipliers, and synchronizes authoritative snapshots. |
| `backend/app/discovery/scanner.py` | `calc_wilson_lower_bound`, `calculate_authentic_wallet_stats`, `evaluate_pending_wallets`, `scan_for_wallets` | 2-Stage autonomous discovery scanner. Pulls leaderboards, trades, positions, activity, computes Wilson 90% LB, profit factor, max drawdown, and HFT/crypto mono-trader filters. |
| `backend/app/discovery/polymarket_client.py` | `PolymarketClient`, `fetch_order_book`, `fetch_live_token_price`, `fetch_batch_live_prices`, `discover_candidates` | Multi-stage API client for Polymarket Data API, Gamma API, and CLOB API. Resolves condition IDs to CLOB token IDs, fetches order books, and manages rate limits. |
| `backend/app/scoring/engine.py` | `ScoringResult`, `score_wallet(wallet_stats)` | Applies deterministic filtration criteria ($PnL \ge \$25k$, trades/day $\le 100$, outlier concentration $\le 35\%$, win rate $\ge 55\%$) and assigns Gold Sniper tier. |
| `backend/app/scoring/basket.py` | `compute_baleen_score`, `get_active_basket`, `refresh_basket` | Multi-horizon consistency scoring engine (PnL 30pts, Win Rate 30pts, 1d/3d/7d rolling consistency 25pts, Drawdown shield 15pts). |
| `backend/app/scoring/dormancy.py` | `check_dormancy(hours_since_last_trade, median_inter_trade_gap)` | Dynamic per-whale relative dormancy detector ($t > 8 \times \text{median gap}$). |
| `backend/app/models.py` | `Wallet`, `WalletSnapshot`, `User`, `ExecutionLog`, `FeeCharge`, `PortfolioSnapshot`, `SystemEvent`, `KeyValue` | Canonical SQLAlchemy async ORM models with SQLite/Postgres GUID polyfills and unique/check constraints. |
| `backend/app/database.py` | `init_db`, `get_db`, `SessionLocal`, `engine` | Database engine manager with PostgreSQL connection pooling, retry logic, and SQLite local fallback. |
| `backend/app/api/signals.py` | `receive_whale_signal`, `WhaleTradeSignalPayload` | Webhook endpoint receiving on-chain `OrderFilled` signals from Envio HyperSync listener. |
| `backend/app/api/execution_logs.py` | `get_execution_logs`, `get_portfolio_summary`, `get_portfolio_snapshots`, `reset_sandbox`, `get_trade_price_chart` | REST API providing execution logs, portfolio metrics, bucketed equity curves, and chart trajectories. |
| `backend/app/api/wallets.py` | `list_wallets`, `get_copied_wallet_stats`, `get_wallet` | REST API providing basket members, whale analytics, AI summaries, and score histories. |
| `backend/app/api/users.py` | `login`, `signup`, `guest_login`, `update_settings`, `reset_user_sandbox`, `reset_global_sandbox` | User authentication, risk profile management, and per-user sandbox isolation. |
| `backend/app/api/admin.py` | `get_admin_status`, `re_evaluate_wallets`, `purge_and_rescan`, `hard_wipe_all_database`, `export_trades_csv`, `analyze_portfolio_ai` | Administrative diagnostics, pipeline triggers, full database wipes, CSV exports, and AI audits. |
| `backend/mcp_server.py` | `baleen-mcp` | Model Context Protocol stdio server exposing 7 administrative control and inspection tools. |
| `backend/app/workers/*` | `discovery_worker`, `scoring_worker`, `analysis_worker` | APScheduler background worker routines for 20-minute discovery and 24-hour rescoring. |
| `listener/src/event-processor.ts`| `parseOrderFilledLog`, `matchesBasketWallet` | Decodes raw EVM log topics and data into `OrderFilledEvent`, identifies maker/taker whale matches. |
| `listener/src/hypersync.ts` | `HyperSyncHttpClient`, `createHyperSyncClient`, `streamEvents`, `buildQuery` | Native & HTTP fallback Envio HyperSync client streaming Polygon CTF Exchange events. |
| `listener/src/checkpoint.ts` | `saveCheckpoint`, `getResumeBlock` | Atomic block height persistence via temporary file rename (`checkpoint.json`). |
| `listener/src/queue.ts` | `enqueueSignal`, `dequeueSignals`, `postSignalToBackend` | Local file-backed FIFO queue (`queue.jsonl`) with memory deduplication. |

---

## 3. Deep-Dive Subsystem & Mathematical Analysis

### 3.1 Order Book Modeling & Book-Walking (`fill_simulator.py`)
- **Mechanism:** `simulate_fill(order_value_usd, order_book, side, latency_ms)` retrieves the asks (for BUY) or bids (for SELL), sorts them ascending (asks) or descending (bids), and consumes levels sequentially until `remaining_value == 0` or depth is exhausted.
- **Mathematical Formula:**
  $$\text{Shares Taken}_i = \begin{cases} \frac{\text{Remaining Value}}{P_i} & \text{if } \text{Remaining Value} \le P_i \cdot S_i \\ S_i & \text{otherwise} \end{cases}$$
  $$\text{Average Price} = \frac{\sum_i (\text{Shares Taken}_i \cdot P_i)}{\sum_i \text{Shares Taken}_i}$$
  $$\text{Slippage \%} = \frac{|\text{Average Price} - \text{Best Price}|}{\text{Best Price}}$$
- **Edge Cases & Failure Modes:**
  1. *Empty Books (`asks: []` or `bids: []`):* Correctly returns `FillResult(avg_price=0.0, total_filled=0.0, slippage_pct=0.0, levels_consumed=0)`.
  2. *Zero Price in Level ($P_i = 0.0$):* If a book contains a zero-price level, `level_value = 0`. If `remaining_value == 0`, `shares_taken = 0 / 0` triggers `ZeroDivisionError`.
  3. *In-Place Mutation Bug:* `levels = order_book.get(...)` returns a reference to the list. `levels.sort(...)` mutates the input dictionary list in place!
  4. *Case Sensitivity Bug:* `if side == "BUY"` checks exact uppercase. If lowercase `"buy"` is passed, it matches `bids` and sorts descending!

### 3.2 Dynamic Sizing & Risk Cap Engine (`dynamic_sizer.py`)
- **Mechanism:** Trades are sized live per event without static capital partitioning:
  $$\text{Base Notional} = \frac{\text{User Balance}}{N_{\text{active}}}$$
  $$\text{Whale Risk \%} = \frac{\text{Whale Trade Value}}{\text{Whale Portfolio Value}}$$
  $$\text{Raw Order Value} = \text{Base Notional} \times \text{Whale Risk \%}$$
  $$\text{Max Allowed} = \text{User Balance} \times \text{Risk Cap}(\text{profile})$$
  $$\text{Order Value} = \min(\text{Raw Order Value}, \text{Max Allowed})$$
- **Risk Caps:** Conservative: 5% (0.05), Balanced: 10% (0.10), Aggressive: 20% (0.20).
- **Minimum Order Floor:** If $\text{Order Value} < \$5.00$, returns `SKIPPED_BELOW_MINIMUM`.
- **Zero-Division Guards:**
  - `if n_active <= 0:` returns `SKIPPED_NO_ACTIVE_WALLETS`.
  - `if whale_portfolio_value <= 0:` returns `SKIPPED_INVALID_PORTFOLIO`.

### 3.3 Directional Slippage Engine (`slippage.py`)
- **Mechanism:** Directionally asymmetric validator:
  - BUY order: $\text{Adverse \%} = \frac{P_{\text{current}} - P_{\text{whale}}}{P_{\text{whale}}}$
  - SELL order: $\text{Adverse \%} = \frac{P_{\text{whale}} - P_{\text{current}}}{P_{\text{whale}}}$
  - If $\text{Adverse \%} \le 0$, returns `EXECUTE_ORDER` (favorable discount on BUY, favorable premium on SELL).
- **Regime-Specific Thresholds:**
  - $P_{\text{whale}} \le 0.25$: Max adverse slippage $1.2\%$ (`0.012`)
  - $P_{\text{whale}} \le 0.50$: Max adverse slippage $2.0\%$ (`0.020`)
  - $P_{\text{whale}} > 0.50$: Max adverse slippage $3.0\%$ (`0.030`)
- **Edge Cases:**
  - `if whale_price <= 0:` returns `EXECUTE_ORDER` directly (bypasses slippage check).

### 3.4 Official 2026 Quadratic Polymarket Fee Schedule (`polymarket_fees.py`)
- **Formula:**
  $$\text{Fee (USD)} = \theta \cdot \text{Notional} \cdot (1 - p)$$
  $$\text{Effective Fee Rate (\%)} = \theta \cdot (1 - p) \times 100\%$$
- **Category $\theta$ Coefficients:**
  - Crypto: $\theta = 0.072$ (Max effective rate $3.60\%$ at $p=0.50$)
  - Economics / Finance: $\theta = 0.060$ (Max effective rate $3.00\%$)
  - Culture, Weather & Tech: $\theta = 0.050$ (Max effective rate $2.50\%$)
  - Politics: $\theta = 0.040$ (Max effective rate $2.00\%$)
  - Sports: $\theta = 0.030$ (Max effective rate $1.50\%$)
  - Geopolitics & Macro Events: $\theta = 0.000$ ($0\%$ Fee-Free)
- **Rounding:** Uses Python `decimal` with Banker's Rounding (`ROUND_HALF_EVEN`) to the nearest cent ($0.01).
- **Fee-Aware Expected Value Gate:**
  $$\text{EV Gate}: \text{Expected Edge} \ge 2.5 \times \text{Fee Rate} = 2.5 \times [\theta \cdot (1 - p)]$$

### 3.5 Trade Execution & FIFO Lot Matching (`live_poller.py`)
- **Cash Limit & Exposure Invariance:**
  $$\text{Current Open Notional} = \sum \text{Notional}_{\text{FILLED, BUY}}$$
  $$\text{Settled Cash} = \$10,000.00 + \sum \text{Realized PnL}_{\text{CLOSED}}$$
  $$\text{Free Cash} = \max(0.0, \text{Settled Cash} - \text{Current Open Notional})$$
  - If $\text{Free Cash} < \$10.00$, BUY trade is blocked (`TRADE_SKIPPED_CASH_LIMIT`).
- **FIFO Partial Sell Lot Splitting:**
  When a SELL order of size $S_{\text{sell}}$ arrives:
  1. Queries all open `FILLED` BUY logs for that market and whale in ascending chronological order (`executed_at.asc()`).
  2. For each open BUY:
     - If $\text{Buy Notional} \le \text{Remaining Sell Notional} + 0.01$:
       - Status set to `CLOSED`.
       - $\text{Realized PnL} = \text{Buy Notional} \times \frac{P_{\text{fill}} - P_{\text{buy}}}{P_{\text{buy}}} - (\text{Buy Fee} + \text{Allocated Sell Fee})$.
       - $\text{Remaining Sell Notional} -= \text{Buy Notional}$.
     - If $\text{Buy Notional} > \text{Remaining Sell Notional}$:
       - Closes portion $S_{\text{closed}} = \text{Remaining Sell Notional}$.
       - Updates existing row to $S_{\text{closed}}$, sets status `CLOSED` and computes partial realized PnL.
       - Creates a new `split_buy` row with remaining notional $S_{\text{rem}} = \text{Buy Notional} - S_{\text{closed}}$, status `FILLED`, and prorated fee.
       - Breaks loop.

---

## 4. State Machine Invariant Matrix

The Baleen execution engine and accounting state machine must satisfy the following strict mathematical invariants across all test scenarios:

| Invariant | Mathematical Expression | Enforced Location | Verification Check |
|---|---|---|---|
| **INV-1: Cash Non-Negativity** | $\text{Settled Cash} \ge 0.0$ and $\text{Free Cash} \ge 0.0$ | `live_poller.py:243-246` | Under no sequence of losses or order splits can settled cash or free cash become negative. |
| **INV-2: Total Capital Conservation** | $\text{Total Equity} = \text{Free Cash} + \text{Open Margin (Notional)} + \text{Unrealized PnL}$ | `mark_to_market.py:213` | Sum of free cash, open position principal, and unrealized floating PnL equals portfolio balance. |
| **INV-3: Lot Conservation in Splitting** | $\text{Notional}_{\text{original}} = \text{Notional}_{\text{closed}} + \text{Notional}_{\text{remaining}}$ | `live_poller.py:290-313` | In partial liquidations, the sum of closed notional and split notional must equal the original buy notional within $0.0001$. |
| **INV-4: Fee Conservation in Splitting** | $\text{Fee}_{\text{original}} = \text{Fee}_{\text{closed}} + \text{Fee}_{\text{remaining}}$ | `live_poller.py:297-313` | Original entry fee must be exactly allocated between closed and remaining lots without fee leaks. |
| **INV-5: High-Water Mark Monotonicity** | $\text{HWM}_{t+1} = \max(\text{HWM}_t, \text{Equity}_{t+1})$ | `models.py`, `mark_to_market.py:245` | User high-water mark is non-decreasing ($\text{HWM}_{t+1} \ge \text{HWM}_t$). |
| **INV-6: Idempotency & Deduplication** | $\text{Count}(\text{TxHash}, \text{LogIndex}, \text{UserId}) \le 1$ | `models.py:136`, `signals.py`, `live_poller.py:523` | Replaying identical on-chain events produces exactly 1 execution log. |
| **INV-7: Zero Orphaned Positions** | $\forall \text{closed lots}, \text{status} \in \{\text{'CLOSED'}, \text{'RESOLVED'}\}$ | `live_poller.py:283-300` | Full liquidations must close all matching open lots; no hanging `FILLED` ghost lots. |
| **INV-8: Fee Bound Invariance** | $0.0 \le \text{Fee Rate} \le \theta \times (1 - 0.001)$ | `polymarket_fees.py:117-124` | Dynamic taker fee cannot exceed the maximum category theoretical fee. |
| **INV-9: Price Bound Invariance** | $0.001 \le P_{\text{effective}} \le 0.999$ (or $0.00/1.00$ at resolution) | `mark_to_market.py:284`, `polymarket_client.py:377` | No negative, infinite, or NaN prices are ever processed. |
| **INV-10: Sizing Risk Cap Invariance** | $\text{Order Value} \le \text{User Balance} \times \text{Cap}(\text{Profile})$ | `dynamic_sizer.py:26` | No trade may exceed the user's risk-profile cap regardless of whale multiplier. |

---

## 5. Discovered Vulnerabilities, Edge Cases & Logic Traps

### Vulnerability 1: Fatal Runtime `NameError` in Multi-User Copy Trading
- **Location:** `backend/app/services/live_poller.py`, Line 351
- **Observation:**
  ```python
  for u in users:
      whale_port_val = float(source_whale.all_time_pnl_usd or 50000.0) if source_whale else 50000.0
      whale_trade_val = float(price * notional if notional > 0 else 500.0)
  ```
- **Logic Chain:** Variable `notional` is not defined anywhere within `process_trade_fill`. When `users` table has $\ge 1$ record, executing this line raises `NameError: name 'notional' is not defined`, crashing the entire trade copying loop for all users.
- **Remediation:** Replace `notional` with `cash_usd` (the actual parameter passed to `process_trade_fill`):
  ```python
  whale_trade_val = float(cash_usd if cash_usd > 0 else (price * 500.0))
  ```

### Vulnerability 2: In-Place Order Book Mutation in `simulate_fill`
- **Location:** `backend/app/sizing/fill_simulator.py`, Lines 20–26
- **Observation:**
  ```python
  levels = order_book.get("asks" if side == "BUY" else "bids", [])
  if side == "BUY":
      levels.sort(key=lambda x: float(x.get("price", 0)))
  ```
- **Logic Chain:** In Python, dictionaries passed by reference return lists that are mutable. Calling `.sort()` mutates the caller's dictionary list in place. If the caller reuses the order book object across multiple evaluations or concurrent threads, the internal order book structure is corrupted.
- **Remediation:** Create a shallow copy before sorting:
  ```python
  levels = list(order_book.get("asks" if side.upper() == "BUY" else "bids", []))
  levels.sort(key=lambda x: float(x.get("price", 0)), reverse=(side.upper() != "BUY"))
  ```

### Vulnerability 3: Case-Sensitivity Hazard in Order Book Matching
- **Location:** `backend/app/sizing/fill_simulator.py`, Line 20
- **Observation:** `order_book.get("asks" if side == "BUY" else "bids", [])`
- **Logic Chain:** If `side` is passed as lowercase `"buy"` or `"Buy"`, `side == "BUY"` evaluates to `False`. The function erroneously retrieves `bids` and executes a buy order against sell bids.
- **Remediation:** Normalize `side.upper()`:
  ```python
  side_norm = (side or "BUY").upper()
  levels = list(order_book.get("asks" if side_norm == "BUY" else "bids", []))
  ```

### Vulnerability 4: Zero-Price Contract Falsy Fallback Bug in Fee Calculation
- **Location:** `backend/app/services/polymarket_fees.py`, Line 117 & Line 147
- **Observation:** `p = max(0.001, min(0.999, float(price or 0.5)))`
- **Logic Chain:** In Python, `0.0` is falsy (`bool(0.0) == False`). When a contract resolves to `0.0` or trades at `0.0`, `float(0.0 or 0.5)` evaluates to `0.5`. This forces a $50\%$ midpoint fee calculation instead of clamping to the boundary $0.001$.
- **Remediation:** Explicitly check for `None`:
  ```python
  raw_p = 0.5 if price is None else float(price)
  p = max(0.001, min(0.999, raw_p))
  ```

### Vulnerability 5: Zero-Division Vulnerability in `simulate_fill` for Zero-Priced Levels
- **Location:** `backend/app/sizing/fill_simulator.py`, Line 49
- **Observation:** `shares_taken = remaining_value / price`
- **Logic Chain:** If an order book level has `price == 0.0` (e.g. illiquid or broken test book) and `remaining_value <= level_value` (which is $0 \le 0$, `True`), `remaining_value / price` results in `0.0 / 0.0` -> `ZeroDivisionError`.
- **Remediation:** Guard price with `if price > 0: shares_taken = remaining_value / price else: shares_taken = size`.

### Vulnerability 6: Ghost SELL Execution on Zero-Position Users
- **Location:** `backend/app/services/live_poller.py`, Lines 373–459
- **Observation:** When processing a SELL signal, the system checks `if not target_open_buys: return` for the system portfolio. But inside `for u in users:`, if `u_open_buys` is empty, the loop continues and creates a `user_log = ExecutionLog(..., side="SELL", status="CLOSED")` and charges user fees.
- **Logic Chain:** Users who never copied the original BUY order get phantom SELL logs with fees deducted from their virtual cash.
- **Remediation:** For users during a SELL signal, only execute and log if `u_open_buys` is non-empty:
  ```python
  if side == "SELL" and not u_open_buys:
      continue
  ```

### Vulnerability 7: Dual PnL Recording Hazard on SELL Logs
- **Location:** `backend/app/services/live_poller.py`, Line 343 & Line 456
- **Observation:** For system trades, `sys_realized_pnl_val = None` is passed to the SELL log, while realized PnL is attached to the closed BUY log. However, for users, if a SELL log also records realized PnL while the closed BUY logs record realized PnL, any naive query summing `realized_pnl_usd` across all records will double-count PnL.
- **Remediation:** Ensure all SELL logs strictly have `realized_pnl_usd = None`, locking realized PnL exclusively to the closed BUY logs.

---

## 6. Comprehensive 200+ Scenario Stress-Testing Matrix

To achieve 100% verification across all failure modes, we define a structured matrix of 200+ programmatic test scenarios across 4 core domains:

```
+-----------------------------------------------------------------------------------------------+
|                       BALEEN 200+ SCENARIO STRESS-TESTING SUITE MATRIX                        |
+-----------------------------------------------------------------------------------------------+
| Domain 1: Order Book & Liquidity Extremes (Scenarios 001 - 060)                               |
| - Empty books, crossed/inverted books, micro-liquidity, whale depth exhaustion                |
| - Extreme price shocks (0.99 -> 0.01, 0.01 -> 0.99), 0-price contracts, 1-price resolutions   |
| - Non-standard order book formats (string types, zero sizes, negative prices, NaN/Inf)        |
+-----------------------------------------------------------------------------------------------+
| Domain 2: Timing, Network & Settlement Dynamics (Scenarios 061 - 110)                         |
| - Out-of-order Envio HyperSync logs, block reorgs (1-15 blocks), duplicate txs/log indices    |
| - Asynchronous latency penalties (0ms to 60,000ms), websocket dropouts & reconnection bursts   |
| - Gamma/CLOB API 429 rate limit backoff, 500 server errors, JSON payload truncations         |
+-----------------------------------------------------------------------------------------------+
| Domain 3: Complex Position & Lifecycle Sequences (Scenarios 111 - 160)                        |
| - Multi-trade FIFO partial liquidations (1 buy -> 3 partial sells, 3 buys -> 1 giant sell)   |
| - Interleaved BUY/SELL signals on identical condition IDs, token inversions (Token 0 vs 1)    |
| - Resolution payouts ($1.00 WIN, $0.00 LOSS, voided market refunds), orphan lot prevention    |
| - High-water mark ratcheting through boom-bust-recovery cycles                                |
+-----------------------------------------------------------------------------------------------+
| Domain 4: Multi-Tenancy & Portfolio Scaling (Scenarios 161 - 210)                            |
| - Concurrent users with diverse risk profiles (Conservative, Balanced, Aggressive)           |
| - Zero-balance & near-zero free cash boundary conditions (< $5.00 min order)                   |
| - Rapid whale bursts (50 trades/sec across 20 markets), basket additions/demotions/dormancy   |
| - 100% validation of all 10 State Machine Invariants                                         |
+-----------------------------------------------------------------------------------------------+
```

### Domain 1: Order Book & Liquidity Extremes (60 Scenarios)
1. **Empty Book Scenarios (001–010):**
   - Scenario 001: Empty asks list on BUY.
   - Scenario 002: Empty bids list on SELL.
   - Scenario 003: Missing asks/bids keys in dictionary.
   - Scenario 004: Non-dict order book input (`None`, `[]`, `""`).
   - Scenario 005: Book with 0 size across all levels.
   - Scenario 006: Book with 0 price across all levels.
   - Scenario 007: Book with negative prices or negative sizes.
   - Scenario 008: Book with NaN or Infinity prices/sizes.
   - Scenario 009: Book containing non-numeric strings (`"abc"`, `None`).
   - Scenario 010: Extremely large asks list (10,000 levels) performance benchmark.

2. **Crossed & Inverted Order Books (011–020):**
   - Scenario 011: Unsorted asks (0.80, 0.20, 0.50) -> verify ascending depth walk.
   - Scenario 012: Unsorted bids (0.20, 0.80, 0.50) -> verify descending depth walk.
   - Scenario 013: Inverted book where best bid > best ask (crossed book arbitrage).
   - Scenario 014: Duplicate price levels in book -> verify aggregation.
   - Scenario 015: In-place mutation test (verify caller book unmodified).
   - Scenario 016: Lowercase `"buy"` / `"sell"` input normalization.
   - Scenario 017: Mixed case `"bUy"` / `"sElL"` input normalization.
   - Scenario 018: Invalid side parameter (`"HOLD"`, `""`, `123`) fallback safety.
   - Scenario 019: Book with zero-spread (best ask == best bid).
   - Scenario 020: Book with 1000x wide spread (ask = 0.99, bid = 0.01).

3. **Micro-Liquidity & Partial Depth (021–035):**
   - Scenario 021: Order value $100, available depth $10 -> partial fill $10, 1 level.
   - Scenario 022: Order value $100, available depth $99.99 -> partial fill $99.99.
   - Scenario 023: Order value $100, exact depth $100.00 across 5 levels.
   - Scenario 024: Order value $0.01 (sub-cent micro order) -> precision check.
   - Scenario 025: Order value $0.00 -> 0 fill, 0 levels consumed.
   - Scenario 026: Negative order value ($-50.00) -> 0 fill, error safety.
   - Scenario 027: Fractional share remaining after depth exhaustion.
   - Scenario 028: High precision price levels ($0.54321) depth walking.
   - Scenario 029: Extreme depth count (consuming 50 levels in single fill).
   - Scenario 030: Single level with 1 share @ $0.99 -> fill $0.99.
   - Scenarios 031–035: Granular micro-liquidity steps ($1, $2, $3, $4, $5 vs $100 orders).

4. **Whale Orders & Pricing Extremes (036–050):**
   - Scenario 036: Massive whale order $1,000,000 against $500 book depth.
   - Scenario 037: Price shock 0.99 -> 0.01 on BUY (favorable discount execution).
   - Scenario 038: Price shock 0.01 -> 0.99 on BUY (adverse slippage cancellation).
   - Scenario 039: Price shock 0.99 -> 0.01 on SELL (adverse slippage cancellation).
   - Scenario 040: Price shock 0.01 -> 0.99 on SELL (favorable premium execution).
   - Scenario 041: Boundary price $0.001 fee and slippage check.
   - Scenario 042: Boundary price $0.999 fee and slippage check.
   - Scenario 043: True zero price $0.00 fee check (falsy handling).
   - Scenario 044: True $1.00 price fee check.
   - Scenario 045: Sizing cap check on $10M whale trade with Conservative user.
   - Scenario 046: Sizing cap check on $10M whale trade with Balanced user.
   - Scenario 047: Sizing cap check on $10M whale trade with Aggressive user.
   - Scenario 048: Sizing calculation when $N_{\text{active}} = 1$.
   - Scenario 049: Sizing calculation when $N_{\text{active}} = 100$.
   - Scenario 050: Sizing calculation when $N_{\text{active}} = 0$ (`SKIPPED_NO_ACTIVE_WALLETS`).

5. **Category Fee Curves & EV Gates (051–060):**
   - Scenario 051: Crypto category ($\theta = 0.072$) across prices $0.05, 0.25, 0.50, 0.75, 0.95$.
   - Scenario 052: Finance category ($\theta = 0.060$) across same prices.
   - Scenario 053: Tech category ($\theta = 0.050$) across same prices.
   - Scenario 054: Politics category ($\theta = 0.040$) across same prices.
   - Scenario 055: Sports category ($\theta = 0.030$) across same prices.
   - Scenario 056: Geopolitics category ($\theta = 0.000$) -> $0 fee.
   - Scenario 057: Maker fee check (`is_maker = True`) -> $0 fee.
   - Scenario 058: Banker's rounding on half-cents ($0.025 \to 0.02$, $0.035 \to 0.04$).
   - Scenario 059: EV Gate passing trade ($\text{Edge} = 0.15 > 2.5 \times \text{Fee}$).
   - Scenario 060: EV Gate failing trade ($\text{Edge} = 0.02 < 2.5 \times \text{Fee}$).

### Domain 2: Timing, Network & Settlement Dynamics (50 Scenarios)
- Scenarios 061–070: Asynchronous latency simulation (0ms, 100ms, 500ms, 1000ms, 5000ms, 15000ms, 60000ms).
- Scenarios 071–080: Out-of-order Envio log ingestion (Block 1005 received before Block 1000).
- Scenarios 081–090: Duplicate signal replays (same tx hash + same log index, same tx + different log index).
- Scenarios 091–100: Polymarket Gamma API 429 rate limit backoff and recovery.
- Scenarios 101–110: Abrupt RPC disconnection and database connection pool recovery.

### Domain 3: Complex Position & Lifecycle Sequences (50 Scenarios)
- Scenarios 111–120: Multi-trade FIFO partial liquidations (1 BUY of $100, 3 SELLs of $30, $30, $40).
- Scenarios 121–130: 3 BUYs ($30 @ 0.40, $40 @ 0.50, $50 @ 0.60) liquidated by 1 giant SELL ($120 @ 0.80).
- Scenarios 131–140: Interleaved BUY/SELL signals on the same market across multiple whales.
- Scenarios 141–150: Binary resolution payouts ($1.00 WIN, $0.00 LOSS, voided 50/50 refund).
- Scenarios 151–160: High-water mark ratcheting through boom-bust-recovery cycles ($10k \to 15k \to 8k \to 12k \to 18k$).

### Domain 4: Multi-Tenancy & Portfolio Scaling (50 Scenarios)
- Scenarios 161–170: Concurrent multi-user copy executions (10 users with mixed risk profiles).
- Scenarios 171–180: User zero-balance and near-zero free cash boundary states ($0, $1, $4.99, $5.00, $5.01).
- Scenarios 181–190: Whale burst stress testing (50 incoming signals/sec).
- Scenarios 191–200: Whale promotion, demotion, dormancy transitions during active positions.
- Scenarios 201–210: Comprehensive validation of all 10 State Machine Invariants across full lifecycle.

---

## 7. Concrete Recommendations & Next Steps

1. **Fix Critical Runtime Bugs in Backend:**
   - Patch line 351 of `backend/app/services/live_poller.py` to replace undefined `notional` with `cash_usd`.
   - Patch `backend/app/sizing/fill_simulator.py` to copy order book levels before sorting and handle case insensitivity.
   - Patch `backend/app/services/polymarket_fees.py` to check `price is None` rather than falsy `price or 0.5`.
   - Patch `backend/app/services/live_poller.py` to prevent ghost SELL logs for users with 0 open positions.
2. **Implement the 200+ Scenario Regression Suite:**
   - Create modular pytest scenario suites in `backend/tests/` structured across the 4 domains:
     - `test_scenario_orderbook_extremes.py` (Scenarios 001–060)
     - `test_scenario_network_settlement.py` (Scenarios 061–110)
     - `test_scenario_fifo_lifecycle.py` (Scenarios 111–160)
     - `test_scenario_multitenancy_invariants.py` (Scenarios 161–210)
3. **Execute Invariant Verification Engine:**
   - Assert all 10 mathematical and cash invariants on every test scenario run.
