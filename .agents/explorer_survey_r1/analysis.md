# Deep Survey & Technical Specification: Universal 100% Polymarket CLOB Fill Slippage Modeling (Requirement 1)

**Working Directory**: `c:\Users\arthu\Documents\Baleen-master`  
**Investigator Role**: R1 Slippage Spec Miner  
**Date**: 2026-08-31  

---

## 1. Executive Summary

This investigation surveys the execution pipeline of the Baleen paper trading and live copy-trading system (`backend/app/services/live_poller.py`, `backend/app/sizing/fill_simulator.py`, `backend/app/sizing/slippage.py`, and `backend/app/services/polymarket_fees.py`).

The objective is to establish the authoritative specification and technical blueprint for **Requirement 1 (R1): Universal 100% Polymarket CLOB Fill Slippage Modeling**, ensuring that **100% of simulated fills across all execution branches execute with realistic CLOB depth and spread walk slippage (`slippage_bps > 0` on every market execution, and non-null `latency_ms`)**.

### Summary of Key Findings:
1. **Zero-Slippage Fallback Bypasses Exist in 4 Execution Paths**:
   - **Out-of-Order SELL Leg**: In `live_poller.py:519` and `live_poller.py:582`, `user_fill_price` is hardcoded to `pending_sell_match.price` (the exact whale entry price), causing `slippage_bps = 0.0`.
   - **Anti-Rounding Collapse Bug**: In `live_poller.py:348-354`, the inline formula `round(price * (1.0 \pm slippage_factor), 4)` collapses to `price` when `price * slippage_factor < 0.00005` (e.g. low odds $p \le 0.06$ or small notionals $\le \$50$), yielding `slippage_bps = 0.0`.
   - **Top-of-Book Un-slipped Fallback**: In `live_poller.py:345`, if `live_p != price`, `effective_fill_price = live_p` without adding taker spread or depth impact.
   - **Single-Level Fit in Fill Simulator**: In `fill_simulator.py:64-67`, when order size fits in Level 0, `avg_price == best_price` $\Rightarrow$ `slippage_pct = 0.0`.
2. **Missing `latency_ms` in Split Lots**:
   - In `live_poller.py:666-688`, the system `split_buy` `ExecutionLog` instantiation completely omits `latency_ms`, causing it to default to database `NULL`.
3. **Dead Code / Architectural Duplication**:
   - `backend/app/sizing/slippage.py` contains `calculate_simulated_fill_price`, but `live_poller.py` does NOT use it, having implemented an inline flawed version instead.
   - `fill_simulator.py` accepts `latency_ms: int = 1000` but ignores it entirely in the function body.

---

## 2. Line-by-Line Codebase Audit Across All Execution Paths

### 2.1 Branch 1: Direct Market BUY (Regular Ingestion)
- **Files & Lines**: `backend/app/services/live_poller.py:314-354`, `693-715`, `813-836`
- **Observed Code**:
  ```python
  # Line 315
  live_p = get_live_price(condition_id, outcome=outcome, asset=asset or tx_hash or "", fallback=price)
  
  # Lines 345-354
  if live_p != price and 0.001 <= live_p <= 0.999:
      effective_fill_price = live_p
  else:
      depth_impact_bps = 8.0 + min(35.0, (cash_usd / 2000.0) * 20.0)
      slippage_factor = depth_impact_bps / 10000.0
      if side == "BUY":
          effective_fill_price = min(0.99, max(0.01, round(price * (1.0 + slippage_factor), 4)))
      else:
          effective_fill_price = max(0.01, min(0.99, round(price * (1.0 - slippage_factor), 4)))
  ```
- **Analysis & Flaw**:
  - If `live_p != price`, it uses raw `live_p`. If `live_p` was top-of-book, there is 0 taker spread walk.
  - If `live_p == price`, at $p = 0.04$ and $\text{cash} = \$20$, $\text{depth\_bps} = 8.2 \text{ bps} = 0.00082$. $0.04 \times 1.00082 = 0.0400328$. `round(0.0400328, 4) = 0.0400`. The resulting `user_fill_price` equals `whale_entry_price`, resulting in `slippage_bps = 0.0`.

