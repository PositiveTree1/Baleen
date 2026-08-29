# Paper Trading Simulation & Quantitative Mathematical Audit Report (Reviewer 2)

**Working Directory**: `c:\Users\arthu\Documents\Baleen-master`  
**Agent Metadata Directory**: `c:\Users\arthu\Documents\Baleen-master\.agents\reviewer_sim_and_math\`  
**Timestamp**: 2026-08-29T11:12:00Z  
**Reviewer**: Reviewer 2 (Simulation & Quantitative Math Reviewer)  
**Roles**: Reviewer, Adversarial Critic  
**Verdict**: **REQUEST_CHANGES** (Integrity Violations, Simulation Bypasses, and Mathematical Logic Errors)

---

## 1. Observation

A rigorous, independent quantitative and forensic audit of 100% of the mathematical modeling, paper trading simulation, statistical scoring, fee structures, and execution accounting components across the Baleen codebase was conducted.

### 1.1 Summary of Reviewed Code Artifacts

| Component | File Path | Core Mathematical / Simulation Responsibility |
|---|---|---|
| **Live Trade Mirror** | `backend/app/services/live_poller.py` | Real-time whale trade copy engine, slippage guard, EV gate filtering, PnL accounting, free cash balance enforcement. |
| **Mark-to-Market Engine** | `backend/app/services/mark_to_market.py` | Continuous valuation loop, unrealized MTM PnL calculation, consensus tracking, portfolio snapshot persistence. |
| **Dynamic Fee Schedule** | `backend/app/services/polymarket_fees.py` | Official 2026 Polymarket dynamic quadratic taker fee formula, banker's rounding, market classification, fee-aware EV gate. |
| **Fill Simulator** | `backend/app/sizing/fill_simulator.py` | Order book depth walking, price-weighted average fill computation, depth liquidity consumption. |
| **Slippage Model** | `backend/app/sizing/slippage.py` | Price divergence thresholds and execution blocking. |
| **Dynamic Sizer** | `backend/app/sizing/dynamic_sizer.py` | Proportional dynamic trade sizing across active basket members with user risk caps. |
| **Whale Scanner** | `backend/app/discovery/scanner.py` | Wilson score lower bound calculation, peak-to-trough drawdown, holding duration, 2-stage discovery evaluation. |
| **Scoring Engine** | `backend/app/scoring/engine.py` | 4-filter gating rules (PnL, Anti-HFT, outlier concentration, win rate) and Gold Sniper tier classification. |
| **Basket Rescoring** | `backend/app/scoring/basket.py` | Multi-horizon rolling consistency scoring (1d, 3d, 7d) and 24h basket membership maintenance. |
| **Dormancy Model** | `backend/app/scoring/dormancy.py` | Relative cadence dormancy threshold ($8 \times \text{median inter-trade gap}$). |
| **Frontend Profit Simulator**| `frontend/src/components/landing/ProfitSimulator.tsx` | Interactive marketing compounding calculator. |
| **Ingestion Listener Parser**| `listener/src/event-processor.ts` | Polygon CTF Exchange `OrderFilled` ABI decoding, side mapping, and token extraction. |

---

### 1.2 Verbatim Observations & Mathematical Forensic Findings

#### Finding 1 (Critical - Integrity Violation): User Realized PnL Double-Counting on Closed Trades
- **Location**: `backend/app/services/live_poller.py#L331-L355` and `backend/app/services/mark_to_market.py#L237-L244`
- **Verbatim Code in `live_poller.py`**:
  ```python
  # Lines 331-334
  u_earliest_buy.status = "CLOSED"
  u_earliest_buy.realized_pnl_usd = round(u_orig_notional * u_ratio - float(u_earliest_buy.fee_usd or 0.0), 2)
  u_realized_pnl_val = round(u_notional * u_ratio - float(u_fee["fee_usd"]), 2)

  # Lines 335-356
  user_log = ExecutionLog(
      user_id=u.id,
      side="SELL",
      status="CLOSED",
      realized_pnl_usd=u_realized_pnl_val,
      ...
  )
  db.add(user_log)
  ```
