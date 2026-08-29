# Baleen R1 Quantitative Filter & Scoring Specification Mining Report

**Date**: 2026-08-29  
**Auditor**: R1 Quantitative Spec Miner  
**Target Codebase**: Baleen (`backend/`)  
**Scope**: Requirement R1 (Quantitative Gatekeeper Filters, 5-Factor Scoring, Normalization, Roster Hysteresis)

---

## 1. Executive Summary

This report delivers an exhaustive, line-by-line quantitative audit of the candidate discovery, gatekeeper filtration, multi-factor scoring, and Top 10 roster selection engine within Baleen.

All 359 tests across the backend test suite currently execute and pass in `27.63s` using the dedicated Python 3.11 virtual environment (`backend/.venv`). However, deep static and dynamic inspection reveals **one critical runtime bug** in `backend/app/discovery/scanner.py` (`UnboundLocalError` on `baleen_score`), **two logic bypass loopholes** in `backend/app/scoring/engine.py` (zero trade count falsy evaluation and an undocumented $500k PnL exemption), and several edge case discrepancies between the specification and implementation.

---

## 2. Architecture & File Mapping (R1)

| Module Path | Primary Responsibility | Key Functions / Classes |
|-------------|------------------------|-------------------------|
| `backend/app/discovery/scanner.py` | Leaderboard scraping, trade & position ingestion, authentic stats computation, stage 2 candidate audit | `calculate_authentic_wallet_stats()`, `evaluate_pending_wallets()`, `scan_for_wallets()`, `calc_wilson_lower_bound()` |
| `backend/app/scoring/engine.py` | Disqualifying hard gatekeeper filter execution & tier classification | `score_wallet()`, `ScoringResult` |
| `backend/app/scoring/basket.py` | 5-factor scoring, intra-pool min-max normalization, 5-point hysteresis Top 10 roster selection, 24h rescore | `compute_raw_factors()`, `normalize_and_score_pool()`, `compute_baleen_score()`, `select_top_10_roster()`, `refresh_basket()` |
| `backend/app/scoring/dormancy.py` | Inactivity/dormancy evaluation relative to trader's individual pace | `check_dormancy(hours_since_last_trade, median_inter_trade_gap_hours)` |
| `backend/app/models.py` | ORM entity definitions for persistent wallet records and historical snapshots | `Wallet`, `WalletSnapshot` |
| `backend/app/workers/scoring_worker.py` | Background 24h rescoring worker | `run_rescoring()` |
| `backend/app/workers/discovery_worker.py` | Background candidate discovery worker | `run_discovery()` |
| `backend/tests/test_scoring_filters.py` | Unit tests for gatekeeper filters | `test_pnl_threshold_*`, `test_hft_screen_*`, `test_outlier_*`, `test_gold_tier_*`, `test_boundary_*` |
| `backend/tests/test_scoring_5factor_and_hysteresis.py` | Unit tests for composite scoring, normalization, hysteresis | `test_intra_pool_dynamic_normalization()`, `test_roster_5pt_hysteresis_prevents_churn()` |
| `backend/tests/test_dormancy.py` | Unit tests for trader dormancy threshold | `test_dormancy_is_relative_to_own_median_gap()`, `test_daily_trader_*`, `test_weekly_trader_*` |

---

## 3. Detailed Gatekeeper Filter & Scoring Verification

### 3.1 Gatekeeper Filters Matrix

