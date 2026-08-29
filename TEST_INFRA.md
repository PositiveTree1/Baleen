# Baleen 4-Tier End-to-End (E2E) Test Infrastructure Specification

**Document Version**: 1.0.0  
**Target Codebase**: Baleen Portfolio Management & Copy-Trading Engine (`c:\Users\arthu\Documents\Baleen-master`)  
**Target Platform**: Polymarket Prediction Markets  
**Runtime Environment**: Python 3.11.16 (`backend/.venv`), Pytest 9.1.1, Next.js 16.3.0 (`frontend/`)  
**Verification Status**: 359 / 359 Tests Passing (100.0%)

---

## 1. Executive Overview & Testing Philosophy

The Baleen test architecture utilizes a rigorous, multi-tiered End-to-End (E2E) validation framework designed to verify quantitative filter accuracy, mathematical fee invariance, portfolio sizing safety, order book execution fidelity, asynchronous network resilience, and state machine conservation.

```
====================================================================================================
                             BALEEN 4-TIER TESTING ARCHITECTURE
====================================================================================================

      ┌────────────────────────────────────────────────────────────────────────┐
      │  TIER 4: REAL-WORLD 220+ MULTI-SCENARIO STRESS SUITE                   │
      │  - 55 Orderbook Extremes (Empty/Inverted Books, Micro-Liquidity)       │
      │  - 55 Network & Settlement Dynamics (Lag, OOO Ingestion, Deduplication)│
      │  - 55 Position Lifecycle Sequences (FIFO Lot Splits, Multi-BUY Closes) │
      │  - 55 Multi-Tenancy & Portfolio Scaling ($50 - $500k, Risk Profiles)   │
      └───────────────────────────────────┬────────────────────────────────────┘
                                          │
      ┌───────────────────────────────────┴────────────────────────────────────┐
      │  TIER 3: CROSS-FEATURE COMBINATIONS & STATE INVARIANTS                 │
      │  - Sleeve Isolation + 2026 Quadratic Fee Schedule                      │
      │  - Mark-to-Market Valuation + Cash Non-Negativity & Margin Equation    │
      │  - 5-Point Hysteresis + Roster Rebalancing + Dormancy Watchdog         │
      │  - FIFO Lot Conservation + Slippage Bounds + Binary Settlement         │
      └───────────────────────────────────┬────────────────────────────────────┘
                                          │
      ┌───────────────────────────────────┴────────────────────────────────────┐
      │  TIER 2: BOUNDARY & CORNER CASES                                       │
      │  - Zero/Single Trade Accounts, Zero/Negative Volume                    │
      │  - Closed Position Concentration Cap (> 25% Outlier Wins)              │
      │  - Boundary Prices ($0.0001, $0.001, $0.50, $0.999, $1.00, None)       │
      │  - Zero/Negative Notionals, Empty/Crossed Order Books                  │
      │  - Single-Candidate Pool Normalization & Zero-Variance Sharpe          │
      └───────────────────────────────────┬────────────────────────────────────┘
                                          │
      ┌───────────────────────────────────┴────────────────────────────────────┐
      │  TIER 1: FEATURE COVERAGE & QUANTITATIVE SPECIFICATIONS                │
      │  - 8 Disqualifying Hard Gatekeepers & Wilson Win Rate Lower Bound      │
      │  - 5-Factor Scoring Engine & Intra-Pool Dynamic Min-Max Normalization  │
      │  - 10-Wallet Sleeve Partitioning ($Cash / 10) & Conviction Sizing      │
      │  - 2026 Dynamic Quadratic Fee Formula (6 Categories + Banker's Round)  │
      │  - Live Poller Deduplication, OOO Queue, and Binary Market Resolution  │
      │  - Next.js Dashboard Components, Drawers, Modals & Financial Charts    │
      └────────────────────────────────────────────────────────────────────────┘
====================================================================================================
```

---

## 2. Tier 1: Feature Coverage & Quantitative Specifications

Tier 1 exercises all primary functional paths, gatekeeper filters, scoring algorithms, sizing models, fee calculations, and frontend presentation modules.

