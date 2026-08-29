# Frontend, Paper Trading Simulation & Quantitative Integrity Audit Report

## Executive Summary
This survey provides a comprehensive audit of the Baleen system across three major pillars:
1. **Frontend (`frontend/`)**: Architecture, page structure, component tree, trade drawer, real-time state displays, and API hooks.
2. **Paper Trading Simulation & Execution Fill Logic**: Order book walking, slippage modeling, quadratic taker fees, latency models, cash accounting, and PnL mechanics.
3. **Mathematical & Quantitative Integrity**: Wilson score confidence intervals, Kelly criterion position sizing, win rate filtering, expected value (EV) gates, max drawdown formulas, and multi-candidate price discovery.

---

## 1. Observation

### 1.1 Frontend Pages, Components, State Displays & API Hooks
The Frontend is built on **Next.js 14 App Router**, **Tailwind CSS**, **Framer Motion**, and **Recharts**.

#### Page Routes (`frontend/src/app/`)
| Route | File Path | Description |
|---|---|---|
| `/` | `frontend/src/app/page.tsx` | Marketing landing page featuring `Hero`, `FeaturesGrid`, `AdvantageSection`, `InfrastructureSection`, `Leaderboard`, `LiveTicker`, `ProfitSimulator`, and `ShaderGradientBackground`. |
| `/dashboard` | `frontend/src/app/dashboard/page.tsx` | Main trading control plane. Integrates `BalanceCounter`, `PortfolioAnalytics`, `LiveTape`, `WalletLeaderboard`, `TradeLog`, `TradeDrawer`, `WalletDrawer`, `BaleenCopilot`, `ActivityFeed`, and 4 action modals. |
| `/admin` | `frontend/src/app/admin/page.tsx` | Admin control panel for wallet evaluation, discovery progress, system status, and database wipe/re-evaluate controls. |
| `/settings` | `frontend/src/app/settings/page.tsx` | User risk profile settings (`Conservative`, `Balanced`, `Aggressive`) and daily digest preferences. |
| `/auth/login` | `frontend/src/app/auth/login/page.tsx` | NextAuth credential authentication and guest login. |
| `/auth/signup` | `frontend/src/app/auth/signup/page.tsx` | User registration with initial sandbox balance selection ($10,000 default). |
| `/api/auth/[...nextauth]` | `frontend/src/app/api/auth/[...nextauth]/route.ts` | NextAuth route handler for session management. |
| `/api/debug-env` | `frontend/src/app/api/debug-env/route.ts` | Backend URL connectivity and environment variable debugging endpoint. |

#### Core Dashboard Components (`frontend/src/components/dashboard/`)
- `BalanceCounter.tsx`: Animated number counter (`framer-motion`) displaying current sandbox balance and PnL, with 4 action buttons (Mirror, Rebalance, Analytics, Reset).
- `PortfolioAnalytics.tsx` (`file:///c:/Users/arthu/Documents/Baleen-master/frontend/src/components/dashboard/PortfolioAnalytics.tsx#L1-L949`):
  - Area Chart and Candlestick OHLC trader chart toggle with timeframe pills (`1H`, `6H`, `1D`, `1W`, `1M`, `YTD`, `ALL`).
  - Active Capital Allocation progress bar and whale breakdown legend.
  - Execution Win Rate dual-bar scorecard.
  - Top Alpha and Top Drawdown market attribution cards.
- `TradeDrawer.tsx` (`file:///c:/Users/arthu/Documents/Baleen-master/frontend/src/components/dashboard/TradeDrawer.tsx#L1-L208`): Slide-out drawer with market metadata, outcome badges, entry/exit prices, net PnL, consensus multiplier status, `TradePriceChart`, source whale link, and external Polymarket order book URL.
- `WalletDrawer.tsx`: Slide-out drawer for whale analytics, displaying AI summary, win rate, Wilson lower bound, Baleen score history, daily PnL bar chart (`DailyWinLossBarChart`), and recent trade fills.
- `LiveTape.tsx` (`file:///c:/Users/arthu/Documents/Baleen-master/frontend/src/components/dashboard/LiveTape.tsx#L1-L207`): Live execution feed with real-time polling (4s interval), filtering by side (`ALL`, `BUY`, `SELL`, `CONSENSUS`), search, and market category icons.
- `TradeLog.tsx` (`file:///c:/Users/arthu/Documents/Baleen-master/frontend/src/components/dashboard/TradeLog.tsx#L1-L249`): Execution audit feed with tab switches (`Holding`, `Closed`) and modal export trigger for `FullHistorySpreadsheetModal`.
- `BaleenCopilot.tsx`: Groq LLaMA-3.1 70B AI conversational assistant with tool calling for portfolio health, quadratic fee audits, and wallet promotions.
- `ActivityFeed.tsx`: System notification panel displaying execution logs, slippage guard skips, EV gate skips, and sandbox reset events.

