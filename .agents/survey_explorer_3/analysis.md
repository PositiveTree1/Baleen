# In-Depth Survey & Architectural Analysis: Requirement R3
## Overnight Paper Trading Execution & State Machine Invariance

**Agent:** `survey_explorer_3`  
**Date:** 2026-08-30  
**Project:** Baleen (`c:\Users\arthu\Documents\Baleen-master`)  
**Scope:** Requirement R3 (Live Poller, Sleeve Sizing, Quadratic Fees, Slippage, Out-of-Order SELL Matching, State Machine Invariance, 24/7 Overnight Resilience, Backend Test Suite)

---

## 1. Executive Summary

Requirement R3 establishes the operational core for Baleen's automated copy-trading engine: continuous 24/7 paper trading with isolated sleeve risk budgeting, quadratic taker fee gating, directional slippage protection, out-of-order execution reconciliation, zero-orphan trade lifecycle guarantees, and mathematical state machine invariance.

Our in-depth survey confirms that Baleen possesses an advanced, production-grade paper trading implementation built around:
1. **Live Trade Mirror Service (`LiveTradeMirrorService` in `backend/app/services/live_poller.py`)** with dual ingestion (Polymarket Data API + Envio on-chain HyperSync), real-time startup protection (0-second lookback), deduplication guards, and binary market settlement.
2. **10-Wallet Isolated Sleeve Architecture (`SleeveManager` in `backend/app/sizing/sleeve_manager.py`)** implementing dynamic even splitting ($1,000 base budget per sleeve on a $10,000 bankroll), Conviction Percentile sizing ($5 feeler to $1,000 full conviction), anti-starvation mechanics, and copy-PnL EMA dynamic budget adjustments (floored at $300, capped at $1,500).
3. **2026 Polymarket Quadratic Fee Engine (`backend/app/services/polymarket_fees.py`)** implementing the official formula $\text{Fee} = \Theta \times \text{Notional} \times (1 - p)$ across all 6 asset categories, Banker's rounding (`ROUND_HALF_EVEN`), 0% maker fees, and Fee-Aware Expected Value gating ($\text{Expected Edge} \ge 2.5 \times \text{Fee Rate}$).
4. **Directional Slippage & Pricing Bounds (`backend/app/sizing/slippage.py`, `fill_simulator.py`)** with asymmetric threshold filtering, boundary price screening ($p < 0.04$ or $p > 0.96$ skipped), and 3-strike anti-arbitrage bot demotion ($p \le 0.02$ or $p \ge 0.98$).
5. **Out-of-Order SELL Reconciliation & FIFO Matching** preventing ghost short positions, orphan trades, and ensuring exact notional/fee conservation on partial lot splits.
6. **220-Scenario Test & Invariant Harness (`backend/tests/scenarios/`)** guaranteeing all 10 state machine invariants under extreme order book depth, timing jitter, interleaved executions, and multi-tenant scaling.

---

## 2. Codebase Architecture & Component Mapping

| Subsystem / Module | File Path | Primary Function & Responsibility |
|---|---|---|
| **Live Polling & Execution Engine** | `backend/app/services/live_poller.py` | 2.5s continuous polling loop, dual-ingestion deduplication, out-of-order SELL matching, FIFO lot execution, binary market resolution, event emission. |
| **10-Wallet Sleeve Manager** | `backend/app/sizing/sleeve_manager.py` | Dynamic bankroll allocation ($1,000 base), conviction percentile trade sizing, copy-PnL EMA scaling (0.30x-1.50x), capture rate logging. |
| **Polymarket 2026 Quadratic Fees** | `backend/app/services/polymarket_fees.py` | Category classification, $\Theta \in [0.00, 0.072]$, taker fee calculation with Banker's rounding, Fee-Aware EV Gate ($2.5\times$ fee rate). |
| **Directional Slippage Guard** | `backend/app/sizing/slippage.py` | Asymmetric slippage validator allowing favorable price improvements; blocks adverse slippage exceeding tier limits. |
| **Order Book Depth Walk Simulator** | `backend/app/sizing/fill_simulator.py` | Immutable order book depth walking, volume-weighted average price (VWAP), levels consumed computation. |
| **Mark-to-Market Valuation & Consensus** | `backend/app/services/mark_to_market.py` | 5.0s valuation loop, Gamma API batch price sync, multi-whale consensus detection, self-healing snapshot continuity watchdog. |
| **Automated Periodic Disk Backup** | `backend/app/services/disk_backup.py` | 15-minute periodic JSON & CSV trade export to disk (`data/backups/`) for disaster recovery. |
| **Database & Connection Pooling** | `backend/app/database.py` | PostgreSQL engine with aggressive connection recycling (`pool_recycle=60s`), pre-ping, zero statement cache for PgBouncer / Supabase; WAL-mode SQLite fallback. |
| **Data Models & Constraints** | `backend/app/models.py` | `ExecutionLog`, `User`, `Wallet`, `PortfolioSnapshot`, `SystemEvent`, `KeyValue` tables with unique and check constraints. |
| **Lifecycle & Keep-Alive Orchestrator** | `backend/app/main.py` | FastAPI application lifecycle, 5-minute keep-alive ping loop, 20-minute discovery scheduler, 24-hour rescoring scheduler. |

