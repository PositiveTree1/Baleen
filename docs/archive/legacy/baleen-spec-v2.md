# Baleen — Automated Polymarket Whale-Index Engine
## Master Build Specification v2 (Complete — Agent-Buildable)

> **What it is:** A consumer web app that runs a single, curated, auto-updating basket ("index") of top-performing Polymarket wallets. Users don't pick individual traders — they fund one account (virtual money in the free sandbox, real money later in Phase 2) and the system mirrors every trade from every wallet currently in the basket, sized dynamically. Every trade is logged with the exact source wallet, market, price, and time, so the whole thing is independently auditable.
> **Positioning:** Existing Polymarket copy-trading tools (PolyCop, Kreo, PolyGun, and similar) are Telegram bots built for crypto-native power users who already have a funded wallet and understand on-chain trading. Baleen targets the segment none of them serve: people with no crypto experience who want to watch $20 of play money mirror real elite traders before ever connecting a wallet. Lead with that gap in any pitch — don't compete on raw execution speed against tools built for that.
> **Document purpose:** buildable end-to-end by an AI coding agent with no other context, and legible as a portfolio artifact — every non-obvious decision states why.

---

## 0. Product Model Summary (read this first)

- **One basket, not a marketplace.** No user ever chooses a wallet to follow. An algorithm chooses and continuously updates the basket; users just fund an account.
- **Basket size is uncapped** and re-evaluated automatically every 24 hours — however many wallets currently pass the gold-tier filters (§4) are in the basket. No human review step.
- **Capital sizing is fully dynamic, computed per trade**, not pre-split into fixed allocations (§5). This is the mechanism that makes an uncapped, ever-changing basket work at all — there's no static allocation to rebalance.
- **Phase 1 (Sandbox/Demo) is the actual deliverable to build first and build completely.** No wallet connection, no KYC, no crypto — email/Google sign-up, pick a virtual starting balance, done. Positions use real market data and resolve on real outcomes; only the capital is fake. This is both the trust-building mechanism (prove the system works before anyone risks money) and the low-friction, shareable consumer product in its own right.
- **Phase 2 (Live) is gated and explicitly harder than the original draft assumed** — see §9 for why storing a user's Polymarket API credentials alone does *not* give you the ability to place trades on their behalf, and what actually does.
- **Monetization: performance fee only, no subscription.** "You only pay if you win." Mechanics in §8.
- **Whales are shown by raw wallet address only** — no nicknames or personas, by design (keeps the transparency story unambiguous).
- **Notifications are a daily digest email** (this is a web app, not a native app — no push).

---

## 1. Architecture

```
+---------------------------------------------------------------------------------------+
|                                    BALEEN — PHASE 1                                   |
+---------------------------------------------------------------------------------------+
|                                                                                         |
|  [DISCOVERY]                    [SCORING ENGINE]                  [STORAGE]           |
|  Polymarket Data API      -->   Filter + score wallets       -->  PostgreSQL          |
|  Polymarket Gamma API     -->   (independent of the                (wallets,          |
|                                   backtester project's engine       wallet_snapshots,  |
|                                   — see §4)                         users, logs)       |
|                                                                                         |
|  [AI WHALE ANALYSIS]  (§6)                                                             |
|  Nightly job: stats -> LLM -> plain-English summary + style tag, stored per wallet     |
|                                                                                         |
|  [SIGNAL LISTENER]                        [DYNAMIC SIZING + SIMULATED FILL]  (§5)     |
|  Envio HyperSync (Polygon)  -->  detect  -->  compute live per-trade size  -->         |
|  watching CTF Exchange           OrderFilled     (balance / current active count)      |
|  contract                        from a basket   -> walk order book for realistic      |
|                                   wallet            fill -> apply slippage model  -->   |
|                                                      write execution_logs               |
|                                                                                         |
|  [DAILY DIGEST]  (§7)                    [FRONTEND]  (§10)                            |
|  Resend + React Email                    Next.js dashboard, live tape, animated UI     |
|                                                                                         |
+---------------------------------------------------------------------------------------+
                                          |
                                          v  (opt-in, see §9 — genuinely harder than Phase 1)
+---------------------------------------------------------------------------------------+
|                                    BALEEN — PHASE 2                                    |
|  Embedded-wallet delegated signing (Magic/Privy) -> real order construction ->         |
|  CLOB V2 submission -> pre-trade risk checks -> kill switch -> performance-fee billing |
+---------------------------------------------------------------------------------------+
```