#### Modals & Actions
- `ResetSandboxModal.tsx`: Calls `POST /api/executions/reset-sandbox` or `POST /api/users/{id}/reset-sandbox` to restore $10,000.00 balance and clear execution history.
- `MirrorStrategyModal.tsx` (`file:///c:/Users/arthu/Documents/Baleen-master/frontend/src/components/dashboard/MirrorStrategyModal.tsx#L1-L174`): UI for configuring whale copy weights and multipliers (1.0x, 1.5x, 2.0x).
- `RebalanceModal.tsx` (`file:///c:/Users/arthu/Documents/Baleen-master/frontend/src/components/dashboard/RebalanceModal.tsx#L1-L135`): UI for selecting rebalancing algorithm (`Alpha / PnL Weighted`, `Win-Rate Weighted`, `Equal Weight`).
- `DeepAnalyticsModal.tsx`: Comprehensive quantitative modal displaying net return, win rate, CLOB fills count, notional traded, fees paid, and consensus alpha.
- `FullHistorySpreadsheetModal.tsx`: Full tabular view of all historical trade records with sorting and CSV export.

#### Client API Layer (`frontend/src/lib/api-client.ts`)
- Two-tier caching: In-Memory `Map` + browser `sessionStorage` with 60–120s TTL (`getCached`, `setCached`, `clearAllCache`).
- API Endpoints mapped:
  - `fetchWallets`, `fetchWallet`, `fetchCopiedWhalesStats`, `fetchCopiedWalletStats`
  - `fetchExecutionLogs`, `fetchTradePriceChart`, `fetchPortfolioSummary`, `fetchPortfolioSnapshots`
  - `fetchUserSettings`, `updateUserSettings`, `resetSandboxAmount`, `resetSandboxLedger`
  - `fetchAdminStatus`, `fetchAdminWallets`, `reEvaluateWallets`, `purgeAndRescanWallets`, `fetchDiscoveryProgress`, `hardWipeAllDatabase`
  - `fetchSystemEvents`, `fetchCopilotChat`

---

### 1.2 Paper Trading Simulation & Execution Fill Logic Audit

#### 1. Disconnected Standalone Fill Simulator (`backend/app/sizing/fill_simulator.py`)
```python
# file:///c:/Users/arthu/Documents/Baleen-master/backend/app/sizing/fill_simulator.py#L10-L74
def simulate_fill(order_value_usd: float, order_book: dict, side: str, latency_ms: int = 1000) -> FillResult:
```
- **Unused Latency Parameter**: `latency_ms` is accepted as an argument (default 1000ms) but completely ignored in the calculation.
- **In-Place Mutation**: `levels.sort(key=...)` mutates the input dictionary's list reference in place.
- **ZeroDivisionError Risk**: Line 49: `shares_taken = remaining_value / price` causes `ZeroDivisionError` if an order book level contains `price == 0.0`.
- **Complete Disconnection**: `simulate_fill` is never called by `live_poller.py` or `signals.py`; it is only called in unit tests (`test_fill_model.py`).

#### 2. Disconnected Slippage & Dynamic Sizing Modules
- `backend/app/sizing/slippage.py`: `check_slippage(whale_price, current_price)` is only referenced in unit tests.
- `backend/app/sizing/dynamic_sizer.py`: `size_trade(user_balance, risk_profile, n_active, ...)` is only referenced in unit tests.
- In production (`backend/app/services/live_poller.py` lines 220 & 306), sizing is computed via hardcoded formulas:
  - System: `sys_notional = round(min(max(10.0, cash_usd * 0.1 * sizing_multiplier), 350.0), 2)`
  - User: `u_notional = round(min(max(5.0, cash_usd * 0.05 * sizing_multiplier), 150.0), 2)`

