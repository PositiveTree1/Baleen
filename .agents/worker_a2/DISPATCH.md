## 2026-08-29T12:00:32Z

You are Worker M-A2 for the Baleen Comprehensive Scenario Modeling & Stress-Testing Project.
Your Working Directory: c:\Users\arthu\Documents\Baleen-master\.agents\worker_a2
Your Scope File: c:\Users\arthu\Documents\Baleen-master\.agents\m_a2\SCOPE.md
Your Project File: c:\Users\arthu\Documents\Baleen-master\.agents\PROJECT.md
Your Request File: c:\Users\arthu\Documents\Baleen-master\.agents\ORIGINAL_REQUEST.md
Your Dispatch File: c:\Users\arthu\Documents\Baleen-master\.agents\worker_a2\DISPATCH.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Fix `backend/app/services/live_poller.py`:
   - In lines 296-315 (platform FIFO partial split), cache `orig_buy_fee = float(open_buy.fee_usd or 0.0)` before mutating `open_buy.fee_usd = round(closed_buy_fee, 4)`. Set `split_buy.fee_usd = round(max(0.0, orig_buy_fee - closed_buy_fee), 4)`.
   - In lines 410-428 (user copy FIFO partial split), apply the identical fix: cache `orig_u_fee = float(u_open_buy.fee_usd or 0.0)` before mutating `u_open_buy.fee_usd`, and set `u_split_buy.fee_usd = round(max(0.0, orig_u_fee - u_closed_buy_fee), 4)`.
   - In lines 373-459 (user copy trade loop for SELL): if `not u_open_buys`, log and skip the user to prevent ghost SELL execution logs and phantom fee deductions.
2. Fix `backend/app/services/mark_to_market.py`:
   - In lines 244-246, verify and ensure HWM ratchets monotonically: `new_hwm = max(current_hwm, total_equity)`.
3. Run pytest across `backend/tests` using: `& "backend/.venv/Scripts/python.exe" -m pytest backend/tests`
4. Write your handoff report to `c:\Users\arthu\Documents\Baleen-master\.agents\worker_a2\handoff.md` and send a message when complete.
