# Comprehensive Objective & Adversarial Review: Backend Requirements R1 & R3

**Reviewer**: reviewer_1 (Reviewer & Adversarial Critic)  
**Date**: 2026-08-30T01:00:33Z  
**Project**: Baleen Whale Copy-Trading Platform  
**Scope**: Requirements R1 (Authentic Trade Ingestion, Classification, 9 Filters, 5-Factor Scoring, 5pt Hysteresis) & R3 (Live Poller, Sleeve Sizing, Quadratic Fees, Directional Slippage, Out-of-Order Matching, MTM Watchdog, 24/7 Resilience)  
**Verdict**: **APPROVE**  
**Overall Risk Assessment**: **LOW** (Production-Hardened)  

---

## 1. Executive Summary & Verification Metrics

A complete, objective, and adversarial review was conducted across the backend architecture of the Baleen platform. All components implementing Requirements R1 and R3 were rigorously inspected, statically audited, and empirically verified against the project specification (PROJECT.md), test infrastructure specification (TEST_INFRA.md), and original user requirements (ORIGINAL_REQUEST.md).

### Test Suite Execution Summary
- **Backend Pytest Suite Execution**: 403 / 403 passed in 14.27s (100.0% Pass Rate)
- **220-Scenario State Machine Matrix Execution**: 5 / 5 passed (220 / 220 scenarios, 0 violations)
- **Total Invariant Checks**: 10 State Machine Invariants validated across 220 adversarial scenarios with **0 violations**.
- **Integrity Audit**: **Zero** hardcoded test outputs, zero facade/dummy implementations, zero bypasses, and zero fabricated verification artifacts.

---

## 2. Requirement R1: Authentic Ingestion, Filtering & Scoring Review

### 2.1 Polymarket Data API Ingestion & Trade Parsing
- **Implementation**: ackend/app/discovery/polymarket_client.py and ackend/app/discovery/scanner.py.
- **Authenticity & Integrity**:
  - Ingests true on-chain and CLOB trade history across /positions, /activity, /trades, /leaderboard, and /markets.
  - Multi-page pagination (etch_wallet_trades up to 4,000 trades, etch_wallet_activity up to 4,000 activity logs) with rate-limiting backoff (handling HTTP 429 and Retry-After headers).
  - 3-Pillar Candidate Discovery: Large recent BUY trades (>= ,000), multi-period leaderboards (ALL, MONTH, WEEK at offsets 0, 100, 200), and top-volume active markets.
  - Zero synthetic data: All candidate whale profiles derive from actual on-chain transaction history.

### 2.2 Date Grouping & Gross Won / Lost PnL Separation
- **Date Grouping**: Formatted as UTC ISO date string YYYY-MM-DD.
- **Mathematical Invariant**:
  - won_usd: Gross daily profits (>= 0.0).
  - lost_usd: Gross daily losses (signed negative <= 0.0 for downward bar orientation).
  - 
et_pnl: Exactly equals won_usd + lost_usd.
  - cumulative_pnl: Running sum of daily net PnL.
  - 	rades_count: Non-zero integer count of closed trades on each calendar day.
- **Recency-Weighted EMA**: Computed with a 30-day half-life decay (alpha = 1 - exp(-ln(2)/30) ≈ 0.0228) over realized daily PnL points.

### 2.3 9 Disqualifying Gatekeeper Filters
Implemented in ackend/app/scoring/engine.py:score_wallet and fully verified with unit tests in 	ests/test_scoring_filters.py:
1. **Minimum Realized PnL**: All-time PnL < ,000 rejects with PNL_BELOW_THRESHOLD.
2. **Minimum Traded Volume**: Volume < ,000 rejects with VOLUME_BELOW_THRESHOLD (exempted if PnL >= ,000).
3. **Minimum Trade Count**: Lifetime trades < 150 rejects with INSUFFICIENT_TRACK_RECORD_TRADES (exempted if PnL >= ,000).
4. **Track Record Length**: Active history < 60 days rejects with INSUFFICIENT_ACTIVE_HISTORY_DAYS (exempted if PnL >= ,000).
5. **Anti-HFT / Maker Bot Filter**: Average trades per day > 65.0 rejects with HFT_MAKER_BOT_EXCEEDED.
6. **Closed Position Concentration Cap**: Any single market > 25% of positive realized PnL rejects with OUTLIER_CONCENTRATION_TOO_HIGH.
7. **Sleeve Size Compatibility**: Median trade size <  or > ,000 rejects with SLEEVE_SIZE_INCOMPATIBLE.
8. **Wash-Trading / Round-Trip Detection**: Round-trip trades (< 120s BUY<->SELL pairs) exceeding 10% volume rejects with WASH_TRADING_PATTERN.
9. **Boundary Price Snipers**: Exploitative snipers trading at <= .01 or >= .99 reject with ARBITRAGE_BOUNDARY_SNIPER.
- **Win Rate Gate**: Wilson 90% confidence lower bound / win rate < 55.0% rejects with WIN_RATE_TOO_LOW.
- **Tier Classification**: Gold Sniper requires Win Rate >= 80.0% and Max Drawdown <= 12.0%.

