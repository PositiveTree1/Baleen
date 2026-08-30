# Project: Baleen Quantitative Engineering & Robustness (R1-R4)

## Architecture
Baleen is an automated copy-trading and market discovery platform for Polymarket prediction markets.
- **Core Engine & Execution**: `backend/app/services/live_poller.py`, `backend/app/sizing/fill_simulator.py`, `backend/app/sizing/slippage.py`, `backend/app/services/polymarket_fees.py`.
- **Sizing & Risk Management**: `backend/app/sizing/sleeve_manager.py`, `backend/app/sizing/dynamic_sizing.py`.
- **Valuation & MTM State Machine**: `backend/app/services/mark_to_market.py`, `backend/app/api/execution_logs.py`.
- **Frontend & Visualization**: `frontend/src/components/portfolio/PortfolioAnalytics.tsx`, `BalanceCounter.tsx`.
- **Testing & Verification**: `backend/tests/`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | R1: Universal CLOB Fill Slippage | Guaranteed `slippage_bps > 0` on 100% of simulated fills across all 5 branches (direct buys, FIFO sells, split lots, OOO matches, onchain signals) | M1 | ORIGINAL_REQUEST §R1 |
| 2 | R1: Universal Non-Null Latency | Non-null `latency_ms` across all execution paths including split lots | M1 | ORIGINAL_REQUEST §R1 |
| 3 | R1: Absolute Tick Delta Floor | Minimum price tick movement ($\delta_{\min} \ge 0.0005$) preventing anti-rounding collapse on small prices/sizes | M1 | Survey |
| 4 | R2: Bayesian Credibility Sizing Prior | $Z(N)$ shrinkage prior for $N < 15$ anchoring whale sleeve budgets strictly within $\pm 10\%$ ($900-$1,100) of $1,000 base | M2 | ORIGINAL_REQUEST §R2 |
| 5 | R2: Smooth EMA Scaling & Bounded Sensitivity | Bounded single-trade sensitivity and smooth scaling to full $[0.30\times, 1.50\times]$ range over dozens of trades | M2 | ORIGINAL_REQUEST §R2 |
| 6 | R3: Timeframe Net Worth Synchronization | Zero valuation jumps between 1H, 1D, 1W, ALL timeframes; elimination of cold-cache markdown spikes ($9.6k \leftrightarrow 10.1k$) | M3 | ORIGINAL_REQUEST §R3 |
| 7 | R3: Harmonized Snapshot Bucketing & API | Single-authoritative MTM writer, last-of-bucket sampling in `/api/executions/snapshots`, and consistent Genesis baseline | M3 | ORIGINAL_REQUEST §R3 |
| 8 | R4: Automated Regression Test Suite | Dedicated comprehensive regression test suite in `backend/tests/` covering R1, R2, R3 invariants | M4 | ORIGINAL_REQUEST §R4 |
| 9 | R4: Full Pytest & Frontend Build Verification | 100% test pass rate across all backend pytest suites and 0-error Next.js production build | M4 | ORIGINAL_REQUEST §R4 |

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Universal CLOB Fill Slippage & Latency Modeling | Fix zero-slippage bypasses in `live_poller.py`, `fill_simulator.py`, tick delta floors, and non-null `latency_ms` | None | PLANNED |
| M2 | Sample-Size Damped Dynamic Sleeve Budget Sizing | Implement Bayesian credibility prior $Z(N)$ and bounded EMA in `sleeve_manager.py` | None | PLANNED |
| M3 | Portfolio Timeframe & Net Worth Synchronization | Synchronize MTM snapshots, bucketing in `execution_logs.py`, and eliminate balance fluctuation | None | PLANNED |
| M4 | Automated Regression Suite & System Verification | Implement comprehensive regression test suite in `backend/tests/`, verify 100% pytest and frontend build | M1, M2, M3 | PLANNED |

## Interface Contracts
### `calculate_simulated_fill_price` ↔ `live_poller.py`
- Signature: `calculate_simulated_fill_price(price: float, side: str, cash_usd: float = 100.0, order_book: Optional[Dict] = None, latency_ms: Optional[float] = None) -> Tuple[float, float, float]`
- Returns: `(effective_fill_price, slippage_bps, latency_ms)`
- Guarantees: `slippage_bps > 0.0`, `latency_ms > 0.0`, `abs(effective_fill_price - price) >= 0.0005`

### `SleeveManager.calculate_adjusted_sleeve_budget` ↔ `live_poller.py`
- Signature: `calculate_adjusted_sleeve_budget(base_budget: float, copy_pnl: float, baleen_score: float = 80.0, trades_count: Optional[int] = None) -> float`
- Guarantees: For `trades_count < 15`, returned budget is strictly in `[0.90 * base_budget, 1.10 * base_budget]`.

### `MarkToMarketService` ↔ `/api/executions/snapshots`
- Snapshot Model: `PortfolioSnapshot(user_id=None, timestamp=now_dt, balance=canonical_balance, total_pnl=round(total_portfolio_pnl, 2), active_trades_count=trades_count)`
- Bucketing: Last-of-bucket selection with consistent timeframe endpoints.

## Code Layout
- `backend/app/sizing/slippage.py`: Centralized slippage & latency calculation.
- `backend/app/sizing/fill_simulator.py`: Multi-level order book fill simulation.
- `backend/app/services/live_poller.py`: Trade copy execution and log generation.
- `backend/app/sizing/sleeve_manager.py`: Bayesian sample-size damped dynamic sleeve budget sizing.
- `backend/app/services/mark_to_market.py`: Mark-to-market continuous valuation service.
- `backend/app/api/execution_logs.py`: Portfolio snapshots and summary API endpoints.
- `backend/tests/`: Pytest regression suites.
- `frontend/`: Next.js portfolio analytics and dashboard.
