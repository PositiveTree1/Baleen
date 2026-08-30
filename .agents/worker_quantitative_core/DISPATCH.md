## 2026-08-31T00:36:47Z

You are Worker: Quantitative Core Engineer.
Working directory: c:\Users\arthu\Documents\Baleen-master\.agents\worker_quantitative_core
Original Request: c:\Users\arthu\Documents\Baleen-master\.agents\ORIGINAL_REQUEST.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Background & Specifications:
Read the comprehensive survey and mathematical specifications from the 3 survey explorers:
- `c:\Users\arthu\Documents\Baleen-master\.agents\explorer_survey_r1\analysis.md` (R1 CLOB Slippage)
- `c:\Users\arthu\Documents\Baleen-master\.agents\explorer_survey_r2\analysis.md` (R2 Bayesian Sleeve Sizing)
- `c:\Users\arthu\Documents\Baleen-master\.agents\explorer_survey_r3\analysis.md` (R3 Portfolio MTM Synchronization)

Task:
Implement the core quantitative engineering fixes across the codebase:

1. **R1: Universal CLOB Fill Slippage & Latency Modeling**:
   - In `backend/app/sizing/slippage.py`:
     Implement/refine `calculate_simulated_fill_price` to combine base half-spread (>= 6 bps), depth impact (<= 40 bps), and latency drift (<= 15 bps), with an absolute minimum tick floor delta_min = max(0.0005, price * 0.0010). Ensure effective fill price is strictly greater than whale price on BUY (p_fill > p_whale) and strictly less on SELL (p_fill < p_whale) with `slippage_bps > 0.0` on 100% of executions, and non-null `latency_ms in [180.0, 1400.0]`.
   - In `backend/app/sizing/fill_simulator.py`:
     Ensure multi-level and single-level order book matches incorporate spread/latency slippage floor so `slippage_pct > 0` and non-null `latency_ms` are universally guaranteed.
   - In `backend/app/services/live_poller.py`:
     Route ALL execution branches (direct buys, FIFO sells, split lots, out-of-order matches at lines 519/582, onchain signals) through the unified slippage and latency calculation. Eliminate hardcoded whale price copies on OOO SELL legs. Ensure `split_buy` at lines 666-688 includes `latency_ms`.

2. **R2: Sample-Size Damped Dynamic Sleeve Budget Sizing**:
   - In `backend/app/sizing/sleeve_manager.py`:
     Implement the continuous two-stage Bayesian credibility function Z(N):
     Z(N) = (1/7) * (N / 15) for 0 <= N < 15
     Z(N) = (1/7) + (6/7) * ((N - 15) / ((N - 15) + 20.0)) for N >= 15
     Anchor low-sample whales (N < 15, e.g. N=1, 2, 5) within $900.00 - $1,100.00 (+/- 10% of $1,000 base) under all extreme PnL or score shocks. Clip single-trade innovations to +/- $500.00 for smooth EMA scaling. Maintain backward compatibility where `trades_count=None` defaults to full credibility (Z=1.0).
   - In `backend/app/services/live_poller.py`:
     Pass wallet trade count `trades_count` and `baleen_score` to `SleeveManager.calculate_adjusted_sleeve_budget`.

3. **R3: Portfolio Timeframe & Net Worth Synchronization**:
   - In `backend/app/services/mark_to_market.py`:
     Ensure mark-to-market valuations do not markdown open positions to `-fee` when prices are being loaded. Ensure single authoritative snapshot generation.
   - In `backend/app/api/execution_logs.py`:
     Ensure `/api/executions/snapshots` returns consistent net worth across `1H`, `1D`, `1W`, and `ALL` timeframes with consistent Genesis alignment and last-of-bucket sampling.

4. **Build & Test Verification**:
   - Run full pytest test suite:
     `& "c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\python.exe" -m pytest`
   - Verify all tests pass with 100% success rate.
   - Update any tests if signature additions require backwards-compatible parameters.