### 2.2 Branch 2: FIFO SELL Execution (Closing Open BUY Lots)
- **Files & Lines**: `backend/app/services/live_poller.py:633-691`, `742-812`, `693-715`, `813-836`
- **Observed Code**:
  ```python
  # Line 645
  price_ratio = ((effective_fill_price - orig_buy_price) / orig_buy_price) if orig_buy_price > 0 else 0.0
  # Line 651
  open_buy.realized_pnl_usd = round(buy_notional * price_ratio - (buy_fee + allocated_sell_fee), 2)
  # Line 701
  sys_log = ExecutionLog(..., side="SELL", whale_entry_price=price, user_fill_price=effective_fill_price, ...)
  ```
- **Analysis & Flaw**:
  - Suffers from the same rounding collapse on sell orders: `round(price * (1.0 - slippage_factor), 4)` collapses to `price` for low prices or small sizes, executing sells at 0 slippage.

### 2.3 Branch 3: Split Lots (FIFO Partial Lot Closes)
- **Files & Lines**: `backend/app/services/live_poller.py:666-688` (System), `786-809` (User)
- **Observed Code**:
  ```python
  # Lines 666-688
  split_buy = ExecutionLog(
      user_id=None,
      source_wallet_address=open_buy.source_wallet_address,
      market_condition_id=open_buy.market_condition_id,
      market_question=open_buy.market_question,
      event_slug=open_buy.event_slug,
      icon=open_buy.icon,
      side="BUY",
      whale_entry_price=open_buy.whale_entry_price,
      user_fill_price=open_buy.user_fill_price,
      resolution_outcome=open_buy.resolution_outcome,
      onchain_tx_hash=open_buy.onchain_tx_hash,
      onchain_log_index=open_buy.onchain_log_index,
      notional_usd=remaining_portion,
      fee_usd=round(max(0.0, orig_buy_fee - closed_buy_fee), 4),
      market_category=open_buy.market_category,
      active_basket_size_at_trade=open_buy.active_basket_size_at_trade,
      is_sandbox=True,
      status="FILLED",
      realized_pnl_usd=None,
      executed_at=open_buy.executed_at
      # NOTE: latency_ms is completely absent!
  )
  ```
- **Analysis & Flaw**:
  - `latency_ms` is NOT set in `split_buy`. In SQLAlchemy / SQLite / Postgres, this column becomes `NULL`, failing the requirement that 100% of execution logs have non-null `latency_ms`.
  - `split_buy` inherits `open_buy.user_fill_price`. If `open_buy` had 0 slippage, the remaining lot retains 0 slippage.

### 2.4 Branch 4: Out-of-Order Match Execution (Lagging BUY matching Pending SELL)
- **Files & Lines**: `backend/app/services/live_poller.py:472-596`
- **Observed Code**:
  ```python
  # Line 511-520 (System Out-of-Order SELL log)
  sys_sell_log = ExecutionLog(
      ...
      side="SELL",
      whale_entry_price=pending_sell_match.price,
      user_fill_price=pending_sell_match.price, # <--- HARDCODED 0 SLIPPAGE!
      ...
  )
  # Line 573-583 (User Out-of-Order SELL log)
  u_sell_log = ExecutionLog(
      ...
      side="SELL",
      whale_entry_price=pending_sell_match.price,
      user_fill_price=pending_sell_match.price, # <--- HARDCODED 0 SLIPPAGE!
      ...
  )
  ```
- **Analysis & Flaw**:
  - On the SELL leg of an out-of-order match, `user_fill_price` is directly assigned `pending_sell_match.price`.
  - Result: `slippage_bps = abs(pending_sell_match.price - pending_sell_match.price) == 0.0 bps`. 100% of out-of-order SELL legs bypass slippage modeling!

### 2.5 Branch 5: Onchain Signals (`process_onchain_signal`)
- **Files & Lines**: `backend/app/services/live_poller.py:879-923`
- **Observed Code**:
  ```python
  ts_sec = (timestamp_ms / 1000.0) if timestamp_ms else datetime.utcnow().timestamp()
  ...
  await self.process_trade_fill(
      wallet_address=wallet_address,
      condition_id="", # resolved from asset_id
      title="Polymarket Prediction",
      side=side.upper(),
      price=price,
      cash_usd=cash_usd,
      dt=dt,
      asset=asset_id,
      tx_hash=tx_hash,
      log_index=log_index
  )
  ```
