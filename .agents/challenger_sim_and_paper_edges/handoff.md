# Empirical Challenger Audit Report: Paper Trading Simulation, Fees, Slippage & Accounting

**Agent**: Challenger 1 (`challenger_sim_and_paper_edges`)  
**Target Repository**: `c:\Users\arthu\Documents\Baleen-master`  
**Date**: 2026-08-29  
**Verdict**: **APPROVE WITH EMPIRICAL CONFIRMATION & REMEDIATIONS**

---

## 1. Observation

A rigorous empirical audit and stress testing harness (`backend/tests/test_challenger_execution_stress.py`) was constructed and executed against the Python backend environment (`Python 3.11.16`, `pytest 9.1.1`). 17 comprehensive empirical test cases were evaluated, confirming 5 major failure modes and execution divergences in the paper trading simulation.

```powershell
& 'c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\pytest.exe' tests/test_challenger_execution_stress.py -v
============================= 17 passed in 0.35s ==============================
```

### 1.1 Topic 1: Order Book Walking Against Shallow, Empty & Inverted Depth
- **Source File**: `backend/app/sizing/fill_simulator.py` (`file:///c:/Users/arthu/Documents/Baleen-master/backend/app/sizing/fill_simulator.py#L10-L75`)
- **Direct Observations**:
  1. **In-Place Input Mutation (`file:///.../fill_simulator.py#L24-L26`)**:
     ```python
     levels = order_book.get("asks" if side == "BUY" else "bids", [])
     if side == "BUY":
         levels.sort(key=lambda x: float(x.get("price", 0)))
     else:
         levels.sort(key=lambda x: float(x.get("price", 0)), reverse=True)
     ```
     Calling `simulate_fill` modifies the caller's list in-place via `.sort()`. In `test_fill_simulator_in_place_mutation_vulnerability`, `book["asks"][0]["price"]` was altered from `0.80` to `0.20`.
  2. **Case Sensitivity Failure (`file:///.../fill_simulator.py#L20`)**:
     Passing lowercase `"buy"` or mixed case evaluates `side == "BUY"` to `False`, fetching `"bids"` and sorting in descending order, executing a BUY order against sell bids (`test_fill_simulator_case_sensitivity_hazard`).
  3. **Partial Fills / Missing Completeness Metadata (`file:///.../fill_simulator.py#L4-L8`)**:
     `FillResult(avg_price, total_filled, slippage_pct, levels_consumed)` omits `is_fully_filled` or `unfilled_usd`. When order size exceeds depth, `total_filled < order_value_usd` is returned without an explicit boolean status flag.
  4. **Production Pipeline Disconnection (`file:///.../live_poller.py#L202-L220`)**:
     `simulate_fill()` is never called in `live_poller.py` or `signals.py`. Paper trading executes instantaneous fills at `effective_fill_price = live_p`, granting an ungrounded zero-slippage, infinite-liquidity execution advantage.

### 1.2 Topic 2: Quadratic Taker Fees & Boundary Pricing ($p \to 0.01$, $p \to 0.99$)
- **Source File**: `backend/app/services/polymarket_fees.py` (`file:///c:/Users/arthu/Documents/Baleen-master/backend/app/services/polymarket_fees.py#L62-L154`)
- **Direct Observations**:
  1. **Category Rates & Keywords**:
     - Geopolitics ($\Theta = 0.000$), Crypto ($\Theta = 0.072$), Economics/Finance ($\Theta = 0.060$), Culture/Tech ($\Theta = 0.050$), Politics ($\Theta = 0.040$), Sports ($\Theta = 0.030$), General Fallback ($\Theta = 0.050$).
     - Keyword priority: Geopolitics is matched first (`war`, `ceasefire`). A market titled `"Trump war on inflation"` is classified as Geopolitics (0% fee) rather than Politics or Economics.
     - Documented divergence: `copilot.py#L98` claims Sports is 3.5%, Crypto is 2.5%, Politics is 1.5%, which contradicts `polymarket_fees.py`.
  2. **Boundary Prices**:
     - At $p = 0.99$ on $100 notional (Crypto $\Theta = 0.072$): $\text{Fee} = 100 \times 0.072 \times 0.01 = \$0.072 \to \$0.07$ (Effective rate: 0.07%).
     - At $p = 0.50$: $\text{Fee} = 100 \times 0.072 \times 0.50 = \$3.60$ (Effective rate: 3.60%).
     - At $p = 0.01$: $\text{Fee} = 100 \times 0.072 \times 0.99 = \$7.128 \to \$7.13$ (Effective rate: 7.13%).
     - Clamping: Prices outside $[0.001, 0.999]$ are safely clamped.
  3. **Inverted EV Gate Formula (`file:///.../polymarket_fees.py#L138-L153` & `file:///.../live_poller.py#L205`)**:
     ```python
     # In live_poller.py:
     expected_edge = abs(effective_fill_price - 0.5)
     # In polymarket_fees.py:
     fee_rate = theta * (1.0 - p)
     min_required_edge = 2.5 * fee_rate
     should_pass = (expected_edge >= min_required_edge)
     ```
     `abs(p - 0.5)` is the market price's distance from 50%, not alpha. For a high-probability favorite with 0 edge ($p = 0.95$), `expected_edge = 0.45 >= 0.009` (passes unconditionally). For a massive alpha opportunity at $p = 0.51$, `expected_edge = 0.01 < 0.0882` (rejected).