| Filter Spec | Specification Threshold | Implemented Location | Code Logic / Implementation | Verification Status | Observed Discrepancies & Notes |
|-------------|-------------------------|----------------------|-----------------------------|---------------------|--------------------------------|
| **1. Track Record Length (Trades)** | $\ge 150$ lifetime trades | `engine.py:34`<br>`scanner.py:375` | `if trades_count > 0 and trades_count < 150 and pnl < 500000.0:`<br>`return ScoringResult("rejected", ...)` | ⚠️ Partial / Warning | **1. Falsy Bug**: If `trades_count == 0`, the check evaluates to `False` (passes).<br>**2. PnL Bypass**: If `pnl >= $500,000`, the 150-trade requirement is skipped entirely. |
| **2. Track Record Length (Active Days)** | $\ge 60$ active days | `engine.py:37`<br>`scanner.py:174` | `if active_days < 60.0 and pnl < 500000.0:`<br>`return ScoringResult("rejected", ...)` | ⚠️ Partial / Warning | **1. Default Value**: If timestamps are missing in API, `active_days` defaults to `60.0` in both `scanner.py` and `engine.py`, bypassing the gate.<br>**2. PnL Bypass**: `pnl >= $500,000` bypasses active days. |
| **3. Anti-HFT / Maker-Rebate** | $\le 15$ trades / day | `engine.py:41`<br>`scanner.py:305` | `if trades_per_day > 15.0:`<br>`return ScoringResult("rejected", ..., "HFT_MAKER_BOT_EXCEEDED", False)` | ✅ Compliant | Exact match ($\le 15.0$ trades/day). Note: Error string in `scanner.py:398` mentions `> 100/day max` (cosmetic string mismatch). |
| **4. Closed Position Concentration Cap** | $\le 25\%$ ($0.25$) of positive realized PnL sum | `engine.py:45`<br>`scanner.py:130-133, 386` | `outlier_concentration = biggest_win / pos_pnl_sum`<br>`if outlier_pct > 0.25: return rejected` | ✅ Compliant | Strictly computed over closed positions with `cashPnl > 0`. Single-position outlier whales ($>25\%$) are rejected. |
| **5. Minimum Scale (PnL & Volume)** | $\text{PnL} \ge \$50\text{k}$, $\text{Volume} \ge \$150\text{k}$ | `engine.py:27-31`<br>`scanner.py:380` | `if pnl < 50000.0: return rejected`<br>`if vol > 0 and vol < 150000.0 and pnl < 250000.0: return rejected` | ✅ Compliant | Rejects $\text{PnL} < \$50\text{k}$. If volume is reported ($>0$), requires $\ge \$150\text{k}$ (with high-pnl exemption $\ge \$250\text{k}$). Upper boundary cap at $\$22\text{M}$ in scanner to exclude platform pool anomalies. |
| **6. Sleeve Size Compatibility** | $\$20 \le \text{median trade} \le \$3,000$ | `scanner.py:180-195`<br>`engine.py:49` | `is_sleeve_incompatible = bool(median_trade_size < 20.0 or median_trade_size > 3000.0)` | ✅ Compliant | Calculates median from `usdcSize`. Rejects if $< \$20$ or $> \$3,000$. If trade array is empty, defaults to $\$150.0$ (compatible). |
| **7. Wash-Trading Detection** | $< 120\text{s}$ BUY$\leftrightarrow$SELL pairs $\le 10\%$ | `scanner.py:197-214`<br>`engine.py:53` | Checks consecutive sorted trades on same `conditionId` with opposite sides in $\le 120\text{s}$. Flags if `wash_ratio > 0.10 and wash_pair_count >= 2`. | ✅ Compliant | Prevents self-dealing / wash-trading volume inflation while avoiding false positives on isolated single flips. |
| **8. Intra-Pool Normalization** | $0-100$ min-max across candidate pool | `basket.py:69-117` | Computes raw metrics across pool, scales each factor to $[0, 100]$ via $\frac{x - \min}{\max - \min} \times 100$. | ✅ Compliant | Zero-division guarded (`high - low <= 1e-7` returns 50.0). Composite uses 5 exact weights and shifts by $+10.0$ offset. |
| **9. Top 10 Roster Selection & Hysteresis** | Top 10 roster with $5.0$-point hysteresis defense | `basket.py:137-158, 222-231` | Ranking key: $\text{score} + (5.0 \text{ if incumbent else } 0) + (3.0 \text{ if gold else } 0)$. Top 10 selected. | ✅ Compliant | Incumbents retain seat unless challenger beats them by $> 5.0$ points. Gold Snipers receive $+3.0$ boost. Dormant whales excluded. |
| **10. Trader Dormancy Invariant** | Inactive $> 8 \times \text{median inter-trade gap}$ | `dormancy.py:1-9` | `hours_since_last_trade > 8 * median_inter_trade_gap_hours` | ✅ Compliant | Relative to individual trader cadence (e.g. 2h gap $\to$ 16h; 24h gap $\to$ 192h). |
| **11. Gold Sniper Classification** | Win Rate $\ge 80\%$, Max DD $\le 12\%$ | `engine.py:69` | `if win_rate >= 80.0 and max_drawdown <= 12.0: tier = "gold_sniper"` | ✅ Compliant | High conviction, low drawdown classification. |
| **12. Boundary Arbitrage Filter** | Reject $0.01 / 0.99$ settlement snipers | `engine.py:61` | `if wallet_stats.get('is_boundary_arb'): return rejected` | ✅ Compliant | Rejects toxic boundary arbitrage bots. |
| **13. Minimum Win Rate Gate** | Win Rate $\ge 55\%$ | `engine.py:65`<br>`scanner.py:390` | `if win_rate < 55.0: return rejected` | ✅ Compliant | Rejects wallets below coin-flip / breakeven threshold. |