- **Verbatim Code in `mark_to_market.py`**:
  ```python
  # Lines 237-240
  u_logs = [l for l in all_logs if l.user_id == u.id]
  if not u_logs:
      u_logs = platform_logs
  u_pnl = sum(float(l.realized_pnl_usd or 0.0) for l in u_logs)
  ```
- **Direct Observation**:
  When a user's open BUY position is closed by a whale SELL signal:
  1. The original BUY log (`u_earliest_buy`) is set to `status = "CLOSED"` with `realized_pnl_usd = u_orig_notional * u_ratio - u_earliest_buy.fee_usd`.
  2. The new exit SELL log (`user_log`) is also marked `status = "CLOSED"` with `realized_pnl_usd = u_notional * u_ratio - u_fee["fee_usd"]`.
  3. In `mark_to_market.py`, `sum(l.realized_pnl_usd)` iterates over all user logs in `u_logs`. Because both `u_earliest_buy` and `user_log` have non-null `realized_pnl_usd`, the realized return is summed twice ($200\%$).
  4. In contrast, for system execution (`user_id is None`), line 279 explicitly sets `sys_realized_pnl_val = None`, properly recording PnL only on `earliest_buy`.
- **Empirical Proof**:
  A $100 notional BUY entry at $0.50 closed at $0.70 (+40% gross = +$40.00 gross profit, $3.60 entry fee, $2.16 exit fee, True Net = +$34.24):
  - `u_earliest_buy.realized_pnl_usd` = $40.00 - $3.60 = $36.40
  - `user_log.realized_pnl_usd` = $40.00 - $2.16 = $37.84
  - Total `u_pnl` recorded = $36.40 + $37.84 = **$74.24** (an overstatement of +$40.00, or +116.8% over true net profit).

---

#### Finding 2 (Critical - Mathematical Flaw / Integrity): Inverted Fee-Aware EV Gate Replaces Alpha with Market Extremity
- **Location**: `backend/app/services/live_poller.py#L204-L218` and `backend/app/services/polymarket_fees.py#L138-L154`
- **Verbatim Code in `live_poller.py`**:
  ```python
  # Line 205
  expected_edge = abs(effective_fill_price - 0.5)
  ev_pass, fee_rate, min_edge = calculate_fee_aware_ev_gate(effective_fill_price, title, expected_edge)
  ```
- **Verbatim Code in `polymarket_fees.py`**:
  ```python
  # Lines 146-152
  _, theta = classify_market_category(market_title)
  p = max(0.001, min(0.999, float(price or 0.5)))
  fee_rate = theta * (1.0 - p)
  min_required_edge = 2.5 * fee_rate
  should_pass = (expected_edge >= min_required_edge)
  ```
- **Direct Observation**:
  `expected_edge` is defined as `abs(p - 0.5)`. This is the market price's distance from 50% (price extremity / market certainty), **not** the copy-trader's expected alpha ($\alpha = E[\text{Win}] - p$).
- **Mathematical Stress Test / Attack Scenarios**:
  - **Attack Scenario A (High Alpha Toss-up Market)**:
    Whale with verified 80% win rate ($W = 0.80$) buys an undervalued 50/50 race at $p = 0.51$. True expected edge is $\alpha = 0.80 - 0.51 = +0.29$ (29.0% positive EV).
    The code calculates `expected_edge = abs(0.51 - 0.50) = 0.01` (1.0%).
    For Crypto ($\Theta = 0.072$), $\text{min\_edge} = 2.5 \times 0.072 \times (1 - 0.51) = 0.0882$ (8.82%).
    Because $0.01 < 0.0882$, the EV gate **rejects** this high-alpha trade.
  - **Attack Scenario B (Negative Alpha Extreme Favorite)**:
    Whale with 85% win rate buys a heavy favorite at $p = 0.95$. True expected edge is $\alpha = 0.85 - 0.95 = -0.10$ (10.0% negative EV).
    The code calculates `expected_edge = abs(0.95 - 0.50) = 0.45` (45.0%).
    $\text{min\_edge} = 2.5 \times 0.072 \times (1 - 0.95) = 0.009$ (0.9%).
    Because $0.45 \ge 0.009$, the EV gate **approves** this negative-EV trade.

---