---

## 3. Deep-Dive Subsystem Analysis

### 3.1. Live Polling Loop & Ingestion Mechanics (`live_poller.py`)

#### Polling Pipeline & Roster Expansion
The poller operates on an asynchronous `while self.running:` loop with a 2.5-second sleep (`_poll_loop`, lines 898-905):
1. **Dynamic Active Roster Query:** Selects the top 10 highest-scoring active whales (`Wallet.status == 'active'`, `dormant == False`, `is_hft == False`, `avg_trades_per_day <= 65.0`) ordered by `Wallet.baleen_score.desc()`.
2. **Open-Position Source Expansion (Demoted/Rejected Whale Exit Following):**
   ```python
   # Lines 917-933
   stmt_open_sources = select(ExecutionLog.source_wallet_address).where(
       ExecutionLog.status == "FILLED",
       ExecutionLog.side == "BUY",
       ExecutionLog.source_wallet_address.isnot(None)
   ).distinct()
   ```
   Even if a whale was subsequently demoted, blacklisted, or made dormant, if Baleen holds an open `BUY` position from that whale, the service dynamically adds that address to the polling roster so that Baleen follows their exit `SELL` signal.
3. **Paced Rate-Limit Throttling:** Calls `https://data-api.polymarket.com/trades?user={addr}&limit=50` with an inter-whale pause (`await asyncio.sleep(0.05)`) to prevent HTTP 429 rate limits.
4. **Real-Time Startup Guard (0-Second Lookback):** Sets `self.started_at = datetime.utcnow().timestamp()` on start. Trades with `ts_sec < self.started_at` are flagged as historical and skipped without execution.
5. **Strict Boundary Price Screening:** Discards noise and toxic lottery dust trades where $p < 0.04$ or $p > 0.96$.

#### Dual Ingestion & Idempotency Deduplication Guard
Baleen supports dual-stream trade ingestion (Polymarket Data API polling + Envio HyperSync on-chain event subscriptions). To eliminate double-execution:
- **In-Memory Guard:** `seen_trade_keys` checks `f"{addr}:{cid}:{side}:{ts_sec}:{price}:{size}:{tx_hash}"`.
- **Database Idempotency Guard (Lines 141-167):** Queries for existing `ExecutionLog` with `user_id IS NULL`, matching `onchain_tx_hash` and `onchain_log_index`. If found, execution is skipped and an info event (`TRADE_SKIPPED_DUPLICATE`) is recorded.

---

### 3.2. 10-Wallet Sleeve Sizing Engine (`SleeveManager`)

The sleeve manager enforces strict capital segmentation to prevent a high-frequency whale from exhausting the entire portfolio bankroll:

```
Total Portfolio Bankroll: $10,000
├── Sleeve 1 (Whale A): Base $1,000 -> Adjusted $300 to $1,500 -> Open: $400 -> Free: $600
├── Sleeve 2 (Whale B): Base $1,000 -> Adjusted $300 to $1,500 -> Open: $1,000 -> Free: $0 (Exhausted, does not starve others)
├── Sleeve 3 (Whale C): Base $1,000 -> Adjusted $300 to $1,500 -> Open: $0   -> Free: $1,000
└── ... (Sleeves 4 to 10)
```

1. **Dynamic Base Allocation:**
   $$\text{Base Sleeve Budget} = \frac{\text{Settled Cash}}{\text{Active Roster Size}} = \frac{\$10,000}{10} = \$1,000.00$$