### 1.3 Topic 3: Slippage Rules with Favorable Discounts vs Adverse Run-Ups
- **Source File**: `backend/app/sizing/slippage.py` (`file:///c:/Users/arthu/Documents/Baleen-master/backend/app/sizing/slippage.py#L8-L14`)
- **Direct Observations**:
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
  1. **Directional Inversion**: `abs(current_price - whale_price)` penalizes positive price improvement.
     - BUY @ whale entry $0.20 when market price drops to $0.18 (10% discount): `diff = 0.10 > 0.012` $\to$ `'CANCEL_ORDER: SLIPPAGE_EXCEEDED'`.
     - SELL @ whale entry $0.20 when market price surges to $0.25 (+25% gain): `diff = 0.25 > 0.012` $\to$ `'CANCEL_ORDER: SLIPPAGE_EXCEEDED'`.
  2. **Production Discrepancy (`file:///.../live_poller.py#L188-L202`)**:
     `live_poller.py` completely bypasses `check_slippage()`. Instead, it uses an inline check `if side == "BUY" and (live_p - price) > 0.015: return` (fixed 1.5 cents absolute tolerance), and executes all SELL orders unconditionally.

### 1.4 Topic 4: Cash Balance Accounting Under Rapid MTM Swings
- **Source Files**: `backend/app/services/mark_to_market.py` (`file:///c:/Users/arthu/Documents/Baleen-master/backend/app/services/mark_to_market.py#L174-L245`) and `backend/app/services/live_poller.py#L223-L253`
- **Direct Observations**:
  1. **Phantom Cash Inflation (`file:///.../live_poller.py#L237`)**:
     ```python
     free_cash = max(0.0, total_portfolio_equity - current_open_notional)
     ```
     `total_portfolio_equity` is read from `PortfolioSnapshot.balance`, which includes unrealized floating MTM gains. In `test_unrealized_gains_phantom_free_cash_inflation`:
     - Initial cash: $10,000. Deployed: $5,000 in open token.
     - Token surges 9x (unrealized gain = $40,000). Total portfolio equity = $50,000.
     - `free_cash` becomes $45,000, allowing the system to deploy $40,000 of settled cash it does not own.
     - If the token collapses to $0 before closing, the portfolio is overleveraged 4.5x above the initial bankroll.
  2. **Database Column Overloading (`file:///.../mark_to_market.py#L180`)**:
     For `status == "FILLED"` (open) trades, `elog.realized_pnl_usd` is actively overwritten with unrealized floating PnL on every MTM loop cycle (`elog.realized_pnl_usd = round(net_pnl, 2)`). The column stores unrealized PnL while open, and realized PnL when closed.

### 1.5 Topic 5: User Realized PnL Double-Counting in Live Poller FIFO
- **Source Files**: `backend/app/services/live_poller.py` (`file:///c:/Users/arthu/Documents/Baleen-master/backend/app/services/live_poller.py#L324-L355`) and `backend/app/services/mark_to_market.py#L240`
- **Direct Observations**:
  1. **Dual PnL Recording on Position Close**:
     ```python
     # live_poller.py:
     u_earliest_buy.status = "CLOSED"
     u_earliest_buy.realized_pnl_usd = round(u_orig_notional * u_ratio - float(u_earliest_buy.fee_usd or 0.0), 2)
     u_realized_pnl_val = round(u_notional * u_ratio - float(u_fee["fee_usd"]), 2)
     user_log = ExecutionLog(..., side="SELL", status="CLOSED", realized_pnl_usd=u_realized_pnl_val, ...)
     ```
     When `mark_to_market.py` sums user PnL (`u_pnl = sum(float(l.realized_pnl_usd or 0.0) for l in u_logs)`), both `u_earliest_buy` and `user_log` contribute, doubling the user's realized profit or loss. In `test_user_realized_pnl_double_counting_simulation`, a $27.40 true net profit was computed as **$57.40**.
  2. **Multi-Trade FIFO Orphan Bug (`test_multi_trade_fifo_orphan_bug`)**:
     When multiple BUY logs exist for a market, `u_open_buys[0]` closes only the first batch. Subsequent batches (`u_open_buys[1:]`) remain in `FILLED` status forever, continuing to accrue floating MTM even after the whale has fully exited the market.