---

### 3.2 5-Factor Scoring Mathematical Definition

The 5-factor composite score $S_w \in [0, 100]$ is computed as:

$$S_w = \text{clamp}\Big(0.30 \cdot F_{\text{odds}} + 0.30 \cdot F_{\text{sharpe}} + 0.20 \cdot F_{\text{recency}} + 0.10 \cdot F_{\text{cat}} - 0.10 \cdot F_{\text{penalty}} + 10.0, \; 0, \; 100\Big)$$

Where each factor $F_k$ is min-max normalized across the candidate pool:

$$F_k(w) = \begin{cases} 
50.0 & \text{if } \max_i(f_k(i)) - \min_i(f_k(i)) \le 10^{-7} \\
\text{clamp}\left(\frac{f_k(w) - \min_i(f_k(i))}{\max_i(f_k(i)) - \min_i(f_k(i))} \times 100, \; 0, \; 100\right) & \text{otherwise}
\end{cases}$$

#### Raw Factor Inputs ($f_k$):
1. **Odds-Weighted Edge ($f_{\text{odds}}$)**:
   $$f_{\text{odds}} = \frac{\text{win\_rate}}{100} - \text{clamp}(\text{avg\_entry\_price}, 0.05, 0.95)$$
   *(Measures alpha generated beyond implied market probability)*

2. **Risk-Adjusted Return ($f_{\text{sharpe}}$)**:
   $$f_{\text{sharpe}} = \frac{\mu(\text{daily\_pnl})}{\sigma(\text{daily\_pnl}) + 10^{-6}}$$
   *(Calculated over closed daily PnL series with $\ge 5$ days; defaults to $1.0$ otherwise)*

3. **Recency-Weighted EMA ($f_{\text{recency}}$)**:
   $$\text{EMA}_t = (1 - \alpha)\text{EMA}_{t-1} + \alpha \cdot \text{PnL}_t, \quad \alpha = 1 - e^{-\frac{\ln(2)}{30}} \approx 0.02284$$
   *(30-day half-life exponential decay)*

4. **Category Consistency ($f_{\text{cat}}$)**:
   $$f_{\text{cat}} = |\text{Profitable Distinct Market Categories}| \in \{1, 2, 3, 4\}$$
   *(Sports, Politics, Culture & Tech, Macro & Finance)*

5. **Copyability Penalty ($f_{\text{penalty}}$)**:
   $$f_{\text{penalty}} = \min\left(1.0, \; \frac{\text{median\_trade\_size}}{5000.0}\right)$$
   *(Penalizes illiquid whale trade sizing that cannot be replicated without heavy slippage)*

---

## 4. Specification Discovery Tables