2. **Conviction Percentile Ranking:**
   Rather than guessing a whale's total net worth, Baleen ranks the whale's trade size against their own trailing trade history:
   $$\text{Percentile} = \frac{\sum \mathbf{1}_{s_i \le s_{\text{current}}}}{N_{\text{trailing}}}, \quad \text{Clamped to } [0.05, 1.00]$$
3. **Trade Sizing & Quality Multipliers:**
   $$\text{Intended Size} = \max(\$5.00, \text{Sleeve Budget} \times \text{Percentile} \times M_{\text{sniper}} \times M_{\text{consensus}})$$
   where $M_{\text{sniper}} = 1.35$ for Gold Snipers (win rate $\ge 85\%$, $\le 5$ trades/day) and $M_{\text{consensus}} = 1.50$ when $\ge 2$ basket whales enter the same market outcome.
4. **Sleeve Capacity Clipping (Zero Starvation):**
   $$\text{Actual Size} = \min(\text{Intended Size}, \max(0.0, \text{Adjusted Budget} - \text{Open Notional}))$$
   If $\text{Actual Size} < \$5.00$, the trade is skipped (`SKIPPED_SLEEVE_EXHAUSTED` or `SKIPPED_BELOW_MINIMUM`). If $\text{Actual Size} < \text{Intended Size}$, the trade executes at available capacity and logs `TRADE_CLIPPED_SLEEVE` with the exact capture rate percentage.
5. **Copy-PnL EMA Budget Adjustment:**
   Tracks Baleen's actual realized performance copying each whale ($\alpha = 0.05$):
   $$\text{Multiplier} = \text{clamp}\left(1.0 + \frac{\text{EMA}_{\text{copy PnL}}}{500}, 0.30, 1.50\right)$$
   $$\text{Adjusted Budget} = \text{Base Budget} \times \text{Multiplier}$$
   Ensures losing whales are throttled down to a $\$300$ floor without starvation, while winning whales scale up to $\$1,500$.

---

### 3.3. 2026 Quadratic Polymarket Fee Gate & Category Matrix

#### Official 2026 Polymarket Fee Formula
Polymarket's dynamic fee formula taxes contract count $C = \text{Notional} / p$:
$$\text{Fee (USD)} = \Theta \times C \times p \times (1 - p) = \Theta \times \text{Notional} \times (1 - p)$$
$$\text{Effective Fee Rate (\%)} = \Theta \times (1 - p) \times 100\%$$

#### 6 Official Fee Categories & Theta Schedule
| Category | Theta ($\Theta$) | Max Effective Taker Fee | Keyword Detection Summary |
|---|---|---|---|
| **Crypto** | `0.072` | 3.60% ($p=0.50$) | `bitcoin`, `btc`, `eth`, `solana`, `up or down`, `15m` |
| **Economics / Finance** | `0.060` | 3.00% ($p=0.50$) | `fed`, `interest rate`, `cpi`, `inflation`, `gdp`, `treasury` |
| **Culture, Weather & Tech** | `0.050` | 2.50% ($p=0.50$) | `apple`, `openai`, `nvidia`, `musk`, `weather`, `gta 6` |
| **Politics** | `0.040` | 2.00% ($p=0.50$) | `election`, `president`, `senate`, `trump`, `biden`, `vote` |
| **Sports** | `0.030` | 1.50% ($p=0.50$) | `vs`, `open:`, `championship`, `fc`, `nba`, `tennis`, `f1` |
| **Geopolitics & World Events** | `0.000` | 0.00% (Fee-Free) | `war`, `ceasefire`, `treaty`, `sanctions`, `nato`, `un` |

#### Mathematical Invariants
- **Maker Zero-Fee Invariant:** `is_maker=True` strictly returns `fee_usd = 0.0` and `maker_rebate_eligible = True`.
- **Banker's Rounding:** Quantized using `decimal.Decimal('0.01')` with `ROUND_HALF_EVEN` to avoid fractional cent drift over millions of simulated trades.
- **Fee-Aware Expected Value Gate (`calculate_fee_aware_ev_gate`):**
  $$\text{Min Required Edge} = 2.5 \times [\Theta \times (1 - p)]$$
  If whale's expected alpha / statistical edge does not exceed $2.5\times$ the taker fee rate, the trade is rejected (`TRADE_SKIPPED_EV`).
- **Option A Price-Adjusted Sports Gate:**
  - For Sports BUY where $p \ge 0.60$: requires $\text{Whale Win Rate} \ge p \times 100\%$.
  - For Sports BUY where $p < 0.60$: requires $\text{Whale Win Rate} \ge 50.0\%$.