#### Finding 3 (High Severity - Simulation Bypass): Production Disconnection of Fill Simulator, Dynamic Sizer, and Slippage Models
- **Location**: `backend/app/services/live_poller.py#L188-L255`
- **Direct Observation**:
  1. **Order Book Walking Bypassed**: `simulate_fill()` in `backend/app/sizing/fill_simulator.py` is never called. `live_poller.py` fills orders instantaneously at `effective_fill_price = live_p` without order book depth consumption or partial fill modeling.
  2. **Dynamic Sizing Bypassed**: `size_trade()` in `backend/app/sizing/dynamic_sizer.py` is never called. Sizing is hardcoded to `min(max(10.0, cash_usd * 0.1 * multiplier), 350.0)`. User risk profile (`conservative`, `balanced`, `aggressive`) is completely ignored.
  3. **Directional Slippage Logic Bug**: `check_slippage()` in `backend/app/sizing/slippage.py` uses `diff = abs(current_price - whale_price) / whale_price`. On a BUY order, if market price drops from $0.20 to $0.18 (a 10% favorable price discount), `diff = 0.10 > 0.012`, causing the function to return `'CANCEL_ORDER: SLIPPAGE_EXCEEDED'`.

---

#### Finding 4 (High Severity - Pipeline Ingestion): Listener CTF Exchange Event Inversion and Asset ID "0" Bug
- **Location**: `listener/src/event-processor.ts#L71-L85`
- **Verbatim Code**:
  ```typescript
  if (isTakerBasket) {
    side = 'BUY';
    walletAddress = takerLower;
    assetId = event.makerAssetId;
    amountFilled = event.makerAmountFilled;
  } else {
    side = 'SELL';
    walletAddress = makerLower;
    assetId = event.makerAssetId;
    amountFilled = event.makerAmountFilled;
  }
  const price = '0'; // Placeholder
  ```
- **Direct Observation**:
  In Polygon CTF Exchange `OrderFilled` events, USDC collateral is represented by token ID `0`.
  1. If a whale sells outcome tokens to a Maker bidding USDC collateral, `makerAssetId = "0"`. The parser assigns `assetId = "0"`, discarding the actual token ID (`takerAssetId`).
  2. The parser assumes Taker is always `BUY`, setting `side = 'BUY'` even when Taker is selling conditional tokens.
  3. `price` is hardcoded to `'0'`, causing `backend/app/services/live_poller.py#L425` to fall back to `0.50`.
  4. `timestamp` uses local Node.js time `Date.now()` instead of Polygon block timestamp.

---

#### Finding 5 (Medium Severity - Integrity / Synthetic Fabrication): Synthetic Win Rate and Wilson Score Assignment
- **Location**: `backend/app/discovery/scanner.py#L116-L122`
- **Verbatim Code**:
  ```python
  if total_resolved >= 3:
      win_rate = round((wins / total_resolved) * 100.0, 1)
      wilson_lb = calc_wilson_lower_bound(wins, total_resolved)
  elif all_time_pnl > 50000.0:
      win_rate = 72.0
      wilson_lb = 62.0
  else:
      win_rate = 58.0
      wilson_lb = 50.0
  ```
- **Direct Observation**: When a candidate whale has `< 3` resolved positions in `/positions`, the scanner fabricates synthetic statistics (72.0% / 62.0% or 58.0% / 50.0%) rather than computing authentic metrics from historical activity redemptions or applying small-sample uncertainty penalties.

---

#### Finding 6 (Medium Severity - Synthetic Simulation): MD5 Pseudo-Random PnL History Synthesis in `wallets.py`
- **Location**: `backend/app/api/wallets.py#L318-L393`
- **Direct Observation**: When `cached_daily_pnl` is empty, `get_wallet()` hashes the wallet address with MD5 (`addr_seed = int(hashlib.md5(clean_addr.encode()).hexdigest()[:8], 16)`) and generates a synthetic 45-day daily PnL curve scaled to match `wallet.all_time_pnl_usd`.

---

#### Finding 7 (Medium Severity - Code Defect): Unreachable Dead Code with Undefined Variables in `scanner.py`
- **Location**: `backend/app/discovery/scanner.py#L327-L350`
- **Direct Observation**: Lines 327-350 in `calculate_authentic_wallet_stats` follow line 325 `return {...}`. They reference undeclared variables (`realized_pnl`, `total_trades_count`, `volume`, `trades_per_hour`, `is_hft`).

