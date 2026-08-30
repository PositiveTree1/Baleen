# Technical Analysis & Mathematical Specification: Requirement 2 (R2)
## Sample-Size Damped Dynamic Sleeve Budget Sizing

**Author:** R2 Sizing Explorer  
**Date:** 2026-08-31  
**Status:** COMPLETE / SPECIFICATION READY  
**Scope:** `backend/app/sizing/sleeve_manager.py`, `backend/app/sizing/dynamic_sizer.py`, `backend/app/services/live_poller.py`, `backend/app/models.py`, `backend/tests/`

---

## 1. Executive Summary

Requirement 2 (R2) addresses a critical quantitative vulnerability in Baleen's capital allocation and sleeve management engine: **stochastic small-sample budget destruction**.

In prediction market copy trading, newly qualified or newly discovered whales (e.g., `SitsToPee` with $N=1, 2, 5$ trades) often encounter initial drawdown purely through Bernoulli variance ($p \approx 0.60–0.75$). Under an undamped dynamic adjustment formula, a single losing trade (e.g., $-\$350$ realized PnL) immediately slashes the whale's sleeve budget from the $\$1,000.00$ base allocation down to the absolute $\$300.00$ ($0.30\times$) floor—a **$70\%$ capital destruction** without statistically significant empirical evidence.

Conversely, a lucky initial win (e.g., $+\$300$) immediately inflates the sleeve budget to the $\$1,500.00$ ($1.50\times$) cap on a single coin flip.

This document specifies a mathematically rigorous **Bayesian Credibility and Sample-Size Shrinkage Prior** that:
1. **Guarantees** that any whale with sample evidence $N < 15$ trades remains strictly anchored within $\pm 10\%$ of base budget ($\$900.00 \le B_{\text{adj}} \le \$1,100.00$ on a $\$1,000.00$ base).
2. **Smoothly expands** the dynamic budget ceiling and floor as trade evidence matures ($N \ge 15$), unlocking the full $[0.30\times, 1.50\times]$ range over dozens of trades with $C^0$ continuous scaling.
3. **Enforces bounded per-trade sensitivity** via clipped EMA innovations, preventing rogue single-trade liquidation spikes from destabilizing portfolio allocations.

---

## 2. Comprehensive Codebase & Architecture Audit