---

### 3.4. Slippage Guards & Anti-Frontrunning

- **Directional Slippage Logic (`check_slippage` in `slippage.py`):**
  - BUY: $\text{Adverse Slippage} = (\text{Live Price} - \text{Whale Price}) / \text{Whale Price}$. If $\text{Live Price} \le \text{Whale Price}$, trade receives price improvement (`EXECUTE_ORDER`).
  - SELL: $\text{Adverse Slippage} = (\text{Whale Price} - \text{Live Price}) / \text{Whale Price}$. If $\text{Live Price} \ge \text{Whale Price}$, trade receives price improvement (`EXECUTE_ORDER`).
  - Adverse Thresholds:
    - $p \le 0.25 \implies \text{Max Adverse} = 1.2\%$
    - $p \le 0.50 \implies \text{Max Adverse} = 2.0\%$
    - $p > 0.50 \implies \text{Max Adverse} = 3.0\%$
- **Order Book Depth Walking (`fill_simulator.py`):**
  - Walks ask book for BUY and bid book for SELL.
  - Sorts unsorted order books without mutating the caller's data structure.
  - Computes exact volume-weighted average fill price across consumed levels.

---

### 3.5. Out-of-Order Execution & Zero-Orphan Matching

In live WebSocket environments, network latency can deliver a whale's `SELL` transaction before the prior `BUY` transaction.

```
Scenario A: Standard Ingestion
[BUY Signal]  ──> Create FILLED Lot ($50 @ 0.50)
[SELL Signal] ──> Match against open lot ──> Realized PnL ──> Lot CLOSED (0 Open Lots)

Scenario B: Out-of-Order Ingestion (Reordered by Network)
[SELL Signal arrives first] ──> 0 open lots held ──> Register PendingOutOfOrderSell in memory
                                                     (No ghost position, no negative cash)
[Lagging BUY arrives]      ──> Detected in pending registry ──> Match BUY & SELL immediately
                               ──> Write CLOSED BUY & CLOSED SELL to DB
                               ──> Realized PnL locked in ──> 0 Open Lots
```

1. **Pending Registration:** When a whale `SELL` arrives and `target_open_buys` is empty, `PendingOutOfOrderSell` is appended to `self.pending_out_of_order_sells[ooo_key]`.
2. **Lagging Match Execution:** When the matching `BUY` subsequently arrives, the pending SELL is popped, buy/sell fees are calculated, exact net realized PnL is computed, both system logs are committed as `status="CLOSED"`, user balances are credited/debited, and `PortfolioSnapshot` is updated.
3. **Zero Orphaned Positions Guarantee:** At no point does the system hold an open position after an out-of-order sequence completes.

---

### 3.6. FIFO Lot Lifecycle & Binary Market Resolution

#### Partial Lot Splitting Conservation
When a SELL signal is smaller than an open BUY lot:
- The existing `open_buy` is modified in-place to `status="CLOSED"`, with `notional_usd = closed_portion`, `fee_usd = closed_portion * fee_rate`, and `realized_pnl_usd` locked in.
- A new `split_buy` is inserted with `status="FILLED"`, `notional_usd = orig_notional - closed_portion`, `fee_usd = orig_fee - closed_fee`, preserving exact notional and fee conservation down to the sub-cent.

#### Binary Market Settlement (`settle_market_resolution`)
When an event resolves:
- Winning outcome positions settle at $\$1.00$ / share payout:
  $$\text{Realized PnL} = \text{Notional} \times \left(\frac{1.0 - p_{\text{fill}}}{p_{\text{fill}}}\right) - \text{Fee}$$
- Losing outcome positions settle at $\$0.00$ payout:
  $$\text{Realized PnL} = -\text{Notional} - \text{Fee}$$
- All matching lots transition from `FILLED` to `CLOSED`. Active trade count decrements to 0 for that market. User balances update and High-Water Marks ratchet upward.

---

## 4. State Machine Invariant Verification Matrix

Baleen defines and monitors 10 formal invariants via `backend/tests/scenarios/invariant_monitor.py`:

