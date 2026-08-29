# Handoff Report — Reviewer 1 (Backend & Invariants Reviewer)

**Date**: 2026-08-29  
**Agent**: Reviewer 1 (`.agents/reviewer_1`)  
**Roles**: reviewer, critic  
**Target Codebase**: Baleen Portfolio Management & Copy-Trading Engine (`c:\Users\arthu\Documents\Baleen-master`)  
**Parent Conversation ID**: `80a690ee-3a02-4f8b-b9bd-343f548c6fae`  
**Gate Verdict**: **APPROVE**  
**Integrity Status**: **CLEAN (0 Integrity Violations)**

---

## 1. Observation

### 1.1 Direct Source Code Inspection
1. **`backend/app/discovery/scanner.py`**:
   - Lines 369: `baleen_score = compute_baleen_score(stats)` is explicitly evaluated after `calculate_authentic_wallet_stats(...)` and prior to `score_wallet(stats)` and line 424.
   - Lines 424-428: `if baleen_score >= 80.0 or stats['all_time_pnl_usd'] >= 100000.0:` assigns `wallet.tier = 'gold_sniper'`.
   - Line 452: `wallet.baleen_score = baleen_score` safely persists the score with zero `UnboundLocalError`.
   - Lines 76-86: `calc_wilson_lower_bound` contains strict zero-division protection `if total <= 0: return 0.0`.
   - Lines 197-214: Wash trading detection accurately flags opposing trades on matching conditions with $\Delta t \le 120\text{s}$, requiring `wash_ratio > 0.10 and wash_pair_count >= 2`.

2. **`backend/app/scoring/engine.py`**:
   - Lines 34-38:
     ```python
     if trades_count < 150 and pnl < 500000.0:
         return ScoringResult("rejected", None, "INSUFFICIENT_TRACK_RECORD_TRADES", False)
     if active_days < 60.0 and pnl < 500000.0:
         return ScoringResult("rejected", None, "INSUFFICIENT_ACTIVE_HISTORY_DAYS", False)
     ```
     Candidate wallets with $0$ lifetime trades, $1$ trade, or $149$ trades are strictly rejected unless lifetime PnL $\ge \$500,000$.
   - Lines 40-46: Anti-HFT gate (`avg_trades_per_day > 15.0`) and position concentration cap (`outlier_concentration_pct > 0.25`) strictly reject violators.

3. **`backend/app/scoring/basket.py`**:
   - Lines 69-117: `normalize_and_score_pool()` performs min-max intra-pool normalization across the 5 orthogonal factors (Odds-Edge 30%, Sharpe 30%, Recency-EMA 20%, Category 10%, Copy Penalty -10%). Zero-spread and single-candidate pools return safe default $50.0$ score with zero division-by-zero errors.
   - Lines 137-157: `select_top_10_roster()` enforces the $+5.0\text{pt}$ incumbent defense buffer and $+3.0\text{pt}$ Gold Sniper boost.

4. **`backend/app/sizing/sleeve_manager.py`**:
   - Lines 39-43: Bankroll split $\text{Cash} / N$ floors at $0.0$ and prevents negative budget.
   - Lines 58-63: `calculate_conviction_percentile()` clamps conviction rank to $[0.05, 1.0]$.
   - Lines 74-84: `calculate_adjusted_sleeve_budget()` clamps the Copy-PnL EMA multiplier to $[0.30\text{x}, 1.50\text{x}]$.
   - Lines 100-111: `sleeve_remaining = max(0.0, sleeve_budget_usd - open_notional_usd)` strictly enforces sleeve isolation and prevents cross-wallet capital starvation.

5. **`backend/app/services/polymarket_fees.py`**:
   - Lines 62-94: Categorizes markets into 6 official Polymarket categories:
     - Crypto ($\Theta = 0.072$)
     - Economics / Finance ($\Theta = 0.060$)
     - Culture, Weather & Tech ($\Theta = 0.050$)
     - Politics ($\Theta = 0.040$)
     - Sports ($\Theta = 0.030$)
     - Geopolitics ($\Theta = 0.000$, Fee-Free)
   - Lines 96-136: Computes quadratic fee $\Theta \times \text{Notional} \times (1 - p)$ with Banker's Rounding (`ROUND_HALF_EVEN`) to $\$0.01$. Maker orders and Geopolitics return `fee_usd = 0.0`.
   - Lines 138-154: `calculate_fee_aware_ev_gate()` requires $\text{Expected Edge} \ge 2.5 \times [\Theta \times (1 - p)]$.

6. **`backend/app/services/mark_to_market.py`**:
   - Lines 199-230: Settled cash is derived strictly from initial deposit plus realized trade PnL. Mark-to-market unrealized swings update open logs and portfolio equity, but strictly never mutate settled cash or free cash.