---

#### Finding 8 (Medium Severity - Scoring Consistency): Threshold Inconsistencies and Pytest Failures in `engine.py`
- **Location**: `backend/app/scoring/engine.py#L25-L41`
- **Direct Observation**:
  - `engine.py` line 26 sets anti-HFT threshold to `> 300` trades/day (spec requires `> 100`).
  - `engine.py` line 38 sets Gold Sniper drawdown to `<= 15.0%` (spec requires `<= 10.0%`) and includes `or (pnl >= 100000 and win_rate >= 70.0)`, bypassing drawdown rules.
  - This causes 3 test failures in `backend/tests/test_scoring_filters.py`.
  - Inconsistency: `scanner.py` admits wallets with PnL $\ge \$25,000$, but nightly rescore in `basket.py` calls `score_wallet()` which rejects wallets with PnL $<\$50,000$.

---

#### Finding 9 (Medium Severity - Quantitative Realism): Unconstrained Compounding in Profit Simulator
- **Location**: `frontend/src/components/landing/ProfitSimulator.tsx#L14-L15`
- **Verbatim Code**:
  ```typescript
  const baseGrowthFactorPerMonth = 2.815;
  const projectedBalance = initialCapital * Math.pow(baseGrowthFactorPerMonth, timeHorizonMonths);
  ```
- **Direct Observation**: Applies an unconstrained monthly multiplier of $2.815\times$ ($+181.5\%$/mo). A $1,000 starting balance over 12 months projects $\$243,365,684$, ignoring market liquidity caps, adverse slippage, and fee drag.

---

#### Finding 10 (Medium Severity - Accounting Realism): Unrealized MTM Gains Treated as Liquid Cash
- **Location**: `backend/app/services/live_poller.py#L237` and `backend/app/services/mark_to_market.py#L213`
- **Direct Observation**: `free_cash = max(0.0, total_portfolio_equity - current_open_notional)`. Because `total_portfolio_equity` incorporates unrealized mark-to-market gains from `mark_to_market.py`, paper trading allows purchasing new positions using unrealized paper gains before settlement.

---

## 2. Logic Chain

1. **PnL Double-Counting Logic**:
   - In `live_poller.py`, closing a trade assigns net PnL to `u_earliest_buy.realized_pnl_usd` AND `user_log.realized_pnl_usd`.
   - In `mark_to_market.py`, user balance is computed by summing `realized_pnl_usd` across all user execution logs.
   - Therefore, the user's realized profit or loss is counted twice for every closed position.

2. **EV Gate Inversion Logic**:
   - Expected edge is quantitatively defined as $\alpha = E[P] - p$.
   - In `live_poller.py`, expected edge is computed as `abs(p - 0.5)`.
   - Distance from 0.50 measures price extremity, not edge.
   - Therefore, the EV gate rejects true alpha on toss-up contracts and accepts negative-EV positions on extreme favorites.

3. **Simulation Disconnect Logic**:
   - The specification requires order book depth walking, latency-penalized fill simulation, and dynamic sizing.
   - `live_poller.py` bypasses `simulate_fill()`, `size_trade()`, and `check_slippage()`, filling all orders at `effective_fill_price = live_p`.
   - Therefore, the simulation assumes infinite liquidity and zero slippage.

4. **Listener Ingestion Inversion Logic**:
   - In CTF exchange contracts, USDC collateral is token ID `0`.
   - `event-processor.ts` unconditionally assigns `makerAssetId` without checking if it is `0`, sets price to `0`, and assumes taker is always `BUY`.
   - Therefore, on-chain signal ingestion corrupts token IDs and flips trade directions.

---

## 3. Caveats

- Live Polymarket CLOB endpoints (`https://clob.polymarket.com/book`) were evaluated based on official API schemas and local unit tests; rate limits were not stressed.
- Groq AI Copilot and Analysis workers depend on valid API keys (`GROQ_API_KEY`); fallback mechanisms operate deterministically when keys are unset.
- Local tests execute on SQLite via `aiosqlite`; production uses PostgreSQL via `asyncpg`.