### 1.1 Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind, Framer Motion | SSR for shareable public pages; Framer Motion for the animated UI in §10 |
| Backend — scoring/analysis | Python 3.11, FastAPI | Numeric filtration logic, easy to unit-test in isolation |
| Backend — signal listener | Node.js/TypeScript, `@envio-dev/hypersync-client` | Envio SDK is TS-first |
| Database | PostgreSQL (Neon or Supabase free tier) | Relational integrity across wallets/users/logs/fees |
| Queue | Redis or a Postgres-backed job table | Decouples the chain listener from scoring/execution — a slow write must never stall event ingestion |
| Email | Resend + React Email | Free tier (3,000/mo) is enough for MVP scale; digest as a real React component, not hand-written HTML |
| AI whale analysis | Groq via API | Cheap, fast, sufficient for short grounded summaries — see §6 for why "grounded" matters |
| Phase 2 wallet/signing | Magic or Privy embedded wallets | Delegated signing — your server never holds a raw private key (see §9.1) |

### 1.2 Non-Goals

- No cross-chain support — Polygon/Polymarket only.
- No leverage or margining.
- Phase 1 never touches a real credential, key, or exchange account.
- Not hardened against adversarial public load until Phase 2 traffic requires it.

---

## 2. Data Model (PostgreSQL)

```sql
-- WALLETS: current + historical basket members
CREATE TABLE wallets (
    address TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',        -- pending | active | rejected
    tier TEXT NOT NULL DEFAULT 'standard',          -- gold_sniper | standard
    all_time_pnl_usd NUMERIC(14,2) DEFAULT 0,
    win_rate_pct NUMERIC(5,2) DEFAULT 0,
    total_trades_analyzed INT DEFAULT 0,
    avg_trades_per_day NUMERIC(6,2) DEFAULT 0,
    median_inter_trade_gap_hours NUMERIC(8,2) DEFAULT 0,   -- used for the idle/dormancy check, §4.3
    max_drawdown_pct NUMERIC(5,2) DEFAULT 0,
    outlier_concentration_pct NUMERIC(5,2) DEFAULT 0,
    baleen_score NUMERIC(8,2) DEFAULT 0,
    rejection_reason TEXT,
    ai_summary TEXT,
    ai_style_tag TEXT,                              -- e.g. "High-conviction, low-frequency"
    dormant BOOLEAN NOT NULL DEFAULT false,
    first_seen_at TIMESTAMPTZ DEFAULT now(),
    last_scored_at TIMESTAMPTZ DEFAULT now()
);

-- WALLET_SNAPSHOTS: append-only score history, powers decay visualization
CREATE TABLE wallet_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_address TEXT REFERENCES wallets(address) ON DELETE CASCADE,
    baleen_score NUMERIC(8,2),
    win_rate_pct NUMERIC(5,2),
    pnl_usd NUMERIC(14,2),
    snapshot_at TIMESTAMPTZ DEFAULT now()
);

-- USERS
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    google_id TEXT UNIQUE,
    risk_profile TEXT NOT NULL DEFAULT 'balanced',   -- conservative | balanced | aggressive
    sandbox_starting_balance_usd NUMERIC(14,2) NOT NULL,
    sandbox_balance_usd NUMERIC(14,2) NOT NULL,
    sandbox_high_water_mark_usd NUMERIC(14,2) NOT NULL,
    live_trading_enabled BOOLEAN NOT NULL DEFAULT false,
    live_high_water_mark_usd NUMERIC(14,2),
    daily_digest_opt_in BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- LIVE_WALLET_LINKS (Phase 2): reference to embedded-wallet provider, never a raw key
CREATE TABLE live_wallet_links (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,              -- 'magic' | 'privy'
    provider_user_id TEXT NOT NULL,
    polymarket_wallet_address TEXT NOT NULL,
    clob_api_key_enc BYTEA,              -- for read-only balance queries only, see §9
    kms_key_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ
);

-- EXECUTION_LOGS: the audit trail — the core trust artifact of the whole product
CREATE TABLE execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    source_wallet_address TEXT NOT NULL,             -- which basket whale triggered this
    market_condition_id TEXT NOT NULL,
    market_question TEXT,                             -- human-readable, cached for display
    side TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
    whale_entry_price NUMERIC(6,4) NOT NULL,
    user_fill_price NUMERIC(6,4),
    notional_usd NUMERIC(14,2) NOT NULL,
    active_basket_size_at_trade INT NOT NULL,          -- N used in the sizing formula, §5 — kept for auditability
    is_sandbox BOOLEAN NOT NULL,
    status TEXT NOT NULL,        -- SUCCESS | SLIPPAGE_BLOCKED | SKIPPED_BELOW_MINIMUM | RISK_BLOCKED | FAILED
    failure_detail TEXT,
    latency_ms INT,               -- whale-fill-detected -> our order recorded
    resolution_outcome TEXT,      -- NULL until resolved: WON | LOST
    realized_pnl_usd NUMERIC(14,2),
    onchain_tx_hash TEXT,
    onchain_log_index INT,
    executed_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    UNIQUE(onchain_tx_hash, onchain_log_index, user_id)   -- idempotency, §8 of prior draft / §11 tests
);

CREATE INDEX idx_execution_logs_user_time ON execution_logs(user_id, executed_at DESC);
CREATE INDEX idx_wallets_status_tier ON wallets(status, tier);

-- FEE_CHARGES: performance-fee billing history (Phase 2 only, but designed now — §8)
CREATE TABLE fee_charges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    starting_high_water_mark_usd NUMERIC(14,2) NOT NULL,
    ending_value_usd NUMERIC(14,2) NOT NULL,
    profit_above_hwm_usd NUMERIC(14,2) NOT NULL,
    fee_pct NUMERIC(5,2) NOT NULL,
    fee_amount_usd NUMERIC(14,2) NOT NULL,
    charged_at TIMESTAMPTZ DEFAULT now()
);
```

