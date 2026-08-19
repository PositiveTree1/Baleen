# Baleen — Architecture Audit & Jira Project Tracking Registry

> **System Overview:** Baleen is an automated Polymarket Whale-Index & Copy-Trading Engine that aggregates on-chain predictions from top-performing prediction market traders into a unified, dynamically-sized index basket.

---

## 1. Atlassian Jira Board Mapping (`KAN` / Antigravity)

| Issue Key | Type | Status | Summary & Scope |
|---|---|---|---|
| **KAN-1** | Epic | `In Progress` | **Phase 1: Core Whale Indexing & Sandbox Engine** |
| **KAN-2** | Epic | `To Do` | **Phase 2: Live Trading, Embedded Wallets & Monetization** |
| **KAN-3** | Story | `Done` | **Authentic Polymarket Wallet Scraping & Profile Ingestion Engine**: Integration with `/v1/leaderboard`, `/positions`, and `/activity`. Net realized PnL, authentic usernames (`name`), pseudonyms (`pseudonym`), and avatars (`profile_image`). |
| **KAN-4** | Story | `Done` | **Titan Real-Time CLOB Midpoint & Gamma Outcome Price Discovery**: Multi-stage price engine resolving `/midpoint`, `/price`, and Gamma `outcomePrices`. Elimination of multiples-of-5 and 0.50 fallbacks. |
| **KAN-5** | Task | `Done` | **Dynamic Polymarket Fee Engine (2026 Quadratic Taker Curve)**: Quadratic taker fee formula (`Notional × Rate × (1 - Price)`) across Crypto (5%), Sports (5%), Politics/Finance (3%), and Geopolitics (2%). |
| **KAN-6** | Story | `Done` | **Execution Audit Log System & Full History Retention**: Realized & active fill persistence with full history retention (500+ records) and no artificial hourly cutoffs. |
| **KAN-7** | Task | `Done` | **Real Polymarket Event URLs & Market Icon Visual Assets**: Resolution of nested `eventSlug` (`https://polymarket.com/event/{event_slug}`) and display of event logos in LiveTape, Audit Log, and TradeDrawer. |
| **KAN-8** | Story | `Done` | **2-Stage Autonomous Discovery Pipeline & Purge/Rescan Engine**: Candidate scraping and deep multi-page audit with state persistence in Supabase PostgreSQL. |
| **KAN-9** | Task | `Done` | **Groq LLaMA-3.1 70B AI Quantitative Whale Profiler & Typewriter**: Automated AI audit generation with high-contrast glowing card and smooth Typewriter rendering. |
| **KAN-10** | Story | `Done` | **Sandbox Mode Virtual Portfolio & Global Reset Facility**: Zero-risk paper trading mode with virtual $10k balance and instantaneous global portfolio reset. |
| **KAN-11** | Task | `Done` | **Binary Outcome Probability Alignment (`1 - p`) for NO Orders**: Historical CLOB price inversion for Token 1 orders to eliminate cliff-drop artifacts on trade charts. |
| **KAN-12** | Task | `Done` | **High-Frequency & Market-Maker Bot (`MAKER_REBATE`) Filter**: Automated detection and filtering of rebate micro-traders and high-frequency trading bots. |
| **KAN-13** | Story | `In Review` | **Polygon CTF Exchange Envio HyperSync Live Signal Listener**: Node.js/TypeScript event listener streaming on-chain `OrderFilled` events into the backend queue. |
| **KAN-14** | Task | `In Progress` | **Multi-Candidate & Multi-Outcome Price Discovery Calibration**: Token mapping and probability indexing for multi-outcome tournament and election markets. |
| **KAN-15** | Task | `In Progress` | **Maximum Drawdown & On-Chain Equity Curve Verification**: Auditing historical daily position snapshots to verify peak-to-trough drawdown accuracy. |
| **KAN-16** | Story | `To Do` | **Embedded Wallet Delegated Signing Integration (Magic / Privy)**: Delegated signing sessions allowing automated execution without storing user private keys. |
| **KAN-17** | Task | `To Do` | **Polymarket CLOB V2 Order Construction & Nonce Management**: EIP-712 typed order payload generation and gasless relayer dispatch. |
| **KAN-18** | Task | `To Do` | **Pre-Trade Risk Checks & Emergency Kill-Switch Architecture**: Notional exposure limits, slippage bounds, and platform-wide kill switch. |
| **KAN-19** | Story | `To Do` | **High-Water Mark Performance Fee Calculation & Accrual Engine**: Profit-share billing calculated strictly on gains above the historical peak balance. |
| **KAN-20** | Task | `To Do` | **Daily Digest Email Dispatcher (Resend + React Email)**: Nightly performance summary emails for subscribed users. |
| **KAN-21** | Task | `To Do` | **Mobile PWA Responsive Layout & Touch Interactions Optimization**: Viewport adaptation and gesture controls for mobile devices. |
| **KAN-22** | Task | `To Do` | **Automated Staging & Production CI/CD Deployment Workflow**: GitHub Actions test, build, and container deployment pipelines. |

---

## 2. Completed Architectural Milestones

### 2.1 Authentic On-Chain Analytics
- **Leaderboard Integration**: Switched to Polymarket Data API `/v1/leaderboard`, eliminating 404s and preventing total volume from being confused with net realized profit.
- **Bot/MM Filtering**: Automatically filters out accounts where activity is dominated by `MAKER_REBATE` micro-trades.
- **Identity & Profile Metadata**: Stores and displays official Polymarket profile usernames, pseudonyms, and avatars (`name`, `pseudonym`, `profile_image`).

### 2.2 Titan Full Pricing Engine
- **Midpoint Resolution**: Queries Polymarket CLOB `/midpoint?token_id={asset}` and `/price?token_id={asset}&side=BUY` for precision live pricing.
- **Gamma Fallback**: Parses `outcomePrices` and `clobTokenIds` with exact token mapping.
- **Binary Outcome Inversion**: Corrects NO outcome charts by inverting historical YES CLOB data (`p = 1.0 - p`).

### 2.3 2026 Dynamic Polymarket Fee Model
- Calculates dynamic quadratic taker fees: `fee_usd = notional × rate × (1 - price)`.
- Applied across Crypto (5%), Sports (5%), Politics & Finance (3%), and Geopolitics (2%).

### 2.4 User Experience & Trust Layer
- **Execution Audit Log**: Preserves all historical trade executions (500+ records) with live mark-to-market valuations and net PnL.
- **Accurate URLs**: Generates direct links to `https://polymarket.com/event/{event_slug}` using verified Gamma slugs.
- **Live Visuals**: Renders event icons and badges throughout the live execution tape and audit drawer.
