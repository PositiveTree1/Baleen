# E2E Test Infra: Baleen Quantitative Verification & Scenario Stress Matrix

## Test Philosophy
- Requirement-driven, opaque-box and white-box verification of all quantitative models and system invariants.
- 100% test coverage across R1, R2, R3, and R4 requirements:
  1. **R1 Slippage & Latency Invariant**: Guaranteed `slippage_bps > 0` on 100% of simulated executions across all 5 branches (direct buys, FIFO sells, split lots, out-of-order matches, onchain signals); non-null `latency_ms`; tick movement $\ge 0.0005$.
  2. **R2 Bayesian Sizing Stability Invariant**: Low-sample whales ($N < 15$, specifically $N=1, 2, 5$) have adjusted sleeve budget strictly bounded within $\pm 10\%$ ($900.00 to $1,100.00) of $1,000 base; smooth EMA scaling for $N \ge 15$.
  3. **R3 Timeframe Net Worth Synchronization**: Zero balance jumps between 1H, 1D, 1W, ALL timeframes; consistent last-of-bucket selection and Genesis baseline alignment.
  4. **R4 100% Test Pass Rate & Clean Build**: Full pytest pass rate across all test suites and 0-error frontend Next.js production build.

## Core Quantitative Test Invariants (Tier 0)
- `test_r1_universal_slippage`: Direct market buys, FIFO sells, split lots, OOO matches, and onchain signals.
- `test_r2_bayesian_sleeve_damping`: $N \in [0, 14]$ bounds, $N \ge 15$ convergence, single-trade shock resistance.
- `test_r3_portfolio_timeframe_sync`: 1H, 1D, 1W, ALL snapshot continuity, cold-cache isolation, zero balance glitching.

## Scenario Matrix Coverage (220 Scenarios)
### Tier 1: Order Book & Liquidity Extremes (55 Scenarios)
### Tier 2: Timing, Network & Settlement Dynamics (55 Scenarios)
### Tier 3: Complex Position & Lifecycle Sequences (55 Scenarios)
### Tier 4: Multi-Tenancy & Portfolio Scaling (55 Scenarios)

## Test Runners
- Backend Unit & Regression Suite: `& "c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\python.exe" -m pytest`
- Frontend Build Check: `cd frontend && npm.cmd run build`