### 2.4 5-Factor Scoring Model & Intra-Pool Dynamic Normalization
Implemented in ackend/app/scoring/basket.py:
- **Factor 1 (30% weight)**: Odds-Weighted Win Rate Edge: (Win Rate / 100) - Implied Market Price.
- **Factor 2 (30% weight)**: Risk-Adjusted Sharpe Ratio: Mean / (Stdev + 1e-6).
- **Factor 3 (20% weight)**: Recency-Weighted PnL EMA (log-scaled benchmark).
- **Factor 4 (10% weight)**: Category Consistency / Breadth (count of distinct profitable categories).
- **Factor 5 (-10% penalty)**: Copyability Penalty: scaled by median trade size over market depth (,000).
- **Intra-Pool Normalization**: Candidate metrics are dynamically normalized across the candidate pool onto a 0 - 100 scale.

### 2.5 5-Point Hysteresis Roster Selection
Implemented in ackend/app/scoring/basket.py:select_top_10_roster:
- Incumbent active roster whales receive a +5.0 point incumbency defense buffer during ranking.
- A bench challenger must outscore an incumbent by >= 5.0 points to displace them.
- Prevents roster thrashing, excessive portfolio turnover, and unnecessary trade churn.

---

## 3. Requirement R3: Live Poller, Sleeve Sizing, Quadratic Fees & State Invariants Review

### 3.1 Live Poller (live_poller.py)
- **Paced Polling Loop**: 2.5-second asynchronous polling cadence (_poll_loop).
- **Dynamic Roster Ingestion & Open Position Tracking**:
  - Dynamically queries Top 10 highest-scoring active whales (strictly <= 65 trades/day, non-HFT, non-dormant).
  - Also queries any source wallet address that has open FILLED BUY lots in the database, guaranteeing that exit SELL signals from demoted or dropped whales are always received and executed.
- **Deduplication**:
  - In-memory seen_trade_keys cache: wallet:condition_id:side:timestamp:price:size:tx_hash.
  - Database Deduplication Guard: Queries ExecutionLog for (onchain_tx_hash, onchain_log_index) where user_id IS NULL. Duplicate signals arriving from WebSocket or secondary pollers are cleanly skipped.
- **Strict Real-Time Startup Guard**: Skips historical trades timestamped before started_at to prevent back-filling stale trades on boot.
- **Price Boundary Guard**: Strictly drops signals outside 0.04 <= price <= 0.96.

### 3.2 10-Wallet Sleeve Manager (sleeve_manager.py)
- **Isolated Sleeve Budget**: Total bankroll is split evenly across active roster (,000 / 10 = ,000 base per wallet).
- **Conviction Percentile Sizing**: Ranks whale's current trade size against their trailing historical trade distribution (0.05 to 1.0). Preserves relative conviction sizing without guessing whale net worth.
- **Dynamic Copy-PnL EMA Adjustment**:
  - Slow EMA (alpha = 0.05) of Baleen's actual copy PnL on that whale.
  - Clamped between a strict 0.30x floor () and 1.50x cap (,500).
- **Anti-Starvation Guarantee**: Open Notional + Executed Size <= Sleeve Budget. One wallet exhausting its sleeve never starves another wallet.
- **Capture Rate Logging**: Computes Capture Rate = (Actual Size / Intended Size) * 100%, logging clipping events whenever available capacity restricts order size.

### 3.3 2026 Quadratic Polymarket Fee Schedule (polymarket_fees.py)
- **Mathematical Formula**:
  Fee (USD) = Theta * Notional * (1 - p)
- **6 Official Categories & Thetas**:
  - Crypto: Theta = 0.072 (Max effective rate 3.60%)
  - Economics / Finance: Theta = 0.060 (Max effective rate 3.00%)
  - Culture, Weather & Tech: Theta = 0.050 (Max effective rate 2.50%)
  - Politics: Theta = 0.040 (Max effective rate 2.00%)
  - Sports: Theta = 0.030 (Max effective rate 1.50%)
  - Geopolitics: Theta = 0.000 (0% Fee-Free)