---

## 4. Conclusion & Audit Verdict

### Overall Verdict: **REQUEST_CHANGES**

The Baleen codebase contains critical quantitative and simulation flaws that must be remediated before production readiness:

### Summary of Findings & Remediation Requirements

| Finding ID | Severity | Category | Target File & Line | Summary | Required Remediation |
|---|---|---|---|---|---|
| **ISS-SIM-01** | **CRITICAL** | Accounting / Simulation | `live_poller.py#L331-L355` | User Realized PnL Double-Counting | Set `realized_pnl_usd` only on the closed BUY log; set SELL log `realized_pnl_usd = None`. |
| **ISS-SIM-02** | **CRITICAL** | Quantitative / EV Gate | `live_poller.py#L205` | Fee-Aware EV Gate Inversion | Compute $\alpha = \max(0.0, W_{\text{whale}} - p)$ using whale's Wilson lower bound. |
| **ISS-SIM-03** | **HIGH** | Simulation Realism | `live_poller.py#L188-L255` | Sizing & Fill Models Bypassed | Integrate `size_trade()` and `simulate_fill()` directly into live poller. |
| **ISS-SIM-04** | **HIGH** | Pipeline / Listener | `event-processor.ts#L71-L85` | Asset ID 0 & Side Inversion | Identify collateral (`0`), assign conditional token ID, compute price from fill amounts. |
| **ISS-SIM-05** | **MEDIUM** | Quantitative Integrity | `scanner.py#L116-L122` | Synthetic Win Rate & Wilson LB | Remove hardcoded 72%/58% stats; compute from authentic redemption activity. |
| **ISS-SIM-06** | **MEDIUM** | Quantitative Integrity | `wallets.py#L318-L393` | MD5 Synthetic PnL Timeline | Return authentic trade records or empty history flag; remove pseudo-random synthesizer. |
| **ISS-SIM-07** | **MEDIUM** | Code Quality | `scanner.py#L327-L350` | Unreachable Dead Code | Delete dead code block after return statement. |
| **ISS-SIM-08** | **MEDIUM** | Scoring Engine | `engine.py#L25-L41` | Spec Threshold Inconsistencies | Update anti-HFT to 100, Gold Sniper drawdown to 10.0%, remove PnL bypass. |
| **ISS-SIM-09** | **MEDIUM** | Frontend Realism | `ProfitSimulator.tsx#L14-L15` | Exponential Compounding ($243M) | Add realistic liquidity ceilings and logarithmic compounding model. |
| **ISS-SIM-10** | **MEDIUM** | Cash Accounting | `live_poller.py#L237` | Unrealized Gains as Free Cash | Track settled cash balance separately from mark-to-market total portfolio equity. |

---

### Concrete Remediation Diffs

#### Patch 1: Fix User Realized PnL Double-Counting (`backend/app/services/live_poller.py`)
```diff
--- a/backend/app/services/live_poller.py
+++ b/backend/app/services/live_poller.py
@@ -328,9 +328,12 @@ class LiveTradeMirrorService:
                         u_orig_notional = float(u_earliest_buy.notional_usd or u_notional)
                         u_ratio = ((effective_fill_price - u_orig_price) / u_orig_price) if u_orig_price > 0 else 0.0
                         
+                        u_buy_fee = float(u_earliest_buy.fee_usd or 0.0)
+                        u_sell_fee = float(u_fee["fee_usd"] or 0.0)
                         u_earliest_buy.status = "CLOSED"
-                        u_earliest_buy.realized_pnl_usd = round(u_orig_notional * u_ratio - float(u_earliest_buy.fee_usd or 0.0), 2)
-                        u_realized_pnl_val = round(u_notional * u_ratio - float(u_fee["fee_usd"]), 2)
+                        u_earliest_buy.realized_pnl_usd = round(u_orig_notional * u_ratio - (u_buy_fee + u_sell_fee), 2)
+                        # PnL is tracked strictly on the closed position; exit SELL log is an audit record
+                        u_realized_pnl_val = None
 
                 user_log = ExecutionLog(
                     user_id=u.id,
```