### 2.1 Component Overview & Roles

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                               BALEEN SIZING ENGINE                               │
├───────────────────────────────┬──────────────────────────────────────────────────┤
│ Module                        │ Function & Architectural Responsibility          │
├───────────────────────────────┼──────────────────────────────────────────────────┤
│ `app/sizing/sleeve_manager.py`│ 10-Wallet Isolated Sleeve Architecture:          │
│                               │ - `calculate_sleeve_budget`: Bankroll / N_active │
│                               │ - `calculate_conviction_percentile`: Rank size   │
│                               │ - `update_copy_pnl_ema`: Slow alpha=0.05 EMA     │
│                               │ - `calculate_adjusted_sleeve_budget`: Damped dyn │
│                               │ - `size_sleeve_trade`: Anti-starvation isolation │
├───────────────────────────────┼──────────────────────────────────────────────────┤
│ `app/sizing/dynamic_sizer.py` │ Proportional Risk Sizer (§5 Spec):              │
│                               │ - Proportional risk profile caps (5%, 10%, 20%)  │
│                               │ - Denominator scaling across active basket       │
├───────────────────────────────┼──────────────────────────────────────────────────┤
│ `app/services/live_poller.py` │ Execution Engine & Live Ingestion:               │
│                               │ - Queries settled portfolio value & copy-PnL     │
│                               │ - Invokes `SleeveManager.size_sleeve_trade`      │
│                               │ - Enforces sleeve capacity clipping & events     │
├───────────────────────────────┼──────────────────────────────────────────────────┤
│ Database Models (`models.py`) │ Supabase Persistence & State:                    │
│                               │ - `ExecutionLog`: closed copy trades, PnL        │
│                               │ - `Wallet`: `total_trades_analyzed`, score       │
│                               │ - `SandboxRun` / `SandboxReevaluation`: audits   │
└───────────────────────────────┴──────────────────────────────────────────────────┘
```

### 2.2 Detailed File & Line Audit

#### 1. `backend/app/sizing/sleeve_manager.py` (Lines 65–106)
- **`update_copy_pnl_ema(current_ema, new_realized_pnl, alpha=0.05)`**:
  - Updates copy-PnL EMA with smoothing parameter $\alpha = 0.05$ (equivalent to an effective sample span of $S = \frac{2}{\alpha} - 1 = 39$ trades).
  - *Defect:* Lacks outlier clipping on raw trade input. A single extreme outlier (e.g. $-\$5,000$ due to abnormal contract pricing) can induce an instantaneous $50\%$ shock to the EMA.
- **`calculate_adjusted_sleeve_budget(base_budget, copy_pnl_ema, baleen_score, trades_count)`**:
  - Computes the adjusted sleeve budget from base budget, score, and copy-PnL.
  - *Current Defect:* If `trades_count` is omitted or unhandled, or if a linear damping factor $\lambda = N / 15$ is applied naively without adjusting the maximum raw slope, a whale with $N=5$ or $N=14$ trades can still experience budget cuts down to $\$400.00$ or $\$780.00$, violating the $10\%$ ($\$900–\$1,100$) acceptance criteria. Furthermore, omitting `trades_count` broke existing unit tests expecting asymptotic bounds ($1,500.00$ / $300.00$).

#### 2. `backend/app/services/live_poller.py` (Lines 381–435)
- **Lines 381–387**: Queries `ExecutionLog` for all closed positions to calculate total realized PnL and `settled_cash = 10000.0 + total_realized_pnl`.
- **Lines 389–391**: Calculates base sleeve budget $B_{\text{base}} = \text{settled\_cash} / 10$.
- **Lines 393–398**: Queries `func.sum(ExecutionLog.realized_pnl_usd)` for `wallet_address`.
  - *Defect:* Queries raw cumulative sum rather than tracking trade count $N$.
  - *Defect:* Calls `SleeveManager.calculate_adjusted_sleeve_budget(base_sleeve_budget, wallet_copy_pnl)` without passing `source_whale.baleen_score` or the sample size $N$, leaving the sizer blind to whale sample maturity.
- **Lines 424–433**: Invokes `SleeveManager.size_sleeve_trade(...)`.

#### 3. `backend/app/sizing/dynamic_sizer.py` (Lines 8–31)
- Implements `size_trade(user_balance, risk_profile, n_active, whale_trade_value, whale_portfolio_value, min_order_usd)`.
- Enforces risk profile limits (Conservative $5\%$, Balanced $10\%$, Aggressive $20\%$).
- Well-tested and functioning as pure math utility for proportional risk capping.

---

## 3. Empirical Failure Modes in Low-Sample Whales ($N < 15$)

### 3.1 The Bernoulli Variance Trap
Prediction market trade outcomes for high-conviction whales follow a binomial/Bernoulli distribution with true win rate $p \approx 0.65$. For sample sizes $N \in \{1, 2, 5\}$, the probability of observing consecutive initial losses is high:
- For $N=1$: $P(\text{loss}) = 1 - 0.65 = 35.0\%$
- For $N=2$: $P(\text{2 losses}) = 0.35^2 = 12.25\%$
- For $N=5$: $P(\ge 3 \text{ losses}) = \sum_{k=3}^5 \binom{5}{k} (0.35)^k (0.65)^{5-k} = 23.52\%$

### 3.2 Failure Case: `SitsToPee` ($N=2$)
1. **Initial State:** Whale `SitsToPee` is discovered and promoted to Top 10 with `baleen_score = 82.0`. Base sleeve budget = $\$1,000.00$.
2. **Trade 1:** Baleen mirrors a $\$500$ trade on an election market. The trade closes at a loss of $-\$350.00$.
3. **Without Bayesian Shrinkage:**
   $$\text{copy\_pnl\_ema} = -\$350.00 \implies \text{pnl\_factor} = \frac{-350.0}{500.0} = -0.70$$
   $$\text{Multiplier} = 1.0 + (-0.70) = 0.30 \implies B_{\text{adj}} = \$300.00$$
4. **Impact:** On the very next trade (Trade 2), `SitsToPee`'s budget is slashed by $70\%$. When `SitsToPee` executes a high-conviction winner, Baleen can only deploy $\$300$ instead of $\$1,000$, destroying the copy-trading expected value and permanently crippling the strategy's recovery ability.

---

## 4. Mathematical Specification of the Bayesian Shrinkage Prior

### 4.1 Classical Bühlmann Credibility Model
In empirical Bayesian inference and actuarial credibility theory, the posterior estimate of a parameter $\mu$ given sample estimate $\hat{\mu}$ and prior mean $\mu_0$ is:
$$\hat{\mu}_{\text{Bayes}} = Z(N) \cdot \hat{\mu} + (1 - Z(N)) \cdot \mu_0 = \mu_0 + Z(N) \cdot (\hat{\mu} - \mu_0)$$
where $Z(N) \in [0, 1]$ is the credibility factor reflecting sample statistical confidence.

### 4.2 Parameter Definitions & Boundaries
- **Base Sleeve Budget ($B_{\text{base}}$):** $\$1,000.00$ (on standard $\$10,000 / 10$ bankroll).
- **Prior Mean Multiplier ($\mu_0$):** $1.00$ ($100\%$ of base budget).
- **Asymptotic Floor Multiplier ($M_{\min}$):** $0.30$ ($\$300.00$).
- **Asymptotic Cap Multiplier ($M_{\max}$):** $1.50$ ($\$1,500.00$).
- **Sample Size ($N$):** Effective closed trade sample count $\max(0, N_{\text{closed}})$.
- **Threshold for Low Sample Size ($N_{\text{threshold}}$):** $15$ trades.
- **Maximum Allowable Low-Sample Deviation:** $\epsilon_{\max} = 0.10$ ($10\%$, bounding $B_{\text{adj}} \in [\$900.00, \$1,100.00]$).

### 4.3 Formulation of Credibility Factor $Z(N)$

The maximum downward raw deviation from the neutral prior $\mu_0 = 1.00$ is:
$$\Delta_{\text{down}} = 1.00 - M_{\min} = 1.00 - 0.30 = 0.70$$
To guarantee that for all $N < 15$, the maximum downward deviation from prior $1.00$ does not exceed $0.10$, the maximum allowable credibility at $N=15$ is:
$$Z(15) \le \frac{\epsilon_{\max}}{\Delta_{\text{down}}} = \frac{0.10}{0.70} = \frac{1}{7} \approx 0.142857$$

We construct the two-phase continuous Bayesian Credibility function $Z(N)$:

$$Z(N) = \begin{cases}
\frac{1}{7} \cdot \left(\frac{N}{15}\right) & \text{for } 0 \le N < 15 \\
\frac{1}{7} + \frac{6}{7} \cdot \left(\frac{N - 15}{(N - 15) + K_{\text{post}}}\right) & \text{for } N \ge 15
\end{cases}$$

where $K_{\text{post}} = 20.0$ is the post-threshold half-life parameter governing the smooth transition toward full sample maturity ($N \approx 50–100$ trades).

### 4.4 Mathematical Properties & Invariant Proof

#### Property 1: Strict Anchor Invariant ($N < 15$)
For any $N \in [0, 14]$ and for *any* arbitrary raw inputs ($\text{PnL} \in (-\infty, +\infty)$, $\text{Score} \in [0, 100]$):
- Maximum $Z(N)$ for $N < 15$ occurs at $N=14$:
  $$Z(14) = \frac{1}{7} \cdot \frac{14}{15} = \frac{14}{105} \approx 0.133333$$
- Minimum Possible Multiplier (Worst-Case Catastrophic Loss):
  $$M_{\min}(N) = 1.00 + Z(N) \cdot (0.30 - 1.00) = 1.00 - 0.70 \cdot Z(N)$$
  $$M_{\min}(14) = 1.00 - 0.70 \times \frac{14}{105} = 1.00 - 0.093333 = 0.906667 > 0.9000$$
  $$B_{\text{adj, min}}(14) = \$1,000.00 \times 0.906667 = \$906.67 \ge \$900.00$$
- Maximum Possible Multiplier (Worst-Case Outlier Win):
  $$M_{\max}(N) = 1.00 + Z(N) \cdot (1.50 - 1.00) = 1.00 + 0.50 \cdot Z(N)$$
  $$M_{\max}(14) = 1.00 + 0.50 \times \frac{14}{105} = 1.00 + 0.066667 = 1.066667 < 1.1000$$
  $$B_{\text{adj, max}}(14) = \$1,000.00 \times 1.066667 = \$1,066.67 \le \$1,100.00$$

**Conclusion:** $\forall N < 15$, $\$900.00 \le B_{\text{adj}} \le \$1,100.00$ is mathematically guaranteed under all edge cases. $\blacksquare$

#### Property 2: Continuity ($C^0$) at Boundary $N = 15$
- Left limit: $\lim_{N \to 15^-} Z(N) = \frac{1}{7} \times \frac{15}{15} = \frac{1}{7} \approx 0.142857$.
- Right limit: $\lim_{N \to 15^+} Z(N) = \frac{1}{7} + \frac{6}{7} \times \frac{0}{0 + 20} = \frac{1}{7} \approx 0.142857$.
- Value at boundary: $Z(15) = \frac{1}{7}$.
The transition across the $N=15$ boundary is strictly continuous with zero jump discontinuities.

#### Property 3: Asymptotic Behavior ($N \to \infty$)
- At $N = 35$ ($N - 15 = 20 = K_{\text{post}}$): $Z(35) = \frac{1}{7} + \frac{6}{7} \times \frac{20}{40} = \frac{4}{7} \approx 0.5714$.
- At $N = 75$ ($N - 15 = 60 = 3 K_{\text{post}}$): $Z(75) = \frac{1}{7} + \frac{6}{7} \times \frac{60}{80} = \frac{5.5}{7} \approx 0.7857$.
- As $N \to \infty$: $\lim_{N \to \infty} Z(N) = \frac{1}{7} + \frac{6}{7} \times 1.0 = 1.0$.

---

## 5. Bounded Per-Trade Sensitivity & EMA Dynamics

### 5.1 Outlier-Clipped EMA Innovation
To eliminate vulnerability to rogue orderbook executions or illiquid fills, trade innovations to the EMA are bounded:
$$\text{clamped\_pnl} = \operatorname{clip}(\text{new\_realized\_pnl}, -500.0, 500.0)$$
$$\text{EMA}_t = (1 - \alpha) \cdot \text{EMA}_{t-1} + \alpha \cdot \text{clamped\_pnl}$$
with $\alpha = 0.05$.

### 5.2 Maximum Single-Trade Shift
The maximum single-trade shift in the un-damped raw multiplier is:
$$\Delta M_{\text{raw, single}} \le \frac{\alpha \cdot (\text{PnL}_{\max} - \text{PnL}_{\min})}{500.0} = \frac{0.05 \cdot 1000.0}{500.0} = 0.10 \quad (10\%)$$
When scaled by the Bayesian Credibility factor $Z(N)$:
- For $N=2$ (`SitsToPee`): $\Delta B_{\text{trade}} \le Z(2) \cdot 0.10 \cdot \$1,000.00 = 0.0190 \cdot \$100.00 = \$1.90$ per trade.
- For $N=5$: $\Delta B_{\text{trade}} \le Z(5) \cdot 0.10 \cdot \$1,000.00 = 0.0476 \cdot \$100.00 = \$4.76$ per trade.
- For $N=14$: $\Delta B_{\text{trade}} \le Z(14) \cdot 0.10 \cdot \$1,000.00 = 0.1333 \cdot \$100.00 = \$13.33$ per trade.
- For $N=50$: $\Delta B_{\text{trade}} \le 0.68 \cdot 0.10 \cdot \$1,000.00 = \$68.00$ per trade.

This ensures ultra-smooth, stable trajectory tracking without erratic oscillations.

---

## 6. Implementation Specification & Target Code Changes

### 6.1 `backend/app/sizing/sleeve_manager.py`

```python
    @staticmethod
    def update_copy_pnl_ema(
        current_ema: float,
        new_realized_pnl: float,
        alpha: float = 0.05,
        max_trade_pnl_clip: float = 500.0
    ) -> float:
        """
        Slow Exponential Moving Average of Baleen's actual copy-PnL on this wallet.
        alpha = 0.05 ensures a long window (20+ trades) with bounded single-trade sensitivity.
        """
        clamped_pnl = max(-max_trade_pnl_clip, min(max_trade_pnl_clip, new_realized_pnl))
        return round((1.0 - alpha) * current_ema + alpha * clamped_pnl, 4)

    @staticmethod
    def calculate_adjusted_sleeve_budget(
        base_budget: float,
        copy_pnl_ema: float = 0.0,
        baleen_score: float = 80.0,
        trades_count: Optional[int] = None
    ) -> float:
        """
        Adjusts sleeve budget dynamically off Baleen Score base weight + copy-PnL EMA.
        Applies a Bayesian Credibility / Sample-Size Shrinkage Prior for low sample sizes (N < 15)
        such that whales with few trades (e.g. SitsToPee with 2 trades) remain strictly anchored
        within 10% of base budget ($900-$1,100 on $1,000 base) and cannot be violently slashed.
        """
        if base_budget <= 0:
            return 0.0

        # 1. Base multiplier from Baleen Score (benchmark 80.0)
        score_factor = (baleen_score / 80.0) if baleen_score > 0 else 1.0

        # 2. PnL scaling: each $100 in average realized copy-PnL adjusts budget by ~20%
        pnl_factor = (copy_pnl_ema / 500.0)

        raw_multiplier = score_factor + pnl_factor
        clamped_raw = max(0.30, min(1.50, raw_multiplier))

        # 3. Default to asymptotic full credibility if sample size is not specified (backward compatibility)
        if trades_count is None:
            return round(base_budget * clamped_raw, 2)

        # 4. Bayesian Credibility Weight Z(N)
        n = max(0, int(trades_count))
        if n < 15:
            # Strictly bounds deviation to <= 10% for N < 15: Z(N) <= 0.10 / 0.70 = 1/7
            z_n = (1.0 / 7.0) * (float(n) / 15.0)
        else:
            # Smoothly scales from 1/7 at N=15 up to 1.0 with half-life K=20
            k_post = 20.0
            z_n = (1.0 / 7.0) + (6.0 / 7.0) * (float(n - 15) / (float(n - 15) + k_post))

        damped_multiplier = 1.0 + z_n * (clamped_raw - 1.0)
        final_multiplier = max(0.30, min(1.50, damped_multiplier))
        return round(base_budget * final_multiplier, 2)
