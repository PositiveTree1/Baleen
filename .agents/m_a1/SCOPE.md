# Scope: Milestone M-A1 — Core Execution & Order Book Robustness

## Objective
Implement and verify all fixes for:
1. `backend/app/sizing/fill_simulator.py`:
   - Non-mutating order book sorting (copy levels or sort key without modifying caller dictionary).
   - Case-insensitive side handling (`side.upper() == "BUY"`).
   - Zero-division guard on zero-price levels in lines 45-55 (`price > 0`).
2. `backend/app/services/polymarket_fees.py`:
   - Zero-price contract falsy fallback bug in lines 117 & 147: `p = max(0.001, min(0.999, float(price) if price is not None else 0.5))` ensuring `0.0` maps to `0.001` rather than falling back to `0.5`.
3. `backend/app/services/live_poller.py`:
   - Line 351: Fix unbound variable `notional` by using `cash_usd` (`whale_trade_val = float(cash_usd if cash_usd > 0 else 500.0)`).

## Verification Method
- Execute pytest on `backend/tests/test_fill_model.py`, `backend/tests/test_slippage.py`, `backend/tests/test_polymarket_fees.py`, `backend/tests/test_challenger_execution_stress.py`.
- Run full pytest suite across `backend/tests`.
