# Handoff Report — Challenger 1: Slippage & Latency Stress Tester

**Target Requirement**: Requirement 1 (R1) — Universal 100% Polymarket CLOB Fill Slippage Modeling  
**Date**: 2026-08-31T00:46:00Z  
**Verdict**: **`REJECT`** (Empirical boundary invariant violations identified at $p=0.999$ BUY and $p=0.001$ SELL, plus `NoneType` order book crash vulnerability)

---

## 1. Observation

Direct empirical and adversarial stress testing was performed on `backend/app/sizing/slippage.py`, `backend/app/sizing/fill_simulator.py`, and `backend/app/services/live_poller.py` using `backend/tests/test_challenger_r1_slippage_latency_empirical.py` and generative sweeps.

### Observed Behavior:

1. **Boundary Zero-Slippage Collapse at $p = 0.999$ (BUY)**:
   - Tool execution: `calculate_simulated_fill_price(price=0.999, side="BUY", notional_usd=100.0, latency_ms=350.0)`
   - Output returned: `0.999`
   - Invariant check: `user_fill_price > whale_entry_price` evaluates to `0.999 > 0.999` -> `False`.
   - Delta check: `abs(0.999 - 0.999) = 0.0000 < 0.0005` -> `False`.
   - Slippage bps: `((0.999 - 0.999) / 0.999) * 10000.0 = 0.0 bps` (fails invariant `slippage_bps > 0.0`).

2. **Boundary Zero-Slippage Collapse at $p = 0.001$ (SELL)**:
   - Tool execution: `calculate_simulated_fill_price(price=0.001, side="SELL", notional_usd=100.0, latency_ms=350.0)`
   - Output returned: `0.001`
   - Invariant check: `user_fill_price < whale_entry_price` evaluates to `0.001 < 0.001` -> `False`.
   - Delta check: `abs(0.001 - 0.001) = 0.0000 < 0.0005` -> `False`.
   - Slippage bps: `((0.001 - 0.001) / 0.001) * 10000.0 = 0.0 bps` (fails invariant `slippage_bps > 0.0`).

3. **`NoneType` Crash in `simulate_fill` on Null API Payloads**:
   - Tool execution: `simulate_fill(order_value_usd=100.0, order_book={"asks": None}, side="BUY")`
   - Output: `TypeError: 'NoneType' object is not iterable` at line 22 of `backend/app/sizing/fill_simulator.py`.

4. **Robust Performance across $p \in [0.002, 0.998]$ and all 5 Execution Paths**:
   - Across 2,397 unit/scenario/adversarial tests:
     - Direct Buys: `user_fill_price > whale_entry_price` passed across 100% of non-boundary executions.
     - FIFO Sells: `user_fill_price < whale_entry_price` passed across 100% of non-boundary executions.
     - Split Lots: Split child `ExecutionLog` records properly inherited positive fill prices and authentic non-null `latency_ms`.
     - Out-of-Order Matches: Both buy and sell sides generated simulated fills with positive slippage.
     - Onchain Signals: Authentically calculated timestamp deltas produced latency in $[180.0, 1400.0]$ ms.
     - Monotonic scaling: Verified that slippage increases monotonically with notional ($\$0.01$ to $\$100,000$) and latency ($180$ to $1400$ ms).

---

## 2. Logic Chain

1. **R1 Mandate**: R1 requires universal, 100% non-zero CLOB fill slippage modeling across all prices $p \in [0.001, 0.999]$, guaranteeing `slippage_bps > 0.0`, `user_fill_price > whale_entry_price` on BUY, `user_fill_price < whale_entry_price` on SELL, and `abs(user_fill_price - whale_entry_price) >= 0.0005`.
2. **Root Cause of BUY Collapse ($p = 0.999$)**:
   In `backend/app/sizing/slippage.py`, lines 77-80:
   ```python
   if p_fill <= p0:
       p_fill = min(0.995, round(p0 + min_delta, 4))
   if p_fill <= p0:
       p_fill = min(0.999, p0 + 0.0005)
   ```
   When `p0 = 0.999`, `p0 + 0.0005 = 0.9995`. `min(0.999, 0.9995)` clamps `p_fill` back down to `0.999`. Line 81 returns `0.999`, which equals `p0`.
