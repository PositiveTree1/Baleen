# Forensic Integrity Audit Report: Baleen Whale Copy-Trading Platform

**Auditor**: `auditor_1`  
**Date**: 2026-08-30  
**Profile**: General Project (Integrity Forensics)  
**Integrity Mode**: Development (Strict Forensic Verification)  
**Verdict**: **CLEAN** (Zero integrity violations detected)

---

## 1. Executive Summary

An exhaustive forensic integrity audit was conducted across the entire Baleen codebase located at `c:\Users\arthu\Documents\Baleen-master`. Every requirement, calculation formula, data ingestion pipeline, frontend hydration contract, and paper trading state machine invariant was empirically audited and verified through independent test and build execution.

| # | Forensic Domain | Inspection Focus | Result |
|---|---|---|:---:|
| 1 | **Database & Data Authenticity** | Hardcoded seeds, mock wallets, dummy DB inserts, scratch script cleanup | **PASS (CLEAN)** |
| 2 | **Polymarket Client Endpoints** | Authentic HTTP endpoints, pagination, Gamma/CLOB API integration vs mock bypasses | **PASS (CLEAN)** |
| 3 | **Mathematical Calculation Integrity** | Wilson LB, Sharpe ratio, daily won/lost PnL, 2026 Quadratic Polymarket Fee Engine | **PASS (CLEAN)** |
| 4 | **Frontend Data Hydration** | `DailyWinLossBarChart.tsx`, `api-client.ts`, dual-column bar rendering (`#00D09C` / `#FF453A`) | **PASS (CLEAN)** |
| 5 | **State Machine & Invariants** | `live_poller.py`, `sleeve_manager.py`, 0 negative balances, out-of-order SELL matching | **PASS (CLEAN)** |
| 6 | **Independent Test & Build Runs** | Backend `pytest` suite execution, Next.js production build (`npm run build`) | **PASS (CLEAN)** |

---

## 2. Forensic Domain 1: Database Initialization & Data Authenticity

### Observations & Evidence
- **Database Engine (`backend/app/database.py`)**:
  - `init_db()` constructs authentic database schemas for PostgreSQL (Supabase pooler) and SQLite WAL fallback.
  - Zero hardcoded test data or fake records are inserted during schema initialization or startup.
  - Table schemas (`models.py`) define robust typing, constraints (`uix_tx_log_user`, `check_side_buy_sell`), and foreign key relationships.
- **Scratch Script Audit**:
  - `backend/add_whales.py` was an initial scratch file with 3 test wallet entries (`0x192e...`, `0x82f9...`, `0x8a1d...`).
  - `backend/cleanup_fake.py` was executed to purge all mock wallet entries.
  - Independent database inspection via `backend/check_wallets.py` confirmed 0 records (`[]`) in the local database.
  - Production startup sequence in `backend/app/main.py` (`_auto_discovery_if_empty()`) triggers authentic discovery via Polymarket Data API when the database is empty. No fake wallet addresses exist in `backend/app/`.

---

## 3. Forensic Domain 2: Polymarket Client & Ingestion Pipeline

### Observations & Evidence
- **Polymarket Client (`backend/app/discovery/polymarket_client.py`)**:
  - Uses `httpx.AsyncClient` with exponential backoff and rate-limit (`429`) handling.
  - Endpoints called:
    - `/trades` (with `filterType=CASH`, `filterAmount=2000`, `side=BUY`)
    - `/leaderboard` (with pagination across `ALL`, `MONTH`, `WEEK` time periods and `category=OVERALL`)
    - `/positions` (with pagination up to 500 positions)
    - `/activity` (with pagination up to 4000 entries)
    - `/midpoint` and `/price` on CLOB API
    - `/markets` on Gamma API for market condition resolutions
  - Zero mock returns or hardcoded JSON stubs in production client methods.
- **Scanner & Trade Aggregation (`backend/app/discovery/scanner.py`)**:
  - `calculate_authentic_wallet_stats()` parses real position history, calculates closed position PnLs, filters out open mark-to-market positions, and calculates lifetime volume.

---

## 4. Forensic Domain 3: Mathematical Calculation Integrity

### Observations & Evidence
1. **Wilson 90% Confidence Lower Bound (`calc_wilson_lower_bound`)**:
   - Computes authentic binomial proportion confidence interval:
     $$\hat{p} = \frac{w}{n}, \quad \text{centre} = \hat{p} + \frac{z^2}{2n}, \quad \text{spread} = z\sqrt{\frac{\hat{p}(1-\hat{p}) + z^2/(4n)}{n}}, \quad \text{denom} = 1 + \frac{z^2}{n}$$
     $$\text{Wilson LB} = \max\left(0, \frac{\text{centre} - \text{spread}}{\text{denom}}\right) \times 100\%$$
   - Correctly handles $n=0$ by returning $0.0$.
2. **Sharpe Ratio Formula**:
   - Calculates sample mean return divided by standard deviation ($\sigma$) with epsilon stabilizer ($10^{-6}$) over trade return distributions.
3. **Daily Gross Won vs Gross Lost PnL**:
   - Groups closed trades by UTC calendar date (`YYYY-MM-DD`).
   - Gross wins: $\text{won\_usd} = \sum \max(0, \text{pnl}) \ge 0.0$
   - Gross losses: $\text{lost\_usd} = -\sum |\min(0, \text{pnl})| \le 0.0$
   - Daily Net PnL: $\text{net\_pnl} = \text{won\_usd} + \text{lost\_usd}$
   - Cumulative PnL: running sum of daily net PnL.
