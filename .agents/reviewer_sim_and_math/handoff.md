# Quantitative & Mathematical Review Report (R1, R2, R3, R4)

**Agent**: Reviewer 2: Quantitative & Math Reviewer (Reviewer & Adversarial Critic)  
**Date**: 2026-08-31T00:44:30Z  
**Verdict**: **APPROVE**  
**Working Directory**: `c:\Users\arthu\Documents\Baleen-master\.agents\reviewer_sim_and_math`

---

## 1. Observation

Direct mathematical evaluation, static code auditing, and automated execution runs confirmed the following:

### R1. Universal CLOB Fill Slippage & Latency Formulation
In `backend/app/sizing/slippage.py` (`calculate_simulated_fill_price`):
1. **Half-Spread Floor**:
   $$\text{spread\_bps}(p_0) = \max\left(6.0, 12.0 \cdot (1.0 - 2.0 |p_0 - 0.5|)\right) \ge 6.0\text{ bps}$$
   - Mid-market ($p_0 = 0.50$): $\text{spread\_bps} = 12.0\text{ bps}$.
   - Wings ($p_0 \to 0.0$ or $p_0 \to 1.0$): $\text{spread\_bps} = 6.0\text{ bps}$.
2. **CLOB Depth Walk**:
   $$\text{depth\_bps}(\text{notional}) = 8.0 + \min\left(40.0, \left(\frac{\text{notional}}{1500.0}\right)^{0.75} \times 25.0\right) \le 48.0\text{ bps}$$
   - Sub-linear growth ($0.75$ exponent) models concave liquidity consumption with an explicit $40.0\text{ bps}$ marginal cap.
3. **Latency Adverse Selection Drift**:
   $$\text{latency\_bps}(\text{lat\_ms}) = \min\left(15.0, 5.0 \cdot \left(\frac{\text{lat\_ms}}{350.0}\right)^{0.5}\right) \le 15.0\text{ bps}$$
   - Square-root diffusion drift models adverse price evolution over latency window $\text{lat\_ms} \in [180.0, 1400.0]$.
4. **Anti-Rounding Tick Floor**:
   $$\delta_{\min}(p_0) = \max(0.0005, p_0 \times 0.0010)$$
   $$\Delta p = \max(\text{raw\_delta}, \delta_{\min})$$
   - Guarantees $\Delta p \ge 0.0005$, ensuring 4-decimal rounding (`round(p_fill, 4)`) never truncates slippage to zero for micro prices ($p \le 0.06$).
5. **Strict Directionality**:
   - $p_{\text{fill}} > p_0$ on BUY and $p_{\text{fill}} < p_0$ on SELL across all valid prices $p_0 \in (0, 1)$.
   - Validated across 945 synthetic price/notional/latency combinations in `verify_quant_math.py` with 0 failures.

### R2. Sample-Size Damped Dynamic Sleeve Sizing & Credibility Function $Z(N)$
In `backend/app/sizing/sleeve_manager.py` (`calculate_adjusted_sleeve_budget`):
1. **Two-Stage Continuous Formulation**:
   $$Z(N) = \begin{cases} \frac{1}{7} \cdot \left(\frac{N}{15}\right) = \frac{N}{105} & \text{for } 0 \le N < 15 \\ \frac{1}{7} + \frac{6}{7} \cdot \left(\frac{N - 15}{(N - 15) + 20.0}\right) & \text{for } N \ge 15 \end{cases}$$
2. **Boundary Anchoring ($N < 15$)**:
   - Multiplier $M(N) = 1.0 + Z(N)(M_{\text{raw}} - 1.0)$ where $M_{\text{raw}} \in [0.30, 1.50]$.
   - Max downward shock: $M_{\min}(N) = 1.0 - Z(N) \times 0.70 > 1.0 - \frac{1}{7} \times 0.70 = 0.90$ ($\ge \$900.00$ on $\$1,000.00$ base).
   - Max upward shock: $M_{\max}(N) = 1.0 + Z(N) \times 0.50 < 1.0 + \frac{1}{7} \times 0.50 \approx 1.0714$ ($\le \$1,071.43 \le \$1,100.00$).
   - For `SitsToPee` ($N=2$, EMA $= -\$350.00$, Score $= 82.0$): Adjusted budget is $\$987.14$ (98.7% of base budget), completely eliminating the previous 70% slash bug.
   - Validated over 810 extreme shock test cases with 0 bound violations.
3. **$C^0$ Continuity at $N=15$**:
   $$\lim_{N \to 15^-} Z(N) = \frac{1}{7} = Z(15) = \frac{1}{7} \approx 0.142857$$
   - Multiplier at $N=14 \implies \$906.67$, $N=15 \implies \$900.00$, $N=16 \implies \$871.43$.
4. **Smooth Asymptotic Convergence**:
   $$\lim_{N \to \infty} Z(N) = 1.0 \implies \lim_{N \to \infty} M(N) = M_{\text{raw}} \in [0.30, 1.50]$$
5. **Single-Trade EMA Innovation Clipping**:
   - In `update_copy_pnl_ema`: Innovations clipped to $\pm \$500.00$, bounding single-trade EMA delta to $|\Delta \text{EMA}| \le 0.05 \times \$500 = \$25.00$.
6. **Backward Compatibility**:
   - When `trades_count=None`, defaults to $Z=1.0$ ($M = M_{\text{raw}}$).