- **Analysis & Flaw**:
  - Forwards into `process_trade_fill`. Inherits all rounding collapse and fallback zero-slippage flaws.
  - If `timestamp_ms` is slightly ahead of local machine time due to clock drift, `now_epoch_sec - trade_epoch_sec` can be $\le 0$, hitting `max(50.0, ...)` clamped to `180.0 ms`.

### 2.6 Branch 6: Binary Market Resolution Settlement
- **Files & Lines**: `backend/app/services/live_poller.py:1039-1169`
- **Analysis**:
  - Binary resolution settles positions against terminal payoff ($1.00 for winning outcome, $0.00 for losing outcome).
  - Payout PnL is computed from `user_fill_price`. If the opening BUY had zero slippage, the payout return is unrealistically high.

---

## 3. Order Book Walking & `fill_simulator.py` Audit

### Current Implementation (`backend/app/sizing/fill_simulator.py`):
```python
def simulate_fill(order_value_usd: float, order_book: dict, side: str, latency_ms: int = 1000) -> FillResult:
    is_buy = str(side).upper() == "BUY"
    raw_levels = order_book.get("asks" if is_buy else "bids", [])
    levels = sorted(raw_levels, key=lambda x: float(x.get("price", 0)), reverse=not is_buy)
    
    if not levels:
        return FillResult(avg_price=0.0, total_filled=0.0, slippage_pct=0.0, levels_consumed=0)
    ...
    best_price = float(levels[0].get("price", 0))
    ...
    if best_price > 0:
        slippage_pct = abs(avg_price - best_price) / best_price
    else:
        slippage_pct = 0.0
```

### Critical Flaws in `fill_simulator.py`:
1. **Single-Level Fill produces 0% Slippage**:
   - If `order_value_usd` $\le \text{Level 0 value}$, then `avg_price == best_price` $\Rightarrow$ `slippage_pct = 0.0`.
   - Real CLOB taker orders always cross the half-spread from the mid price and suffer adverse selection.
2. **Ignored `latency_ms` Parameter**:
   - `latency_ms` is accepted in the signature but completely unused in calculation.
3. **Empty Book / Malformed Book Handling**:
   - Returns 0 fills without an empirical liquidity fallback.

---

## 4. Mathematical and Algorithmic Specification

To guarantee **100% of fills execute with realistic CLOB depth and spread walk slippage (`slippage_bps > 0` and non-null `latency_ms`)**, we specify the following unified model:

```
+-----------------------------------------------------------------------------------+
|                        UNIVERSAL CLOB SLIPPAGE ENGINE                             |
|                                                                                   |
|  Inputs: price (p0), side (BUY/SELL), notional ($V), latency (tau), live_p (opt)  |
|                                                                                   |
|  1. Base Half-Spread Crossing:                                                    |
|     Spread_bps = max(6.0, 12.0 * (1.0 - 2.0 * |p0 - 0.5|))                        |
|                                                                                   |
|  2. CLOB Non-Linear Depth Walk:                                                   |
|     Depth_bps = 8.0 + min(40.0, (V / 1500.0)^0.75 * 25.0)                        |
|                                                                                   |
|  3. Latency Adverse Selection Drift:                                              |
|     Latency_bps = min(15.0, 5.0 * sqrt(tau / 350.0))                             |
|                                                                                   |
|  4. Total Basis Points:                                                           |
|     Total_bps = Spread_bps + Depth_bps + Latency_bps  (19.0 to 67.0 bps)          |
|                                                                                   |
|  5. Guaranteed Tick Floor (Anti-Rounding Collapse):                              |
|     raw_delta = p0 * (Total_bps / 10000.0)                                        |
|     min_delta = max(0.0005, p0 * 0.0010)                                          |
|     delta_p   = max(raw_delta, min_delta)                                         |
|                                                                                   |
|  6. Fill Price Output:                                                            |
|     BUY:  p_fill = min(0.995, max(0.005, round(p0 + delta_p, 4)))                 |
|           assert p_fill > p0  (Strict Inequality)                                 |
|     SELL: p_fill = max(0.005, min(0.995, round(p0 - delta_p, 4)))                 |
|           assert p_fill < p0  (Strict Inequality)                                 |
+-----------------------------------------------------------------------------------+
```