#### Patch 2: Fix EV Gate Expected Edge Calculation (`backend/app/services/live_poller.py`)
```diff
--- a/backend/app/services/live_poller.py
+++ b/backend/app/services/live_poller.py
@@ -202,7 +202,8 @@ class LiveTradeMirrorService:
             effective_fill_price = live_p if (0.001 <= live_p <= 0.999) else price
 
             # Rule 1: Fee-Aware Expected Value Gate (EV_net > 2.5 * Fee Rate)
-            expected_edge = abs(effective_fill_price - 0.5)
+            whale_expected_p = (float(source_whale.wilson_lower_bound or source_whale.win_rate_pct or 60.0) / 100.0) if source_whale else 0.60
+            expected_edge = max(0.0, whale_expected_p - effective_fill_price) if side == "BUY" else max(0.0, effective_fill_price - (1.0 - whale_expected_p))
             ev_pass, fee_rate, min_edge = calculate_fee_aware_ev_gate(effective_fill_price, title, expected_edge)
             if not ev_pass and expected_edge > 0.02 and side == "BUY":
```

#### Patch 3: Fix Directional Slippage Function (`backend/app/sizing/slippage.py`)
```diff
--- a/backend/app/sizing/slippage.py
+++ b/backend/app/sizing/slippage.py
@@ -1,13 +1,18 @@
-def check_slippage(whale_price: float, current_price: float) -> str:
+def check_slippage(whale_price: float, current_price: float, side: str = "BUY") -> str:
     """
-    Slippage check from spec.
+    Directional slippage validator:
+    Rejects only adverse price movement; allows favorable price improvements.
     """
     if whale_price <= 0:
         return 'EXECUTE_ORDER'
         
-    diff = abs(current_price - whale_price) / whale_price
-    if whale_price <= 0.25 and diff > 0.012:
+    if side.upper() == "BUY":
+        adverse_pct = (current_price - whale_price) / whale_price
+    else:
+        adverse_pct = (whale_price - current_price) / whale_price
+        
+    if whale_price <= 0.25 and adverse_pct > 0.012:
         return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
-    elif whale_price <= 0.50 and diff > 0.02:
+    elif whale_price <= 0.50 and adverse_pct > 0.02:
         return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
-    elif diff > 0.03:
+    elif adverse_pct > 0.03:
         return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
     return 'EXECUTE_ORDER'
```

#### Patch 4: Fix Scoring Engine Gating & Tier Rules (`backend/app/scoring/engine.py`)
```diff
--- a/backend/app/scoring/engine.py
+++ b/backend/app/scoring/engine.py
@@ -22,19 +22,19 @@ def score_wallet(wallet_stats: dict) -> ScoringResult:
     if pnl < 50000:
         return ScoringResult("rejected", None, "PNL_BELOW_THRESHOLD", False)
 
-    # FILTER 2: Anti-HFT (only reject high-frequency automated market maker bots >300 trades/day)
-    if trades_per_day > 300:
+    # FILTER 2: Anti-HFT (reject automated market maker bots >100 trades/day)
+    if trades_per_day > 100:
         return ScoringResult("rejected", None, "HFT_EXCEEDED", False)
 
     # FILTER 3: Outlier concentration (max_single_trade_profit/realized_pnl <= 0.35)
     if outlier_pct > 0.35:
         return ScoringResult("rejected", None, "OUTLIER_CONCENTRATION_TOO_HIGH", False)
 
     # FILTER 4: Minimum Win Rate >= 55.0% (reject losing wallets with negative alpha)
     if win_rate < 55.0:
         return ScoringResult("rejected", None, "WIN_RATE_TOO_LOW", False)
 
-    # TIER: Gold Sniper if win_rate >= 80.0% OR (pnl >= $100,000 and win_rate >= 70.0%)
-    if (win_rate >= 80.0 and max_drawdown <= 15.0) or (pnl >= 100000 and win_rate >= 70.0):
+    # TIER: Gold Sniper requires win_rate >= 85.0% AND max_drawdown <= 10.0%
+    if win_rate >= 85.0 and max_drawdown <= 10.0:
         tier = "gold_sniper"
     else:
         tier = "standard"
```

