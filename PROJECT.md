# Project: Baleen Codebase Comprehensive Audit & Verification

## Architecture
Baleen is an automated copy-trading and predictive market intelligence platform for Polymarket.
The system consists of four primary subsystems:
1. **Ingestion Listener (`listener/src/`)**: Envio HyperSync client streaming Polygon `OrderFilled` events from CTF Exchange contracts, filtering by active whale basket, local queueing, and webhook forwarding to backend `/api/signals`.
2. **Backend Services & API (`backend/app/`)**: FastAPI server, SQLAlchemy async engine (PostgreSQL/SQLite), APScheduler background workers (Discovery, Rescoring, Analysis), Live Trade Mirror engine (`live_poller.py`), Mark-to-Market revaluation loop (`mark_to_market.py`), and Groq LLaMA-3.1 AI Copilot (`copilot.py`).
3. **Database Layer (`db/`, `backend/app/database.py`, `backend/app/models.py`)**: Canonical PostgreSQL schema (`wallets`, `wallet_snapshots`, `users`, `execution_logs`, `fee_charges`, `portfolio_snapshots`, `system_events`), indexing, connection pool retry, and auto-migrations.
4. **Frontend Dashboard (`frontend/`)**: Next.js 14 App Router, Tailwind CSS, Framer Motion, Recharts, trade drawers, wallet analytics, interactive charts, and risk settings.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Test Suite Execution | Execute and evaluate backend pytest and listener jest test suites | M1 | ORIGINAL_REQUEST §5 |
| 2 | HyperSync Event Ingestion | Stream and parse OrderFilled logs from CTF Exchange contracts | M2 | ORIGINAL_REQUEST §R1 |
| 3 | Whale Basket Matching & Signal Dispatch | Decode topics/data, match against active whale addresses, forward to backend | M2 | ORIGINAL_REQUEST §R1 |
| 4 | Block Checkpointing & Queue Persistence | Atomic block height tracking and offline signal queueing | M2 | ORIGINAL_REQUEST §R1 |
| 5 | Database Connection & Schema Management | Async SQLAlchemy pool management, reconnect retries, migrations, and model integrity | M3 | ORIGINAL_REQUEST §R1 |
| 6 | Execution Logging & User Isolation | Trade execution logging, portfolio snapshots, user query filtering, and sandbox resets | M3 | ORIGINAL_REQUEST §R1 |
| 7 | Backend Workers & Scheduling | Autonomous discovery (20m), rescoring (24h), and analysis (24h) workers | M3 | ORIGINAL_REQUEST §R1 |
| 8 | MCP Admin Server | Model Context Protocol stdio server exposing admin inspection and control tools | M3 | ORIGINAL_REQUEST §R1 |
| 9 | Fill Simulation & Book Walking | Order book walking, depth consumption, and execution fill pricing | M4 | ORIGINAL_REQUEST §R2 |
| 10 | Dynamic Quadratic Taker Fees | 2026 Polymarket dynamic quadratic fee curves across market categories | M4 | ORIGINAL_REQUEST §R2 |
| 11 | Slippage Modeling & Latency | Slippage guards, favorable price improvements vs adverse movement, block timestamps | M4 | ORIGINAL_REQUEST §R2 |
| 12 | PnL & Equity Accounting Realism | Realized PnL double-counting fixes, mark-to-market valuations, free cash vs MTM equity | M4 | ORIGINAL_REQUEST §R2 |
| 13 | Wilson Score Lower Bounds & Win Rate Filtering | Statistical scoring, binomial confidence intervals, sample size gating | M5 | ORIGINAL_REQUEST §R3 |
| 14 | Sizing & Kelly Position Models | Proportional sizing, Kelly criterion balance management, risk caps | M5 | ORIGINAL_REQUEST §R3 |
| 15 | Multi-Candidate Discovery & Fee-Aware EV Gates | 2-stage discovery scanning, threshold harmonization, alpha-aware EV gates | M5 | ORIGINAL_REQUEST §R3 |
| 16 | Frontend Dashboard & State Displays | TradeDrawer, WalletDrawer, PortfolioAnalytics, LiveTape, TradeLog, and Copilot | M6 | ORIGINAL_REQUEST §R1 |
| 17 | Frontend Compounding & Simulation Realism | ProfitSimulator models, modal persistence, and client-side probability math | M6 | ORIGINAL_REQUEST §R1 |
| 18 | Adversarial Verification & Forensic Audit | Stress testing, edge case challenging, and zero-tolerance integrity audit | M7 | System Requirements |
| 19 | Final Comprehensive Audit Report | Structured report with line citations, failure mechanics, concrete diffs, and ambiguities | M8 | ORIGINAL_REQUEST §R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Test Suite Execution & Baseline Evaluation | Run pytest and jest; document baseline pass/fail rates | none | DONE |
| M2 | Ingestion Listener & Pipeline Audit | Deep audit of listener/src/, event parsing, topics, queueing, checkpointing | M1 | DONE |
| M3 | Backend Services, API & Database Audit | Deep audit of backend/app/, database.py, models.py, mcp_server.py | M1 | DONE |
| M4 | Paper Trading Simulation & Uneven Edge Audit | Deep audit of fill_simulator, slippage, fees, live_poller, PnL accounting | M1 | DONE |
| M5 | Mathematical & Quantitative Integrity Audit | Deep audit of scanner, Wilson score, Kelly sizing, EV gates, discovery | M1 | DONE |
| M6 | Frontend Architecture & Realism Audit | Deep audit of frontend/ components, drawers, simulator, API hooks | M1 | DONE |
| M7 | Adversarial Review & Forensic Gate | Challenger stress-tests and Forensic Auditor integrity verification | M2, M3, M4, M5, M6 | DONE |
| M8 | Comprehensive Audit Report Synthesis | Final structured audit report with diffs, failure mechanics, ambiguities | M7 | IN_PROGRESS |

## Interface Contracts
### Listener (`listener/src/`) ↔ Backend (`backend/app/api/signals.py`)
- Endpoint: `POST /api/signals`
- Payload: `WhaleTradeSignal`
  - `walletAddress`: string (0x...)
  - `side`: 'BUY' | 'SELL' (strictly reflecting outcome token direction)
  - `assetId`: string (Polymarket token ID, never '0' for collateral)
  - `amountFilled`: string (raw units / decimal)
  - `price`: string (calculated execution price 0.00-1.00)
  - `transactionHash`: string (0x...)
  - `logIndex`: number
  - `blockNumber`: number
  - `timestamp`: number (block timestamp in ms)

### Backend Services (`live_poller.py`) ↔ Sizing & Fill Models (`app/sizing/`)
- `simulate_fill(order_value_usd, order_book, side)` -> `FillResult(average_price, total_filled_usd, is_fully_filled, levels_walked)`
- `check_slippage(whale_price, current_price, side)` -> `'EXECUTE_ORDER' | 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'`
- `size_trade(user_balance, risk_profile, n_active, ...)` -> `SizingResult(order_size_usd, reason)`

## Code Layout
- `backend/app/`: Core backend application code (API routers, discovery, scoring, services, sizing, workers).
- `backend/tests/`: Pytest unit and integration test suite.
- `listener/src/`: Envio HyperSync listener TypeScript source code.
- `listener/tests/`: Jest test suite for listener.
- `frontend/src/`: Next.js frontend application (app router, components, lib).
- `db/`: Database schemas and migration files.
