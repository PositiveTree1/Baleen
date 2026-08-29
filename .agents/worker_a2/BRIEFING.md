# BRIEFING — 2026-08-29T12:00:32Z

## Mission
Execute fixes in `live_poller.py` (FIFO partial split fee caching & user sell no-open-buys guard) and `mark_to_market.py` (HWM monotonic ratcheting), verify with pytest, and generate a handoff report.

## 🔒 My Identity
- Archetype: implementer
- Roles: implementer, qa, specialist
- Working directory: c:\Users\arthu\Documents\Baleen-master\.agents\worker_a2
- Original parent: 980dffcb-98f6-47fd-9529-c31fd4fe4c24
- Milestone: M-A2 FIFO partial split fixes & MTM HWM fix

## 🔒 Key Constraints
- Genuine implementations only; no hardcoding or dummy test results.
- Only modify what is required according to the minimal change principle.
- Verify using pytest on `backend/tests`.
- Write handoff.md and send message to parent upon completion.

## Current Parent
- Conversation ID: 980dffcb-98f6-47fd-9529-c31fd4fe4c24
- Updated: not yet

## Task Summary
- **What to build**:
  1. Fix `backend/app/services/live_poller.py`:
     - Platform FIFO partial split fee calculation: cache original fee before mutating `open_buy.fee_usd`.
     - User FIFO partial split fee calculation: cache original fee before mutating `u_open_buy.fee_usd`.
     - User copy trade SELL loop: skip user if `not u_open_buys` with logging.
  2. Fix `backend/app/services/mark_to_market.py`:
     - Verify/ensure HWM ratchets monotonically: `new_hwm = max(current_hwm, total_equity)`.
  3. Run pytest across `backend/tests`.
  4. Write handoff report.
- **Success criteria**: All tests pass, accurate FIFO fee conservation, monotonic HWM updates, clean handoff report.
- **Interface contracts**: PROJECT.md / SCOPE.md
- **Code layout**: `backend/app/services/`

## Key Decisions Made
- Follow precise task instructions for fee calculations and HWM math.

## Change Tracker
- **Files modified**: None yet
- **Build status**: Not run yet
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending
- **Lint status**: Clean
- **Tests added/modified**: Pending

## Loaded Skills
- None