```

### 6.2 `backend/app/services/live_poller.py`

In `live_poller.py` lines 388–403:

```python
            # 3. Fetch wallet's realized copy-PnL and closed trade count
            stmt_wallet_stats = select(
                func.coalesce(func.sum(ExecutionLog.realized_pnl_usd), 0.0),
                func.count(ExecutionLog.id)
            ).where(
                ExecutionLog.user_id.is_(None),
                ExecutionLog.source_wallet_address.ilike(wallet_address),
                ExecutionLog.status == "CLOSED"
            )
            stats_row = (await db.execute(stmt_wallet_stats)).first()
            wallet_copy_pnl = float(stats_row[0]) if stats_row else 0.0
            wallet_closed_count = int(stats_row[1]) if stats_row else 0

            # Dynamic sleeve budget with Bayesian sample-size shrinkage
            adjusted_sleeve_budget = SleeveManager.calculate_adjusted_sleeve_budget(
                base_budget=base_sleeve_budget,
                copy_pnl_ema=wallet_copy_pnl,
                baleen_score=float(source_whale.baleen_score or 80.0) if source_whale else 80.0,
                trades_count=wallet_closed_count
            )
```

---

## 7. Verification Test Suite Matrix

The following test suites in `backend/tests/` verify R2 compliance:

| Test Case | Condition / Input | Expected Result | Acceptance Rule |
|---|---|---|---|
| `test_low_trade_count_whale_anchoring_n2` | $N=2$, $\text{PnL} = -\$800$ | $B_{\text{adj}} = \$986.67 \in [\$900, \$1100]$ | R2 Acceptance Criteria |
| `test_low_trade_count_whale_anchoring_n5` | $N=5$, $\text{PnL} = -\$800$ | $B_{\text{adj}} = \$966.67 \in [\$900, \$1100]$ | R2 Acceptance Criteria |
| `test_low_trade_count_whale_anchoring_n14` | $N=14$, $\text{PnL} = -\$1,000,000$ | $B_{\text{adj}} = \$906.67 \in [\$900, \$1100]$ | R2 Worst-Case Bound |
| `test_low_trade_count_whale_positive_cap_n14` | $N=14$, $\text{PnL} = +\$1,000,000$ | $B_{\text{adj}} = \$1,066.67 \in [\$900, \$1100]$ | R2 Worst-Case Bound |
| `test_asymptotic_full_credibility_clamping` | Default `trades_count=None`, extreme PnL | $B_{\text{adj}} = \$1,500$ (pos) / $\$300$ (neg) | Invariant Invariance |
| `test_ema_bounded_sensitivity_outliers` | $\text{PnL} = -\$10,000$ outlier | Clamped to $\pm \$500$ innovation | Outlier Safety |
| `test_continuity_at_n15_threshold` | $N=15^-$ vs $N=15^+$ | Exact matching value ($B_{\text{adj}} = \$900.00$) | $C^0$ Continuity |