**Notes an agent should preserve:**
- There is **no `copy_subscriptions` table** — earlier drafts had one because the product was originally a marketplace. It isn't anymore; every user follows the same basket, so "which wallets does this user follow" isn't a thing that needs storage.
- `active_basket_size_at_trade` on `execution_logs` exists purely so the dynamic sizing formula in §5 is independently auditable after the fact — a skeptical user (or you, in an interview) should be able to reconstruct exactly why a trade was sized the way it was.
- `onchain_tx_hash` + `onchain_log_index` uniqueness constraint is the idempotency mechanism required by §11's test suite.

---

## 3. Wallet Discovery

- **Sources:** `GET https://data-api.polymarket.com/trades` (24h volume-sorted) for currently active large traders; Gamma Leaderboard API for consistently profitable traders.
- **Cadence:** discovery scan every 6h; full rescoring of all tracked wallets every 24h (matches the "gold list stays gold" requirement).
- Merge, dedupe by address, insert new candidates as `status = 'pending'`.

---

## 4. Scoring Engine

Independent from the `polymarket-backtester` project by design — that engine validates strategies against full historical data offline; this one decides, continuously, which currently-active wallets belong in a live basket. Different job, different constraints (see the comparison table in the original v1 spec if you need the full rationale restated).

```python
# FILTER 1 — Minimum realized PnL
if wallet.realized_pnl_usd < 50_000:
    reject("PnL below $50,000 threshold")

# FILTER 2 — Anti-HFT / bot screening
trades_per_day = wallet.total_trades_4k / wallet.active_days_span
if trades_per_day > 100:
    reject("Likely automated/HFT — not copyable at human-relevant granularity")

# FILTER 3 — Outlier concentration
if (wallet.max_single_trade_profit / wallet.realized_pnl_usd) > 0.35:
    reject("Single trade >35% of total PnL — one lucky bet, not a repeatable edge")

# FILTER 4 — Copyability
if wallet.median_fill_speed_ms < system.p95_listener_latency_ms:
    flag_as("low_copyability")   # shown in UI, not auto-rejected

# TIER — Gold Sniper (basket membership)
if wallet.win_rate_pct >= 85.0 and wallet.max_drawdown_pct <= 10.0:
    wallet.tier = "gold_sniper"
    wallet.status = "active"      # this wallet is now IN the basket
else:
    wallet.status = "rejected" if wallet.status != "active" else wallet.status
```

**4.1 Dormancy check (per-whale-relative, not a fixed timer)**
```python
hours_since_last_trade = now() - wallet.last_trade_at
if hours_since_last_trade > 8 * wallet.median_inter_trade_gap_hours:
    wallet.dormant = True   # excluded from active_basket_size_at_trade, but stays in the basket
```
A daily trader going quiet for a week is meaningfully different from a weekly trader doing the same — this check adapts to each wallet's own rhythm instead of applying one global cutoff. Dormant wallets stay in `wallets` with `status='active'` but are excluded from `N_active` in the sizing formula below, so they don't distort sizing while dormant and rejoin automatically the moment they trade again.

**4.2 Basket refresh:** fully automatic, no manual review, tied to the 24h rescoring job. A wallet dropping below the gold-tier bar on any rescoring pass is set to `status='rejected'` immediately — new copying from it stops on the next signal, but any of its already-open positions in `execution_logs` ride to natural market resolution rather than being force-closed.

---

## 5. Dynamic Per-Trade Sizing (the core mechanism)

No pre-allocated capital splits. Every trade is sized live, at the moment it's detected:

```python
def size_trade(user, whale_trade_event):
    N_active = count_wallets(status='active', dormant=False)   # basket size right now
    base_notional = user.available_balance / N_active           # equal weight across currently-active members

    whale_risk_pct = whale_trade_event.value_usdc / whale_trade_event.whale_portfolio_value_usdc
    raw_order_value = base_notional * whale_risk_pct

    risk_caps = {"conservative": 0.05, "balanced": 0.10, "aggressive": 0.20}
    max_allowed = user.available_balance * risk_caps[user.risk_profile]

    order_value = min(raw_order_value, max_allowed)

    if order_value < POLYMARKET_MIN_ORDER_USD:
        return skip("SKIPPED_BELOW_MINIMUM")

    return order_value
```

**Why this shape, explicitly, for the doc/interview:**
- It's the only way an *uncapped, daily-changing* basket stays workable — a fixed pre-split would need manual rebalancing every time the basket size changed.
- It's also the fix for the idle-capital question from earlier: dormant wallets are excluded from `N_active`, so no capital sits parked against a wallet that isn't trading — the denominator just shrinks and every other active wallet's share grows slightly.
- The `risk_profile` cap exists specifically for the edge case where the basket temporarily shrinks to one or two wallets — without it, a user's entire balance could ride on a single signal.
- `POLYMARKET_MIN_ORDER_USD` matters a lot at small starting balances (the $20 pitch) — verify the current minimum via the CLOB API docs before hardcoding it; it's small but nonzero, and at $20 spread across a large active basket you will hit it. This is precisely why the basket, while uncapped in principle, will self-limit in practice at very low balances — worth surfacing to the user in the UI ("N of your basket's M active wallets were too small to copy this round") rather than silently dropping trades.

**5.1 Simulated fill model (Phase 1)**
- Pull the real Polymarket order book at signal-detection time and walk it for the sized quantity — don't assume a fill at the whale's exact price.
- Apply a measured latency penalty before taking that snapshot (start conservative — 800ms–2s — until `latency_ms` data from the live listener gives you a real number). This is the single most important integrity decision in the demo: silently assuming instant, perfect fills produces numbers nobody should trust, including you.

---

## 6. AI Whale Analysis

**Purpose:** turn a wallet's raw stats into a short, plain-English description a non-trader can understand — without letting the model invent anything not supported by the data.

**Generation (nightly, part of the 24h rescoring job):**

```python
prompt = f"""You are describing a Polymarket trader's style in plain English for a
retail audience with no trading background. Use ONLY the numbers provided —
do not invent behavior, motives, or predictions. 2-3 sentences, no jargon.

Stats:
- Win rate: {win_rate_pct}%
- Total realized PnL: ${all_time_pnl_usd}
- Avg trades/day: {avg_trades_per_day}
- Max drawdown: {max_drawdown_pct}%
- Median time between trades: {median_inter_trade_gap_hours} hours
- Typical price range traded: {price_regime_summary}

Also output a 2-4 word style tag (e.g. "High-conviction, low-frequency",
"Steady grinder", "Deep-value hunter")."""
```

- Model: llama-3.3-70b-versatile or llama-3.1-8b-instant — this task needs grounded summarization, not deep reasoning; use the cheap fast tier.
- **Grounding constraint is load-bearing, not decorative** — the prompt explicitly forbids inventing anything, because a hallucinated "this trader tends to succeed during election cycles" next to real audited trade data would quietly undermine the entire trust story the product depends on. Consider a lightweight post-generation check that flags summaries containing numbers not present in the input stats.
- **Anomaly flagging (same nightly job):** compare each wallet's last-24h behavior to its own historical baseline (trade frequency, average size, price regime) and flag material deviations for the scoring engine — a sudden behavior shift is a real signal about whether a wallet's edge is stable, and it's a natural extension of the copyability check in §4.

---

## 7. Sandbox / Demo Mode

- User picks their own starting virtual balance at signup (no fixed default).
- Runs continuously, 24/7, independent of whether the user has the app open.
- **P&L is real** — positions are sized against real detected trades, filled against real order-book data (§5.1), and resolve based on real Polymarket market outcomes. Only the capital is fake. This is what makes the sandbox a credible trust signal rather than a toy.
- Full trade-by-trade log, filtered per user from `execution_logs` (`is_sandbox = true`): source wallet address, market, side, price, size, status, and resolution outcome once settled.
- **Resolution moments are a distinct, higher-emphasis UI event** from routine trade-opened notifications — this is the "did it actually work" payoff and the most natural thing for a user to share.

---

## 8. Monetization — Performance Fee with High-Water Mark