### 2.1 Quantitative Gatekeeper Filters (`backend/app/discovery/scanner.py` & `engine.py`)
Baleen evaluates whale candidate wallets against 8 strict gatekeepers prior to roster consideration:

1. **Track Record Length (Lifetime Trades)**: Candidate must have $\ge 150$ lifetime closed trades (`trades_count >= 150`). Wallets with $< 150$ trades are rejected with `INSUFFICIENT_TRACK_RECORD_TRADES` (unless high-scale realized PnL $\ge \$500,000$).
2. **Track Record Length (Active Days)**: Candidate must have $\ge 60$ active trading history days (`active_days >= 60.0`). Wallets with $< 60$ days are rejected with `INSUFFICIENT_ACTIVE_HISTORY_DAYS` (unless PnL $\ge \$500,000$).
3. **Anti-HFT / Maker-Rebate Filter**: Candidate must not exceed $15.0$ trades/day (`avg_trades_per_day <= 15.0`). Accounts exceeding $15.0$ are rejected with `HFT_MAKER_BOT_EXCEEDED`.
4. **Closed Position Concentration Cap**: Single biggest winning position must not exceed $25\%$ of positive realized PnL sum ($\frac{\text{Biggest Win}}{\sum \text{Positive PnL}} \le 0.25$). Wallets exceeding $25\%$ are rejected with `OUTLIER_CONCENTRATION_TOO_HIGH`.
5. **Minimum Scale (PnL & Volume)**: Candidate must have all-time realized $\text{PnL} \ge \$50,000.00$. If volume is reported ($> 0$), volume must be $\ge \$150,000.00$ (with high-PnL bypass at $\ge \$250,000$).
6. **Sleeve Size Compatibility**: Candidate median trade size must fall within $[\$20.00, \$3,000.00]$. Accounts with median trade $< \$20$ or $> \$3,000$ are rejected with `SLEEVE_SIZE_INCOMPATIBLE`.
7. **Wash-Trading Detection Filter**: Consecutive trades on the same market condition with opposing sides executed within $\le 120\text{s}$ are classified as wash pairs. If wash ratio $> 10\%$ and count $\ge 2$, rejected with `WASH_TRADING_PATTERN`.
8. **Boundary Arbitrage Filter**: Accounts generating profits via toxic $0.01 / 0.99$ settlement boundary sniping are rejected with `ARBITRAGE_BOUNDARY_SNIPER`.
9. **Minimum Win Rate & Wilson Lower Bound**: Candidate raw win rate must be $\ge 55.0\%$, supported by the 90% Wilson confidence lower bound ($z=1.645$).
10. **Gold Sniper Tier Classification**: Wallets with win rate $\ge 80.0\%$ and maximum drawdown $\le 12.0\%$ are promoted to the `"gold_sniper"` tier.

### 2.2 5-Factor Scoring & Intra-Pool Min-Max Normalization (`backend/app/scoring/basket.py`)
Qualifying candidate wallets are scored using 5 orthogonal alpha and risk factors:

$$S_w = \text{clamp}\Big(0.30 \cdot F_{\text{odds}} + 0.30 \cdot F_{\text{sharpe}} + 0.20 \cdot F_{\text{recency}} + 0.10 \cdot F_{\text{cat}} - 0.10 \cdot F_{\text{penalty}} + 10.0, \; 0.0, \; 100.0\Big)$$

- **Odds-Weighted Edge ($F_{\text{odds}}$)**: Raw factor $f_{\text{odds}} = \frac{\text{win\_rate}}{100} - \text{clamp}(\text{avg\_entry\_price}, 0.05, 0.95)$.
- **Risk-Adjusted Return ($F_{\text{sharpe}}$)**: Raw factor $f_{\text{sharpe}} = \frac{\mu(\text{daily\_pnl})}{\sigma(\text{daily\_pnl}) + 10^{-6}}$ over $\ge 5$ daily PnL observations.
- **Recency-Weighted EMA ($F_{\text{recency}}$)**: Exponential moving average with 30-day half-life decay ($\alpha = 1 - e^{-\frac{\ln(2)}{30}} \approx 0.02284$).
- **Category Consistency ($F_{\text{cat}}$)**: Number of profitable distinct market categories ($|\text{Categories}| \in \{1, 2, 3, 4\}$).
- **Copyability Penalty ($F_{\text{penalty}}$)**: Liquidity penalty $f_{\text{penalty}} = \min\left(1.0, \frac{\text{median\_trade\_size}}{5000.0}\right)$.
- **Intra-Pool Normalization**: Each raw factor is min-max scaled across the active pool:
  $$F_k(w) = \begin{cases} 50.0 & \text{if } \max_i(f_k(i)) - \min_i(f_k(i)) \le 10^{-7} \\ \text{clamp}\left(\frac{f_k(w) - \min_i(f_k(i))}{\max_i(f_k(i)) - \min_i(f_k(i))} \times 100, 0, 100\right) & \text{otherwise} \end{cases}$$
