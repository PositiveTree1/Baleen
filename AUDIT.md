# Baleen — Architecture Audit & Jira Project Tracking Registry

> **System Overview:** Baleen is an automated Polymarket Whale-Index & Copy-Trading Engine that aggregates on-chain predictions from top-performing prediction market traders into a unified, dynamically-sized index basket.

---

## 1. Atlassian Jira Board Status (`KAN` / Antigravity)

| Issue Key | Type | Status | Summary & Verification Status |
|---|---|---|---|
| **KAN-1** | Epic | `Done` | **Baleen Phase 1: Core Whale Indexing & Sandbox Engine** (100% Complete) |
| **KAN-2** | Epic | `To Do` | **Baleen Phase 2: Live Trading, Embedded Wallets & Monetization** |
| **KAN-3** | Story | `Done` | **Authentic Polymarket Wallet Scraping & Profile Ingestion Engine**: Live scraping of `/v1/leaderboard`, `/positions`, and `/activity`. Extracts verified on-chain realized PnL, authentic usernames (`name`), pseudonyms (`pseudonym`), and avatars (`profile_image`). |
| **KAN-4** | Story | `Done` | **Titan Real-Time CLOB Midpoint & Gamma Outcome Price Discovery**: Multi-stage price engine resolving `/midpoint`, `/price`, and Gamma `outcomePrices`. Elimination of multiples-of-5 and 0.50 fallbacks. |
| **KAN-5** | Task | `Done` | **Dynamic Polymarket Fee Engine (2026 Quadratic Taker Curve)**: Quadratic taker fee formula (`Notional × Rate × (1 - Price)`) across Crypto (5%), Sports (5%), Politics/Finance (3%), and Geopolitics (2%). |
| **KAN-6** | Story | `Done` | **Execution Audit Log System & Full History Retention**: Realized & active fill persistence with full history retention (500+ records) and no artificial hourly cutoffs. |
| **KAN-7** | Task | `Done` | **Real Polymarket Event URLs & Market Icon Visual Assets**: Resolution of nested `eventSlug` (`https://polymarket.com/event/{event_slug}`) and display of event logos in LiveTape, Audit Log, and TradeDrawer. |
| **KAN-8** | Story | `Done` | **2-Stage Autonomous Discovery Pipeline & Purge/Rescan Engine**: Candidate scraping and deep multi-page audit with state persistence in Supabase PostgreSQL. |
| **KAN-9** | Task | `Done` | **Groq LLaMA-3.1 70B AI Quantitative Whale Profiler & Typewriter**: Automated AI audit generation with high-contrast glowing card and smooth Typewriter rendering. |
| **KAN-10** | Story | `Done` | **Sandbox Mode Virtual Portfolio & Global Reset Facility**: Zero-risk paper trading mode with virtual $10k balance and instantaneous global portfolio reset. |
| **KAN-11** | Task | `Done` | **Binary Outcome Probability Alignment (`1 - p`) for NO Orders**: Historical CLOB price inversion for Token 1 orders to eliminate cliff-drop artifacts on trade charts. |
| **KAN-12** | Task | `Done` | **High-Frequency & Market-Maker Bot (`MAKER_REBATE`) Filter**: Automated detection and filtering of rebate micro-traders and high-frequency trading bots. |
| **KAN-13** | Story | `Done` | **Polygon CTF Exchange Envio HyperSync Live Signal Listener**: Node.js/TypeScript event listener streaming on-chain `OrderFilled` events into the backend queue with cross-platform fallback and 100% test coverage. |
| **KAN-14** | Task | `Done` | **Multi-Candidate & Multi-Outcome Price Discovery Calibration**: Token mapping, candidate indexing, and live probability pricing for multi-candidate tournament and election markets. |
| **KAN-15** | Task | `Done` | **Maximum Drawdown & On-Chain Equity Curve Verification**: Peak-to-trough max drawdown calculation from cumulative daily equity history, verified against live Polymarket trader curves. |
| **KAN-16** | Story | `To Do` | **Embedded Wallet Delegated Signing Integration (Magic / Privy)**: Delegated signing sessions allowing automated execution without storing user private keys. |
| **KAN-17** | Task | `To Do` | **Polymarket CLOB V2 Order Construction & Nonce Management**: EIP-712 typed order payload generation and gasless relayer dispatch. |
| **KAN-18** | Task | `To Do` | **Pre-Trade Risk Checks & Emergency Kill-Switch Architecture**: Notional exposure limits, slippage bounds, and platform-wide kill switch. |
| **KAN-19** | Story | `To Do` | **High-Water Mark Performance Fee Calculation & Accrual Engine**: Profit-share billing calculated strictly on gains above the historical peak balance. |
| **KAN-20** | Task | `To Do` | **Daily Digest Email Dispatcher (Resend + React Email)**: Nightly performance summary emails for subscribed users. |
| **KAN-21** | Task | `To Do` | **Mobile PWA Responsive Layout & Touch Interactions Optimization**: Viewport adaptation and gesture controls for mobile devices. |
| **KAN-22** | Task | `To Do` | **Automated Staging & Production CI/CD Deployment Workflow**: GitHub Actions test, build, and container deployment pipelines. |

---

## 2. System Stability & Test Verification Matrix

### 2.1 Backend Test Suite (Pytest)
- **Status:** **32 / 32 Passed** (100% Pass Rate in 12.76s)
- **Covered Subsystems:**
  - AI Summary generation (`test_ai_summary.py`)
  - Checkpoint and resume mechanics (`test_checkpoint.py`)
  - Daily digest formatters (`test_digest.py`)
  - Dormancy detection (`test_dormancy.py`)
  - Dynamic position sizing & Kelly weights (`test_dynamic_sizing.py`)
  - 2026 Quadratic dynamic fee engine (`test_fee_calculation.py`)
  - Fill model and slippage computation (`test_fill_model.py`, `test_slippage.py`)
  - On-chain trade idempotency and deduplication (`test_idempotency.py`)
  - Quantitative scoring filters & Wilson lower bounds (`test_scoring_filters.py`)
  - REST API endpoints & wallet snapshots (`test_wallet_api.py`)

### 2.2 Listener Service (Envio HyperSync / Jest)
- **Status:** **3 / 3 Passed** (100% Pass Rate with `tsc` clean compilation)
- **Covered Subsystems:**
  - Native + HTTP REST cross-platform HyperSync stream client
  - Polygon CTF Exchange event query builder (`fromBlock`, `OrderFilled` topics)
  - Persistent block checkpointing (`checkpoint.json`)

### 2.3 Frontend Application (Next.js 14 / Turbopack)
- **Status:** **Build Successful** (0 TypeScript Errors, 0 Lint Errors, 9/9 Static Pages Prerendered)

### 2.4 Database Health (Supabase PostgreSQL Pooler)
- **Tables Verified:**
  - `public.wallets`: 1,385 wallets active/ingested
  - `public.execution_logs`: 6,462 executions tracked
  - `public.portfolio_snapshots`: 3,263 snapshot points
  - `public.users`: active sandbox portfolio records