| # | Invariant Name | Mathematical Rule | Enforcement Mechanism | Failure Impact If Violated |
|---|---|---|---|---|
| **I1** | **Cash Non-Negativity** | $\text{Cash} \ge \$0.00$ | `SleeveManager` and `dynamic_sizer` floor sizing at available free cash / sleeve capacity. | Portfolio insolvency |
| **I2** | **Margin Equation** | $\text{Free Cash} = \max(0, \text{Settled Cash} - \text{Open Margin})$ | Open margin strictly tracks sum of active `FILLED` BUY notional. | Over-allocation of capital |
| **I3** | **HWM Monotonicity** | $\text{HWM}_{t+1} \ge \text{HWM}_t$ | `u.sandbox_high_water_mark_usd = max(cur_hwm, u.sandbox_balance_usd)`. | Phantom fee charges |
| **I4** | **FIFO Lot Split Conservation** | $\sum V_{\text{split}} = V_{\text{orig}}, \sum \text{Fee}_{\text{split}} = \text{Fee}_{\text{orig}}$ | Exact remainder math on partial FIFO closes (`live_poller.py:630-668`). | Capital leakage or creation |
| **I5** | **Fee Bounds** | $\$0.00 \le \text{Fee} \le 0.072 \times \text{Notional}$ | Exact $\Theta$ multiplication with Banker's rounding in `calculate_polymarket_fee`. | Inaccurate PnL accounting |
| **I6** | **Zero Orphaned Positions** | $\text{Open Lots} = 0$ after complete exit/settlement | Full FIFO sweep + out-of-order matching + binary settlement transition. | Stale capital lockup |
| **I7** | **Ghost Sell Fill Prevention** | No SELL fills when open positions $= 0$ | Verification of `target_open_buys` prior to executing SELLs (`live_poller.py:183-225`). | Phantom short positions |
| **I8** | **Numerical & IEEE Safety** | No `NaN`, `Inf`, or division by zero | Clamping prices to $[0.001, 0.999]$ and explicit `if price > 0` guards. | Process crash / corrupt DB |
| **I9** | **MTM Cash Isolation** | $\Delta \text{Unrealized PnL} \implies \Delta \text{Settled Cash} = 0$ | Settled cash queries only `status == "CLOSED"` logs; MTM updates only unrealized marks. | Phantom cash deployment |
| **I10** | **Equity Identity** | $\text{Equity} = \text{Settled Cash} + \text{Unrealized PnL}$ | Mark-to-Market engine authoritative snapshot synchronization. | Desynchronized dashboard |

---

## 5. 24/7 Continuous Overnight Resilience Analysis

| Vulnerability Vector | Codebase Protection Mechanism | Status | Recommendation / Observation |
|---|---|---|---|
| **Render / Cloud Idle Spin-Down** | `keep_alive_job` (`main.py:49-67`) pings `/health` every 5 minutes. | **Robust** | Verified. Prevents PaaS free/standard tier spin-down. |
| **Unhandled Async Exceptions in Poller** | `_poll_loop` wraps `_poll_active_whales` in `try...except Exception:` with `exc_info=True`. | **Robust** | Crashes within a single poll cycle log stack trace and resume after 2.5s. |
| **Database Pool Exhaustion (PgBouncer/Supabase)** | `pool_recycle=60`, `pool_pre_ping=True`, `pool_size=2`, `max_overflow=3`, `statement_cache_size=0`. | **Robust** | Tailored for Supabase connection pooler / transactional PgBouncer. |
| **Startup / Restart State Desynchronization** | `_ensure_snapshot_continuity` (`mark_to_market.py:39-66`) detects time gaps $> 30\text{min}$ and carries forward last known good balance. | **Robust** | Prevents cold-cache database collapse on server restart. |
| **Periodic State Persistence to Disk** | `DiskBackupService` (`disk_backup.py:82-108`) dumps all execution logs to JSON & CSV in `data/backups/` every 15 minutes. | **Robust** | Provides persistent disk snapshot independent of database state. |
| **Unbounded Memory in `seen_trade_keys`** | `self.seen_trade_keys = set()` in `LiveTradeMirrorService`. | **Low Risk** | Currently unbounded. While 1 month of trades is $< 5\text{MB}$, adding a FIFO cap (e.g. 100,000 keys) ensures multi-month safety. |
| **Unbounded Memory in `pending_out_of_order_sells`** | `self.pending_out_of_order_sells` dictionary. | **Low Risk** | If a whale sells a position Baleen never bought (e.g. bought pre-start), pending sell stays in memory. Adding a 24-48h TTL reaper ensures memory cleanliness. |
| **HTTP Client Churn in MTM Loop** | `PolymarketClient()` instantiated on every 5s cycle in `mark_to_market.py`. | **Optimization** | Reusing a long-lived `httpx.AsyncClient` on the service instance reduces TCP socket churn. |