- **Top 10 Roster Hysteresis**: Incumbents receive a $+5.0$ defense buffer and Gold Snipers receive a $+3.0$ boost. Challengers must beat incumbents by $> 5.0$ composite points to displace them.
- **Adaptive Trader Dormancy**: Wallets inactive for $> 8 \times \text{their individual median inter-trade gap}$ are flagged dormant and excluded from the active roster.

### 2.3 10-Wallet Sleeve Partitioning & Dynamic Sizing (`backend/app/sizing/sleeve_manager.py` & `dynamic_sizer.py`)
- **Bankroll Partitioning**: Total settled portfolio cash is partitioned into equal sub-portfolio sleeves:
  $$\text{Base Sleeve Budget} = \text{round}\left(\frac{\max(0, \text{Settled Cash})}{\text{Active Roster Size}}, 2\right)$$
- **Conviction Percentile Sizing**: Whale trade sizes are evaluated against their trailing 50-trade history percentile rank ($0.05$ to $1.00$).
- **Dynamic Copy-PnL EMA Multiplier**:
  $$\text{Multiplier} = \text{clamp}\left(0.30, 1.50, 1.0 + \frac{\text{EMA}_{\text{PnL}}}{500.0}\right)$$
  Underperforming sleeves floor at $0.30\text{x}$ ($30\%$ of base budget), preserving capital while avoiding total abandonment.
- **Sleeve Remaining**: $\text{Remaining} = \max(0.0, \text{Adjusted Budget} - \text{Open Notional})$.

### 2.4 2026 Quadratic Polymarket Fee Engine (`backend/app/services/polymarket_fees.py`)
Calculates dynamic quadratic taker fees across 6 official Polymarket categories:
$$\text{Fee (USD)} = \Theta_{\text{category}} \times \text{Notional} \times (1 - p)$$

| Category | Theta ($\Theta$) | Effective Fee Rate @ $p=0.50$ | Max Fee Rate ($p \to 0.001$) |
|:---|:---:|:---:|:---:|
| **Crypto** | **0.072** | **3.60%** | **7.19%** |
| **Economics / Finance** | **0.060** | **3.00%** | **5.99%** |
| **Culture, Weather & Tech** | **0.050** | **2.50%** | **5.00%** |
| **Politics** | **0.040** | **2.00%** | **4.00%** |
| **Sports** | **0.030** | **1.50%** | **3.00%** |
| **Geopolitics** | **0.000 (Fee-Free)** | **0.00%** | **0.00%** |
| **General (Default)** | **0.050** | **2.50%** | **5.00%** |

- **Rounding**: Decimal quantization with Banker's Rounding (`ROUND_HALF_EVEN`) to the nearest cent ($0.01).
- **Maker Exemption**: `is_maker = True` returns `fee_usd = 0.0` and `maker_rebate_eligible = True`.
- **EV Net Gate**: Requires $\text{Expected Edge} \ge 2.5 \times [\Theta \times (1 - p)]$.

### 2.5 Mark-to-Market Valuation & Cash Isolation (`backend/app/services/mark_to_market.py`)
- Authoritative portfolio balance formula: $\text{Settled Cash} = \$10,000.00 + \sum \text{Realized PnL}$.
- Mark-to-Market unrealized price swings adjust `total_unrealized_pnl_usd` and `equity_usd`, but strictly never mutate `settled_cash_usd` or `free_cash_usd`.