### 4.1 Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Gatekeeper | Realized PnL Floor | Disqualifies wallets with $< \$50,000$ all-time realized PnL | `all_time_pnl_usd: float` | `ScoringResult("rejected", None, "PNL_BELOW_THRESHOLD", False)` | Returns rejection tuple | `app/scoring/engine.py:27` |
| 2 | Gatekeeper | Volume Floor | Disqualifies wallets with $< \$150,000$ volume (unless $\text{PnL} \ge \$250\text{k}$) | `total_volume_usd: float`, `all_time_pnl_usd: float` | `ScoringResult("rejected", None, "VOLUME_BELOW_THRESHOLD", False)` | Returns rejection tuple | `app/scoring/engine.py:30` |
| 3 | Gatekeeper | Lifetime Trade Count | Disqualifies wallets with $< 150$ lifetime trades (unless $\text{PnL} \ge \$500\text{k}$) | `trades_count: int`, `all_time_pnl_usd: float` | `ScoringResult("rejected", None, "INSUFFICIENT_TRACK_RECORD_TRADES", False)` | Returns rejection tuple | `app/scoring/engine.py:34` |
| 4 | Gatekeeper | Active Days Floor | Disqualifies wallets with $< 60$ active trading history days (unless $\text{PnL} \ge \$500\text{k}$) | `active_days: float`, `all_time_pnl_usd: float` | `ScoringResult("rejected", None, "INSUFFICIENT_ACTIVE_HISTORY_DAYS", False)` | Returns rejection tuple | `app/scoring/engine.py:37` |
| 5 | Gatekeeper | Anti-HFT Screen | Disqualifies maker/rebate bots with $> 15.0$ trades/day | `avg_trades_per_day: float` | `ScoringResult("rejected", None, "HFT_MAKER_BOT_EXCEEDED", False)` | Returns rejection tuple | `app/scoring/engine.py:41` |
| 6 | Gatekeeper | Outlier Concentration Cap | Disqualifies single trade profit $> 25\%$ of positive realized PnL sum | `outlier_concentration_pct: float` | `ScoringResult("rejected", None, "OUTLIER_CONCENTRATION_TOO_HIGH", False)` | Returns rejection tuple | `app/scoring/engine.py:45` |
| 7 | Gatekeeper | Sleeve Size Bounds | Disqualifies median trade size $< \$20$ or $> \$3,000$ | `is_sleeve_incompatible: bool` | `ScoringResult("rejected", None, "SLEEVE_SIZE_INCOMPATIBLE", False)` | Returns rejection tuple | `app/scoring/engine.py:49` |
| 8 | Gatekeeper | Wash Trading Detection | Disqualifies $< 120\text{s}$ BUY$\leftrightarrow$SELL flips $> 10\%$ ($\ge 2$ pairs) | `is_wash_trading: bool` | `ScoringResult("rejected", None, "WASH_TRADING_PATTERN", False)` | Returns rejection tuple | `app/scoring/engine.py:53` |
| 9 | Gatekeeper | Boundary Arb Screen | Disqualifies 0.01 / 0.99 settlement sniping bots | `is_boundary_arb: bool` | `ScoringResult("rejected", None, "ARBITRAGE_BOUNDARY_SNIPER", False)` | Returns rejection tuple | `app/scoring/engine.py:61` |
| 10 | Gatekeeper | Minimum Win Rate | Disqualifies wallets with win rate $< 55.0\%$ | `win_rate_pct: float` | `ScoringResult("rejected", None, "WIN_RATE_TOO_LOW", False)` | Returns rejection tuple | `app/scoring/engine.py:65` |
| 11 | Classification | Gold Sniper Tier | Promotes active wallets with $\text{WR} \ge 80\%$ and $\text{DD} \le 12\%$ | `win_rate_pct: float`, `max_drawdown_pct: float` | `tier = "gold_sniper"` | Defaults to `"standard"` | `app/scoring/engine.py:69` |
| 12 | Scoring | Intra-Pool Normalization | Min-max scales 5 metrics across candidate pool to $0-100$ | `candidate_stats_list: List[dict]` | `List[float]` (scores) | Spread $\le 10^{-7} \to 50.0$ | `app/scoring/basket.py:69` |
| 13 | Scoring | Standalone Baleen Score | Scores individual wallet using fixed benchmark anchors | `stats: dict` | `float` ($0.0 - 100.0$) | Clamped to $[0.0, 100.0]$ | `app/scoring/basket.py:119` |
| 14 | Selection | Roster Hysteresis | Selects Top 10 roster with $+5.0$ incumbent buffer & $+3.0$ gold boost | `candidates: List[Wallet]`, `current_incumbent_addresses: Set[str]` | `List[Wallet]` (Top 10) | Ignores dormant wallets | `app/scoring/basket.py:137` |
| 15 | Invariant | Adaptive Dormancy | Flags wallet as dormant if inactive $> 8 \times \text{median inter-trade gap}$ | `hours_since_last_trade: float`, `median_inter_trade_gap_hours: float` | `bool` | Returns `False` if gap $\le 0$ or None | `app/scoring/dormancy.py:1` |
| 16 | Confidence | Wilson Lower Bound | Computes 90% Wilson confidence lower bound for win rate | `wins: int`, `total: int`, `z=1.645` | `float` (0.0 - 100.0) | Returns `0.0` if `total <= 0` | `app/discovery/scanner.py:76` |

---

### 4.2 Edge Cases & Observed Behaviors

