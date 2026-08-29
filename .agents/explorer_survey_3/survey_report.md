# Baleen Architecture & State Machine Comprehensive Survey Report
**Project:** Baleen Comprehensive Scenario Modeling and Stress-Testing Project  
**Author:** Survey Explorer 3  
**Date:** 2026-08-29  
**Target Repository:** `c:\Users\arthu\Documents\Baleen-master`  
**Status:** Complete  

---

## Table of Contents
1. [Executive Architecture & Subsystem Map](#1-executive-architecture--subsystem-map)
2. [Source Files, Classes & Function Registry](#2-source-files-classes--function-registry)
3. [Portfolio State Machine & Lifecycle Transitions](#3-portfolio-state-machine--lifecycle-transitions)
4. [Cash, Margin & Equity Invariance Specifications](#4-cash-margin--equity-invariance-specifications)
5. [High-Water Mark (HWM) & Performance Fee Invariance](#5-high-water-mark-hwm--performance-fee-invariance)
6. [Polymarket Dynamic Quadratic Fee Engine (2026 Spec)](#6-polymarket-dynamic-quadratic-fee-engine-2026-spec)
7. [Multi-Trade FIFO Partial Liquidations & Split/Merge Token Lots](#7-multi-trade-fifo-partial-liquidations--splitmerge-token-lots)
8. [Dynamic Sizing & Multi-Tenancy Risk Scaling](#8-dynamic-sizing--multi-tenancy-risk-scaling)
9. [Forensic Vulnerability Catalog & Edge-Case Mechanics](#9-forensic-vulnerability-catalog--edge-case-mechanics)
10. [Recommended 200+ Scenario Stress-Testing Matrix](#10-recommended-200-scenario-stress-testing-matrix)

---

## 1. Executive Architecture & Subsystem Map

Baleen is an automated copy-trading and prediction market intelligence platform for Polymarket. It indexes on-chain positions from elite prediction market whales, constructs a dynamic basket, and mirrors orders into sandbox and live trading accounts with dynamic sizing, slippage guards, and mark-to-market accounting.

```
+----------------------------------------------------------------------------------------------------+
|                                    BALEEN SYSTEM ARCHITECTURE                                      |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [INGESTION LISTENER] (Node.js/TS)              [DISCOVERY & SCORING ENGINE] (Python)              |
|  - Envio HyperSync Polygon CTF Stream           - Gamma Leaderboards & Data API Scraper            |
|  - Topic: OrderFilled (0xd0a39...)              - 4-Tier Filters (PnL >= $25k, WR >= 55%)          |
|  - Local Queue (queue.jsonl) & Deduplication    - Wilson Lower Bound & Baleen Score (0-100)        |
|  - Checkpoint (checkpoint.json)                 - Whale Profiling & Groq LLaMA AI Summarizer       |
|                            \                                  /                                    |
|                             \                                /                                     |
|                              v                              v                                      |
|  +----------------------------------------------------------------------------------------------+  |
|  |                          FASTAPI CORE SERVICES & EXECUTION ENGINE                            |  |
|  |                                                                                              |  |
|  |  [Dual Ingestion Router] (/api/signals)   <--- Real-time on-chain events & Poller            |  |
|  |  [Live Trade Mirror] (live_poller.py)     <--- Deduplication, Sizing Multipliers             |  |
|  |  [Fee Engine] (polymarket_fees.py)        <--- 6-Category 2026 Quadratic Curves              |  |
|  |  [Sizing & Risk] (dynamic_sizer.py)       <--- Denominator-scaling (N_active), Risk Caps     |  |
|  |  [Fill Simulator] (fill_simulator.py)     <--- Depth-walking, Slippage validation            |  |
|  |  [FIFO Matching & Lot Splitter]           <--- Pro-rated entry/exit fee lot accounting       |  |
|  |  [Mark-to-Market Service] (mark_to_market)<--- Live Gamma valuation loop (5s), Consensus    |  |
|  +----------------------------------------------------------------------------------------------+  |
|                                                |                                                   |
|                                                v                                                   |
|  [PERSISTENCE LAYER] (SQLAlchemy Async Engine + PostgreSQL / SQLite WAL Fallback)                  |
|  - wallets, wallet_snapshots, users, execution_logs, fee_charges, portfolio_snapshots, events     |
|                                                |                                                   |
|                                                v                                                   |
|  [PRESENTATION & CLIENT APIS] (/api/executions, /api/wallets, /api/users, /api/admin, /api/events) |
+----------------------------------------------------------------------------------------------------+
```

The system comprises four primary operational subsystems:
1. **Ingestion Listener (`listener/src/`)**: Envio HyperSync client streaming Polygon `OrderFilled` events from CTF Exchange contracts, filtering by active whale basket, local queueing, and webhook forwarding to backend `/api/signals`.
2. **Backend Services & Execution Engine (`backend/app/services/`, `backend/app/sizing/`, `backend/app/scoring/`, `backend/app/discovery/`)**: FastAPI server, SQLAlchemy async engine (PostgreSQL/SQLite), APScheduler background workers (Discovery 20m, Rescoring 24h, Analysis 24h), Live Trade Mirror engine (`live_poller.py`), Mark-to-Market revaluation loop (`mark_to_market.py`), and Groq LLaMA-3.1 AI Copilot (`copilot.py`).
3. **Database Layer (`backend/app/database.py`, `backend/app/models.py`)**: Async SQLAlchemy pool management, table schemas (`wallets`, `wallet_snapshots`, `users`, `execution_logs`, `fee_charges`, `portfolio_snapshots`, `system_events`, `kv_store`), idempotency constraints, and automatic migration patching.
4. **Presentation & API Layer (`backend/app/api/`)**: REST endpoints delivering portfolio summaries, bucketed equity snapshots, wallet analytics, execution audit logs, trade price trajectories, and administrative controls.

---

## 2. Source Files, Classes & Function Registry

The following table documents every core source module across the Baleen codebase:

| File Path | Primary Classes / Functions | Primary Responsibility | Key Invariants / Interfaces |
|---|---|---|---|
| `backend/app/models.py` | `Wallet`, `WalletSnapshot`, `User`, `LiveWalletLink`, `ExecutionLog`, `FeeCharge`, `PortfolioSnapshot`, `SystemEvent`, `KeyValue`, `GUID` | Canonical ORM schema definitions and database relational constraints | `UniqueConstraint('onchain_tx_hash', 'onchain_log_index', 'user_id')`, `CheckConstraint(side IN ('BUY', 'SELL'))` |
| `backend/app/database.py` | `init_db()`, `get_db()`, `SessionLocal`, `engine` | Async SQLAlchemy engine configuration, connection retry loop, and SQLite WAL fallback | 5-attempt retry loop with backoff, statement cache zeroing for Supabase PgBouncer |
| `backend/app/config.py` | `Settings`, `settings` | Pydantic configuration loader for environment variables, API keys, and URLs | Dynamic conversion of PostgreSQL URLs to `postgresql+asyncpg://` |
| `backend/app/services/live_poller.py` | `LiveTradeMirrorService`, `process_trade_fill()`, `process_onchain_signal()`, `_poll_active_whales()` | Core copy-trading execution engine, dual ingestion handler, cash guards, and FIFO lot matching | Cash ceiling guard (`free_cash >= 10.0`), sniper multiplier (1.35x), consensus multiplier (1.5x), FIFO partial lot splitting |
| `backend/app/services/mark_to_market.py` | `MarkToMarketService`, `get_live_price()`, `set_live_price()`, `get_consensus()`, `_ensure_snapshot_continuity()` | Continuous valuation loop (5s), batch price caching, PnL updates, snapshot writing, and gap-filling watchdog | 25s snapshot throttling, cold-cache protection guard, consensus aggregation across 100 recent trades |
| `backend/app/services/polymarket_fees.py` | `classify_market_category()`, `calculate_polymarket_fee()`, `calculate_fee_aware_ev_gate()` | 2026 Polymarket dynamic quadratic taker fee computation and EV threshold validation | Banker's Rounding (`ROUND_HALF_EVEN`) to $0.01, 6 categories ($\Theta \in [0.00, 0.072]$), EV gate ($2.5 \times \text{Fee Rate}$) |
| `backend/app/sizing/dynamic_sizer.py` | `size_trade()`, `SizingResult` | Live trade sizing based on active basket size, whale risk fraction, and user risk caps | Risk caps (Conservative 5%, Balanced 10%, Aggressive 20%), `$5.00` min order threshold |
| `backend/app/sizing/fill_simulator.py` | `simulate_fill()`, `FillResult` | Order book depth-walking simulator computing weighted average execution fill price | Order book depth consumption, slippage computation, levels consumed tracking |
| `backend/app/sizing/slippage.py` | `check_slippage()` | Directional slippage guard allowing favorable price improvements while blocking adverse moves | Favorable discounts/premiums executed; adverse moves blocked by price tier ($0.25: 1.2\%, 0.50: 2.0\%, >0.50: 3.0\%$) |
| `backend/app/scoring/engine.py` | `score_wallet()`, `ScoringResult` | 4-stage quantitative screening engine evaluating candidate whale track records | PnL $\ge \$25k$, trades/day $\le 100$, outlier $\le 35\%$, win rate $\ge 55\%$, Gold Sniper tier (WR $\ge 85\%$ & DD $\le 10\%$) |
| `backend/app/scoring/basket.py` | `compute_baleen_score()`, `get_active_basket()`, `refresh_basket()` | Multi-horizon consistency evaluation (1d, 3d, 7d rolling wins) and 0-100 score computation | PnL score (30pts), Win rate score (30pts), Consistency (25pts), Drawdown shield (15pts) |
| `backend/app/scoring/dormancy.py` | `check_dormancy()` | Per-whale relative dormancy evaluator | Dormant if `hours_since_last_trade > 8 * median_inter_trade_gap_hours` |
| `backend/app/discovery/scanner.py` | `scan_for_wallets()`, `evaluate_pending_wallets()`, `calculate_authentic_wallet_stats()`, `calc_wilson_lower_bound()` | 2-stage discovery pipeline, multi-period scraping, Wilson lower bound, and drawdown calculations | 90% Wilson confidence lower bound ($z=1.645$), Peak-to-Trough equity drawdown calculation |
| `backend/app/discovery/polymarket_client.py` | `PolymarketClient`, `_to_decimal_token()` | Direct HTTP client interfacing with Polymarket Data, Gamma, and CLOB APIs | Exponential backoff retry, rate-limit header parsing, token ID hexadecimal normalization |
| `backend/app/api/signals.py` | `receive_whale_signal()`, `WhaleTradeSignalPayload` | REST ingestion endpoint for Envio HyperSync signals | Background task dispatch for sub-millisecond response acknowledgement |
| `backend/app/api/execution_logs.py` | `get_execution_logs()`, `get_portfolio_summary()`, `get_portfolio_snapshots()`, `reset_sandbox()`, `get_trade_price_chart()` | Query filtering, historical bucketed snapshots, CLOB price trajectory, and sandbox reset | Timeframe filtering (`1h`, `6h`, `1d`, `1w`, `1m`, `ytd`, `all`), genesis baseline prepending, snapshot bucketing |
| `backend/app/api/wallets.py` | `list_wallets()`, `get_copied_wallet_stats()`, `get_wallet()` | Leaderboard querying, copy performance attribution, and profile retrieval | Dynamic fallback AI summary generation, snapshot sparkline history |
| `backend/app/api/users.py` | `login()`, `signup()`, `guest_login()`, `get_settings()`, `update_settings()`, `reset_user_sandbox()`, `reset_global_sandbox()` | User lifecycle, authentication, settings management, and user sandbox reset | SHA-256 password hashing, user-specific execution log deletion |
| `backend/app/api/admin.py` | `listener_heartbeat()`, `get_admin_status()`, `re_evaluate_wallets()`, `purge_and_rescan()`, `hard_wipe_all_database()`, `export_trades_csv()`, `analyze_portfolio_ai()` | Administrative inspection, heartbeat monitor, hard wipe, CSV export, and AI portfolio audit | RFC-compliant CSV trade log stream, Groq LLM portfolio performance synthesis |
| `backend/app/api/events.py` | `get_events()` | Real-time system notifications and audit trail endpoint | In-memory circular buffer fallback if database event logs are unavailable |
| `backend/app/workers/*.py` | `discovery_worker.py`, `scoring_worker.py`, `analysis_worker.py` | APScheduler recurring background tasks | Autonomous discovery (20m), rescoring (24h), and analysis (24h) |
| `listener/src/hypersync.ts` | `HyperSyncHttpClient`, `createHyperSyncClient()`, `buildQuery()`, `streamEvents()` | Polygon CTF Exchange event streaming client with HTTP fallback | Rate limit protection ($1.6\text{s}$ catch-up, $4.5\text{s}$ chain tip), block height progression |
| `listener/src/event-processor.ts` | `parseOrderFilledLog()`, `matchesBasketWallet()` | ABI decoding and whale basket matching | Ethers AbiCoder `OrderFilled` unpacking, maker/taker outcome direction derivation |
| `listener/src/queue.ts` | `enqueueSignal()`, `dequeueSignals()`, `postSignalToBackend()` | Local JSONL signal buffer and deduplication queue | 50,000-key circular memory set for duplicate suppression |
| `listener/src/checkpoint.ts` | `saveCheckpoint()`, `getResumeBlock()` | Block height persistence in `checkpoint.json` | Atomic filesystem write, safe resume on restart |

---

## 3. Portfolio State Machine & Lifecycle Transitions

### 3.1 Trade Processing State Machine
The core execution engine executes a strict, sequential pipeline for every detected whale transaction:

```
[Whale Trade Detected] (Envio HyperSync on-chain OR Data API poller)
          |
          v
[Deduplication Check] ---> (Seen in last 50k keys? -> DROP)
          |
          v
[Basket & Status Gate]
  - If BUY: Source whale MUST be status='active', dormant=False, is_hft=False.
  - If SELL: Position Guard check. Whale must match an existing FILLED BUY in portfolio.
          |
          v
[Price & Category Classification]
  - Price Boundary Guard: 0.04 <= price <= 0.96 (Filters extreme illiquid artifacts).
  - Category Determination: Crypto (0.072), Econ (0.060), Tech (0.050), Politics (0.040), Sports (0.030), Geopolitics (0.000).
  - Category Win Rate Gate: If Sports/Esports, whale win rate must exceed 65.0%.
          |
          v
[Directional Slippage Check]
  - Pull live CLOB/Gamma price.
  - If BUY: Check adverse upward movement. Favorable discounts allowed.
  - If SELL: Check adverse downward movement. Favorable premiums allowed.
  - If adverse shift > tier tolerance (1.2% / 2.0% / 3.0%) -> ABORT (SLIPPAGE_EXCEEDED).
          |
          v
[Fee-Aware EV Gate]
  - Expected Edge = Whale Win Rate Probability - Fill Price.
  - Gate: Expected Edge >= 2.5 * [Theta * (1 - p)]. If failed -> ABORT (EV_GATE_BLOCKED).
          |
          v
[Dynamic Sizing & Risk Caps]
  - Multipliers applied: Sniper Multiplier (1.35x) + Multi-Whale Consensus (1.5x).
  - Proportional sizing: Base = Balance / N_active.
  - Risk Caps enforced: Conservative (5%), Balanced (10%), Aggressive (20%).
  - Minimum order check: Notional >= $5.00.
          |
          v
[Strict Cash Ceiling Guard (BUYs)]
  - Settled Cash = Starting Balance ($10k) + Cumulative Realized PnL.
  - Open Margin = Sum of notional_usd for all FILLED BUYs.
  - Free Cash = max(0.0, Settled Cash - Open Margin).
  - If Free Cash < $10.00 -> ABORT (CASH_LIMIT_REACHED). Sizing clamped to Free Cash.
          |
          v
[FIFO Position Matching & Execution]
  - If BUY: Record ExecutionLog with status='FILLED', realized_pnl=None.
  - If SELL: Query earliest FILLED BUYs (FIFO order).
      * Full close: Mark BUY as 'CLOSED', compute net PnL (Gross - Entry Fee - Exit Fee).
      * Partial close: Split BUY record into 'CLOSED' portion and remaining 'FILLED' split-lot.
      * Record SELL ExecutionLog with status='CLOSED', realized_pnl=None (to prevent double count).
          |
          v
[Mark-to-Market & Balance Synchronization]
  - Recompute total portfolio PnL across platform logs.
  - Update user balances and ratcheting High-Water Mark.
  - Write throttled PortfolioSnapshot record.
```

### 3.2 State Enums and Entity Lifecycles

1. **Wallet Lifecycle:**
   - `pending`: Newly scraped candidate awaiting deep trade audit.
   - `active`: Passed all 4 quantitative filters and Wilson lower bound; currently in copy basket.
   - `rejected`: Failed one or more filters (e.g. `PNL_BELOW_THRESHOLD`, `HFT_EXCEEDED`, `OUTLIER_CONCENTRATION_TOO_HIGH`, `WIN_RATE_TOO_LOW`).
   - `dormant` (boolean flag): Active whale whose inactivity exceeds $8 \times \text{median inter-trade gap}$. Excluded from active denominator $N_{\text{active}}$ but retains membership.
2. **ExecutionLog Lifecycle:**
   - `FILLED`: Open active position currently subjected to live mark-to-market revaluations.
   - `CLOSED`: Position settled and realized via a subsequent whale SELL order.
   - `RESOLVED`: Binary market reached resolution ($1.00 payout for winning outcome, $0.00 for losing outcome).
   - `SKIPPED_BELOW_MINIMUM`: Sized order value fell below $\$5.00$ minimum threshold.
   - `SLIPPAGE_BLOCKED`: Live price drifted adversely beyond allowable regime tolerance.
3. **User Balance Lifecycle:**
   - `sandbox_starting_balance_usd`: Initial virtual balance selected at registration (default $\$10,000.00$).
   - `sandbox_balance_usd`: Authoritative equity balance ($\text{Starting Balance} + \text{Total Realized PnL} + \text{Floating MTM}$).
   - `sandbox_high_water_mark_usd`: Monotonically non-decreasing peak equity watermark.

---

## 4. Cash, Margin & Equity Invariance Specifications

To guarantee mathematical realism and eliminate accounting leaks, the Baleen engine operates under four core accounting invariants:

### 4.1 Invariant Equations

1. **Non-Negative Cash Invariant:**
   $$\text{Free Cash} \ge 0.00 \quad \text{and} \quad \text{Settled Cash} \ge 0.00$$
   Under no market conditions or liquidation sequences may an account's cash balance drop below zero.

2. **Settled Cash vs Open Margin Invariance:**
   $$\text{Settled Cash} = \text{Starting Balance} + \sum_{i \in \text{CLOSED}} \text{Realized PnL}_i$$
   $$\text{Open Margin} = \sum_{j \in \text{FILLED}} \text{Notional USD}_j$$
   $$\text{Free Cash} = \max\left(0.00, \; \text{Settled Cash} - \text{Open Margin}\right)$$

3. **MTM Phantom Cash Prohibition:**
   Unrealized mark-to-market floating gains must **never** be added to `Settled Cash` or used to expand `Free Cash`. Only cash unlocked by an actual closing transaction (`SELL` or binary `RESOLVED`) can fund subsequent `BUY` orders.

4. **Mark-to-Market Total Equity Invariance:**
   $$\text{Total Equity} = \text{Settled Cash} - \text{Open Margin} + \sum_{j \in \text{FILLED}} \text{Current MTM Value}_j$$
   $$\text{Total Equity} \equiv \text{Free Cash} + \sum_{j \in \text{FILLED}} \text{Current MTM Value}_j$$

---

## 5. High-Water Mark (HWM) & Performance Fee Invariance

### 5.1 High-Water Mark Non-Decreasing Logic
The High-Water Mark represents the historical peak valuation of an account. It is strictly non-decreasing:
$$\text{HWM}_{t} = \max\left(\text{HWM}_{t-1}, \; \text{Total Equity}_t\right)$$

### 5.2 Performance Fee Accrual Engine (Phase 2 Spec)
Baleen employs a "Pay-Only-On-New-Profit" performance fee model. Fees are assessed exclusively on net profits exceeding the previous historical peak:

$$\text{Profit Above HWM} = \max\left(0.00, \; \text{Ending Equity} - \text{Starting HWM}\right)$$
$$\text{Fee Amount} = \text{Profit Above HWM} \times \text{Fee Pct} \quad (\text{e.g. } 15.0\%)$$
$$\text{New HWM} = \text{Ending Equity} - \text{Fee Amount}$$

### 5.3 Invariant Rules
- **Drawdown Recovery Invariance:** If an account drops from $\$10,000$ to $\$8,000$ and recovers to $\$9,500$, the accrued fee is strictly $\$0.00$. Recovering past drawdowns never incurs fees.
- **Ratchet Invariance:** After charging a performance fee, the new HWM ratchets to the post-fee equity level and can never decrease, even if market prices subsequently decline.

---

## 6. Polymarket Dynamic Quadratic Fee Engine (2026 Spec)

### 6.1 Mathematical Formulation
In prediction markets, contract risk and liquidity requirements scale quadratically as probabilities approach certainty. Polymarket's 2026 fee structure assesses dynamic taker fees according to:

$$\text{Fee (USD)} = \Theta \times C \times p \times (1 - p) = \Theta \times \text{Notional} \times (1 - p)$$

Where:
- $C = \text{Number of Outcome Shares} = \frac{\text{Notional}}{p}$
- $p = \text{Fill Price} \in [0.001, 0.999]$
- $\text{Notional} = C \times p$
- $\Theta = \text{Category-specific fee coefficient}$
- $\text{Effective Fee Rate (\%)} = \Theta \times (1 - p) \times 100\%$

### 6.2 The 6 Asset Classes & Theta Coefficients

| Category Name | Theta ($\Theta$) | Max Effective Rate ($p=0.50$) | Extreme Low Price Rate ($p=0.01$) | Key Identifiers / Keywords |
|---|---|---|---|---|
| **Crypto** | `0.072` | **3.60%** | **7.13%** | `bitcoin`, `btc`, `eth`, `solana`, `sol`, `crypto`, `up or down`, `15m` |
| **Economics / Finance** | `0.060` | **3.00%** | **5.94%** | `fed `, `interest rate`, `cpi`, `inflation`, `gdp`, `recession`, `s&p` |
| **Culture, Weather & Tech** | `0.050` | **2.50%** | **4.95%** | `apple`, `google`, `nvidia`, `openai`, `weather`, `temperature`, `movie` |
| **Politics** | `0.040` | **2.00%** | **3.96%** | `election`, `president`, `senate`, `house`, `trump`, `biden`, `vote` |
| **Sports** | `0.030` | **1.50%** | **2.97%** | `vs`, `atp`, `championship`, `fc`, `nba`, `nfl`, `tennis`, `premier league` |
| **Geopolitics & World Events** | `0.000` | **0.00% (Fee-Free)** | **0.00%** | `war`, `ceasefire`, `treaty`, `sanctions`, `nato`, `un `, `ukraine`, `gaza` |

### 6.3 Precision & Maker Rules
- **Rounding:** All calculated fees must use **Banker's Rounding** (`ROUND_HALF_EVEN`) quantized to the nearest cent ($\$0.01$).
- **Maker Exemption:** Maker limit orders providing liquidity have $\text{Fee} = \$0.00$ and are eligible for maker rebates.

---

## 7. Multi-Trade FIFO Partial Liquidations & Split/Merge Token Lots

### 7.1 FIFO Matching Mechanics
When a basket whale executes a `SELL` order, Baleen locates and settles open `BUY` positions using First-In-First-Out (FIFO) queue matching:

1. Locate all open `ExecutionLog` records where `status = 'FILLED'`, `side = 'BUY'`, `resolution_outcome = outcome`, and `source_wallet_address = whale_address`, sorted by `executed_at ASC`.
2. Iterate through each open lot until `remaining_sell_notional` is exhausted:
   - **Case A: Full Lot Liquidation (`buy_notional <= remaining_sell_notional + 0.01`)**
     - Target BUY status transitions to `CLOSED`.
     - Net Realized PnL is computed:
       $$\text{PnL} = \text{Buy Notional} \times \left(\frac{p_{\text{sell}} - p_{\text{buy}}}{p_{\text{buy}}}\right) - (\text{Buy Fee} + \text{Allocated Sell Fee})$$
     - `remaining_sell_notional` decrements by `buy_notional`.
   - **Case B: Partial Lot Liquidation (`buy_notional > remaining_sell_notional`)**
     - Closed portion $N_{\text{closed}} = \text{remaining\_sell\_notional}$.
     - Remaining portion $N_{\text{rem}} = \text{buy\_notional} - N_{\text{closed}}$.
     - Pro-rated entry fee on closed portion: $\text{Fee}_{\text{closed}} = N_{\text{closed}} \times \left(\frac{\text{Original Buy Fee}}{\text{Original Notional}}\right)$.
     - Target BUY record modified: `notional_usd` becomes $N_{\text{closed}}$, `fee_usd` becomes $\text{Fee}_{\text{closed}}$, status transitions to `CLOSED`, and realized PnL is locked in.
     - **Split-Lot Record Created:** A new `ExecutionLog` is inserted with `notional_usd` $= N_{\text{rem}}$, `fee_usd` $= \text{Original Fee} - \text{Fee}_{\text{closed}}$, `status = 'FILLED'`, `realized_pnl_usd = None`, inheriting original timestamps.
     - `remaining_sell_notional` becomes $0.00$, terminating loop.

### 7.2 Zero Orphaned Positions & Share Conservation
Every partial split strictly preserves total capital and share counts:
$$\text{Notional}_{\text{original}} = \text{Notional}_{\text{closed}} + \text{Notional}_{\text{split\_rem}}$$
$$\text{Fee}_{\text{original}} = \text{Fee}_{\text{closed}} + \text{Fee}_{\text{split\_rem}}$$
$$\text{Shares}_{\text{original}} = \text{Shares}_{\text{closed}} + \text{Shares}_{\text{split\_rem}}$$

### 7.3 Interleaved Trades & Position Guard
- **Interleaved Outcome Lots:** Positions on the same market condition ID with different outcomes (e.g. Yes vs No) are strictly segregated by `resolution_outcome` matching. Buying No never accidentally liquidates a Yes lot.
- **Position Guard:** If a whale executes a `SELL` on a market where the portfolio holds zero open `BUY` lots from that whale, the execution engine logs a security notice and safely bypasses the order, preventing negative short positions or synthetic liability.

---

## 8. Dynamic Sizing & Multi-Tenancy Risk Scaling

### 8.1 Sizing Formula
To support an uncapped, continuously updating basket without constant portfolio rebalancing, Baleen sizes each trade live at the moment of execution:

$$\text{Active Basket Size } (N_{\text{active}}) = \text{Count}(\text{Wallets with } status=\text{'active'}, dormant=\text{False}, is\_hft=\text{False})$$
$$\text{Base Notional} = \frac{\text{User Free Balance}}{\max(1, N_{\text{active}})}$$
$$\text{Whale Risk Ratio} = \frac{\text{Whale Order Value (USD)}}{\text{Whale Total Portfolio Value (USD)}}$$
$$\text{Raw Order Value} = \text{Base Notional} \times \text{Whale Risk Ratio}$$
$$\text{Max Allowed} = \text{User Free Balance} \times \text{Risk Profile Cap}$$
$$\text{Final Order Value} = \min(\text{Raw Order Value}, \text{Max Allowed}) \times \text{Sizing Multiplier}$$

### 8.2 Risk Profile Matrix

| Risk Profile | Max Per-Trade Capital Cap | Target User Persona | Behavior during Basket Shrinkage ($N_{\text{active}} \to 1$) |
|---|---|---|---|
| **Conservative** | **5.0%** of Free Balance | Capital preservation, low volatility | Hard-capped at 5% even if single whale risks 100% |
| **Balanced** (Default) | **10.0%** of Free Balance | Standard growth with drawdown defense | Hard-capped at 10% per signal |
| **Aggressive** | **20.0%** of Free Balance | High conviction, alpha maximization | Hard-capped at 20% per signal |

### 8.3 Sizing Multipliers
- **Sniper Multiplier ($1.35\times$):** Applied when the source whale is classified as a `gold_sniper` or maintains $\ge 85.0\%$ win rate with low velocity ($\le 5$ trades/day).
- **Consensus Multiplier ($1.50\times$):** Applied when $\ge 2$ distinct active basket whales take identical outcome positions on the same market condition.
- **Cumulative Multiplier:** $1.35 \times 1.50 = \mathbf{2.025\times}$ for consensus trades involving gold snipers.

---

## 9. Forensic Vulnerability Catalog & Edge-Case Mechanics

Our forensic audit across the codebase uncovered 10 critical edge cases, accounting vulnerabilities, and algorithmic risks:

### 1. User Realized PnL Double-Counting / Dual-Recording Hazard
- **Location:** `backend/app/services/live_poller.py` lines 399-456 vs `backend/app/services/mark_to_market.py` line 240.
- **Mechanic:** In `live_poller.py`, when a user BUY is closed, `u_buy.realized_pnl_usd` is populated. If `u_realized_pnl_val` is also attached to the corresponding user `SELL` log, `mark_to_market.py` sums all execution logs (`status IN ('FILLED', 'CLOSED', 'RESOLVED')`), causing total realized PnL to be counted twice ($2\times$ inflation).
- **Remediation:** Realized PnL must strictly reside on the `CLOSED` BUY lot; user `SELL` logs must maintain `realized_pnl_usd = None`.

### 2. Phantom Free Cash Inflation from Floating MTM Gains
- **Location:** `backend/app/services/live_poller.py` lines 349-364.
- **Mechanic:** User sizing queries `u.sandbox_balance_usd`, which `mark_to_market.py` updates to include *unrealized floating MTM*. If a single penny token surges from $0.10 to $0.90, `u.sandbox_balance_usd` surges, causing `size_trade()` to deploy phantom capital that does not exist in settled cash.
- **Remediation:** Sizer must receive `user_free_settled_cash = settled_cash - open_margin`, never total MTM equity.

### 3. In-Place Caller Mutation in Fill Simulator
- **Location:** `backend/app/sizing/fill_simulator.py` lines 24-26.
- **Mechanic:** `levels.sort(key=...)` sorts the dictionary list in place. When called with a shared order book reference, it permanently mutates the caller's internal order book state.
- **Remediation:** Clone the order book list (`levels = list(order_book.get(...))`) before sorting.

### 4. Case-Sensitivity Execution Inversion
- **Location:** `backend/app/sizing/fill_simulator.py` line 20.
- **Mechanic:** `levels = order_book.get("asks" if side == "BUY" else "bids", [])`. If a caller passes lowercase `"buy"`, `side == "BUY"` evaluates to `False`, causing a BUY order to execute against BIDS (selling prices).
- **Remediation:** Standardize with `side.upper() == "BUY"`.

### 5. Distance-from-0.5 EV Gate Inverted Logic Fallacy
- **Location:** `backend/app/services/polymarket_fees.py` line 149 vs `backend/app/services/live_poller.py` line 209.
- **Mechanic:** If expected edge is calculated as `abs(p - 0.50)`, a high-alpha trade at $p=0.51$ (true probability 80%) has $\text{edge} = 0.01 < 2.5 \times \text{Fee Rate}$ and gets blocked, while a zero-alpha favorite at $p=0.95$ has $\text{edge} = 0.45$ and gets approved unconditionally.
- **Remediation:** Expected edge must strictly be $\max(0, p_{\text{whale\_win\_rate}} - p_{\text{fill}})$.

### 6. Wilson Score Lower Bound Variance Underflow
- **Location:** `backend/app/discovery/scanner.py` line 85.
- **Mechanic:** If unconstrained or out-of-bounds inputs ($w < 0$ or $w > n$) are provided, the variance term `p_hat * (1 - p_hat)` becomes negative, causing `math.sqrt()` to raise `ValueError: math domain error`.
- **Remediation:** Clamp `wins = max(0, min(wins, total))` and `max(0.0, variance_term)`.

### 7. Multi-User Open Margin Tracking Discrepancy
- **Location:** `backend/app/services/live_poller.py` line 228 vs line 349.
- **Mechanic:** The global cash limit guard checks platform-wide free cash (`user_id IS NULL`), but individual users in the multi-tenancy loop are not checked for individual free cash exhaustion.
- **Remediation:** Compute per-user settled cash and open margin before creating `user_log`.

### 8. Float Division by Zero on Near-Zero Prices
- **Location:** `backend/app/services/live_poller.py` line 280, `backend/app/services/mark_to_market.py` line 176.
- **Mechanic:** `price_ratio = (cur_p - fill_p) / fill_p`. If $p_{\text{fill}} \le 0.000$, division by zero crashes the worker loop.
- **Remediation:** Enforce floor guard: `fill_p = max(0.001, fill_p)`.

### 9. Database Connection Pool Exhaustion on Envio Event Bursts
- **Location:** `backend/app/database.py` lines 27-30 (`pool_size = 2, max_overflow = 3`).
- **Mechanic:** During high-volume market events (e.g. election night), Envio streams 20+ signals/second. With pool size of 2, PgBouncer / asyncpg runs out of connection slots, throwing `TimeoutError`.
- **Remediation:** Increase connection pool parameters and utilize background queuing with batch database commits.

### 10. Checkpoint Desynchronization on RPC Timeout
- **Location:** `listener/src/hypersync.ts` line 155 vs `listener/src/checkpoint.ts`.
- **Mechanic:** If the Envio HTTP query times out after partial event ingestion, `saveCheckpoint()` may save a block height before all events in that block were committed to the backend.
- **Remediation:** Ensure block checkpoint updates are committed only after backend `/api/signals` returns `HTTP 200`.

---

## 10. Recommended 200+ Scenario Stress-Testing Matrix

To systematically validate all 100% mathematical, accounting, and state invariants, we recommend executing a 200-scenario automated matrix partitioned into 5 core domains:

```
+----------------------------------------------------------------------------------------------------+
|                                200+ SCENARIO STRESS-TESTING MATRIX                                 |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [CATEGORY 1: Order Book & Liquidity Extremes] (40 Scenarios)                                      |
|  - SC-001 to SC-010: Empty order books, single-level micro liquidity ($1.00 depth), inverted books  |
|  - SC-011 to SC-020: 100-level deep books, whale orders consuming 50+ levels, fractional share lots|
|  - SC-021 to SC-030: Boundary price shocks: $0.99 -> $0.01, $0.01 -> $0.99, $0.50 -> $0.001       |
|  - SC-031 to SC-040: Zero-price contracts, inverted spreads (bid > ask), stale order book replay   |
|                                                                                                    |
|  [CATEGORY 2: Timing, Network & Settlement Dynamics] (40 Scenarios)                                |
|  - SC-041 to SC-050: Asynchronous block latency (1s, 5s, 15s, 30s, 60s delays)                    |
|  - SC-051 to SC-060: Out-of-order Envio HyperSync log delivery, duplicate tx hashes, re-org replays|
|  - SC-061 to SC-070: Rapid WebSocket reconnect bursts, abrupt RPC downtime (503/429/Timeout)      |
|  - SC-071 to SC-080: Database reconnect failover during live signal processing                     |
|                                                                                                    |
|  [CATEGORY 3: Complex Position & Lifecycle Sequences] (40 Scenarios)                               |
|  - SC-081 to SC-090: Multi-trade FIFO partial liquidations (1 Buy vs 5 partial Sells)              |
|  - SC-091 to SC-100: Multi-trade FIFO aggregation (5 Buys vs 1 large Sell) with exact split lots   |
|  - SC-101 to SC-110: Interleaved BUY Yes / BUY No / SELL Yes on same condition IDs                 |
|  - SC-111 to SC-120: Binary resolution payouts: $1.00 Won, $0.00 Lost, 50/50 Void/Cancelled       |
|                                                                                                    |
|  [CATEGORY 4: Multi-Tenancy & Portfolio Scaling] (40 Scenarios)                                    |
|  - SC-121 to SC-130: Concurrent users with Conservative, Balanced, and Aggressive risk profiles    |
|  - SC-131 to SC-140: Zero-balance edge states, near-zero accounts ($5.01 balance), sub-min trades  |
|  - SC-141 to SC-150: Whale burst concurrency (20 whales trading simultaneously on same block)      |
|  - SC-151 to SC-160: Sandbox global & user resets during active order processing                   |
|                                                                                                    |
|  [CATEGORY 5: Mathematical, Fee & Invariant Safety] (40 Scenarios)                                 |
|  - SC-161 to SC-170: 2026 Quadratic fees across all 6 asset classes at boundary probabilities     |
|  - SC-171 to SC-180: Banker's Rounding exact half-cent boundary tests ($0.025 -> $0.02, $0.035)    |
|  - SC-181 to SC-190: High-Water Mark monotonicity under severe 90% drawdown and recovery cycles    |
|  - SC-191 to SC-200: Cash non-negativity and settled cash invariance under extreme stress          |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

---
*Report compiled and certified by Survey Explorer 3.*
