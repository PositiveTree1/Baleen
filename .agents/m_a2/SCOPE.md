# Scope: Milestone M-A2 — State Machine, FIFO Lot Splitting & Cash Invariance

## Objective
Implement and verify all fixes for:
1. `backend/app/services/live_poller.py`:
   - FIFO partial split fee zeroing bug (lines 296-315 and lines 410-428):
     Save `original_fee = float(open_buy.fee_usd or 0.0)` before updating `open_buy.fee_usd = round(closed_buy_fee, 4)`. Then compute `split_buy.fee_usd = round(original_fee - closed_buy_fee, 4)`.
   - Ghost SELL execution logs and unearned fee deductions on users holding 0 positions (lines 373-459):
     If `not u_open_buys`, the user has 0 matching open positions for this condition/outcome; skip creating a SELL ExecutionLog and do not deduct fees for this user.
2. `backend/app/services/mark_to_market.py`:
   - High-Water Mark floating gain inflation (lines 244-246):
     Ensure HWM ratchets monotonically strictly on verified total portfolio equity (`settled_cash + unrealized_pnl` if positive, or strictly settled profits) without phantom spikes.
3. Cash & Margin Invariance:
   - Ensure user copy sizing deducts open margin from settled balance (`user_free_cash = max(0.0, u.sandbox_balance_usd - u_open_margin)`).

## Verification Method
- Run pytest suite: `& "backend/.venv/Scripts/python.exe" -m pytest backend/tests`
- Verify with unit tests in `backend/tests/test_challenger_execution_stress.py` or new dedicated tests.
