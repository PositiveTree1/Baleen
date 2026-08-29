# Project: Baleen Codebase Stress Testing, Invariant Verification, Quantitative Audit, and Frontend UI Validation

## Architecture
Baleen is an automated copy-trading and portfolio management engine for Polymarket prediction markets.
- **Backend Architecture**:
  - `backend/app/discovery/scanner.py`: Whale candidate discovery, trade history fetching, gatekeeper evaluation, and tier assignment.
  - `backend/app/scoring/engine.py` & `backend/app/scoring/basket.py`: 8 gatekeeper filters, 5-factor scoring engine (Odds-Edge, Sharpe, Recency-EMA, Category, Penalty), intra-pool 0-100 min-max normalization, and top 10 roster selection with 5-point hysteresis.
  - `backend/app/sizing/sleeve_manager.py`: 10-wallet bankroll partitioning ($Cash/10$), Conviction Percentile sizing, Copy-PnL EMA multiplier, and sleeve isolation.
  - `backend/app/services/polymarket_fees.py`: 2026 Polymarket Quadratic Dynamic Fee formula ($\text{Fee} = \Theta \times \text{Notional} \times (1-p)$) across 6 categories with Banker's Rounding to $0.01.
  - `backend/app/services/mark_to_market.py` & `live_poller.py`: Mark-to-market valuation, cash invariance enforcement, out-of-order execution resolution, and platform state deduplication.
  - `backend/tests/scenarios/`: 220-scenario stress testing matrix (Orderbook extremes, Network timing, Lifecycle FIFO, Multitenancy scaling) and Invariant Monitor.
- **Frontend Architecture**:
  - `frontend/src/app/dashboard/page.tsx`: Next.js 16.3.0 dashboard orchestrating `BalanceCounter`, `PortfolioAnalytics`, `LiveTape`, `WalletLeaderboard`, `TradeLog`, `WalletDrawer`, `TradeDrawer`, and action modals.
  - `frontend/src/components/charts/`: `DailyWinLossBarChart`, `CumulativePnLChart`, `PortfolioAnalytics` (Area/OHLC), and `TradePriceChart`.
  - `frontend/src/context/ThemeContext.tsx`: Dark/light mode theme management.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 150+ Lifetime Trades & 60+ Active Days Gate | Gatekeeper requiring candidate whales to have $\ge 150$ closed trades and $\ge 60$ active days track record | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Anti-HFT / Maker-Rebate Filter | Gatekeeper capping trade frequency at $\le 15$ trades/day | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Closed Position Concentration Cap | Outlier cap rejecting whales where top closed winning position exceeds $25\%$ of positive realized PnL | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Minimum Scale Filter | Gatekeeper requiring $\ge \$50\text{k}$ all-time PnL and $\ge \$150\text{k}$ total traded volume | M1 | ORIGINAL_REQUEST §R1 |