| # | Feature | Input Scenario | Observed Code Behavior | Severity / Risk |
|---|---------|----------------|------------------------|-----------------|
| 1 | `evaluate_pending_wallets` in `scanner.py` | Valid candidate wallet passing all gates reaches line 422 | `baleen_score` variable is referenced before assignment (`if baleen_score >= 80.0...`). Raises `UnboundLocalError`. | 🔴 **CRITICAL BUG** (crashes Stage 2 discovery on qualifying wallet) |
| 2 | `score_wallet` in `engine.py` | `trades_count = 0` (e.g. empty or missing field) | `trades_count > 0 and trades_count < 150` evaluates to `False`. Wallet passes trade count filter with 0 trades! | 🟡 **LOGIC DEFECT** (zero trades bypasses trade threshold) |
| 3 | `score_wallet` in `engine.py` | Single-trade whale with PnL = $550,000, 1 trade, 1 active day | `pnl < 500000.0` is `False`, bypassing both the 150-trade and 60-day gates. Single-trade whale is marked active. | 🟡 **UNDOCUMENTED EXEMPTION** (may admit single-trade whales) |
| 4 | `calculate_authentic_wallet_stats` in `scanner.py` | API returns trade/position objects with missing or corrupt timestamps | `all_ts` is empty $\to$ `active_days` defaults to `60.0`, automatically meeting the 60-day threshold. | 🟡 **DEFAULT VALUE LEAK** |
| 5 | `normalize_and_score_pool` in `basket.py` | Single candidate in pool or all candidates have identical metrics | `high - low <= 1e-7` condition catches zero spread and assigns `50.0`. Zero division avoided. | 🟢 **HANDLED SAFELY** |
| 6 | `compute_raw_factors` in `basket.py` | Daily history has 0 variance (all days identical PnL) | `stdev == 0` is handled by `stdev + 1e-6` and `sharpe_raw = 1.0` if `stdev == 0`. Zero division avoided. | 🟢 **HANDLED SAFELY** |
| 7 | `calc_wilson_lower_bound` in `scanner.py` | `total == 0` trades | Returns `0.0` immediately. Zero division avoided. | 🟢 **HANDLED SAFELY** |
| 8 | `calculate_authentic_wallet_stats` in `scanner.py` | All closed positions are losses (`pos_pnl_sum == 0`) | `pos_pnl_sum > 0 and biggest_win > 0` evaluates `False`, defaults `outlier_concentration = 0.10`. Passes concentration filter. | 🟢 **HANDLED SAFELY** (will be rejected by PnL or win rate gate anyway) |
| 9 | `select_top_10_roster` in `basket.py` | Challenger score = 89.0, Incumbent score = 85.0 (both standard tier) | Incumbent rank key = 85.0 + 5.0 = 90.0 > 89.0. Challenger does NOT displace incumbent. Churn prevented. | 🟢 **HANDLED SAFELY** |
| 10 | `select_top_10_roster` in `basket.py` | Challenger score = 91.0, Incumbent score = 85.0 (both standard tier) | Incumbent rank key = 90.0 < 91.0. Challenger displaces incumbent. Hysteresis buffer cleanly breached. | 🟢 **HANDLED SAFELY** |

---

## 5. Existing Test Coverage & Gap Analysis

### 5.1 Current Test Matrix for R1

| Test File | Test Case | Target Checked | Status |
|-----------|-----------|----------------|--------|
| `backend/tests/test_scoring_filters.py` | `test_pnl_threshold_rejects_below_50k` | PnL $< \$50\text{k} \to \text{rejected}$ | ✅ Passed |
| `backend/tests/test_scoring_filters.py` | `test_hft_screen_rejects_over_15_trades_per_day` | $> 15.0 \text{ trades/day} \to \text{rejected}$ | ✅ Passed |
| `backend/tests/test_scoring_filters.py` | `test_outlier_concentration_rejects_single_trade_over_25pct` | Outlier $> 25\% \to \text{rejected}$ | ✅ Passed |
| `backend/tests/test_scoring_filters.py` | `test_gold_tier_requires_both_winrate_and_drawdown` | Win rate / Max DD requirements for Gold Sniper | ✅ Passed |
| `backend/tests/test_scoring_filters.py` | `test_gold_tier_accepts_qualifying_wallet` | High WR + Low DD $\to$ Gold Sniper | ✅ Passed |
| `backend/tests/test_scoring_filters.py` | `test_wallet_above_all_thresholds_but_failing_drawdown` | High WR + High DD $\to$ Standard | ✅ Passed |
| `backend/tests/test_scoring_filters.py` | `test_boundary_arbitrage_filter_rejects_boundary_snipers` | Boundary arb flag $\to \text{rejected}$ | ✅ Passed |
| `backend/tests/test_scoring_5factor_and_hysteresis.py` | `test_hard_filters_outlier_concentration_25pct` | Concentration 20% passes vs 28% rejected | ✅ Passed |
| `backend/tests/test_scoring_5factor_and_hysteresis.py` | `test_anti_hft_maker_bot_filter` | 18 trades/day rejected | ✅ Passed |
| `backend/tests/test_scoring_5factor_and_hysteresis.py` | `test_sleeve_compatibility_and_wash_trading_filters` | Incompatible sleeve & wash trading rejection | ✅ Passed |
| `backend/tests/test_scoring_5factor_and_hysteresis.py` | `test_intra_pool_dynamic_normalization` | 2-wallet pool normalization | ✅ Passed |
| `backend/tests/test_scoring_5factor_and_hysteresis.py` | `test_roster_5pt_hysteresis_prevents_churn` | $+2\text{pt}$ challenger fails vs $+8\text{pt}$ challenger wins | ✅ Passed |
| `backend/tests/test_dormancy.py` | `test_dormancy_is_relative_to_own_median_gap` | 17h vs 15h on 2h median gap | ✅ Passed |
| `backend/tests/test_dormancy.py` | `test_daily_trader_dormant_after_8x_gap` | 193h vs 192h on 24h median gap | ✅ Passed |
| `backend/tests/test_dormancy.py` | `test_weekly_trader_not_dormant_at_same_hours` | 193h vs 1344h on 168h median gap | ✅ Passed |