#### 3. Real-Time Fill Logic in Live Poller (`backend/app/services/live_poller.py`)
- **Zero-Slippage Assumption on Full Size**: Full notional ($10.00 – $350.00) is assumed to fill instantly at `effective_fill_price` with zero orderbook depth consumption and no partial fills.
- **Asymmetric Slippage Guard**: BUY orders are checked against `(live_p - price) > 0.015` (1.5 cents). SELL orders bypass all slippage checks and execute unconditionally at live price (`effective_fill_price = live_p if (0.001 <= live_p <= 0.999) else price`).
- **User Realized PnL Double-Counting Bug**:
  In `live_poller.py` lines 331–355:
  ```python
  u_earliest_buy.status = "CLOSED"
  u_earliest_buy.realized_pnl_usd = round(u_orig_notional * u_ratio - float(u_earliest_buy.fee_usd or 0.0), 2)
  u_realized_pnl_val = round(u_notional * u_ratio - float(u_fee["fee_usd"]), 2)
  ...
  user_log = ExecutionLog(..., side="SELL", status="CLOSED", realized_pnl_usd=u_realized_pnl_val, ...)
  ```
  When `mark_to_market.py` sums user PnL (`u_pnl = sum(float(l.realized_pnl_usd or 0.0) for l in u_logs)` at line 240), **both** the closed BUY log and the closed SELL log have `realized_pnl_usd` populated, doubling the user's realized profit/loss on every closed trade! (Note: System execution avoids this because `sys_realized_pnl_val = None` on line 279).
- **Free Cash Accounting Loophole**:
  In `live_poller.py` line 237: `free_cash = max(0.0, total_portfolio_equity - current_open_notional)`.
  Because `total_portfolio_equity` includes unrealized mark-to-market gains of currently open winning positions, open paper gains increase available free cash before closing the position.

---

### 1.3 Mathematical & Quantitative Integrity Audit

#### 1. Wilson Score Lower Bound (`backend/app/discovery/scanner.py`)
```python
# file:///c:/Users/arthu/Documents/Baleen-master/backend/app/discovery/scanner.py#L76-L86
def calc_wilson_lower_bound(wins: int, total: int, z: float = 1.645) -> float:
    if total <= 0:
        return 0.0
    p_hat = float(wins) / float(total)
    n = float(total)
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p_hat + z2 / (2.0 * n)
    spread = z * math.sqrt((p_hat * (1.0 - p_hat) + z2 / (4.0 * n)) / n)
    return round(max(0.0, (centre - spread) / denom) * 100.0, 1)
```
- **Math Formula**: The 90% confidence ($z = 1.645$) Wilson score lower bound formula itself is mathematically sound.
- **Synthetic Fabrication Vulnerability** (`scanner.py` lines 113–121):
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
  If a whale wallet has `< 3` resolved positions in the `/positions` payload, synthetic win rates (72% or 58%) and synthetic Wilson scores (62% or 50%) are assigned instead of computing from historical `/activity` redemptions.

#### 2. Max Drawdown & Dead Code in Scanner (`backend/app/discovery/scanner.py`)
- In `calculate_authentic_wallet_stats` (`scanner.py` lines 214–231), peak-to-trough drawdown is computed from `daily_pnl_history`.
- However, at line 304, the function `return`s `stats`. Lines 327–350 contain **unreachable dead code** that attempts a linear formula `max_drawdown = round(max(3.0, min(16.0, 18.0 - (win_rate * 0.12))), 1)` and references undeclared variables (`realized_pnl`, `total_trades_count`, `volume`).

#### 3. Synthetic Wallet History Generation (`backend/app/api/wallets.py`)
- In `backend/app/api/wallets.py` lines 318–392, if a wallet lacks trade history in the local database or cache, `get_wallet` generates a 45-day pseudo-random daily PnL history using `addr_seed = int(hashlib.md5(clean_addr.encode()).hexdigest()[:8], 16)` and rescales it to match `all_time_pnl_usd`.

#### 4. Dynamic Quadratic Taker Fee & Fee-Aware EV Gate
```python
# file:///c:/Users/arthu/Documents/Baleen-master/backend/app/services/polymarket_fees.py#L119-L153
# Dynamic Taker Fee: Fee = Theta * Notional * (1 - p)
raw_fee = notional_usd * theta * (1.0 - p)
```
- **Category Rate Inconsistencies**:
  - `AUDIT.md` KAN-5: Crypto (5%), Sports (5%), Politics/Finance (3%), Geopolitics (2%).
  - `backend/app/services/copilot.py` line 98: Sports (3.5%), Crypto (2.5%), Politics (1.5%).
  - `backend/app/services/polymarket_fees.py`: Crypto (7.2%), Economics/Finance (6.0%), Culture/Tech (5.0%), Politics (4.0%), Sports (3.0%), Geopolitics (0.0%).