| 5 | Sleeve Size Compatibility | Gatekeeper requiring median trade size between $\$20$ and $\$3,000$ | M1 | ORIGINAL_REQUEST §R1 |
| 6 | Wash-Trading Detection Filter | Gatekeeper flagging $<120\text{s}$ BUY$\leftrightarrow$SELL roundtrips $>10\%$ ($\ge 2$ occurrences) | M1 | ORIGINAL_REQUEST §R1 |
| 7 | Intra-Pool 0-100 Normalization | 5-factor normalization across active pool with division-by-zero guards | M1 | ORIGINAL_REQUEST §R1 |
| 8 | Top 10 Roster with 5-Point Hysteresis | Incumbent defense bonus ($+5.0$) and Gold Sniper boost ($+3.0$) for top 10 selection | M1 | ORIGINAL_REQUEST §R1 |
| 9 | Whale Discovery Score Assignment Fix | Resolve uninitialized `baleen_score` runtime bug in `scanner.py:422` | M1 | Survey Finding R1 |
| 10 | 10-Wallet Sleeve Isolation & Zero Starvation | Dynamic bankroll partitioning with strict sleeve boundaries preventing cross-wallet capital starvation | M2 | ORIGINAL_REQUEST §R2 |
| 11 | Cash Invariance & MTM Isolation | Non-negative cash balance enforcement, margin equation, and prevention of unrealized MTM phantom cash inflation | M2 | ORIGINAL_REQUEST §R2 |
| 12 | 2026 Quadratic Polymarket Fee Invariance | Dynamic quadratic fee calculation across 6 categories (Crypto, Econ, Culture/Tech, Politics, Sports, Geopolitics) with Banker's Rounding | M2 | ORIGINAL_REQUEST §R2 |
| 13 | Zero-Division & Edge-Case Safety | Safe handling of empty history, zero volume, single-trade input, corrupted orderbook levels | M2 | ORIGINAL_REQUEST §R2 |
| 14 | 220+ Multi-Scenario Stress Suite | Comprehensive execution of 220 operational, market, and execution scenarios across 4 tiers | M2 | ORIGINAL_REQUEST §R2 |
| 15 | Responsive Dashboard Viewports (375px, 768px, 1440px) | Zero text collision, robust horizontal containment (`min-w-0`, `truncate`, `shrink-0`) across all device viewports | M3 | ORIGINAL_REQUEST §R3 |
| 16 | Smooth Drawer Transitions & Modals | Spring physics animated drawers and modal overlays with keyboard / backdrop dismissal | M3 | ORIGINAL_REQUEST §R3 |
| 17 | Daily Win/Loss & Financial Charts | Stacked daily win/loss bar chart, cumulative PnL area chart, and localized French date/currency formatting | M3 | ORIGINAL_REQUEST §R3 |
| 18 | Theme Toggle & Dark Mode Uniformity | Seamless dark/light theme toggling and standardized dark mode styling across all modals and charts | M3 | ORIGINAL_REQUEST §R3 |
| 19 | E2E Requirements-Driven Test Suite | Opaque-box 4-tier test verification covering all 18 features | E2E Track | Project Architecture |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Quantitative Filters & Scoring Hardening | Fix `scanner.py:422` uninitialized variable, fix `engine.py:34` trade count condition, add boundary unit tests in `test_scoring_filters.py` | none | DONE |
| M2 | Multi-Scenario Stress & Invariant Validation | Verify all 4 invariants across 220+ scenario matrix, fee boundary matrix, and edge case safety | M1 | DONE |
| M3 | Frontend UI & Theme Uniformity Refinement | Standardize dark mode classes across secondary modals/tooltips/empty states, verify 375px/768px/1440px responsiveness and clean build | none | DONE |
| E2E | E2E Testing Track | Independent requirements-driven test suite across all 4 tiers, publishing `TEST_INFRA.md` and `TEST_READY.md` | none | DONE |
| M_FINAL | Final Acceptance & Adversarial Hardening | Verify 100% pass on all E2E tests + Tier 5 adversarial stress testing | M1, M2, M3, E2E | DONE |

## Interface Contracts
### `scanner.py` ↔ `basket.py`
- `compute_baleen_score(stats: Dict[str, Any]) -> float`: Accepts whale metrics dictionary and returns normalized score in $[0.0, 100.0]$.
- `evaluate_pending_wallets()`: Computes `baleen_score` before assigning `wallet.tier` and persisting `wallet.baleen_score`.

### `engine.py` ↔ `basket.py`
- `score_wallet(stats: Dict[str, Any]) -> Tuple[float, List[str]]`: Evaluates 8 gatekeeper filters and returns score with rejection reasons.
- `trades_count` gate: Must reject accounts with $< 150$ trades (including $0$ trades) unless `pnl >= 500000.0`.

### `sleeve_manager.py` ↔ `InvariantMonitor`
- `size_sleeve_trade(...)`: Respects isolated wallet budget `sleeve_remaining = max(0.0, sleeve_budget - open_notional)`.
- Cash Invariant: Settled cash is modified solely on trade fills and settlements; MTM adjustments modify unrealized PnL/equity only.

### `ThemeContext.tsx` ↔ Modal / Chart Components
- `theme: 'light' | 'dark'`: Root element toggles `.dark` class. All modals and chart tooltips provide corresponding `dark:` utility classes.

## Code Layout
- Backend: `c:\Users\arthu\Documents\Baleen-master\backend\`
  - App: `backend/app/`
    - Discovery: `backend/app/discovery/scanner.py`
    - Scoring: `backend/app/scoring/engine.py`, `backend/app/scoring/basket.py`
    - Sizing: `backend/app/sizing/sleeve_manager.py`, `backend/app/sizing/fill_simulator.py`, `backend/app/sizing/dynamic_sizer.py`
    - Services: `backend/app/services/polymarket_fees.py`, `backend/app/services/mark_to_market.py`, `backend/app/services/live_poller.py`
    - Models: `backend/app/models.py`
  - Tests: `backend/tests/`
    - Unit tests: `backend/tests/test_*.py`
    - Scenarios: `backend/tests/scenarios/`
- Frontend: `c:\Users\arthu\Documents\Baleen-master\frontend\`
  - App: `frontend/src/app/`
  - Components: `frontend/src/components/`
  - Context: `frontend/src/context/`
  - Lib: `frontend/src/lib/`