3. **Root Cause of SELL Collapse ($p = 0.001$)**:
   In `backend/app/sizing/slippage.py`, lines 86-89:
   ```python
   if p_fill >= p0:
       p_fill = max(0.005, round(p0 - min_delta, 4))
   if p_fill >= p0:
       p_fill = max(0.001, p0 - 0.0005)
   ```
   When `p0 = 0.001`, `p0 - 0.0005 = 0.0005`. `max(0.001, 0.0005)` clamps `p_fill` back up to `0.001`. Line 90 returns `0.001`, which equals `p0`.
4. **Root Cause of `simulate_fill` Null Payload Crash**:
   In `backend/app/sizing/fill_simulator.py`, line 19:
   ```python
   raw_levels = order_book.get("asks" if is_buy else "bids", [])
   ```
   When `order_book = {"asks": None}`, `"asks"` exists with value `None`, so `get()` returns `None` instead of `[]`. Line 22 calls `sorted(raw_levels)` on `None`, crashing with `TypeError`.
5. **Inference**: Because the boundary extremes $p = 0.999$ (BUY) and $p = 0.001$ (SELL) violate the invariant `slippage_bps > 0.0` and produce zero-slippage executions, Requirement 1 is not 100% mathematically airtight at the outer boundary edges.

---

## 3. Caveats

- In live production Polymarket trading, prices of $0.999$ and $0.001$ represent extreme boundary contracts ($99.9\%$ and $0.1\%$ implied probability), which are frequently filtered out by the frontrunning/arbitrage bot filter (`boundary_snipe_counts` for $p \le 0.02$ or $p \ge 0.98$).
- For the entire standard operating regime $p \in [0.002, 0.998]$, the slippage modeling, fee structures, and latency calculations are fully compliant and 100% pass across all 2,397 tests.

---

## 4. Conclusion

**Verdict: `REJECT`**

### Summary of Deficiencies:
1. **Zero Slippage at $p = 0.999$ BUY**: Clamping cap in `calculate_simulated_fill_price` returns `0.999`, violating `p_fill > p_whale`.
2. **Zero Slippage at $p = 0.001$ SELL**: Clamping floor in `calculate_simulated_fill_price` returns `0.001`, violating `p_fill < p_whale`.
3. **`NoneType` Crash in `simulate_fill`**: Passing `{"asks": None}` crashes `sorted()`.

### Recommended Fixes for Implementation Team:
1. In `backend/app/sizing/slippage.py`:
   - For BUY: Allow `p_fill` to reach `0.9995` or clamp to `1.000` (or if capped at `0.999`, cap `p0` at `0.9985` so `p_fill` is always $> p0$).
   - For SELL: Allow `p_fill` to reach `0.0005` or `0.0001` (so `p_fill` is always $< p0$).
2. In `backend/app/sizing/fill_simulator.py`:
   - Change `raw_levels = order_book.get("asks" if is_buy else "bids", [])` to:
     `raw_levels = order_book.get("asks" if is_buy else "bids") or []`

---

## 5. Verification Method

To independently reproduce and verify all findings:
```powershell
# 1. Run the empirical challenger test suite
.\.venv\Scripts\pytest.exe tests\test_challenger_r1_slippage_latency_empirical.py -v

# 2. Run the boundary proof script directly
.\.venv\Scripts\python.exe -c "from app.sizing.slippage import calculate_simulated_fill_price; print('BUY 0.999:', calculate_simulated_fill_price(0.999, 'BUY')); print('SELL 0.001:', calculate_simulated_fill_price(0.001, 'SELL'))"

# 3. Run the full regression test suite
.\.venv\Scripts\pytest.exe
```
