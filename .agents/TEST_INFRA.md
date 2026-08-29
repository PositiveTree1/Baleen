# E2E Test Infra: Baleen 220-Scenario Stress Matrix & Invariant Monitor

## Test Philosophy
- Requirement-driven, opaque-box and white-box stress testing of all mathematical invariants and lifecycle edge cases.
- Invariant assertions monitored on every step:
  1. **Cash Non-Negativity**: $\text{Cash} \ge 0$.
  2. **Margin Invariance**: $\text{Free Cash} = \max(0, \text{Settled Cash} - \text{Open Margin})$.
  3. **High-Water Mark Monotonicity**: $\text{HWM}_{t+1} \ge \text{HWM}_t$.
  4. **FIFO Lot Splitting Conservation**: $\sum V_{\text{split}} = V_{\text{orig}}$ and $\sum \text{Fee}_{\text{split}} = \text{Fee}_{\text{orig}}$.
  5. **Fee Bounding**: $0.00 \le \text{Fee} \le 0.072 \times \text{Notional}$.
  6. **Zero Orphaned Positions**: No open BUY lots remaining after fully executed multi-leg SELLs.
  7. **Ghost Sell Prevention**: Users with 0 open positions are never charged fees or logged with fictitious SELLs.
  8. **Numerical & IEEE Safety**: Zero unhandled exceptions or zero-division crashes across $p=0.0$, volume $= 0$, and inverted spreads.

## Scenario Matrix Coverage (220 Scenarios)

### Tier 1: Order Book & Liquidity Extremes (55 Scenarios)
- S001-S010: Empty books, empty bids, empty asks, zero-liquidity fallbacks.
- S011-S020: Crossed/Inverted books, negative spreads, zero-spread top of book.
- S021-S030: Micro-liquidity ($0.01 depth), single-share levels, sub-penny dust.
- S031-S040: Whale order execution, multi-level sweeps, deep book exhaustion.
- S041-S050: Extreme price shocks (0.99 to 0.01, 0.01 to 0.99, flash crashes, binary extremes).
- S051-S055: Zero-price contracts ($p=0.00$), ceiling contracts ($p=1.00$), and boundary fee quantization.

### Tier 2: Timing, Network & Settlement Dynamics (55 Scenarios)
- S056-S065: Asynchronous block latency sweeps (1s, 5s, 15s, 30s, 60s, 120s lag).
- S066-S075: Out-of-order Envio HyperSync log delivery (SELL arriving before BUY, split events inverted).
- S076-S085: Duplicate transaction processing, re-ingestion, and idempotency guarantees.
- S086-S095: WebSocket disconnection/reconnection cycles, buffered event burst delivery.
- S096-S105: Abrupt RPC downtime, rate-limiting (429), and fallback failover.
- S106-S110: Binary resolution payouts ($1.00 / $0.00), condition ID redemption, and lot closure.

### Tier 3: Complex Position & Lifecycle Sequences (55 Scenarios)
- S111-S120: Multi-trade FIFO partial liquidations (10%, 25%, 33.3%, 50%, 75%, 90% lot splits).
- S121-S130: Interleaved BUY and SELL sequences on identical condition IDs across multiple whales.
- S131-S140: Multi-whale consensus triggers, tier upgrades (Gold Sniper vs Standard), and sizing multipliers.
- S141-S150: Multi-outcome market position management (Yes vs No opposing positions, split lots).
- S151-S160: Rapid rebalancing under fast-moving market marks and consecutive executions.
- S161-S165: Dormant wallet reactivation, high-frequency trader (HFT) filtering, and Wilson score tracking.

### Tier 4: Multi-Tenancy & Portfolio Scaling (55 Scenarios)
- S166-S175: Concurrent user execution across Conservative (5%), Balanced (10%), Aggressive (20%) profiles.
- S176-S185: Zero-balance and near-zero balance boundary states (skipping trades without crashing).
- S186-S195: Maximum drawdown limit enforcement, margin exhaustion, and auto-deleveraging.
- S196-S205: Large-scale concurrent user bursts (100+ simulated users executing simultaneously).
- S206-S215: High-Water Mark tracking across complex win/loss cycles and fee deductions.
- S216-S220: Multi-tenant portfolio reconciliation and audit state verification.

## Test Runner Architecture
- Location: `backend/tests/scenarios/`
- Command: `python -m pytest backend/tests/scenarios`
- Harness: Modular scenario runner with parametric fixtures, deterministic mock event sources, and invariant validator hooks.
