# Original User Request

## 2026-08-29T22:21:35Z

Deploy a specialized multi-agent team to perform comprehensive scenario stress testing, invariant verification, quantitative audit, and cross-platform frontend UI validation across the entire Baleen codebase (`c:\Users\arthu\Documents\Baleen-master`).

Working directory: c:\Users\arthu\Documents\Baleen-master
Integrity mode: development

## Requirements

### R1. Quantitative Filter & Scoring Verification
Audit all newly implemented gatekeeper filters and 5-factor scoring in `backend/app/discovery/scanner.py`, `backend/app/scoring/engine.py`, and `backend/app/scoring/basket.py`:
- 150+ lifetime trades & 60+ active days
- Anti-HFT / Maker-Rebate (<= 15 trades/day)
- Closed position concentration cap (<= 25% of positive realized PnL)
- Minimum scale (>= $50k PnL, >= $150k volume)
- Sleeve size compatibility ($20 to $3,000 median trade size)
- Wash-trading detection (<120s BUY<->SELL pairs <= 10%)
- Intra-pool normalization (0-100 min-max across candidate pool)
- Top 10 roster selection with 5-point hysteresis buffer

### R2. Multi-Scenario Stress & Invariant Validation
Execute 200+ operational, market, and execution scenarios:
- Sleeve isolation and zero capital starvation between wallets
- Cash invariance (no negative balances or MTM phantom cash inflation)
- Quadratic Polymarket taker fee invariance across all 6 asset categories
- Zero division safety on zero-volume / single-trade inputs

### R3. Cross-Platform Frontend UI & Responsiveness Audit
Inspect all Next.js dashboard components in `frontend/src/`:
- Test mobile (375px), tablet (768px), and desktop (1440px) viewports
- Ensure zero text overlap, smooth drawer transitions, clean daily win/loss charts, and flawless theme toggling

## Acceptance Criteria
- [ ] 100% of backend tests pass (`pytest`).
- [ ] All edge case failures or logic leaks are documented and fixed.
- [ ] Frontend dashboard renders cleanly across all viewports without visual overlap or layout breaks.
