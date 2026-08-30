# Forensic Audit Handoff Report: Baleen Whale Copy-Trading Platform

**Agent**: `auditor_1` (Forensic Integrity Auditor)  
**Date**: 2026-08-30  
**Verdict**: **CLEAN**

---

## 1. Observation

Direct empirical evidence gathered across the codebase:

1. **Database & Data Cleanliness**:
   - `backend/app/database.py` initializes PostgreSQL / SQLite tables via `Base.metadata.create_all` without inserting synthetic or hardcoded wallet entries.
   - `backend/cleanup_fake.py` purged the 3 mock addresses from `add_whales.py`.
   - `backend/check_wallets.py` executed against the active database and returned `[]` (0 dummy wallets in storage).
   - `backend/app/main.py` line 68 contains `_auto_discovery_if_empty()` which autonomously discovers candidate whales from live Polymarket endpoints on fresh deployment.
2. **Polymarket Data API & CLOB Client (`polymarket_client.py`)**:
   - Discovers candidate whales via `/trades` (CASH $\ge \$2,000$), paginated `/leaderboard` (`ALL`, `MONTH`, `WEEK`), and `/markets` on Gamma API.
   - Fetches live order book `/book`, `/midpoint`, and `/price` with zero hardcoded JSON stubs in production routes.
3. **Calculation Integrity**:
   - `scanner.py` line 76 computes Wilson lower bound with 90% confidence ($z=1.645$).
   - `scanner.py` line 148 computes Sharpe ratio over historical return distributions.
   - `scanner.py` line 273 and `api/wallets.py` separate daily PnL into `won_usd >= 0` and `lost_usd <= 0`.
   - `services/polymarket_fees.py` computes dynamic quadratic fees $\Theta \times \text{Notional} \times (1 - p)$ across 6 categories with Banker's Rounding (`ROUND_HALF_EVEN`) and Fee-Aware EV gate ($2.5 \times \text{fee}$).
4. **Frontend Dual-Column Chart Hydration**:
   - `frontend/src/components/charts/DailyWinLossBarChart.tsx` renders two `<Bar>` components: `wonUsd` with `#00D09C` (gross won) and `lostUsd` with `#FF453A` (gross lost), centered on a zero baseline `ReferenceLine`.
   - `frontend/src/lib/api-client.ts` maps `won_usd` $\to$ `wonUsd` and `lost_usd` $\to$ `lostUsd`.
   - `frontend/src/components/dashboard/WalletDrawer.tsx` dynamically filters timeframes (`1W`, `1M`, `YTD`, `ALL`).
5. **Paper Trading State Machine & Invariants**:
   - `sizing/sleeve_manager.py` implements isolated $1,000 sleeve capacity, Conviction Percentile sizing, and copy-PnL EMA adaptation with strict anti-starvation capacity clipping (`actual_size = min(intended, sleeve_remaining)`).
   - `services/live_poller.py` handles out-of-order SELL matching with FIFO execution, prevents duplicate execution via `uix_tx_log_user` and on-chain tx deduplication, and closes lots upon binary market resolution with 0 negative balances.
6. **Automated Test & Build Execution**:
   - Backend `pytest`: **403 / 403 passed** in **14.19s** (`backend/.venv/Scripts/pytest.exe -v`).
   - Frontend `npm run build`: Exit code **0**, **0 TypeScript errors**, **0 ESLint errors**, all **10 routes** compiled (`C:\Program Files\nodejs\npm.cmd run build`).

---

## 2. Logic Chain

1. **Premise 1**: A system is free of data fabrication if database initialization contains no seed mocks, scratch files are unreferenced in production, and active discovery pulls from authentic external endpoints.
   - *Evidence*: `database.py` contains no mock inserts; `check_wallets.py` confirmed 0 mock wallets; `main.py` triggers live discovery on empty DB.
2. **Premise 2**: Mathematical calculations are authentic if formulas strictly match standard quantitative definitions and do not return hardcoded constants.
   - *Evidence*: Wilson LB, Sharpe ratio, and quadratic fee formulas match mathematical specifications and pass 403 boundary and stress test assertions.
3. **Premise 3**: Frontend data contracts are valid if the UI client consumes genuine backend fields and renders dual bars with the requested color specifications.
   - *Evidence*: `DailyWinLossBarChart.tsx` explicitly renders green `#00D09C` (`wonUsd`) and red `#FF453A` (`lostUsd`) with zero-baseline alignment and full timeframe responsiveness.
4. **Premise 4**: The execution engine is resilient if state transitions preserve financial invariants (no negative balances, no orphaned trades, accurate fee deductions, out-of-order SELL resolution).
   - *Evidence*: The 220-scenario state machine matrix and sleeve isolation tests in `test_massive_220_scenario_matrix.py` and `test_live_poller_m_a3.py` executed and passed 100%.

Therefore, the codebase satisfies all integrity criteria and contains zero integrity violations.

---

## 3. Caveats

- **External Live API Availability**: Tests mock HTTP responses at the network boundary using standard unit test fixtures (`unittest.mock`), while production modules (`polymarket_client.py`, `live_poller.py`) execute genuine HTTP requests against Polymarket APIs.
- **Node.js Environment**: On Windows execution, `C:\Program Files\nodejs` must be in `$env:PATH` for `npm.cmd` sub-processes to invoke `node.exe`.

---

## 4. Conclusion

**Verdict: CLEAN**

The entire Baleen whale copy-trading platform codebase is verified to be genuine, mathematically rigorous, well-tested, and fully integrated across backend services and Next.js frontend components.

---

## 5. Verification Method

To independently re-verify the forensic audit findings:

1. **Run Backend Test Suite**:
   ```powershell
   & "C:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\pytest.exe" -v
   ```
   *Expected*: 403 passed, 0 failed.

2. **Run Frontend Next.js Production Build**:
   ```powershell
   $env:PATH = "C:\Program Files\nodejs;" + $env:PATH
   cd "C:\Users\arthu\Documents\Baleen-master\frontend"
   & "C:\Program Files\nodejs\npm.cmd" run build
   ```
   *Expected*: Exit code 0, 0 TypeScript errors, 10 routes generated.

3. **Verify Database Cleanliness**:
   ```powershell
   & "C:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\python.exe" "C:\Users\arthu\Documents\Baleen-master\backend\check_wallets.py"
   ```
   *Expected*: `[]` (clean database, 0 fake wallets).
