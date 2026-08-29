# Handoff Report — Explorer Survey 3

## 1. Observation
- **Codebase Scope**: Directly inspected all backend Python services (`backend/app/`), database models (`backend/app/models.py`), migration mechanisms (`backend/app/database.py`), execution mirror (`backend/app/services/live_poller.py`), mark-to-market engine (`backend/app/services/mark_to_market.py`), fee engine (`backend/app/services/polymarket_fees.py`), sizing and fill models (`backend/app/sizing/`), scoring filters (`backend/app/scoring/`), discovery pipeline (`backend/app/discovery/`), and listener services (`listener/src/`).
- **Data Models & Schema**:
  - `ExecutionLog` (`backend/app/models.py:107-139`) enforces `UniqueConstraint('onchain_tx_hash', 'onchain_log_index', 'user_id', name='uix_tx_log_user')` and `CheckConstraint(side.in_(['BUY', 'SELL']))`.
  - `User` (`backend/app/models.py:79-94`) tracks `sandbox_starting_balance_usd`, `sandbox_balance_usd`, `sandbox_high_water_mark_usd`, `live_trading_enabled`, `risk_profile`.
  - `Wallet` (`backend/app/models.py:37-68`) tracks `status` ('pending'|'active'|'rejected'), `tier` ('gold_sniper'|'standard'), `all_time_pnl_usd`, `win_rate_pct`, `wilson_lb`, `dormant`, `is_hft`.
- **Cash & Margin Invariance**:
  - `backend/app/services/live_poller.py:228-260`: Free cash calculation implements:
    ```python
    current_open_notional = float((await db.execute(stmt_active_notional)).scalar() or 0.0)
    total_realized_pnl = float((await db.execute(stmt_realized_pnl)).scalar() or 0.0)
    settled_cash = 10000.0 + total_realized_pnl
    free_cash = max(0.0, settled_cash - current_open_notional)
    if free_cash < 10.0:
        return # Skips BUY
    sys_notional = round(min(sys_notional, free_cash), 2)
    ```
- **FIFO Partial Liquidations & Lot Splitting**:
  - `backend/app/services/live_poller.py:270-324`: Loops over `target_open_buys`. For full close, sets `status='CLOSED'`, calculates net realized PnL subtracting buy fee and allocated sell fee. For partial close, modifies original record to `closed_portion` and inserts a new `split_buy` with `remaining_portion` and remaining fee, preserving lot notional and fee conservation.
- **Polymarket 2026 Quadratic Fees**:
  - `backend/app/services/polymarket_fees.py:1-154`: Formula `Fee = Theta * Notional * (1 - p)` across 6 categories: Crypto ($\Theta=0.072$), Economics ($\Theta=0.060$), Culture/Tech ($\Theta=0.050$), Politics ($\Theta=0.040$), Sports ($\Theta=0.030$), Geopolitics ($\Theta=0.000$). Quantized via `ROUND_HALF_EVEN` to $\$0.01$.
- **Vulnerabilities Discovered**:
  - Double-counting hazard in user realized PnL if `u_realized_pnl_val` is attached to both BUY and SELL records (`backend/app/services/live_poller.py:411` vs `backend/app/services/mark_to_market.py:240`).
  - In-place mutation hazard in `backend/app/sizing/fill_simulator.py:24-26` sorting caller's list.
  - Case-sensitivity hazard in `backend/app/sizing/fill_simulator.py:20` matching bids on lowercase `'buy'`.
  - Math domain underflow in `calc_wilson_lower_bound` on unconstrained negative/overflow inputs (`challenge_math_concurrency.py:64-73`).

## 2. Logic Chain
1. *Observation*: The core execution pipeline relies on `LiveTradeMirrorService.process_trade_fill` (`backend/app/services/live_poller.py`) and `MarkToMarketService.update_valuations_and_consensus` (`backend/app/services/mark_to_market.py`).
2. *Deduction*: Any mismatch between settled cash tracking (`10000.0 + total_realized_pnl`) and open margin (`sum(notional_usd)`) directly alters trade sizing and cash solvency.
3. *Observation*: `live_poller.py` bounds `sys_notional` by `free_cash` for the platform level, but in lines 349-364 sizes user copy orders against `u.sandbox_balance_usd` without deducting open user margin.
4. *Deduction*: Under high unrealized floating gains, individual user copy sizes could exceed available settled cash unless clamped by individual free cash.
5. *Observation*: FIFO lot splitting in lines 289-324 exactly allocates `closed_buy_fee` and remaining fee `open_buy.fee_usd - closed_buy_fee`, maintaining exact share and dollar conservation.
6. *Conclusion*: The architecture supports full 200+ edge-case stress modeling once the identified edge-case vulnerabilities (MTM free-cash inflation, in-place sort mutation, and case sensitivity) are handled in the test harnesses and regression suites.

## 3. Caveats
- Production deployment on Render vs local testing was verified via code inspection of `backend/app/database.py` (which detects `RENDER` environment variables and prevents silent degradation to SQLite in production).
- Live HyperSync network latency and RPC timeouts depend on Polygon RPC availability, but the HTTP query fallback and rate limiting in `listener/src/hypersync.ts` (1.6s catch-up, 4.5s tip polling) are robustly engineered.
- AI Whale Summary generation utilizes Groq API with deterministic fallback strings if rate-limited or unconfigured.

## 4. Conclusion
The Baleen architecture is fully mapped, with all source files, classes, functions, accounting rules, state machines, and mathematical formulations forensically documented in `survey_report.md`. The codebase demonstrates strong mathematical foundations in 2026 quadratic fees, Wilson lower bound scoring, and FIFO lot splitting, while presenting clear opportunities for automated scenario stress-testing across order book depth extremes, network latency, interleaved multi-outcome trades, and multi-tenancy risk scaling.

## 5. Verification Method
- **Report Verification**: Inspect `c:\Users\arthu\Documents\Baleen-master\.agents\explorer_survey_3\survey_report.md`.
- **Codebase Verification**: Inspect referenced line numbers in `backend/app/services/live_poller.py`, `backend/app/services/mark_to_market.py`, `backend/app/services/polymarket_fees.py`, and `backend/app/sizing/fill_simulator.py`.
- **Test Suite Verification**: Execute `pytest backend/tests` once Python test runner environment is initialized.
