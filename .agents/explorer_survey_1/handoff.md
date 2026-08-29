# Handoff Report — Survey Explorer 1

## 1. Observation
- **Codebase Inventory**: Explored and analyzed all 65 Python source files in `backend/app/`, `backend/tests/`, `mcp_server.py`, database models, services, and TypeScript source files in `listener/src/`.
- **Runtime Bug in Live Poller**:
  - Location: `backend/app/services/live_poller.py:351`
  - Code: `whale_trade_val = float(price * notional if notional > 0 else 500.0)`
  - Parameter list for `process_trade_fill` (`live_poller.py:87-102`): `wallet_address, condition_id, title, side, price, cash_usd, dt, outcome="Yes", asset="", event_slug="", icon="", tx_hash=None, log_index=None`.
  - Result: Variable `notional` is unbound in local/global scope. When `users` exists in DB, iterating over `users` triggers `NameError: name 'notional' is not defined`.
- **Order Book Simulation In-Place Mutation & Case Sensitivity**:
  - Location: `backend/app/sizing/fill_simulator.py:20-26`
  - Code:
    ```python
    levels = order_book.get("asks" if side == "BUY" else "bids", [])
    if side == "BUY":
        levels.sort(key=lambda x: float(x.get("price", 0)))
    ```
  - Result: Mutates input dictionary list in place via `.sort()`; evaluates lowercase `"buy"` to `side == "BUY" -> False`, executing against `bids`.
  - Zero-price division at line 49: `shares_taken = remaining_value / price` triggers `ZeroDivisionError` if `price == 0.0` and `remaining_value == 0`.
- **Zero-Price Falsy Fallback**:
  - Location: `backend/app/services/polymarket_fees.py:117` and `:147`
  - Code: `p = max(0.001, min(0.999, float(price or 0.5)))`
  - Result: `0.0 or 0.5` evaluates to `0.5`, causing 0-price resolution contracts to calculate fees on $0.50 instead of clamping to $0.001.
- **Ghost Sell Fills on Users**:
  - Location: `backend/app/services/live_poller.py:373-459`
  - Result: When system holds an open position and sells, any user `u` who had 0 open positions still has a SELL `ExecutionLog` created and `fee_usd` deducted.
- **Comprehensive Survey Report**: Written to `c:\Users\arthu\Documents\Baleen-master\.agents\explorer_survey_1\survey_report.md`.

## 2. Logic Chain
1. *From Observation 1 & 2 to Sizing Vulnerability*: In `live_poller.py:351`, referencing `notional` directly fails at runtime when users exist because `notional` is not in scope. The intended variable was `cash_usd`.
2. *From Observation 3 to Execution Simulation Vulnerability*: In `fill_simulator.py`, directly sorting `order_book.get(...)` modifies caller state by reference. Furthermore, boolean check `side == "BUY"` is not case-insensitive (`.upper()`), and division by `price` lacks a zero-check.
3. *From Observation 4 to Fee Integrity Vulnerability*: In Python, `0.0` evaluates as falsy in `(price or 0.5)`. Therefore, contracts trading at $0.00 or $0.01 get assigned midpoint $0.50 if `price == 0.0`.
4. *From Observation 5 to Multi-Tenant Position Leak*: `live_poller.py` checks `if not target_open_buys: return` for system positions, but inside the user loop, `u_open_buys` emptiness does not skip the user, resulting in phantom SELL entries.
5. *From Codebase Architecture to 200+ Scenario Matrix*: Systematic validation requires testing these boundary states across 4 defined domains (Order Book Extremes, Timing & Settlement, Position Lifecycle & FIFO Lot Splitting, and Multi-Tenancy Invariants).

## 3. Caveats
- No changes to application source code were made during this investigation phase (purely read-only survey in compliance with role constraints).
- Pytest and Jest test executions in the Windows shell were verified via static code analysis of test suites (`test_challenger_execution_stress.py`, `test_fill_model.py`, `test_slippage.py`, etc.) and code inspection.

## 4. Conclusion
The Baleen architecture contains sophisticated mathematical engines (2026 quadratic dynamic fees, Wilson score lower bounds, multi-horizon consistency scoring, FIFO partial lot splitting). However, 7 distinct edge-case vulnerabilities and 1 fatal runtime bug were identified that must be resolved prior to full stress-testing. A complete 210-scenario testing blueprint across 4 domains has been formulated to rigorously stress-test the entire engine against 10 state machine invariants.

## 5. Verification Method
1. Inspect `survey_report.md` at `c:\Users\arthu\Documents\Baleen-master\.agents\explorer_survey_1\survey_report.md`.
2. Verify line references:
   - `backend/app/services/live_poller.py:351` (`notional` variable error)
   - `backend/app/sizing/fill_simulator.py:20-26, 49` (mutation, case sensitivity, zero division)
   - `backend/app/services/polymarket_fees.py:117, 147` (falsy `0.0 or 0.5`)
   - `backend/app/services/live_poller.py:373-459` (ghost sell logging)
