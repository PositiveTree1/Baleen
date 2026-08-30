# Project: Baleen Whale Copy-Trading Platform

## Architecture
- **Backend**: FastAPI (`backend/app/main.py`), SQLAlchemy Async SQLite/PostgreSQL (`database.py`), Polymarket Data API client (`polymarket_client.py`), Scanner & Trade Aggregation (`scanner.py`), Scoring Engine (`scoring/engine.py`, `scoring/basket.py`), Live Poller & Paper Trading Engine (`services/live_poller.py`), Sleeve Manager (`sizing/sleeve_manager.py`), Polymarket Quadratic Fees (`services/polymarket_fees.py`), Mark-to-Market Valuation (`services/mark_to_market.py`), Directional Slippage & Fill Simulator (`sizing/slippage.py`, `sizing/fill_simulator.py`), Disk Backup (`services/disk_backup.py`).
- **Frontend**: Next.js 16 App Router (`frontend/src/app`), React components (`frontend/src/components`), Recharts charts (`DailyWinLossBarChart.tsx`), Drawer (`WalletDrawer.tsx`), API client (`frontend/src/lib/api-client.ts`), Tailwind CSS, TypeScript.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Polymarket Data Ingestion | Fetch /positions, /activity, /trades, /leaderboard with pagination and rate limit backoff | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Trade History & PnL Separation | Date grouping (YYYY-MM-DD), authentic gross won vs gross lost separation (`won_usd >= 0`, `lost_usd <= 0`) | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Whale Classification & Scoring | 9 disqualifying filters, 90% Wilson LB, Sharpe ratio, 5-factor pool normalization, 5-point hysteresis | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Dual-Column Win/Loss Bar Chart | Render daily green won bar (`#00D09C`) and red lost bar (`#FF453A`) with reference baseline | M2 | ORIGINAL_REQUEST §R2 |
| 5 | Chart Responsiveness & Tooltips | Zero clipping across 1W/1M/YTD/ALL, interactive tooltips with won/lost/net/trades breakdown | M2 | ORIGINAL_REQUEST §R2 |
| 6 | Frontend Build & Type Safety | 0 TypeScript errors, 0 ESLint errors in build (`npm run build`) | M2 | ORIGINAL_REQUEST §R2 |
| 7 | Live Continuous Polling Loop | Paced 2.5s loop, top-10 active whale roster, dynamic expansion for open position exit tracking | M3 | ORIGINAL_REQUEST §R3 |
| 8 | Isolated Sleeve Sizing | $1,000 base sleeve budget, conviction percentile sizing, dynamic copy-PnL EMA adjustment, anti-starvation capacity clipping | M3 | ORIGINAL_REQUEST §R3 |
| 9 | 2026 Quadratic Polymarket Fee Engine | Exact $\Theta \times \text{Notional} \times (1-p)$ for 6 categories, Banker's rounding, maker 0% fee, Fee-Aware EV gate | M3 | ORIGINAL_REQUEST §R3 |
| 10 | Directional Slippage & Boundary Screening | Asymmetric adverse thresholds, depth walk simulation, boundary price screening ($0.04 - $0.96) | M3 | ORIGINAL_REQUEST §R3 |
| 11 | Out-of-Order Sell Matching & Invariance | Pending SELL registration, lagging BUY pairing, 0 negative balance guarantee, 0 orphaned trades | M3 | ORIGINAL_REQUEST §R3 |
| 12 | 24/7 Resilience & State Persistence | Keep-alive pinging, periodic disk backups, MTM restart recovery watchdog, loop error isolation | M3 | ORIGINAL_REQUEST §R3 |
| 13 | E2E Test Suite (Tiers 1-4) | Comprehensive opaque-box test suite verifying all features and acceptance criteria | M4 | ORIGINAL_REQUEST §Acceptance Criteria |
| 14 | Adversarial Hardening (Tier 5) | Adversarial stress testing, boundary matrices, state machine invariant validation | M5 | Acceptance Criteria & Hardening |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | R1: Authentic Trade History & Classification | Polymarket API ingestion, daily won/lost PnL separation, whale filtering & classification | none | DONE |
| 2 | R2: Dual-Column Win/Loss Chart Rendering | DailyWinLossBarChart.tsx, WalletDrawer timeframe filtering, 0 TS build errors | none | DONE |
| 3 | R3: Live Poller & Overnight Paper Trading | live_poller.py, sleeve_manager.py, quadratic fees, slippage, out-of-order matching, resilience | none | DONE |
| 4 | Final Milestone Phase 1: E2E Test Suite (Tiers 1-4) | 100% pass of test suite across backend and frontend | M1, M2, M3 | DONE |
| 5 | Final Milestone Phase 2: Adversarial Hardening (Tier 5) | Adversarial challenge verification, edge case boundary stress tests | M4 | DONE |

## Interface Contracts

### Scanner / Ingestion ↔ API / Frontend
- `DailyPnLPoint` / `daily_pnl_history` data contract:
  - `date`: string (`YYYY-MM-DD` UTC)
  - `won_usd` / `wonUsd`: float >= 0.0 (gross daily profits)
  - `lost_usd` / `lostUsd`: float <= 0.0 (gross daily losses, signed negative for downward bar orientation)
  - `net_pnl` / `netPnL`: float (net daily PnL = `won_usd + lost_usd`)
  - `cumulative_pnl` / `cumulativePnL`: running total PnL
  - `trades_count` / `tradesCount`: integer

### Sleeve Manager ↔ Live Poller
- Function: `size_sleeve_trade(trade_size, open_notional, sleeve_budget, trailing_sizes, copy_pnl_ema)`
- Returns: `(executed_size_usd, conviction_pct, capture_rate_pct)`
- Invariant: `open_notional + executed_size_usd <= sleeve_budget` (anti-starvation guarantee)

### Polymarket Fees ↔ Execution Engine
- Function: `calculate_dynamic_taker_fee(notional, price, category, is_maker)`
- Returns: `(fee_usd, fee_rate, category_name)`
- Formula: if `is_maker` then 0.0 else `round_half_even(notional * theta * (1 - price))`

## Code Layout
- Backend Source: `backend/app/`
  - Discovery & Ingestion: `backend/app/discovery/` (`polymarket_client.py`, `scanner.py`)
  - Scoring & Roster: `backend/app/scoring/` (`engine.py`, `basket.py`)
  - Execution & Paper Trading: `backend/app/services/` (`live_poller.py`, `polymarket_fees.py`, `mark_to_market.py`, `disk_backup.py`)
  - Sizing & Slippage: `backend/app/sizing/` (`sleeve_manager.py`, `slippage.py`, `fill_simulator.py`)
  - API Routes: `backend/app/api/` (`wallets.py`, `copy.py`, `backtest.py`)
  - Database & Models: `backend/app/database.py`, `backend/app/models/`
- Frontend Source: `frontend/src/`
  - Components & Charts: `frontend/src/components/charts/` (`DailyWinLossBarChart.tsx`), `frontend/src/components/dashboard/` (`WalletDrawer.tsx`)
  - API Client & Types: `frontend/src/lib/api-client.ts`, `frontend/src/types/index.ts`
- Tests:
  - Backend Unit & Integration: `backend/tests/` (23 test modules, 403+ test cases)
  - Scenarios Matrix: `backend/tests/scenarios/` (220-scenario state machine matrix)