### R3. Mark-to-Market & Portfolio Timeframe Synchronization
1. **Cold-Cache Startup Integrity**:
   - In `backend/app/services/mark_to_market.py` lines 180-183: Un-cached open position PnL defaults to `0.0` rather than subtracting upfront taker fees before market prices are retrieved.
   - Watchdog continuity routine carries forward `last_bal` and `last_pnl` from database snapshots to prevent spurious cold balance resets.
2. **Timeframe Snapshot Bucketing**:
   - In `backend/app/api/execution_logs.py` lines 415-430: Bucketing employs last-of-bucket selection (`bucket_map[b_key] = r`) and guarantees `rows[-1]` is preserved as the final element.
   - `1H`, `1D`, `1W`, and `ALL` endpoints converge to the exact same live balance without temporal jumps.

### R4. Automated Testing & Verification
- Full Backend Pytest Suite: **1,410 / 1,410 passed in 26.42s (100% pass rate)**.
- Scratch Mathematical Verification Suite: **100% passed across all sweeps and stress tests**.
- Integrity Audit: **0 hardcoded test cheats, 0 facade stubs, 0 bypass paths**.

---

## 2. Logic Chain

1. **R1 Slippage & Execution Realism**:
   - Because $p_{\text{fill}}$ incorporates spread crossing ($\ge 6\text{ bps}$), non-linear CLOB depth walk ($\le 40\text{ bps}$), latency drift ($\le 15\text{ bps}$), and tick floor $\delta_{\min} = \max(0.0005, p \times 0.0010)$, every simulated fill is strictly adverse ($p_{\text{fill}} > p$ on BUY, $p_{\text{fill}} < p$ on SELL, $\text{slippage\_bps} > 0$).
   - Because `live_poller.py` routes all 5 execution branches (direct buys, FIFO sells, split buys, out-of-order matches, and onchain signals) through `calculate_simulated_fill_price` with `calc_latency_ms \in [180.0, 1400.0]`, 100% of execution logs have non-zero slippage and valid `latency_ms`.

2. **R2 Bayesian Credibility Sizing**:
   - Because $Z(N) \le 1/7$ for all $N < 15$, the maximum allowable adjustment to the $\$1,000$ base sleeve budget is strictly restricted to $[-10\%, +7.14\%] \subset [\$900.00, \$1,100.00]$ regardless of how large the initial drawdown is.
   - Because $Z(N)$ is monotonically increasing and continuous at $N=15$, credibility scales smoothly as statistical sample size grows, unlocking the full $[0.30x, 1.50x]$ sizing envelope only for mature whales ($N \ge 35$).
   - Because single-trade innovations are clamped to $\pm \$500$, no single outlier trade can distort the sleeve's long-term budget.

3. **R3 Snapshot Convergence**:
   - Because un-cached open position PnL defaults to $0.0$, initial system startup does not trigger temporary balance drops.
   - Because time-interval bucketing uses last-of-bucket selection and explicitly appends `rows[-1]`, switching between `1H`, `1D`, `1W`, and `ALL` displays consistent closing trajectories and matches the header counter balance identically.

---

## 3. Caveats

- **Continuous Parameter Tuning**: While $Z(N)$ transition parameters ($N=15$, $K_{\text{post}}=20.0$) satisfy all quantitative constraints and theoretical bounds, they can be calibrated via empirical backtesting over time as historical whale dataset size increases.
- No other caveats.

---

## 4. Conclusion

**Verdict**: **`APPROVE`**

All quantitative and mathematical requirements (R1, R2, R3, and R4) are rigorously satisfied:
1. Universal non-zero CLOB fill slippage ($\text{slippage\_bps} > 0$) and bounded `latency_ms` are enforced across 100% of execution paths.
2. Bayesian credibility prior $Z(N)$ provides exact $C^0$ continuity, asymptotic convergence, and strict $[-10\%, +10\%]$ bounds for low-trade whales ($N < 15$).
3. Timeframe snapshot queries (`1H`, `1D`, `1W`, `ALL`) converge cleanly to the live portfolio balance without temporal valuation jumps.
4. Pytest suite passes 100% (1,410 / 1,410 passed).
5. Code integrity is verified with zero hardcoded facades or bypass shortcuts.

---

## 5. Verification Method

### 1. Full Pytest Suite
```powershell
& "c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\python.exe" -m pytest
```
*Result*: `1410 passed in 26.42s`.

### 2. Dedicated Quant Core Regression Suite
```powershell
& "c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\python.exe" -m pytest tests/test_quant_core_fixes_r1_r2_r3.py -v
```
*Result*: `998 passed in 1.48s`.

### 3. Quantitative Math Verification Script
```powershell
& "c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\python.exe" "c:\Users\arthu\Documents\Baleen-master\.agents\reviewer_sim_and_math\verify_quant_math.py"
```
*Result*: `ALL MATHEMATICAL CHECKS PASSED PERFECTLY!` (945 slippage combos, 810 shock tests, continuity at $N=15$, asymptotic convergence, and EMA clipping).

### 4. Invalidation Conditions
- Any simulated fill producing $p_{\text{fill}} \le p$ on BUY or $p_{\text{fill}} \ge p$ on SELL.
- Any execution log with `latency_ms = None` or `slippage_bps <= 0.0`.
- Any whale with $N < 15$ trades receiving an adjusted sleeve budget outside $[\$900.00, \$1,100.00]$ on $\$1,000$ base.
- Any snapshot endpoint returning divergent latest balances across `1H`, `1D`, `1W`, or `ALL`.