### 2.6 Frontend Components & Interactive Analytics (`frontend/src/`)
- **Dashboard Modules**: `BalanceCounter`, `PortfolioAnalytics`, `LiveTape`, `WalletLeaderboard`, `TradeLog`.
- **Modals & Drawers**: `WalletDrawer`, `TradeDrawer`, `DeepAnalyticsModal`, `FullHistorySpreadsheetModal`, `RebalanceModal`, `ResetSandboxModal`.
- **Financial Visualizations**: `DailyWinLossBarChart`, `CumulativePnLChart`, `TradePriceChart`, `ScoreHistoryChart`.
- **Theme Uniformity**: Complete dark/light mode coverage using `ThemeContext`.

---

## 3. Tier 2: Boundary & Corner Cases

Tier 2 executes exhaustive boundary condition stress tests to prevent numeric overflows, division-by-zero crashes, and unhandled edge states.

| Test Focus Area | Boundary Inputs Tested | Expected Behavior | Validating Test File |
|:---|:---|:---|:---|
| **Zero / 1 Trade Gate** | `trades_count = 0`, `trades_count = 1`, `trades_count = 149` | Disqualified with `INSUFFICIENT_TRACK_RECORD_TRADES` | `test_scoring_filters.py`<br>`test_scoring_5factor_and_hysteresis.py` |
| **Active Days Boundary** | `active_days = 0.0`, `active_days = 59.9` | Disqualified with `INSUFFICIENT_ACTIVE_HISTORY_DAYS` | `test_scoring_filters.py` |
| **Volume & Scale Boundary** | $\text{Vol} = \$0$, $\text{Vol} = \$149,999$, $\text{PnL} = \$49,999$ | Disqualified with `VOLUME_BELOW_THRESHOLD` / `PNL_BELOW_THRESHOLD` | `test_scoring_filters.py` |
| **Outlier Concentration** | $\text{Concentration} = 25.01\%$, $\text{Concentration} = 100\%$ | Disqualified with `OUTLIER_CONCENTRATION_TOO_HIGH` | `test_scoring_filters.py`<br>`test_scoring_5factor_and_hysteresis.py` |
| **Fee Price Boundaries** | $p \in \{0.0000, 0.0010, 0.5000, 0.9990, 1.0000, -0.50, 1.50, \text{None}\}$ | Clamped to $[0.001, 0.999]$, None defaults to $0.50$; no floating exception | `test_polymarket_fees.py`<br>`test_challenger_fee_boundary_matrix.py` |
| **Zero & Negative Notional** | $\text{Notional} \in \{0.0, -0.01, -100.0, 10^9\}$ | Returns `fee_usd = 0.0` for $\le 0$; computes exact cent-level fee for $\$1\text{B}$ | `test_challenger_fee_boundary_matrix.py` |
| **Empty Order Books** | `asks = []`, `bids = []` | Returns `avg_price = 0.0`, `total_filled = 0.0`, `levels_consumed = 0` | `test_challenger_execution_stress.py`<br>`test_scenario_orderbook_extremes.py` |
| **Inverted Spreads** | $\text{Ask} = \$0.45 < \text{Bid} = \$0.55$ | Sorts price levels, walks best available ask without crash | `test_challenger_execution_stress.py`<br>`test_scenario_orderbook_extremes.py` |
| **Micro-Liquidity Depths** | Sub-cent depth ($<\$1.00$/level) across 20 levels | Correctly aggregates weighted average fill price across 20 levels | `test_challenger_execution_stress.py`<br>`test_scenario_orderbook_extremes.py` |
| **Single-Candidate Pool** | $N=1$ pool, or identical metrics across all candidates | Zero spread $\to$ returns $50.0$ default score without division by zero | `test_scoring_5factor_and_hysteresis.py` |
| **Zero-Variance Sharpe** | Daily PnL array with 0 standard deviation | Stdev $+ 10^{-6}$ epsilon and $1.0$ fallback prevent zero division | `test_scoring_5factor_and_hysteresis.py` |
| **Zero Cash & Leverage** | Settled Cash $= \$0.00$, order request $= \$500.00$ | Order rejected with `SKIPPED_INSUFFICIENT_FUNDS` or clipped | `test_dynamic_sizing.py`<br>`test_scenario_multitenancy_scaling.py` |