7. **`backend/tests/test_scoring_filters.py`**:
   - 26 rigorous unit and integration tests covering every boundary condition (0, 149, 150 trades, 59 vs 60 active days, $149,999 vs $150,000 volume, 54.9% vs 55.0% win rate, outlier concentration $>25\%$, anti-HFT $>15/\text{day}$, wash trading, sleeve compatibility, and high-PnL bypasses).

### 1.2 Test Suite Execution Results
1. **Full Backend Pytest Suite**:
   - Command: `.\.venv\Scripts\python.exe -m pytest`
   - Output: `378 passed in 24.42s` (100.0% pass rate).
2. **Dedicated 220-Scenario Stress Matrix**:
   - Command: `.\.venv\Scripts\pytest.exe tests/scenarios/test_massive_220_scenario_matrix.py -v`
   - Output: `5 passed in 1.34s` (220 scenarios executed across Tier 1, Tier 2, Tier 3, Tier 4, plus aggregate matrix; 0 invariant violations).
3. **Targeted Invariant & Boundary Matrix**:
   - Command: `.\.venv\Scripts\pytest.exe tests/test_scoring_filters.py tests/test_scoring_5factor_and_hysteresis.py tests/test_polymarket_fees.py tests/test_sleeve_manager.py tests/test_challenger_fee_boundary_matrix.py tests/test_challenger_execution_stress.py tests/test_challenger_a1_stress.py -v`
   - Output: `88 passed in 6.88s` (100.0% pass rate).

---

## 2. Logic Chain

1. **Integrity Verification**:
   - Inspected all modified and foundational backend modules for hardcoded return values, dummy/facade implementations, bypassed execution paths, or fabricated test results.
   - Code contains genuine mathematical implementations (Decimal Banker's rounding, Wilson 90% confidence bounds, 5-factor min-max scaling, exponential decay EMAs, and SQLite/SQLAlchemy database models). Zero integrity violations detected.
2. **Correctness & R1 Conformance**:
   - All 8 quantitative gatekeeper filters and 5-factor scoring algorithms in `scanner.py`, `engine.py`, and `basket.py` precisely match the requirements in `ORIGINAL_REQUEST.md §R1` and `PROJECT.md`.
   - The previously identified runtime bug in `scanner.py:422` (unbound `baleen_score`) and trade count bypass in `engine.py:34` (`trades_count > 0`) have been resolved and verified with 26 dedicated boundary tests.
3. **Invariance & R2 Conformance**:
   - **Sleeve Isolation**: `sleeve_remaining = max(0.0, sleeve_budget - open_notional)` guarantees that one wallet's trading activity cannot starve or overdraw another wallet's sleeve budget.
   - **Cash Non-Negativity & MTM Isolation**: Settled cash is modified only on trade fills and settlements; MTM adjustments modify unrealized PnL/equity only.
   - **Polymarket 2026 Quadratic Fees**: Dynamic fee formula across all 6 asset categories quantizes with Banker's Rounding to $\$0.01$, with complete maker zero-fee immunity.
   - **Numerical Safety**: Finite float guards prevent IEEE NaN / Inf contamination and division-by-zero crashes across zero-volume and single-trade candidate profiles.
   - **220 Scenario Matrix**: All 220 operational, market, lifecycle, and multitenancy scenarios executed against the 10-invariant monitor with zero violations.

---

## 3. Caveats

- Backend tests run against the local Python 3.11 virtual environment (`backend/.venv`). Any environment migration must retain identical dependencies as specified in `backend/requirements.txt`.
- Frontend UI validation is scoped to Reviewer 2 / M3 Track.

---

## 4. Conclusion

- **Verdict**: **APPROVE**
- The backend implementation of the Baleen prediction market copy-trading engine meets 100% of the quantitative, architectural, and invariant requirements specified in `PROJECT.md` and `ORIGINAL_REQUEST.md` (R1 and R2).
- Zero tests fail, zero invariant violations occur, and zero integrity violations exist.

---

## 5. Verification Method

To independently reproduce and verify this review verdict:

```powershell
cd c:\Users\arthu\Documents\Baleen-master\backend

# 1. Run complete backend test suite (378 tests)
.\.venv\Scripts\python.exe -m pytest

# 2. Run massive 220-scenario stress matrix (220 scenarios across 4 tiers)
.\.venv\Scripts\pytest.exe tests/scenarios/test_massive_220_scenario_matrix.py -v

# 3. Run targeted quantitative gatekeeper filter unit tests (26 tests)
.\.venv\Scripts\pytest.exe tests/test_scoring_filters.py -v
```
