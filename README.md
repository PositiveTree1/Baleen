# Baleen — Automated Polymarket Whale-Index Engine

> Mirror the Top 1% Polymarket Traders On Autopilot.

A consumer web app that runs a single, curated, auto-updating basket ("index") of top-performing Polymarket wallets. Users don't pick individual traders — they fund one account (virtual money in Phase 1) and the system mirrors every trade from every wallet currently in the basket, sized dynamically.

## Architecture

```
Frontend (Next.js 14)  →  Backend API (FastAPI/Python)  →  PostgreSQL
                                    ↑
Signal Listener (Node.js)  →  Envio HyperSync (Polygon)
```

## Quick Start

### Prerequisites
- Node.js >= 18
- Python >= 3.11
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