---

## 2. Logic Chain

1. **Order Book Simulation Integrity**:
   - `simulate_fill` in `fill_simulator.py` correctly calculates price-weighted average execution across depth levels when invoked.
   - However, in-place `.sort()` mutates caller dictionaries, lowercase `"buy"` queries bids, and the module is completely bypassed by `live_poller.py`.
   - Therefore, paper trading results generated by the running system reflect an unconstrained zero-slippage top-of-book execution model rather than the audited book-walking logic.

2. **Quadratic Fee & EV Gate Mathematics**:
   - The quadratic formula $\text{Fee} = \Theta \times N \times (1 - p)$ is mathematically consistent with Polymarket's 2026 schedule and banker's rounding.
   - However, the EV Gate formula `expected_edge = abs(p - 0.5)` confuses distance from 50% with trader alpha, rejecting legitimate edge at toss-up prices and admitting negative-EV favorites.

3. **Slippage Directionality**:
   - In financial execution models, slippage is adverse price movement (paying more for a BUY, receiving less for a SELL).
   - `abs(current_price - whale_price)` treats favorable discounts as slippage breaches, erroneously aborting profitable entry opportunities.

4. **Cash Balance vs MTM Equity**:
   - Free cash must strictly equal $\text{Deposited Cash} + \text{Realized PnL} - \text{Open Notional Cost}$.
   - Basing `free_cash` on $\text{Total Portfolio Equity} = \text{Balance} + \text{Unrealized Gains}$ allows spending un-settled paper gains, introducing catastrophic drawdown risk.

5. **PnL Accounting Rigor**:
   - Realized PnL must be recorded on exactly one audit record per round-trip (either the closed BUY position or the closing SELL order, but never both).
   - System execution (`user_id is None`) correctly left `sys_realized_pnl_val = None` on the SELL log, but user execution assigned PnL to both logs, inflating user returns by >100%.

---

## 3. Caveats

1. **CLOB Depth Availability**: Live Polymarket CLOB order books require real-time WebSocket or REST fetching per market condition ID. When order book depth is unavailable, simulation must fall back to conservative spread models rather than assuming infinite depth.
2. **On-Chain Settlement Latency**: Polygon block confirmation times (~2s) and Envio HyperSync ingestion delays (~1-4s) mean real execution occurs 2-6 seconds after whale submission.

---

## 4. Conclusion

The audit findings and failure mechanics identified in survey reports are **100% EMPIRICALLY CONFIRMED**. The paper trading execution engine contains critical bugs that distort execution prices, double user PnL, reject favorable slippage, and allow phantom cash overleverage.

### Summary of Confirmed Defects & Concrete Remediations

| Ref | Category | Severity | File Reference | Concrete Remediation |
|---|---|---|---|---|
| **EX-01** | Accounting | **CRITICAL** | `backend/app/services/live_poller.py#L331-L355` | Set `u_realized_pnl_val = None` on the user SELL execution log (mirroring line 279 for system trades). |
| **EX-02** | Simulation | **HIGH** | `backend/app/services/live_poller.py#L188-L220` | Wire `simulate_fill()` and `check_slippage()` directly into `process_trade_fill()`. |
| **EX-03** | Quantitative | **HIGH** | `backend/app/services/live_poller.py#L205` | Replace `abs(p - 0.5)` with `whale_win_rate / 100.0 - p` (true expected alpha). |
| **EX-04** | Execution | **HIGH** | `backend/app/sizing/slippage.py#L8-L14` | Distinguish BUY slippage `(current - whale) / whale` from SELL slippage `(whale - current) / whale`. |
| **EX-05** | Accounting | **HIGH** | `backend/app/services/live_poller.py#L237` | Compute `settled_cash = 10000.0 + total_realized_pnl - current_open_notional` (excluding unrealized MTM). |
| **EX-06** | Simulation | **MEDIUM** | `backend/app/sizing/fill_simulator.py#L20-L26` | Use `sorted(levels, ...)` and `.upper()` to prevent in-place mutation and case sensitivity errors. |
| **EX-07** | Execution | **MEDIUM** | `backend/app/services/live_poller.py#L324-L335` | Implement a loop in FIFO close to consume multiple `open_buys` when SELL notional spans multiple batches. |

---

## 5. Verification Method

To independently verify the empirical proofs:

```powershell
cd c:\Users\arthu\Documents\Baleen-master\backend
& '.venv\Scripts\pytest.exe' tests/test_challenger_execution_stress.py -v
```

Expected result: 17 passed test cases covering empty/shallow order books, in-place mutation, quadratic taker fees, boundary prices, banker's rounding, EV gate logic flaws, directional slippage, phantom cash inflation, and FIFO double-counting.