---

## 6. Backend Test Suite Inventory

The Baleen backend contains a comprehensive, multi-tiered test suite with **23 test files** and **220+ scenario matrix cases**:

1. **Unit & Ingestion Tests:**
   - `test_live_poller_m_a3.py`: Platform deduplication, out-of-order SELL matching, binary market resolution ($1.00 win, $0.00 loss), user balance & HWM updates.
   - `test_sleeve_manager.py`: Even split across 10 wallets, conviction percentile ranking, sleeve isolation without starvation, copy-PnL EMA scaling, 0.30x floor, capture rate clipping.
   - `test_polymarket_fees.py` & `test_fee_calculation.py`: Category classification, quadratic formula, maker 0% fee, Banker's rounding, EV gate.
   - `test_slippage.py`: Directional slippage rules, price improvement allowance, adverse threshold rejection.
   - `test_dynamic_sizing.py` & `test_fill_model.py`: Dynamic sizer boundaries, order book depth walking, VWAP calculations.
   - `test_idempotency.py` & `test_checkpoint.py`: Duplicate tx hash idempotency, state checkpointing.
   - `test_dormancy.py`, `test_scoring_filters.py`, `test_scoring_5factor_and_hysteresis.py`: Whale classification, HFT filtering, Wilson bounds.

2. **Challenger Adversarial Suites:**
   - `test_challenger_fee_boundary_matrix.py`: Full cartesian matrix of 6 categories $\times$ 8 boundary prices $\times$ 13 notional levels.
   - `test_challenger_c2_invariant_adversary.py`: Adversarial invariant stress tests (sleeve isolation, MTM cash isolation, fee bounds, zero division).
   - `test_challenger_execution_stress.py`: Order book depth walking, inverted books, non-mutating order books, case insensitivity.
   - `test_challenger_a1_stress.py`: Comprehensive ingestion and sizing stress tests.

3. **Massive 220-Scenario Stress Matrix (`backend/tests/scenarios/`):**
   - `test_massive_220_scenario_matrix.py`: Master runner across all 4 tiers.
   - `test_scenario_orderbook_extremes.py` (Tier 1: 55 scenarios): Empty books, inverted spreads, massive depth, illiquid dust books.
   - `test_scenario_network_timing.py` (Tier 2: 55 scenarios): Out-of-order bursts, network latency jitter, websocket disconnections, simultaneous resolutions.
   - `test_scenario_lifecycle_fifo.py` (Tier 3: 55 scenarios): Fractional partial lot splits (10%, 25%, 33.3%, 50%, 75%, 90%), interleaved multi-whale entries, consensus triggers.
   - `test_scenario_multitenancy_scaling.py` (Tier 4: 55 scenarios): 1 to 100 concurrent users, varying risk profiles (conservative, balanced, aggressive), high-water mark ratcheting under multi-tenant load.

---

## 7. Concrete Architectural Recommendations for R3

1. **Sleeve Capacity & Poller Invariance:** Maintain the isolated 10-sleeve architecture with Conviction Percentile sizing as the standard. Ensure that all active candidate whales in the live poller are strictly bound to their respective sleeve budgets.
2. **Pending Out-of-Order Sell Reaper:** Add a periodic cleanup check (e.g. in `_poll_loop` every 60 minutes) to prune `PendingOutOfOrderSell` entries older than 48 hours to guarantee bounded memory over multi-month continuous running.
3. **Seen Trade Keys Ring Buffer:** Bound `self.seen_trade_keys` in `LiveTradeMirrorService` to the most recent 100,000 entries (or a time-bounded cache) to avoid slow linear memory growth during continuous 24/7 operation.
4. **Persistent HTTP Client in MTM Service:** Update `MarkToMarketService` in `mark_to_market.py` to maintain a single persistent `PolymarketClient` instance across cycles rather than instantiating and closing one every 5 seconds.
5. **Continuous Invariant Telemetry:** Ensure `SystemEvent` logging continues to emit structured events (`TRADE_COPIED`, `TRADE_SKIPPED_SLEEVE`, `TRADE_CLIPPED_SLEEVE`, `TRADE_OOO_MATCHED`, `MARKET_RESOLVED`) for real-time monitoring on the frontend dashboard.