---

## 4. Tier 3: Cross-Feature Combinations & State Invariants

Tier 3 tests multi-module interactions and validates system state invariants across composite operations.

### 4.1 Sleeve Isolation + 2026 Quadratic Taker Fee Invariance
- **Interaction**: Sizing a copy trade simultaneously evaluates the whale's conviction percentile, the sleeve's remaining budget, and the category quadratic taker fee.
- **Invariant**: The sizing model ensures that $(\text{Notional} + \text{Estimated Fee}) \le \text{Sleeve Remaining}$, preventing the fee from causing sleeve overdrafts or cross-sleeve capital starvation.
- **Verification**: Tested in `test_sleeve_manager.py`, `test_challenger_a1_stress.py`, and `test_challenger_fee_boundary_matrix.py`.

### 4.2 Mark-to-Market Valuation + Cash Non-Negativity & Margin Conservation
- **Interaction**: Live poller processes real-time price ticks updating position valuations while concurrent trades execute against settled cash.
- **Invariant**:
  $$\text{Free Cash} = \max(0.0, \text{Settled Cash} - \text{Open Margin})$$
  $$\text{Equity} = \text{Settled Cash} + \text{Total Unrealized PnL}$$
  $$\text{Settled Cash} \ge 0.0, \quad \text{Free Cash} \ge 0.0, \quad \text{Open Margin} \ge 0.0$$
  Unrealized MTM gains never increase settled or free cash. Unrealized MTM losses reduce equity but cannot force settled cash negative.
- **Verification**: Tested in `test_challenger_execution_stress.py`, `test_live_poller_m_a3.py`, and `test_scenario_multitenancy_scaling.py`.

### 4.3 5-Point Hysteresis + Roster Rebalancing + Trader Dormancy
- **Interaction**: Rescoring worker updates all candidate scores, evaluates the 5.0-point hysteresis defense buffer against challengers, checks the 8x adaptive dormancy threshold, and triggers portfolio rebalancing.
- **Invariant**:
  - Incumbent retains seat if $\text{Score}_{\text{incumbent}} + 5.0 \ge \text{Score}_{\text{challenger}}$.
  - Displaced incumbent positions are liquidated cleanly, freeing up sleeve budget for the incoming whale.
  - Dormant whales are immediately excluded from the active top 10 roster regardless of their historical score.
- **Verification**: Tested in `test_scoring_5factor_and_hysteresis.py`, `test_dormancy.py`, and `test_wallet_api.py`.

### 4.4 FIFO Lot Conservation + Slippage Bounds + Binary Market Resolution
- **Interaction**: Multi-lot BUY orders execute at varying prices, followed by partial and full liquidations or binary market settlement ($1.00 / $0.00).
- **Invariant**:
  - Lot splits preserve exact cent-level conservation: $\sum \text{Notional}_{\text{split}} == \text{Notional}_{\text{parent}}$, $\sum \text{Fee}_{\text{split}} == \text{Fee}_{\text{parent}}$, $\sum \text{Shares}_{\text{split}} == \text{Shares}_{\text{parent}}$.
  - PnL is credited exclusively on position closing without double-counting on open BUY logs.
  - Binary market resolution cleanly closes 100% of open lots with zero orphaned positions.
- **Verification**: Tested in `test_challenger_execution_stress.py`, `test_scenario_lifecycle_fifo.py`, and `test_live_poller_m_a3.py`.

### 4.5 Deduplication Guard + Out-of-Order Execution Queue
- **Interaction**: Simultaneous websocket event streams (Envio HyperSync) and REST poller logs deliver out-of-order BUY and SELL events with potential network duplicates.
- **Invariant**:
  - `(onchain_tx_hash, onchain_log_index)` prevents duplicate trade execution.
  - Premature SELL events queue in `PendingOutOfOrderSell` and resolve upon arrival of the lagging BUY with exact PnL and zero open position leakage.