- **No subscription. Fee only on realized new profit, never on losses or on recovering past losses.**
- Mechanics: track `high_water_mark_usd` per user (already in schema). At each billing cycle (recommend monthly):
  ```
  profit_above_hwm = max(0, current_value - high_water_mark)
  fee = profit_above_hwm * fee_pct   # e.g. 15-20%, tune before launch
  high_water_mark = current_value - fee   # ratchets up only, never down
  ```
- Example: $1,000 deposit → grows to $1,200. Fee applies to the $200 of new profit only. If it later drops to $1,000 and climbs back to $1,170, **no fee** — that's recovering old ground, not new profit.
- **This only activates in Phase 2** — sandbox accounts never get charged, since there's no real profit to take a cut of.
- **Regulatory note, stated plainly rather than glossed over:** a performance fee charged on pooled/mirrored trading for retail consumers is close to textbook investment-adviser activity in most jurisdictions. This doesn't block building anything in this document — it blocks *launching Phase 2 with real public deposits* without actual legal review. Treat §9 as buildable architecture, not a go-live plan.

---

## 9. Phase 2 — Live Execution

**9.1 The custody problem, correctly stated.** Polymarket's L2 API credentials (`apiKey`/`secret`/`passphrase`) authenticate REST calls — reading balances, reading order history — but **do not by themselves authorize placing an order**. Every order requires an EIP-712 signature from the wallet's private key. So storing just the L2 credentials (as the original v1 draft assumed) lets you *read* a user's bankroll but not *trade* it. Real options for actually executing on a user's behalf:
1. **Hold the raw private key server-side** — genuinely custodial, real security/regulatory liability. Avoid.
2. **Embedded-wallet delegated signing (Magic or Privy)** — user gets a provider-managed wallet; your backend requests the *provider* sign orders on a delegated, scoped basis after the user authorizes it. Your server never touches the raw key. This is the standard pattern in Polymarket's own reference implementations and is the one to build.
3. **User-side local signer** — genuinely non-custodial, but only "automated" while their device is on. Not compatible with a 24/7 hosted product; worth knowing about but not the primary path.

**9.2 Required before any live order is ever placed:**
- Explicit opt-in with real risk disclosure — not a settings toggle.
- Server-enforced daily loss limit and per-trade cap (not just UI-level).
- A kill switch checked at the top of the execution path before every single order, settable per-user or globally.
- Full audit log (already `execution_logs`), user-visible.
- Legal review of the fee model's regulatory classification before real deposits are accepted.

**9.3 Order execution:** same sizing/slippage logic as §5, against real order books, with pre-trade balance and risk checks added before submission via the delegated signer.

---

## 10. Frontend — Dynamic, Animated UI

**Design ethics constraint, stated up front:** this product is explicitly aimed at people with no trading background, and will eventually involve real money. Animations should feel satisfying and alive, but must not function as dark patterns — no variable-reward "slot machine" effects, no artificial urgency countdowns, no near-miss emphasis on losing trades. The goal is a UI that feels trustworthy and responsive, not one engineered to maximize compulsive checking. This is both an ethical line and a credibility asset — "built responsibly for people who don't know the space" is a stronger portfolio narrative than "built to maximize engagement."

## Landing Page, UI/UX & Visual Identity Design

### 1. Color Palette & Visual Vibe
The visual language adopts a dark, high-contrast, terminal-inspired fintech aesthetic (blending the data density of TradingView and Bloomberg with the sleek, modern design of Uniswap and Polymarket).

* **Background (Primary):** Deep Obsidian (`#0B0E14`) — High-contrast dark backdrop for real-time tickers and data readability.
* **Surface / Cards:** Charcoal Slate (`#161B22` / `#1F2633`) — Used for glassmorphic cards, tables, drawers, and modal overlays.
* **Accent (Primary Brand):** Neon Teal / Cyan (`#00F2FE` / `#4FACFE`) — Represents synchronization, signals, and active mirroring.
* **Positive / Profit:** Emerald Green (`#10B981`) — Highlights winning positions, positive PnL, and gold-tier badges.
* **Negative / Loss:** Crimson Red (`#EF4444`) — Indicates drawdown, position closures at a loss, or execution warnings.
* **Text / High Contrast:** Polar White (`#F9FAFB`) — Headers, core stats, and wallet addresses.
* **Text / Low Contrast:** Muted Slate (`#9CA3AF`) — Secondary metadata, timestamps, and table headers.

---

### 2. UI/UX Reference & Mobbin Guidance
> **Instruction for AI Builder / Agent:** 
> For all UI components, component hierarchy, animations, and user flows, reference established fintech, prediction market, and crypto-native UI patterns using Mobbin (or Mobbin MCP). Look at screen flows from apps like **Polymarket, Robinhood, Uniswap, and TradingView** to structure:
> 1. High-converting onboarding and authentication drawers.
> 2. Dense, highly scannable leaderboard tables with clear visual hierarchy.
> 3. Clean transaction confirmation and vault allocation modals.
> 4. Non-intrusive, live execution tickers and status feeds.

