# Original User Request

## Initial Request — 2026-08-31T00:29:31Z

Deploy a specialized multi-agent engineering team to perform root-cause resolution, quantitative modeling, and rigorous testing across the Baleen trading system (`c:\Users\arthu\Documents\Baleen-master`).

Working directory: c:\Users\arthu\Documents\Baleen-master
Integrity mode: development

## Requirements

### R1. Universal 100% Polymarket CLOB Fill Slippage Modeling
- Audit every execution path in `backend/app/services/live_poller.py` (direct market buys, FIFO sells, split lots, out-of-order buy/sell matches, and onchain signals).
- Ensure realistic CLOB depth and spread walk slippage is applied universally across 100% of simulated fills (guaranteeing `slippage_bps > 0` on every market execution, with no zero-slippage fallback bypasses).

### R2. Sample-Size Damped Dynamic Sleeve Budget Sizing
- Audit the dynamic sleeve adjustment calculation in `backend/app/sizing/sleeve_manager.py` and the Supabase audit views.
- Implement a Bayesian credibility / sample-size shrinkage prior ($N < 15$ trades) so low-trade-count whales (e.g. `SitsToPee` with 2 trades) remain anchored near their $1,000 base sleeve and cannot have their budget violently slashed by 70% without statistically significant sample evidence.
- Ensure EMA adjustments scale smoothly over dozens of trades with bounded per-trade adjustment sensitivity.

### R3. Portfolio Timeframe & Net Worth Synchronization
- Audit mark-to-market snapshot generation in `backend/app/services/mark_to_market.py` and `/api/portfolio/snapshots` in `backend/app/api/execution_logs.py`.
- Resolve the timeframe fluctuation bug where switching between `1H`, `1D`, and `ALL` causes the portfolio balance to jump or glitch between $9.6k and $10.1k.
- Ensure the header balance counter, time-series chart endpoints, and Supabase snapshot records are mathematically aligned with zero temporal valuation discrepancies.

### R4. Automated Testing & Verification Suite
- Add comprehensive regression test suites in `backend/tests/` covering:
  1. Universal non-zero slippage across all 5 execution branches.
  2. Sleeve budget stability on low sample sizes ($N = 1, 2, 5$).
  3. Consistent timeframe snapshot querying with zero valuation jumps.
- Verify 100% test pass rate across the full pytest suite.

## Acceptance Criteria

### Quantitative Integrity & Simulation Realism
- [ ] 100% of simulated fills in `live_poller.py` execute with non-zero CLOB slippage and non-null `latency_ms`.
- [ ] Whales with $< 15$ trades have their adjusted sleeve budget anchored within $10\%$ of base budget ($900–$1,100).
- [ ] Portfolio snapshots across `1H`, `1D`, `1W`, and `ALL` timeframes return consistent, non-glitching net worth curves.
- [ ] 100% of backend tests pass (`pytest`).
- [ ] Next.js frontend builds with 0 errors (`npm run build`).