### Mathematical Properties & Invariants:
1. **Strict Monotonic Adverse Slippage**:
   - For all BUY executions: $p_{\text{fill}} > p_0 \iff \text{slippage\_bps} > 0$.
   - For all SELL executions: $p_{\text{fill}} < p_0 \iff \text{slippage\_bps} > 0$.
2. **Anti-Rounding Floor**:
   - Since $\delta p \ge 0.0005$, rounding to 4 decimal places guarantees $|p_{\text{fill}} - p_0| \ge 0.0005 > 0$.
   - Even at boundary prices ($p = 0.01$ or $p = 0.99$) and micro sizes ($V = \$1.00$), `round(p_fill, 4) != round(p_whale, 4)`.
3. **Bounded Latency Guarantee**:
   - $\tau_{\text{ms}} = \text{clamp}(\Delta t_{\text{ms}}, 180.0, 1400.0) \in [180.0, 1400.0]$.
   - Split lots inherit parent `latency_ms` (or $350.0\text{ ms}$ default if None).

---

## 5. Discovered Features & Edge Cases

## Features Discovered
| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Execution | Direct Market BUY | Simulates taker BUY on CLOB with depth/spread walk | `price, side="BUY", cash_usd, dt` | `user_fill_price > price, latency_ms` | Slippage exceeded $\to$ CANCEL | `live_poller.py:345` |
| 2 | Execution | FIFO SELL | Closes existing open BUY lots in FIFO sequence | `price, side="SELL", cash_usd, dt` | `user_fill_price < price, realized_pnl` | No open buy $\to$ queue OOO sell | `live_poller.py:633` |
| 3 | Execution | Split Lot Buy Retention | Preserves remaining open fraction when partially closed | `open_buy, remaining_notional` | `split_buy ExecutionLog` | Omitted latency_ms $\to$ NULL | `live_poller.py:666` |
| 4 | Execution | Out-of-Order Match | Matches lagging BUY with pending prior SELL | `pending_sell, lagging_buy` | Both closed with realized PnL | Hardcoded sell fill price $\to$ 0 bps | `live_poller.py:472` |
| 5 | Execution | Onchain Signal Ingestion | Ingests Envio HyperSync events and routes to fill poller | `asset_id, amount, price, tx_hash` | `ExecutionLog` written | Duplicate key $\to$ Deduplicate | `live_poller.py:879` |
| 6 | Execution | Binary Resolution Settlement | Settles open lots to $1.00 (win) or $0.00 (loss) | `condition_id, winning_outcome` | `status="CLOSED", payout` | Empty condition $\to$ skip | `live_poller.py:1039` |
| 7 | Sizing | CLOB Depth Fill Simulator | Walks L2 order book levels | `order_value, order_book, side` | `FillResult(avg_price, slippage)` | Empty book $\to$ 0 filled | `fill_simulator.py:10` |
| 8 | Sizing | Directional Slippage Check | Validates adverse slippage thresholds | `whale_price, current_price, side` | `EXECUTE_ORDER` / `CANCEL` | Price $\le 0 \to$ pass | `slippage.py:3` |
| 9 | Sizing | Simulated Fill Price Engine | Computes depth and spread slippage price | `price, side, notional_usd, live_p` | `sim_price` | Unused in poller $\to$ inline dup | `slippage.py:29` |
| 10 | Fees | Polymarket Quadratic Fees | Computes category fee $\Theta \cdot \text{Notional} \cdot (1-p)$ | `notional, price, title, is_maker` | `fee_usd, category, rate` | Clamp $p \in [0.001, 0.999]$ | `polymarket_fees.py:96` |
| 11 | Fees | Fee-Aware EV Gate | Checks if expected edge clears $2.5 \times \text{fee}$ | `price, market_title, edge` | `should_pass, fee_rate, min_edge`| Inverted edge at 0.50 | `polymarket_fees.py:138` |