---

### 3. Landing Page Structure & Hero Layout

#### A. Hero Section (Split 50/50 Layout)
* **Left Column (CTA & Value Proposition):**
  * **Badge:** `AI-POWERED POLYMARKET COPY ENGINE`
  * **Headline:** *"Mirror the Top 1% Polymarket Traders On Autopilot."*
  * **Subheadline:** *"Turn $20 into an automated prediction market portfolio by mirroring hyper-consistent, verified whales."*
  * **CTAs:** `[ Start Copying Free ]` (Primary - Google/Email Signup) and `[ View Live Tape ]` (Secondary Ghost Button).
* **Right Column (Interactive Hero Visual):**
  * **Interactive 3D Live Execution Card:** An interactive 3D glassmorphic card component positioned on the right side of the hero section. The card responds subtly to mouse movement (3D tilt/parallax effect based on cursor position) and displays live, streaming trade executions and active whale stats in real time. *(Implementation details: Framer Motion / CSS 3D transforms).*

#### B. Live Performance Ticker (Social Proof Strip)
A horizontally scrolling ticker ribbon displaying platform stats:
* `Total Volume Mirrored: $X,XXX,XXX`
* `Execution Latency: < 800ms`
* `Active Basket Whales: 38`
* `Indexer Status: Connected (Polygon)`

#### C. Core Features Grid (3x2 Cards)
1. **Real-time Envio Indexing:** Zero-delay event listening straight from Polygon event contracts.
2. **Automated Risk & Slippage Engine:** Dynamic order cancellation if market price shifts past strict regime tolerances.
3. **Dynamic Basket Sizing:** Automatic bankroll scaling across active whales without manual rebalancing.
4. **Non-Custodial & Paper Sandbox:** Test strategies with $10,000 in virtual funds before connecting real trading keys.

#### D. Live Leaderboard & Wallet Detail Drawer
* **Leaderboard Table:** Columns for Wallet Address, Tier (`Gold Sniper`), Win Rate %, Realized PnL, Trades/Day, and an instant `[ Copy Vault ]` action button.
* **Hover & Click States:** Hovering rows triggers subtle radial neon glows; clicking opens a glassmorphic side-drawer featuring the wallet's 4,000-trade PnL chart and an AI-generated plain-English activity summary.

**Concrete Framer Motion patterns:**

| Element | Animation | Notes |
|---|---|---|
| Balance counter | Animated count-up/down via `useMotionValue` + `useTransform` whenever balance changes | Smooth, not sudden — should read as "tracking reality," not a slot-machine tick |
| Live tape | New entries slide/fade in via `AnimatePresence`, oldest entries fade out | Cap visible rate — don't let a burst of trades feel chaotic |
| Basket size changes | Subtle transition when `N_active` changes (a wallet going dormant/active) | Reinforces that sizing is genuinely dynamic, ties back to §5 |
| Wallet score badges | Gentle glow/pulse only on tier changes (e.g. promoted to gold), not persistent | Persistent pulsing reads as manipulative; a one-time transition reads as informative |
| Trade resolution | Distinct, calm "resolved" card animation — clear win/loss state, tied to the realized P&L number | This is the shareable moment (§7) — make it clean and screenshot-worthy, not gamified |
| Score-history chart | Smooth chart transitions when switching time ranges (Recharts + Framer layout animations) | Shows decay/drift, not just a static current number |
| Page loads | Skeleton states matching final layout shape, not generic spinners | Reduces perceived latency without hiding structure |

**Pages:**
- **Landing:** live status pill (current basket size, block height), hero, animated whale-card preview, live tape preview, primary CTA into free sandbox signup — no wallet connection required at any point in this flow.
- **Dashboard:** balance (animated), risk-profile selector, live tape, full trade log with filters, wallet leaderboard (raw addresses, AI style tags, score-history sparkline).
- **Wallet detail drawer:** AI summary (§6), score-history chart, all trades sourced from this wallet.
- **Settings:** starting/current balance display, risk profile (Conservative/Balanced/Aggressive), daily digest opt-in/out.

---