#### Patch 5: Fix Listener CTF Token & Side Parser (`listener/src/event-processor.ts`)
```diff
--- a/listener/src/event-processor.ts
+++ b/listener/src/event-processor.ts
@@ -66,22 +66,35 @@ export function matchesBasketWallet(
   let side: 'BUY' | 'SELL';
   let walletAddress: string;
   let assetId: string;
-  let amountFilled: string;
+  let sharesFilled: string;
+  let priceStr: string;
+
+  const isMakerCollateral = event.makerAssetId === '0';
+  const isTakerCollateral = event.takerAssetId === '0';
 
   if (isTakerBasket) {
-    side = 'BUY';
     walletAddress = takerLower;
-    assetId = event.makerAssetId;
-    amountFilled = event.makerAmountFilled;
+    if (isTakerCollateral) {
+      side = 'BUY';
+      assetId = event.makerAssetId;
+      sharesFilled = event.makerAmountFilled;
+      const collateral = parseFloat(event.takerAmountFilled);
+      const shares = parseFloat(event.makerAmountFilled);
+      priceStr = shares > 0 ? (collateral / shares).toFixed(4) : '0.5';
+    } else {
+      side = 'SELL';
+      assetId = event.takerAssetId;
+      sharesFilled = event.takerAmountFilled;
+      const collateral = parseFloat(event.makerAmountFilled);
+      const shares = parseFloat(event.takerAmountFilled);
+      priceStr = shares > 0 ? (collateral / shares).toFixed(4) : '0.5';
+    }
   } else {
-    side = 'SELL';
     walletAddress = makerLower;
-    assetId = event.makerAssetId;
-    amountFilled = event.makerAmountFilled;
+    // Maker side logic symmetric to taker
+    side = isMakerCollateral ? 'BUY' : 'SELL';
+    assetId = isMakerCollateral ? event.takerAssetId : event.makerAssetId;
+    sharesFilled = isMakerCollateral ? event.takerAmountFilled : event.makerAmountFilled;
+    const collateral = parseFloat(isMakerCollateral ? event.makerAmountFilled : event.takerAmountFilled);
+    const shares = parseFloat(isMakerCollateral ? event.takerAmountFilled : event.makerAmountFilled);
+    priceStr = shares > 0 ? (collateral / shares).toFixed(4) : '0.5';
   }
 
   return {
     walletAddress,
     side,
     assetId,
-    amountFilled,
-    price,
+    amountFilled: sharesFilled,
+    price: priceStr,
     transactionHash: event.transactionHash,
     logIndex: event.logIndex,
     blockNumber: event.blockNumber,
     timestamp: Date.now(),
   };
```

---

## 5. Verification Method

### 5.1 Verification Commands
1. **Pytest Scoring Tests**:
   ```powershell
   cd c:\Users\arthu\Documents\Baleen-master\backend
   c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\pytest.exe -v tests/test_scoring_filters.py
   ```
2. **Empirical Double-Counting Reproduction**:
   ```powershell
   c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\python.exe -c "
   orig_notional = 100.0; price_ratio = 0.40; buy_fee = 3.60; sell_fee = 2.16
   buy_pnl = orig_notional * price_ratio - buy_fee
   sell_pnl = orig_notional * price_ratio - sell_fee
   total_user_pnl = buy_pnl + sell_pnl
   true_net_pnl = orig_notional * price_ratio - (buy_fee + sell_fee)
   print(f'Total Recorded: ${total_user_pnl:.2f} vs True Net: ${true_net_pnl:.2f}')
   assert total_user_pnl > true_net_pnl
   "
   ```
3. **EV Gate Inversion Test**:
   ```powershell
   c:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\python.exe -c "
   from app.services.polymarket_fees import calculate_fee_aware_ev_gate
   # Toss-up at p=0.51
   p_pass, _, _ = calculate_fee_aware_ev_gate(0.51, 'BTC 15m', abs(0.51 - 0.50))
   print('Toss-up (p=0.51) Passed:', p_pass)
   assert p_pass is False
   "
   ```

### 5.2 Invalidation Conditions
- If `test_scoring_filters.py` passes without patching `engine.py`, the test environment is invalid.
- If `mark_to_market.py` sums user PnL from both BUY and SELL logs without doubling, the PnL logic was altered.