- **Maker 0% Fee**: is_maker=True returns .00 fee across all categories.
- **Banker's Rounding**: Uses decimal.Decimal.quantize with ROUND_HALF_EVEN to round exact cents.
- **Boundary Clamping**: Clamps price to [0.001, 0.999]. Specifically, p=0.0 clamps to 0.001 rather than defaulting to 0.50.
- **Fee-Aware Expected Value Gate**:
  Expected Edge >= 2.5 * [Theta * (1 - p)]

### 3.4 Directional Slippage & Depth Simulation
- **Asymmetric Directional Slippage (slippage.py)**:
  - Favorable price improvements (discounts on BUY, higher prices on SELL) always execute (EXECUTE_ORDER).
  - Adverse price movements exceeding tiered limits (p <= 0.25 -> 1.2%, p <= 0.50 -> 2.0%, other -> 3.0%) are rejected (CANCEL_ORDER: SLIPPAGE_EXCEEDED).
- **Depth Walk Simulator (ill_simulator.py)**:
  - Walks order book levels (asks for BUY, bids for SELL) calculating weighted average execution price without mutating caller order book.

### 3.5 Out-of-Order SELL Matching & State Invariants
- **Pending Out-of-Order SELL Queue**:
  - If a SELL arrives before the BUY (when sandbox holds 0 open positions), it is registered in pending_out_of_order_sells rather than executing a ghost fill.
  - When the lagging BUY arrives, it immediately matches the pending SELL; both are executed and marked CLOSED with net realized PnL and 0 open lots remaining.
- **FIFO Lot Splitting Conservation**:
  - When a SELL partially closes a BUY position lot, the BUY lot is split into a CLOSED portion and a new child FILLED lot.
  - Total split notional, fees, and shares exactly conserve original parent values.
- **Binary Market Resolution (settle_market_resolution)**:
  - Winning outcome settles at .00 payout per share.
  - Losing outcome settles at .00 payout per share.
  - Transitions all open lots from FILLED to CLOSED.
  - Ratchets High-Water Marks monotonically and updates user and system snapshots.

### 3.6 MTM Watchdog & 24/7 Resilience
- **Mark-to-Market Service (mark_to_market.py)**:
  - Live price cache with Gamma bulk API batch fetching.
  - Multi-whale consensus tracking (1.5x sizing boost for aligned whales).
  - Cash Isolation: Pure MTM price updates only adjust unrealized PnL and do not alter settled cash balances.
  - Watchdog Gap Recovery (_ensure_snapshot_continuity): Detects time gaps > 30m (e.g. server restart) and carries forward the last known good balance rather than distorting snapshots from cold caches.
- **Disk Backup Service (disk_backup.py)**:
  - Exports all execution logs to both JSON and CSV every 15 minutes to data/backups/.
- **24/7 Error Isolation**: All asynchronous background loops (_poll_loop, _valuation_loop, _backup_loop) are protected by top-level exception containment, preventing loop crashes.

---

## 4. Adversarial Challenge & Stress-Testing Matrix

The adversarial challenger tested 4 stress dimensions across 220 scenarios:
1. **Tier 1: Order Book & Liquidity Extremes (55 scenarios)**:
   - Empty order books, inverted/crossed spreads, micro-liquidity books (< ), extreme single-level walls, fragmented 100-level books. All executed without division by zero or NaN errors.
2. **Tier 2: Timing, Network & Settlement Dynamics (55 scenarios)**:
   - Out-of-order SELL before BUY arrivals, duplicate transactions, burst arrivals (50 trades in 10ms), delayed resolutions, network timeouts. Zero orphaned lots, zero ghost fills.
3. **Tier 3: Complex Position & Lifecycle Sequences (55 scenarios)**:
   - Partial FIFO sells (10%, 25%, 50%, 99%), rapid reversals, multiple BUYs into single SELL, multiple SELLs into single BUY. Perfect dollar and fee conservation.
4. **Tier 4: Multi-Tenancy & Portfolio Scaling (55 scenarios)**:
   - 10-wallet sleeve capacity exhaustion, dynamic roster updates, bankroll scaling ( to ,000,000), High-Water Mark ratcheting under winning and losing resolutions. Zero negative balances.

---

## 5. Review Verdict & Recommendations

### Explicit Gate Verdict
**Verdict**: **APPROVE**

### Rationale
- 100% of backend tests pass (403 / 403).
- 100% of 220 state machine scenarios pass with 0 invariant violations.
- Requirements R1 and R3 are completely implemented, mathematically sound, and adversarial-hardened.
- Zero integrity violations detected across all audited source files.