## Edge Cases
| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Direct Market BUY | $p = 0.04$, $\text{notional} = \$20$ | `round(0.04 * (1 + 0.00082), 4) == 0.0400` $\to$ Zero Slippage Collapse |
| 2 | Out-of-Order SELL | Whale sold @ $0.65$, BUY arrived later @ $0.50$ | `sys_sell_log.user_fill_price = 0.65` $\to$ 0.0 bps slippage on SELL leg |
| 3 | Split Lot Creation | Partial sell closes $\$60$ of $\$100$ lot | `split_buy` has `latency_ms = None` (NULL in database) |
| 4 | Fill Simulator Level 0 | Order $\$25$ in $\$50$ Level 0 book | `avg_price == best_price` $\to$ `slippage_pct = 0.0` (ignores taker spread) |
| 5 | Extreme Low Boundary | $p = 0.005$, $\text{notional} = \$5$ | Must enforce min delta $\ge 0.0005 \implies p_{\text{fill}} = 0.0055$ |
| 6 | Extreme High Boundary | $p = 0.990$, $\text{notional} = \$500$ | Must enforce min delta $\ge 0.0005 \implies p_{\text{fill}} = 0.9950$ (capped at $0.995$) |
| 7 | Asynchronous Latency Lag | Trade timestamp $5\text{s}$ in past | $\tau_{\text{ms}} = \min(1400.0, 5000.0) = 1400.0\text{ ms}$ |
| 8 | Inverted Book | Asks `[0.60, 0.30, 0.45]` | Sorted to `[0.30, 0.45, 0.60]` before walking |

---

## 6. Comprehensive Implementation Plan for Engineering Agent

### File 1: `backend/app/sizing/slippage.py`
1. Replace `calculate_simulated_fill_price` with the robust Universal CLOB model:
   - Accept `price: float, side: str, notional_usd: float = 100.0, latency_ms: float = 350.0, live_p: Optional[float] = None`.
   - Calculate `Spread_bps`, `Depth_bps`, `Latency_bps`.
   - Apply guaranteed `min_delta = max(0.0005, price * 0.0010)`.
   - Enforce strict inequality: $p_{\text{fill}} > \text{price}$ for BUY, $p_{\text{fill}} < \text{price}$ for SELL.
   - Return 4-decimal rounded float.

### File 2: `backend/app/services/live_poller.py`
1. **Replace Inline Slippage Calculation**:
   - In lines 342-354, delete the ad-hoc inline math.
   - Call `calculate_simulated_fill_price(price=price, side=side, notional_usd=sys_notional, latency_ms=calc_latency_ms, live_p=live_p)`.
2. **Fix Out-of-Order SELL Leg**:
   - In lines 473-596, calculate `sell_fill_price = calculate_simulated_fill_price(price=pending_sell_match.price, side="SELL", notional_usd=sys_notional, latency_ms=calc_latency_ms)`.
   - Use `sell_fill_price` in `sys_sell_log.user_fill_price` and `u_sell_log.user_fill_price` (and in PnL calculation).
3. **Fix Split Lot Missing `latency_ms`**:
   - In line 687 (`split_buy`) and line 807 (`u_split_buy`), explicitly populate `latency_ms=open_buy.latency_ms or calc_latency_ms or 350.0`.

### File 3: `backend/app/sizing/fill_simulator.py`
1. Update `simulate_fill` to apply a base taker half-spread and latency penalty:
   - When order fits within level 0, apply half-spread ($S_{\text{half}} \ge 5\text{ bps}$) so `slippage_pct > 0.0`.
   - Apply `latency_ms` adverse selection penalty.

### File 4: Test Suite in `backend/tests/`
1. Create `backend/tests/test_universal_slippage_r1.py`:
   - Test 1: Invariant test verifying `slippage_bps > 0` across all 5 branches (BUY, FIFO SELL, Split Lots, Out-of-Order SELL/BUY, Onchain).
   - Test 2: Invariant test verifying `latency_ms is not None` across all execution logs in DB.
   - Test 3: Anti-rounding collapse test for micro prices ($0.01, 0.04, 0.05$) and micro sizes ($\$5, \$10$).
   - Test 4: Monotonic scaling test (larger order size $\implies$ higher slippage).