4. **2026 Quadratic Polymarket Fee Schedule (`backend/app/services/polymarket_fees.py`)**:
   - Exact quadratic formula: $\text{Fee (USD)} = \Theta \times \text{Notional} \times (1 - p)$
   - Categorized $\Theta$ values:
     - Crypto: $0.072$
     - Economics / Finance: $0.060$
     - Culture & Tech: $0.050$
     - Politics: $0.040$
     - Sports: $0.030$
     - Geopolitics: $0.000$ (Fee-free)
   - Banker's Rounding (`ROUND_HALF_EVEN`) to the nearest cent ($0.01).
   - Maker trade fee exemption: exactly $0.0$.
   - Fee-Aware Expected Value Gate: requires expected edge $\ge 2.5 \times \text{taker fee rate}$.

---

## 5. Forensic Domain 4: Frontend Data Hydration & Dual-Column Bar Chart

### Observations & Evidence
- **Bar Chart Component (`frontend/src/components/charts/DailyWinLossBarChart.tsx`)**:
  - Recharts `BarChart` renders two distinct `<Bar>` components:
    - `<Bar dataKey="wonUsd" name="Gross Won" fill="#00D09C" radius={[4, 4, 0, 0]} />` (Green upward bar)
    - `<Bar dataKey="lostUsd" name="Gross Lost" fill="#FF453A" radius={[0, 0, 4, 4]} />` (Red downward bar)
  - Reference baseline at $y=0$ (`<ReferenceLine y={0} stroke="rgba(0,0,0,0.18)" />`).
  - Stack sign offset (`stackOffset="sign"`) ensures green bars project upward and red bars project downward without clipping.
  - Interactive tooltip correctly formats `+${won}` in `#00D09C` and `-${lost}` in `#FF453A` alongside net PnL and trades count.
- **Data Mapping (`frontend/src/lib/api-client.ts` & `WalletDrawer.tsx`)**:
  - `fetchWallet()` maps `won_usd` $\to$ `wonUsd`, `lost_usd` $\to$ `lostUsd`, `net_pnl` $\to$ `netPnL`.
  - `WalletDrawer.tsx` supports dynamic timeframe slicing (`1W`, `1M`, `YTD`, `ALL`) with correct date filtering.

---

## 6. Forensic Domain 5: Paper Trading State Machine & Invariance

### Observations & Evidence
- **Isolated Sleeve Architecture (`backend/app/sizing/sleeve_manager.py`)**:
  - Dynamically splits bankroll evenly across active roster ($1,000 base sleeve on $10k bankroll).
  - Sizes trades via Conviction Percentile ($0.05 - 1.0$) relative to the whale's own historical distribution.
  - Adjusts sleeve budget via copy-PnL EMA with a $0.30\times$ ($300) floor and $1.50\times$ ($1,500) ceiling.
  - Anti-starvation guarantee: `actual_size = min(intended_size, sleeve_remaining)`. If `sleeve_remaining < min_trade_usd`, execution is skipped (`SKIPPED_SLEEVE_EXHAUSTED`).
  - Guarantees 0 negative balances across all sleeves and user accounts.
- **Out-of-Order SELL Matching (`backend/app/services/live_poller.py`)**:
  - When a whale SELL arrives before a lagging BUY, registers a `PendingOutOfOrderSell`.
  - When the corresponding BUY arrives, pairs them immediately, executes FIFO closure, computes realized PnL minus bidirectional taker fees, and commits state with zero orphaned trades.
- **Binary Market Resolution (`settle_market_resolution`)**:
  - Settles winning positions at $1.00$ payout and losing positions at $0.00$ payout.
  - Transitions all open lots from `FILLED` $\to$ `CLOSED` and updates high-water marks.

---

## 7. Forensic Domain 6: Independent Test & Build Verification

### 1. Backend Test Suite (`pytest`)
- **Command**: `& "C:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\pytest.exe" -v`
- **Results**:
  - Total tests executed: **403**
  - Passed: **403**
  - Failed: **0**
  - Execution time: **14.19s**
  - Coverage: 23 test modules including 220-scenario adversarial state machine matrix (`test_massive_220_scenario_matrix.py`), fee boundary matrix, idempotency, dormancy, and sleeve isolation.

### 2. Frontend Next.js Production Build
- **Command**: `& "C:\Program Files\nodejs\npm.cmd" run build` inside `c:\Users\arthu\Documents\Baleen-master\frontend`
- **Results**:
  - Exit code: **0**
  - TypeScript errors: **0**
  - ESLint errors: **0**
  - Routes compiled: **10/10** (`/`, `/_not-found`, `/admin`, `/auth/login`, `/auth/signup`, `/dashboard`, `/settings`, `/api/auth/[...nextauth]`, `/api/debug-env`)

---

## 8. Forensic Conclusion

The Baleen platform implementation strictly satisfies all architectural contracts and integrity requirements:
- No hardcoded test responses or fake data fixtures exist in production modules.
- Polymarket API endpoints and on-chain ingestion logic operate authentically.
- Mathematical formulations (Wilson LB, Sharpe ratio, Quadratic Fees, PnL separation) are genuine.
- Frontend charts render authentic dual-column bars with exact styling contracts.
- Paper trading state machine maintains all 10 invariants with zero negative balance violations.

**Final Verdict**: **CLEAN**