- **EV Gate Formula Error**:
  In `live_poller.py` line 205:
  `expected_edge = abs(effective_fill_price - 0.5)`
  In `polymarket_fees.py` lines 149–152:
  `fee_rate = theta * (1.0 - p)`
  `min_required_edge = 2.5 * fee_rate`
  `should_pass = (expected_edge >= min_required_edge)`
  **Flaw**: `abs(price - 0.5)` is the market price's distance from 50%, **not** the trader's expected edge ($\alpha$). If a whale buys a high-probability favorite at $p = 0.85$, the code calculates `expected_edge = 0.35` (passes unconditionally). If a whale buys an undervalued toss at $p = 0.51$, the code calculates `expected_edge = 0.01` and rejects the trade ($0.01 < 2.5 \times \text{fee}$), rejecting legitimate edge.

#### 5. On-Chain Listener Token Mapping & Side Inversion (`listener/src/event-processor.ts`)
In `listener/src/event-processor.ts` lines 71–81:
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
```
- In Polygon CTF Exchange `OrderFilled` events, `makerAssetId = 0` or `takerAssetId = 0` indicates USDC collateral.
- The listener assumes `makerAssetId` is always the conditional token ID and that taker is always `BUY`, causing `assetId = "0"` and inverted buy/sell actions when a whale takes or makes a collateral-side order.

#### 6. Frontend Profit Simulator Exponential Compounding (`frontend/src/components/landing/ProfitSimulator.tsx`)
```typescript
// file:///c:/Users/arthu/Documents/Baleen-master/frontend/src/components/landing/ProfitSimulator.tsx#L14-L15
const baseGrowthFactorPerMonth = 2.815;
const projectedBalance = initialCapital * Math.pow(baseGrowthFactorPerMonth, timeHorizonMonths);
```
- Applies an unconstrained monthly multiplier of $2.815\times$ (281.5% ROI per month compounded). Over 12 months with a $1,000 starter capital, this projects $\$1,000 \times 2.815^{12} = \$243,365,684$, ignoring liquidity constraints, drawdown, and fee drag.

---

## 2. Logic Chain

1. **Simulated vs. Realized Execution Gap**:
   - `simulate_fill` in `fill_simulator.py` correctly implements order book walking across depth levels.
   - However, `simulate_fill` was never wired into `live_poller.py` or `signals.py`.
   - `live_poller.py` executes all trades instantaneously at a single price point (`effective_fill_price`) without order book depth consumption or fill volume limits.
   - Therefore, the paper trading simulation assumes zero slippage on size and infinite depth at the top of book, creating an artificial execution advantage over live Polymarket trading.

2. **PnL Accounting and Realized Double-Counting**:
   - In `live_poller.py` lines 331–333, when a user's open BUY is closed by a whale SELL, `u_earliest_buy.realized_pnl_usd` is set to the realized return, and a new `user_log` record with `side = "SELL"` is created with `realized_pnl_usd = u_realized_pnl_val`.
   - In `mark_to_market.py` line 240, `u_pnl = sum(float(l.realized_pnl_usd or 0.0) for l in u_logs)`.
   - Because both records belong to `u_logs` with `status = "CLOSED"`, the user's realized profit or loss is counted twice.

3. **EV Gate Inversion**:
   - Defining `expected_edge = abs(p - 0.5)` treats probability distance from 0.50 as alpha.
   - Under this logic, buying any asset at $p = 0.95$ yields `expected_edge = 0.45` (passing any fee threshold), even if true probability is only 0.90 (negative EV).
   - Buying an asset at $p = 0.52$ with true probability 0.70 yields `expected_edge = 0.02` (rejected by fee gate), rejecting high-alpha opportunities.

4. **UI State Persistence Divergences**:
   - `RebalanceModal.tsx` executes via a `setTimeout` without an API call.
   - `MirrorStrategyModal.tsx` allows setting per-whale multipliers (1.0x, 1.5x, 2.0x), but clicking "Save Strategy" does not persist multipliers to the backend or database.

---

## 3. Caveats
- The backend unit test suite (`pytest`) was inspected directly via source code because the local Windows execution environment lacked active `python`/`pytest` aliases in the primary path.
- The PostgreSQL database tables (`public.wallets`, `public.execution_logs`, `public.portfolio_snapshots`) were verified via existing project documentation and backend models; live DB state was not directly altered.

---

## 4. Conclusion

### Severity Breakdown of Findings

| ID | Category | Severity | File Reference | Summary |
|---|---|---|---|---|
| **ISS-01** | Simulation / Accounting | **CRITICAL** | `backend/app/services/live_poller.py#L331-L355` | User Realized PnL Double-Counting on position closure (PnL counted on both BUY and SELL logs). |
| **ISS-02** | Simulation / Realism | **HIGH** | `backend/app/services/live_poller.py#L220` | Zero-slippage / infinite liquidity assumption during live trade copying; standalone `simulate_fill` is disconnected. |
| **ISS-03** | Quantitative Integrity | **HIGH** | `backend/app/services/live_poller.py#L205` | Fee-Aware EV Gate uses `abs(p - 0.5)` as expected edge, rejecting low-price alpha and approving negative-EV favorites. |
| **ISS-04** | Ingestion / Listener | **HIGH** | `listener/src/event-processor.ts#L71-L81` | CTF Exchange `OrderFilled` parser ignores collateral token (`0`) check, causing inverted side and asset ID `0`. |
| **ISS-05** | Quantitative Integrity | **MEDIUM** | `backend/app/discovery/scanner.py#L116-L121` | Hardcoded synthetic win rate (72%/58%) and Wilson lower bound (62%/50%) when `total_resolved < 3`. |
| **ISS-06** | Quantitative Integrity | **MEDIUM** | `backend/app/api/wallets.py#L318-L392` | Synthetic 45-day pseudo-random daily PnL curve generation using MD5 address seed when historical cache is empty. |
| **ISS-07** | Quantitative Integrity | **MEDIUM** | `backend/app/services/polymarket_fees.py#L14-L20` | Inconsistent dynamic fee schedules across `AUDIT.md`, `copilot.py`, and `polymarket_fees.py`. |
| **ISS-08** | Code Quality / Dead Code | **MEDIUM** | `backend/app/discovery/scanner.py#L327-L350` | Unreachable dead code after `return` statement with potential `NameError` on undeclared variables. |
| **ISS-09** | Frontend Realism | **MEDIUM** | `frontend/src/components/landing/ProfitSimulator.tsx#L14-L15` | Unconstrained exponential compounding formula ($2.815\times$/mo) projecting astronomical returns ($1k \to \$243\text{M}$). |
| **ISS-10** | Frontend Persistence | **LOW** | `frontend/src/components/dashboard/RebalanceModal.tsx` & `MirrorStrategyModal.tsx` | Rebalance execution and whale multiplier changes are mock UI state without backend persistence. |