## 11. API Surface

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/wallets` | GET | Basket leaderboard, filterable by tier/dormancy |
| `/api/wallets/{address}` | GET | Full profile: score history, recent trades, AI summary |
| `/api/execution-logs` | GET | User's trade history, filterable by status/date |
| `/api/user/settings` | GET/PATCH | Risk profile, digest opt-in, balance |
| `/api/fee-charges` | GET | User's fee history (Phase 2) |
| `/ws/tape` | WebSocket | Live execution stream |
| `/api/auth/*` | — | Google OAuth (NextAuth.js) |

---

## 12. Build Sequence

1. Postgres schema (§2) + migrations.
2. Discovery + scoring worker (§3–4), tested against a handful of known real wallet addresses before wiring the full pipeline.
3. HyperSync listener → queue, independent of scoring (idempotent, checkpointed — see test suite).
4. Dynamic sizing + simulated fill engine (§5) — get the fill-model integrity right before anything is built on top of its numbers.
5. AI whale analysis job (§6).
6. FastAPI/Next.js API layer (§11).
7. Frontend: leaderboard → wallet drawer → dashboard → live tape (depends on WebSocket stability) → animations layered in last, once the underlying data is trustworthy.
8. Auth + sandbox account creation.
9. Daily digest email (§7 data + Resend).
10. Only after 1–9 are running end-to-end and the numbers are trusted: begin §9 (Phase 2).

---

## 13. Test Suite (per phase)

### Phase 1 — Discovery & Scoring
```python
# test_scoring_filters.py
def test_pnl_threshold_rejects_below_50k():
    wallet = make_wallet(realized_pnl_usd=40_000)
    assert score(wallet).status == "rejected"

def test_hft_screen_rejects_over_100_trades_per_day():
    wallet = make_wallet(total_trades_4k=5000, active_days_span=40)  # 125/day
    assert score(wallet).rejection_reason == "Likely automated/HFT — not copyable at human-relevant granularity"

def test_outlier_concentration_rejects_single_trade_over_35pct():
    wallet = make_wallet(realized_pnl_usd=100_000, max_single_trade_profit=40_000)
    assert score(wallet).status == "rejected"

def test_gold_tier_requires_both_winrate_and_drawdown():
    wallet = make_wallet(win_rate_pct=90, max_drawdown_pct=15)  # fails drawdown
    assert score(wallet).tier != "gold_sniper"
```

```python
# test_dormancy.py
def test_dormancy_is_relative_to_own_median_gap():
    daily_trader = make_wallet(median_inter_trade_gap_hours=6, hours_since_last_trade=60)   # 10x -> dormant
    weekly_trader = make_wallet(median_inter_trade_gap_hours=168, hours_since_last_trade=60) # <1x -> not dormant
    assert check_dormancy(daily_trader) == True
    assert check_dormancy(weekly_trader) == False
```

### Phase 1 — Signal Listener
```typescript
// test_envio_stream.ts
async function testEnvioConnection() {
  const client = HyperSyncClient.newClient({ url: "https://polygon.hypersync.xyz" });
  const height = await client.getHeight();
  if (height <= 0) throw new Error("Invalid block height.");
  console.log(`[PASS] Envio stream active at height ${height}`);
}
```

```python
# test_idempotency.py
def dedupe_key(tx_hash, log_index, user_id):
    return f"{tx_hash}:{log_index}:{user_id}"

seen = set()
def process_event(tx_hash, log_index, user_id):
    key = dedupe_key(tx_hash, log_index, user_id)
    if key in seen:
        return "SKIPPED_DUPLICATE"
    seen.add(key)
    return "PROCESSED"

assert process_event("0xabc", 4, "u1") == "PROCESSED"
assert process_event("0xabc", 4, "u1") == "SKIPPED_DUPLICATE"
```

```python
# test_checkpoint_backfill.py
# Verifies listener resumes from last processed block on restart, not from "now"
def test_restart_replays_from_checkpoint():
    save_checkpoint(block=1000)
    resumed_from = get_resume_block()
    assert resumed_from == 1000  # not current_block
```

### Phase 1 — Dynamic Sizing
```python
# test_dynamic_sizing.py
def test_sizing_scales_with_active_basket_size():
    user = make_user(balance=1000, risk_profile="balanced")
    size_10_active = size_trade(user, whale_trade(value=500, portfolio=5000), n_active=10)
    size_5_active = size_trade(user, whale_trade(value=500, portfolio=5000), n_active=5)
    assert size_5_active > size_10_active  # fewer active wallets -> bigger per-wallet share

def test_risk_cap_overrides_raw_calculation():
    user = make_user(balance=1000, risk_profile="conservative")  # 5% cap = $50
    raw_would_be = size_trade(user, whale_trade(value=9000, portfolio=10000), n_active=1)  # ~90% of balance uncapped
    assert raw_would_be <= 50

def test_below_minimum_is_skipped_not_failed():
    user = make_user(balance=20, risk_profile="balanced")
    result = size_trade(user, whale_trade(value=1, portfolio=1_000_000), n_active=15)
    assert result.status == "SKIPPED_BELOW_MINIMUM"

def test_dormant_wallets_excluded_from_denominator():
    active_set = get_active_basket()  # should exclude dormant=True wallets
    assert all(w.dormant == False for w in active_set)
```

### Phase 1 — Simulated Fill Integrity
```python
# test_fill_model.py
def test_fill_walks_order_book_not_exact_whale_price():
    book = mock_order_book(best_ask=0.42, depth=[(0.42, 100), (0.43, 200)])
    fill = simulate_fill(order_value_usd=150, book=book)
    assert fill.avg_price > 0.42  # must reflect book-walking, not a naive exact-price assumption

def test_latency_penalty_applied_before_snapshot():
    fill_no_latency = simulate_fill(order_value_usd=100, latency_ms=0)
    fill_with_latency = simulate_fill(order_value_usd=100, latency_ms=1500)
    assert fill_with_latency.snapshot_time > fill_no_latency.snapshot_time
```

### Phase 1 — AI Whale Analysis
```python
# test_ai_summary_grounding.py
def test_summary_does_not_introduce_unlisted_numbers(mock_llm_response):
    stats = {"win_rate_pct": 88, "all_time_pnl_usd": 120000}
    summary = generate_summary(stats, llm_response=mock_llm_response)
    # crude grounding check: any numeric token in summary must appear in stats
    numbers_in_summary = extract_numbers(summary)
    assert all(n in stats.values() for n in numbers_in_summary)
```

### Phase 1 — Slippage
```python
def check_slippage(whale_price, current_price):
    diff = abs(current_price - whale_price) / whale_price
    if whale_price <= 0.25 and diff > 0.012:
        return "CANCEL_ORDER: SLIPPAGE_EXCEEDED"
    return "EXECUTE_ORDER"

assert check_slippage(0.10, 0.12) == "CANCEL_ORDER: SLIPPAGE_EXCEEDED"
assert check_slippage(0.50, 0.505) == "EXECUTE_ORDER"
```

### Phase 1 — Digest Email
```python
# test_digest_content.py
def test_digest_includes_only_opted_in_users():
    users = [make_user(daily_digest_opt_in=True), make_user(daily_digest_opt_in=False)]
    recipients = build_digest_recipient_list(users)
    assert len(recipients) == 1

def test_digest_reflects_actual_trade_log():
    trades = get_trades_for_user(user_id, since=yesterday())
    digest = render_digest(trades)
    assert len(digest.trade_rows) == len(trades)  # no summarization drift from real log
```

### Phase 2 — Custody & Execution
```python
# test_live_execution_gating.py
def test_kill_switch_blocks_before_order_construction():
    user = make_user(live_trading_enabled=False)
    with pytest.raises(TradingDisabledError):
        execute_live_order(user, signal)

def test_daily_loss_limit_enforced_server_side():
    user = make_user(live_trading_enabled=True, daily_loss_so_far=490, daily_loss_limit=500)
    result = execute_live_order(user, signal_sized_at=50)
    assert result.status == "RISK_BLOCKED"

def test_no_raw_private_key_ever_stored():
    link = create_live_wallet_link(user, provider="privy")
    assert not hasattr(link, "private_key")
    assert link.clob_api_key_enc is not None  # read-only creds only
```

### Phase 2 — Performance Fee
```python
# test_fee_calculation.py
def test_no_fee_when_recovering_past_losses():
    user = make_user(high_water_mark=1200, current_value=1000)
    user.current_value = 1150  # recovering toward, not past, HWM
    fee = calculate_fee(user, fee_pct=0.15)
    assert fee == 0

def test_fee_only_on_profit_above_hwm():
    user = make_user(high_water_mark=1000, current_value=1200)
    fee = calculate_fee(user, fee_pct=0.15)
    assert fee == 30  # 15% of the $200 above HWM

def test_hwm_ratchets_up_only():
    user = make_user(high_water_mark=1000, current_value=1200)
    apply_fee_and_update_hwm(user, fee_pct=0.15)
    assert user.high_water_mark == 1170  # never decreases even if value later drops
```

---

## 14. Open Questions (carried forward intentionally, not resolved here)

- `POLYMARKET_MIN_ORDER_USD` needs a live-verified value from current CLOB docs before hardcoding — this directly determines how small a starting balance can realistically work with an uncapped basket.
- Performance fee percentage and billing cadence are placeholders (15% monthly used in tests) — tune before any real launch.
- Legal classification of the fee model + basket structure for Phase 2 is unresolved by design — flagged, not solved, in this document.
- `wallet_snapshots` retention/rollup policy once it grows past a few million rows.





API KEYS: 
ENVIO: [REDACTED]
GROQ Keys (in rotation): 
[REDACTED]
[REDACTED]
[REDACTED]


If you need anything else, ask directly.
