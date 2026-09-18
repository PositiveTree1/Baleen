# Baleen — Automated Polymarket Whale-Index Engine

> Mirror the Top 1% Polymarket Traders On Autopilot.

A consumer web app that runs a single, curated, auto-updating basket ("index") of top-performing Polymarket wallets. Users don't pick individual traders — they fund one account (virtual money in Phase 1) and the system mirrors every trade from every wallet currently in the basket, sized dynamically.

## Architecture

Current wallet strategy: [selection, accounting, copying and capital logic](docs/WALLET_STRATEGY_LOGIC.md), with the [original request preserved verbatim](docs/WALLET_STRATEGY_ORIGINAL_REQUEST.md). See the [API audit, curves and test results](docs/research/WALLET_DATA_AUDIT.md) for implemented small fixes and remaining validation. Historical specifications are archived and do not override this strategy.

Wallet data cutover: [implementation review](docs/WALLET_IMPLEMENTATION_REVIEW.md) and [Gemini deployment/reset instructions](docs/GEMINI_WALLET_CUTOVER.md). This cutover rebuilds wallet statistics while preserving financial records; it does not approve the proposed strategy for new allocations.

Current status and handoff: [live-readiness review](LIVE_READINESS_REVIEW.md), [Gemini finishing work](GEMINI_FINISHING_WORK.md), [scoped wallet setup](docs/SCOPED_WALLET_SETUP.md). Earlier reports are retained in [the archive](docs/archive/gemini/README.md). Live copying remains gated pending the work and evidence listed in the review.

```
Frontend (Next.js 14)  →  Backend API (FastAPI/Python)  →  PostgreSQL
                                    ↑
Signal Listener (Node.js)  →  Envio HyperSync (Polygon)
```

## Quick Start

### Prerequisites
- Node.js >= 18
- Python 3.12 (matching `backend/pyproject.toml`)
- npm

### Setup
```bash
# Install root dependencies
npm install

# Install all project dependencies
npm run setup

# Initialize the database
npm run db:init
```

### Development
```bash
# Start all services concurrently
npm run dev:all

# Or start individually:
npm run dev:frontend   # Next.js on :3000
npm run dev:backend    # FastAPI on :8000
npm run dev:listener   # Envio HyperSync listener
```

### Testing
```bash
# Run all tests
npm run test:all

# Or individually:
npm run test:backend
npm run test:listener
npm run test:frontend
```

### Deploying
Railway and Vercel are configured to deploy from pushed git commits. From the repo root:

```bash
# Commit all local changes and push the current branch to origin
npm run deploy -- "Describe the change"

# Or split the steps
npm run deploy:commit -- "Describe the change"
npm run deploy:push
```

Useful git helpers:

```bash
npm run git:status
npm run git:pull
npm run git:push
npm run git:log
```

## Project Structure

```
baleen/
├── frontend/          # Next.js 14 App Router (TypeScript, Tailwind, Framer Motion)
├── backend/           # Python FastAPI (scoring, sizing, discovery, analysis, API)
├── listener/          # Node.js/TypeScript (Envio HyperSync signal listener)
└── db/                # PostgreSQL schema reference
```

## Phase 1 (Current) — Sandbox/Demo
- Email signup, pick virtual starting balance
- Real market data, real trade signals, simulated fills
- Full trade-by-trade audit log
- AI-generated whale analysis (Groq/LLaMA)

## Phase 2 (Future) — Live Trading
- Embedded-wallet delegated signing (Magic/Privy)
- Real order construction and CLOB submission
- Performance-fee billing (high-water mark model)