- **Verification**: Tested in `test_idempotency.py`, `test_live_poller_m_a3.py`, and `test_scenario_network_timing.py`.

---

## 5. Tier 4: Real-World 220+ Multi-Scenario Stress Suite

Tier 4 is an industrial-grade stress harness consisting of 220 distinct operational, market, execution, network, and numerical scenarios across 4 structured sub-suites.

```
====================================================================================================
                             THE 220-SCENARIO STRESS MATRIX
====================================================================================================

 ┌──────────────────────────────────────┬──────────────────────────────────────┐
 │ TIER 4.1: ORDER BOOK EXTREMES        │ TIER 4.2: TIMING & NETWORK DYNAMICS  │
 │ (55 Scenarios: S001 - S055)          │ (55 Scenarios: S056 - S110)          │
 │ - 10 Empty Books (0 bids/asks)       │ - 15 Out-of-Order Block Ingestions   │
 │ - 15 Inverted/Crossed Spreads        │ - 15 Duplicate Event Bursts (3x tx)  │
 │ - 15 Micro-Liquidity Depth Walks     │ - 15 Binary Resolutions ($1.00/$0.00)│
 │ - 15 Extreme Price Boundary Shocks   │ - 10 Large Block-Lag Catch-up Streams│
 ├──────────────────────────────────────┼──────────────────────────────────────┤
 │ TIER 4.3: POSITION LIFECYCLES (FIFO) │ TIER 4.4: MULTI-TENANCY & SCALING    │
 │ (55 Scenarios: S111 - S165)          │ (55 Scenarios: S166 - S220)          │
 │ - 15 Single BUY -> Multi-SELL Splits │ - 20 Capital Sizing Scales ($50-$500k│
 │ - 15 Multi-BUY -> Single SELL Closes │ - 15 Risk Profile Allocations (5-20%)│
 │ - 15 Interleaved BUY/SELL Sequences  │ - 10 HWM Profit-Loss Ratchet Cycles  │
 │ - 10 Multi-Market Portfolios (4 Mkt) │ - 10 Zero-Cash Margin Ceiling Guards │
 └──────────────────────────────────────┴──────────────────────────────────────┘
====================================================================================================
```

### 5.1 Invariant Monitor (`backend/tests/scenarios/invariant_monitor.py`)
Every scenario run continuously audits 10 state machine invariants on every transaction and state transition:

1. **`CASH_NON_NEGATIVITY`**: Settled Cash $\ge 0.0$, Free Cash $\ge 0.0$, Open Margin $\ge 0.0$.
2. **`MARGIN_EQUATION`**: $\text{Free Cash} == \max(0.0, \text{Settled Cash} - \text{Open Margin})$.
3. **`HIGH_WATER_MARK_MONOTONICITY`**: $\text{HWM}_{t+1} \ge \text{HWM}_t$, with zero downward ratcheting during drawdowns.
4. **`FIFO_LOT_SPLIT_CONSERVATION`**: Exact sum conservation of Notional, Fee, and Shares across lot splits.
5. **`FEE_BOUNDS`**: $\text{Fee} \in [0.0, \Theta \cdot \text{Notional} + 0.015]$; $\text{Fee} == 0.0$ for maker orders.
6. **`ZERO_ORPHANED_POSITIONS`**: Zero open lots remain after 100% position liquidations.
7. **`GHOST_SELL_PREVENTION`**: Accounts with zero open positions cannot execute SELL orders or incur exit fees.
8. **`NUMERICAL_IEEE_SAFETY`**: All balances, prices, notional, and fees are finite floats (zero `NaN`, `+Inf`, or `-Inf`).
9. **`MTM_CASH_ISOLATION`**: Price updates modify unrealized equity without mutating settled cash.
10. **`EQUITY_IDENTITY_INVARIANCE`**: $\text{Equity} == \text{Settled Cash} + \text{Total Unrealized PnL}$.

### 5.2 Scenario Suite Breakdown & Test Files