### 5.2 Identified Test Coverage Gaps

1. **Missing Test: Zero / 1 Lifetime Trades Gate Failure**:
   No test currently asserts that a wallet with `trades_count = 0` or `trades_count = 149` (with PnL $< \$500\text{k}$) is rejected with `INSUFFICIENT_TRACK_RECORD_TRADES`.
2. **Missing Test: Active Days $< 60$ Gate Failure**:
   No test currently asserts that a wallet with `active_days = 59.0` (with PnL $< \$500\text{k}$) is rejected with `INSUFFICIENT_ACTIVE_HISTORY_DAYS`.
3. **Missing Test: Volume $< \$150\text{k}$ Gate Failure**:
   No test currently asserts that a wallet with $\text{volume} = \$149,000$ and $\text{PnL} = \$60,000$ is rejected with `VOLUME_BELOW_THRESHOLD`.
4. **Missing Test: Win Rate $< 55\%$ Gate Failure**:
   No test currently asserts that a wallet with $\text{win\_rate} = 54.9\%$ is rejected with `WIN_RATE_TOO_LOW`.
5. **Missing Test: `evaluate_pending_wallets` End-to-End Execution**:
   No test currently runs `evaluate_pending_wallets()` with mock API responses, which is why the `UnboundLocalError` on `baleen_score` in `scanner.py:422` went undetected.
6. **Missing Test: Pool Normalization Single-Candidate and Uniform-Metric Pools**:
   No test currently asserts that `normalize_and_score_pool` handles a 1-wallet pool or a pool where all candidates have identical odds edge / Sharpe without crashing or producing `NaN`.

---

## 6. Environment & Pytest Execution

- **OS**: Windows (PowerShell)
- **Python Environment**: `c:\Users\arthu\Documents\Baleen-master\backend\.venv` (Python 3.11.16, pytest-9.1.1)
- **Invocation Command**:
  ```powershell
  & "c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\python.exe" -m pytest
  ```
- **Execution Benchmark**:
  - Total tests collected: **359**
  - Total tests passed: **359 (100%)**
  - Execution time: **27.63s**

---

## 7. Actionable Recommendations for Implementation / Fixes

1. **Fix `scanner.py` `UnboundLocalError`**:
   In `backend/app/discovery/scanner.py`, inside `evaluate_pending_wallets()`:
   Compute `baleen_score = compute_baleen_score(stats)` immediately after computing `stats` (around line 368-370) so that `baleen_score` is defined for both tier checks (line 422) and wallet assignment (line 450).
2. **Fix `engine.py` Trade Count Falsy Gate**:
   Change `if trades_count > 0 and trades_count < 150...` to:
   ```python
   if trades_count < 150 and pnl < 500000.0:
       return ScoringResult("rejected", None, "INSUFFICIENT_TRACK_RECORD_TRADES", False)
   ```
3. **Harmonize Error String in `scanner.py:398`**:
   Update the HFT rejection message from `> 100/day max` to `> 15 trades/day max` to match the actual invariant.
4. **Add Unit Tests for All Remaining Gatekeeper Boundaries**:
   Add test cases in `test_scoring_filters.py` for:
   - Volume $< \$150\text{k}$
   - Trades count $< 150$ (including 0 and 149)
   - Active days $< 60$ (including 0 and 59)
   - Win rate $< 55\%$
   - Single-candidate and identical-metric pools in `normalize_and_score_pool`