---

## 5. Verification Method

### 1. Verifying User Realized PnL Double-Counting (ISS-01)
- Inspect `backend/app/services/live_poller.py` lines 331–355 and compare with lines 273–279.
- Inspect `backend/app/services/mark_to_market.py` lines 237–244:
  `u_pnl = sum(float(l.realized_pnl_usd or 0.0) for l in u_logs)`
- Notice that for users, both the closing BUY and the closing SELL have `realized_pnl_usd` set, whereas for the system (`user_id is None`), `sys_realized_pnl_val` is `None`.

### 2. Verifying Disconnected Sizing & Fill Models (ISS-02)
- Grep for `simulate_fill`, `check_slippage`, and `size_trade` across `backend/app/services/` and `backend/app/api/`.
- Notice they are only imported in `backend/tests/test_fill_model.py`, `backend/tests/test_slippage.py`, and `backend/tests/test_dynamic_sizing.py`.

### 3. Verifying EV Gate Formula (ISS-03)
- Inspect `backend/app/services/live_poller.py` line 205: `expected_edge = abs(effective_fill_price - 0.5)`.
- Test case: For $p = 0.51$, `expected_edge = 0.01`. If $\theta = 0.072$, $\text{min\_edge} = 2.5 \times 0.072 \times (1 - 0.51) = 0.0882$. `0.01 < 0.0882` $\to$ rejected, even if the whale has 85% win rate.

### 4. Verifying Listener CTF Event Parser (ISS-04)
- Inspect `listener/src/event-processor.ts` lines 71–81 and verify that `event.makerAssetId` is assigned directly without checking `if (event.makerAssetId === '0')`.
