# Original User Request

## 2026-08-30T00:46:29Z

Deploy a specialized multi-agent engineering team to perform end-to-end verification, on-chain trade classification audit, dual-column chart rendering, and overnight paper-trading readiness across the entire Baleen codebase (`c:\Users\arthu\Documents\Baleen-master`).

Working directory: c:\Users\arthu\Documents\Baleen-master
Integrity mode: development

## Requirements

### R1. Authentic On-Chain Trade History & Real Classification
- Audit Polymarket Data API trade and position ingestion across all active candidate whales (`/positions`, `/activity`, `/trades`).
- Guarantee real date grouping, authentic profit/loss separation (`won_usd` vs `lost_usd`), and zero fabricated/synthetic data.
- Ensure all candidate whales are accurately classified with genuine on-chain win rates, Sharpe ratios, and copyability parameters.

### R2. Dual-Column Daily Wins & Losses Chart Rendering
- Update the frontend daily chart (`DailyWinLossBarChart.tsx`) to render true dual-column bars per day:
  - Green bar (`#00D09C`) for daily gross won profits (`wonUsd`)
  - Red bar (`#FF453A`) for daily gross losses (`lostUsd`)
- Ensure clean visual alignment, zero chart clipping across timeframes (1W, 1M, YTD, ALL), and accurate interactive tooltips.

### R3. Overnight Paper Trading Execution & State Machine Invariance
- Verify `live_poller.py` continuous polling loop, isolated $1,000 sleeve capacity, quadratic Polymarket fee gate, and slippage guards.
- Ensure automated rebalance, out-of-order sell matching, and zero memory leaks or unhandled task crashes for continuous 24/7 overnight operation.

## Acceptance Criteria

### Verification & Automated Tests
- [ ] 100% of backend tests pass (`pytest`).
- [ ] Next.js frontend builds with 0 TypeScript and 0 lint errors (`npm run build`).
- [ ] Dual-column daily win/loss charts render both gross wins and losses cleanly on every wallet profile.
- [ ] Live poller executes isolated sleeve sizing with 0 negative balances and 0 orphaned trades.