| Matrix Tier | Test Suite File | Scenarios Executed | Invariants Checked | Pass Rate |
|:---|:---|:---:|:---:|:---:|
| **Tier 4.1: Order Book Extremes** | `tests/scenarios/test_scenario_orderbook_extremes.py` | 55 | All 10 Invariants | **100.0% (55/55)** |
| **Tier 4.2: Timing & Network Dynamics** | `tests/scenarios/test_scenario_network_timing.py` | 55 | All 10 Invariants | **100.0% (55/55)** |
| **Tier 4.3: Position Lifecycle Sequences** | `tests/scenarios/test_scenario_lifecycle_fifo.py` | 55 | All 10 Invariants | **100.0% (55/55)** |
| **Tier 4.4: Multi-Tenancy & Scaling** | `tests/scenarios/test_scenario_multitenancy_scaling.py` | 55 | All 10 Invariants | **100.0% (55/55)** |
| **Unified 220 Scenario Runner** | `tests/scenarios/test_massive_220_scenario_matrix.py` | 220 | All 10 Invariants | **100.0% (220/220)** |

---

## 6. How to Run the Tests

### 6.1 Running Full Test Suite
From the backend directory (`c:\Users\arthu\Documents\Baleen-master\backend`):
```powershell
# Run all 359 tests in the backend suite
.\.venv\Scripts\python.exe -m pytest -v
```

### 6.2 Running Individual Test Tiers
```powershell
# 1. Run Quantitative Filters and 5-Factor Scoring (Tier 1 & 2)
.\.venv\Scripts\pytest.exe tests/test_scoring_filters.py tests/test_scoring_5factor_and_hysteresis.py tests/test_dormancy.py -v

# 2. Run 2026 Quadratic Fee Schedule & Boundary Matrix (Tier 1, 2, 3)
.\.venv\Scripts\pytest.exe tests/test_polymarket_fees.py tests/test_challenger_fee_boundary_matrix.py tests/test_fee_calculation.py -v

# 3. Run Sleeve Manager & Execution Simulation (Tier 1, 2, 3)
.\.venv\Scripts\pytest.exe tests/test_sleeve_manager.py tests/test_dynamic_sizing.py tests/test_fill_model.py tests/test_slippage.py -v

# 4. Run Execution Stress & Challenger Invariants (Tier 3)
.\.venv\Scripts\pytest.exe tests/test_challenger_execution_stress.py tests/test_challenger_a1_stress.py tests/test_live_poller_m_a3.py -v

# 5. Run Massive 220-Scenario Stress Matrix (Tier 4)
.\.venv\Scripts\pytest.exe tests/scenarios/test_massive_220_scenario_matrix.py -v
```

---

## 7. Quality Assurance & Invariant Verification Summary

| Invariant / Feature Tested | Verification Mechanism | Status |
|:---|:---|:---:|
| **Gatekeeper Hard Filters** | Unit & property-based tests verifying exact thresholds and boundary rejections | ✅ Verified |
| **5-Factor Normalization** | Min-max pool scaling with zero-spread division-by-zero protection | ✅ Verified |
| **Roster Hysteresis (+5.0 pt)** | Challenger vs incumbent rank comparison avoiding roster churn | ✅ Verified |
| **Sleeve Isolation (Zero Starvation)** | 10-wallet budget isolation ($Cash/10) with EMA dynamic multiplier | ✅ Verified |
| **Cash Non-Negativity & Conservation** | $\text{Free Cash} = \max(0, \text{Settled Cash} - \text{Open Margin}) \ge 0.0$ | ✅ Verified |
| **Quadratic 2026 Polymarket Fees** | 6 categories, Banker's Rounding, maker zero-fee exemption | ✅ Verified |
| **FIFO Lot Splitting Conservation** | Cent-level Notional, Fee, and Shares conservation across partial closes | ✅ Verified |
| **Ghost Sell & Orphan Prevention** | Zero open positions remaining after 100% position liquidations | ✅ Verified |
| **MTM Phantom Cash Isolation** | Mark-to-market unrealized valuation updates isolated from settled cash | ✅ Verified |
| **High-Water Mark Monotonicity** | HWM ratchets up on new equity peaks and never declines during loss | ✅ Verified |
| **Numerical Safety** | Finite float enforcement across all 220 stress matrix scenarios | ✅ Verified |

---
*End of Test Infrastructure Specification.*
