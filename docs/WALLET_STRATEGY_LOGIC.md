# Baleen wallet selection and copy logic

Updated: 2026-09-21. This is the single current strategy document. The dated audit sections below preserve the original findings; this implementation summary supersedes their older implementation-status statements. This is not a validated profit claim.

## Current implementation and activation boundary

The paper application now has one server-owned selection per account. The former browser-only switches did not control copying; they have been replaced. Starting a paper run explicitly archives its predecessor, saves the selected admitted wallet addresses, observes current leader equity, and fixes each allocation ratio for that run. This is a forward research trial, not automatic real-money qualification. Fresh exclusion evidence blocks new starts/entries; existing exits remain supported. Quiet research/watchlist wallets are monitored independently of active allocations.

The scheduled paper worker consumes durable source detections, verifies the exact V1/V2 Polygon receipt and confirmation depth, observes book depth and market fee metadata, and writes a unique account decision. Copying rejection cannot erase source detection. Complete legs must meet minimum size/notional, depth, slippage, cash and inventory constraints. Missed in-scope legs pause subsequent entries, preserving visible fidelity failure rather than changing sizes. Exits of leader inventory predating the run are labelled outside its scope. The ratio never uses lifetime P&L.

Cash, inventory, fees, partial exits and paper settlement use the independent Decimal ledger. Missing/stale marks make current equity and P&L unavailable. Binary paper settlement reads confirmed CTF payouts and waits until source delivery/processing has caught up; it is not an on-chain redemption transaction. Old simulator records are separate from these results. The dashboard reads saved selections and journal outcomes rather than inventing a followed count.

Listener supervision restarts both required processes if either exits. A server-stored delivery checkpoint permits restart/redeployment replay; it advances only after acknowledged delivery. Each ingestion batch refreshes the watched roster before advancing. Durable heartbeat/progress state distinguishes unknown, online, stalled and offline across replicas. `python -m app.paper_preflight` provides read-only deployment checks.

**Required before calling production repaired:** deploy the complete backend/listener/frontend release through migration 24, verify the listener and worker in the target environment, start the desired fresh paper configuration, and observe a real new source fill through the deployed journal and UI. Local passing tests alone do not establish this.

**Still empirical, not granted by code:** historical independent reconciliation where external funding/basis is unavailable, adequate prospective resolved outcomes, untouched cohort comparisons, and demonstrable profitable copying. The application does not issue real-money approval. Arbitrary source transfers, splits, merges and conversions are not replicated by the trade-only follower; their absence prevents representing it as a full wallet clone. The independent offline ledger supports those events only when valuation/basis evidence is supplied.

The [original request](WALLET_STRATEGY_ORIGINAL_REQUEST.md) is preserved verbatim. This document separates requested behavior, observed evidence, and proposed decisions. Numerical defaults below are research hypotheses unless explicitly identified as user requirements. Historical build specifications in `archive/` are not current strategy instructions. See the [wallet data audit](research/WALLET_DATA_AUDIT.md) for tests, results, limitations and cleanup details.

## 1. Assessment

The overall architecture is sensible: discover widely, screen cheaply, verify deeply, and allocate only to trades that are practical to copy. One shared wallet registry is the right model. Separating frequent directional traders from occasional high-conviction traders also makes sense.

The objective should be **net copy returns subject to explicit loss, concentration and liquidity limits**. Maximum trading frequency and maximum invested capital are not objectives themselves. A trader can be profitable while a delayed follower loses money. Idle cash can be preferable to a poor trade. No selection rule establishes that we will make the most money possible.

My main recommended changes to the idea:

1. Treat 4,000 trades as an initial sample, never automatically as lifetime history.
2. Separate the platform's displayed P&L from directional trading profits, incentives, open losses, and our achievable copy returns.
3. Measure independent decisions and completed position episodes, not raw fill count alone.
4. Use a watchlist for occasional snipers, with no permanent capital commitment.
5. Fund opportunistic trades from available cash first. Do not automatically sell the worst-performing sleeve.
6. Preserve the leader's relative position sizes with a stable proportional multiplier where feasible; never use lifetime P&L as bankroll. Risk limits determine whether we can copy the strategy faithfully, not arbitrary per-trade conviction multipliers.
7. Allow zero eligible wallets or zero executable signals, especially at $20.

## 2. Requirements preserved from the request

| Area | Requested behavior |
|---|---|
| Registry | One global wallet database and selection algorithm, regardless of account count. |
| Discovery | Keep the existing discovery approach; distinguish discovery from re-evaluation. |
| Cheap gate | Below $50,000 all-time P&L: discard immediately, no stored wallet and no blacklist. |
| Deep evaluation | Above the threshold: collect identity, profile image where available, recent trades and performance evidence. Initially target 4,000 trades with verified pagination. |
| Evidence | Reject insufficient history; check the time span, recent activity, recent gains and long-term consistency. |
| Core ideal | Active directional sniper, **2–30 trades per day** (user clarification on September 17), consistent meaningful returns and controlled losses. HFT is excluded. |
| Undesirable behavior | HFT, difficult-to-copy arbitrage, opposing exposure, resolution-price trading, large swings and persistent flat performance. |
| Occasional sniper | Identify rare substantial trades amid inactivity or small trades; monitor without an ordinary funded sleeve. |
| Opportunistic funding | Consider reallocating a portion of capital when a rare sniper acts; assess whether this is a good idea. |
| Account size | Follow fewer wallets with less capital; approximately one at $20, one or two at $100 if feasible. |
| Minimum orders | Solve proportionally sized orders becoming too small to execute. |
| Accuracy | Test APIs and reconstruction; aim to reconcile with Polymarket rather than inventing curves. |
| Order of work | Agree on the logic before implementing it or doing website work. |

Interpretation: exactly $50,000 passes (`>=`), consistent with rejecting amounts under $50,000. The original says both “above” and “under”; equality is an explicit proposed boundary choice.

## 3. What was actually checked

### Local code inspection

The current discovery client already uses recent 1,000 trades, large trades, ALL/MONTH/WEEK leaderboards, and market scans; the scanner also adds curated seeds. Preserve those sources, but fix their data contracts before trusting their output.

Discrepancies identified September 15, with September 17 disposition:

- **Fixed:** `scan_for_wallets` now verifies ALL-period P&L >= $50,000 before storing a new candidate. Zero, unknown, NaN and infinity do not pass. Existing records are retained.
- `evaluate_pending_wallets`: starts positions/activity/profile/trades/closed-position requests together, before rejecting low P&L.
- **Fixed:** `fetch_wallet_trades` explicitly includes maker trades and pins the cutoff; activity also pins its cutoff. **Pending larger coverage integration:** reaching a sample budget must not become evidence of lifetime completeness.
- **Fixed:** leaderboard discovery now visits offsets 0/50/100/150/200/250 with limit 50 for each period, covering the intended first 300 ranks.
- **Fixed:** discovery no longer invents volume by multiplying a trade or P&L. Unknown volume remains unknown.
- **Fixed:** missing ALL-period P&L no longer falls back to MONTH or current-position `cashPnl`; documented closed-position sort casing and V2 stats identity/null handling are corrected.
- **Fixed after integration testing:** the portfolio summary no longer treats unknown current marks as entry prices with flat P&L; unknown totals remain unknown and known subtotals remain available.
- Scanner and scoring engine duplicate gates; sample-size exemptions at $500k and the scanner's $22m upper P&L cap are not requirements in this request.
- The scanner's `min_capital_required` expression uses lifetime P&L as a sizing denominator. Replace this with executable account-level sizing analysis.

The full existing backend suite was run after these fixes. This is still not a proof of all production accounting/execution paths or strategy profitability.

### Read-only live API sample

See [saved observations](research/wallet_api_probe_2026-09-15.json) and [reproducible probe](research/probe_wallet_data.py). These are public GET requests only. The sampled wallet is a data fixture, not a recommended wallet.

| Check | Observation | What it proves / does not prove |
|---|---|---|
| ALL/WEEK/MONTH user leaderboard | Each returned HTTP 200 and one matching wallet | Period P&L is accessible for this wallet; accounting equivalence and rolling-window semantics remain unverified. |
| Legacy trades | Eight pages of 500, 4,000 distinct diagnostic composite keys, zero wrong-wallet rows, descending timestamps | Pagination worked for this sample. Not proof of full history or canonical event uniqueness. |
| Time span | 0.4464 days, approximately 10.7 hours | 4,000 trades can be nowhere near sufficient temporal coverage. |
| Recent activity | Most recent sampled trade was in August, despite querying in September | Lifetime success must not imply current activity; also check provider freshness before attributing gaps to the trader. |
| Leaderboard size | Request 100, response 50 | Current offset increment needs correction. |
| V2 trades | Data envelope and next cursor returned | V2 is available; full cursor traversal has not yet been validated. |
| V2 profile stats | Distinct-market count and separate fill count, multiple P&L components, fees, rebates and rewards returned | More analysis is possible than profile + four thousand trades; null deposit/withdrawal fields occurred. |
| V2 P&L series | Returned points plus source fidelity and source block | Identical repeated source blocks must not count as independent fresh observations. |
| Current/closed positions and activity | HTTP 200, sample rows returned | Full pagination, reconciliation and all lifecycle cases remain to be tested. |
| Market/book minimum | Sample Gamma market and CLOB book both reported minimum size 5 | A universal one-dollar rule is insufficient; validate share size, price, order type and notional restrictions. |

The first request with Python's default headers returned 403; the same public read with a browser-style User-Agent and JSON Accept header succeeded. Production HTTP behavior needs its own contract test.

The V2 economic P&L and legacy leaderboard P&L differed in this sample. Do not splice those curves together. Source time and methodology must be reconciled first. No profile-page chart comparison or third-party scraper accuracy claim was verified here.

## 4. End-to-end pipeline

```text
Discovery sources -> deduplicate addresses in memory -> cheap ALL P&L gate
  below $50k -> discard; no durable wallet/profile/address rejection record
  unknown/error -> transient retry; never treat as zero
  passes -> shared wallet record -> collect versioned evidence
    incomplete -> pending evidence, ineligible for new copies
    sufficient -> accounting checks -> strategy/copyability gates
      core eligible | opportunistic watchlist | rejected for now
    core eligible -> shadow-copy validation -> account compatibility -> sleeve
    watchlist -> qualified signal -> account compatibility -> opportunity allocation
Every new signal -> price/risk/cash checks -> order -> fill reconciliation -> exits
Re-evaluation -> new immutable decision -> retain / pause / promote / demote
```

### Finding wallets when they are not trading during a scan

Addresses come from public leaderboard entries (`proxyWallet`), historical trade rows, market holders and retained known candidates. The existing leaderboard discovery already works without a simultaneous new trade. Curated seeds are discovery inputs, not automatic qualification.

Keep three acquisition channels: (1) ALL/MONTH/WEEK leaderboards, expanded across categories and rotated rank pages in the later discovery revision; (2) historical trades/holders in a rotating market universe, including resolved markets and quiet periods; (3) retained admitted candidates and the occasional-sniper watchlist, revisited even if absent from today's leaderboard. Apply the same cheap ALL P&L gate to new identities from every source. Keep source/rank/page coverage to expose selection bias. No public leaderboard guarantees discovery of every skilled wallet.

Qualification requires 7/30/90-day evidence, not a trade during the scan's execution. A missed scan does not remove an admitted wallet. New sub-$50k addresses still are not persisted; retained above-threshold candidates are scheduled for re-evaluation. A quiet high-quality wallet belongs on the opportunistic watchlist when it fails the core activity target.

### Cheap gate details

Use a fresh, identity-matched ALL-period platform P&L observation as the initial screen. Record the exact provider/field in the policy version. Do not use a WEEK/MONTH candidate value as lifetime P&L. Do not silently switch from displayed P&L to economic P&L when one endpoint fails.

For new wallets below threshold, retain only aggregate scan counts without addresses. Deduplicate in memory for the current scan; they may be discovered again. Do not persist raw discovery payloads containing these rejected addresses in routine logs. Unknown P&L is an operational retry, not a failed trader.

The no-storage rule applies to newly discovered sub-threshold wallets. A previously admitted wallet that falls below threshold must retain historical decisions and account-position references; pause new copying instead of deleting records needed for exits and accounting.

## 5. Data model and storage

Shared tables, keyed by chain plus normalized profile/proxy wallet address:

- **wallets:** identity, optional names/images, discovery source, classification and latest eligible decision. Display names are never identity keys. Resolve signer/proxy aliases from evidence rather than assuming all addresses belong to one person.
- **provider_observations:** provider version, query, received time, source time/block, payload reference/hash, coverage and errors for admitted wallets.
- **trade_events / account_activity:** canonical events with reversals/reorg handling; include trades, transfers, redemptions, splits, merges, conversions, rewards and fees where relevant.
- **position_episodes:** entry/add/partial-exit/close/reopen lifecycle with cost basis and unresolved inventory. Keep raw events alongside aggregates.
- **pnl_snapshots:** separately named platform, reconstructed realized, unrealized, incentive, and copy P&L; denominator and freshness metadata.
- **evaluations:** immutable metric values, policy version, input cutoff, confidence, all failure reasons and next review time.
- **signal_candidates:** shared leader event or grouped decision, timestamps, class and strategy eligibility.

Account-specific tables: accounts, available/reserved cash, sleeve allocations, account signal decisions, order intents, orders, fills, positions, fees and net P&L. Wallet quality is shared; affordability and actual results are account-specific.

Use fixed-precision decimals for accounting. Enforce unique canonical events, idempotent signal processing, and atomic cash reservations. One source event may lead to one decision per account, not duplicate orders on listener retries. Positions belong to accounts; no capital is shared between users.

## 6. History retrieval and coverage

The initial budget is 4,000 recent trades including maker and taker fills. Record oldest/newest timestamp, cutoff, fill count, independent episodes, markets, distinct active days, calendar span, missing cost basis and truncation.

Prefer the documented V2 cursor interface once its contract tests pass. The existing V1 fallback should use a fixed end time, explicit maker/taker inclusion and verified time windows when paging beyond endpoint limits. The public documentation describes V2 cursors and snake-case fields; adapters must normalize deliberately. [Migration documentation](https://docs.polymarket.com/api-reference/data-api/migrating-from-v1).

Rules:

1. Freeze an evaluation cutoff and preserve it through every page.
2. Detect repeated pages/cursors, wrong wallets, out-of-order rows, schema changes and failures after partial success.
3. Distinguish exhausted history, requested-sample complete, and truncated/unproven coverage.
4. Do not deduplicate on transaction hash alone: a transaction may contain multiple fills. Prefer chain + transaction + log index when available; resolve API-row identities against canonical events before certifying counts.
5. Handle multiple fills at the same timestamp without skipping a boundary second.
6. A 4,000-fill sample spanning a few hours triggers backfill or insufficient-evidence status, not an “all-time” statistic.
7. Fewer than 4,000 fills is fine if enough independent outcomes and calendar coverage exist.
8. A short/empty page is trustworthy only under the validated endpoint contract, not after a swallowed error.
9. Preserve inventory at the start of a window. A sale whose buy predates the window has unknown profit unless opening cost basis is recovered.

Legacy trade documentation exposes `takerOnly` with a true default, plus `start`/`end` filtering. [Trade contract](https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets).

## 7. Accounting and useful statistics

### Do not collapse all P&L into one number

Maintain three views:

1. **Platform P&L:** the platform's original field and curve, with its semantics and timestamp. Used for the cheap gate and display reconciliation.
2. **Reconstructed economic result:** reconciled realized gains/losses, remaining inventory value, fees and other income, with each component separate. Transfers/deposits are not profits.
3. **Follower result:** what our account actually earns, or realistically could earn after delay, spread, depth, fees, missed fills and sizing limits. Use this to judge strategy viability.

The V2 profile and P&L interfaces expose a component breakdown. Field names alone do not establish whether fees are already included; reconcile identities before adding or subtracting them. [Profile stats](https://docs.polymarket.com/api-reference/wallet/get-a-users-profile-stats), [P&L series](https://docs.polymarket.com/api-reference/wallet/get-a-users-pnl-series).

Realized profit per closed quantity = proceeds minus allocated entry cost minus applicable costs, with settlement/redemption handled as cashflows. Open inventory must include losses and unresolved/redeemable positions. An empty open-position list is not a lifetime P&L statement. A closed-position timestamp is not necessarily the date every dollar of its lifetime profit was earned. [Closed-position fields](https://docs.polymarket.com/api-reference/core/get-closed-positions-for-a-user).

For an account with complete equity and cashflows:

`period profit = ending equity - starting equity - deposits + withdrawals`

For external wallets with unavailable cashflows/cost basis, mark return on equity unknown; do not manufacture a percentage. P&L divided by gross trading volume is a turnover metric, not portfolio return. Drawdown percentages require an equity series or explicitly defined risk-capital basis, not a cumulative-P&L curve starting at zero.

### Metrics to compute

| Dimension | Metrics and purpose |
|---|---|
| Evidence | Calendar coverage, completed episodes, independent event clusters, missing basis, provider freshness. |
| Recency | Last meaningful entry, active days, decisions per calendar day, current 7/30/90-day evidence. |
| Profitability | Net trading P&L, profit factor, average win/loss, cost-normalized episode returns, net copy result. |
| Consistency | Profitable weeks, rolling 7/30-day change, losing streaks, recent deterioration. |
| Risk | Equity drawdown where identifiable, worst episode, tail loss, exposure at risk, unresolved losses. |
| Concentration | Share of gross positive profits from top 1/3/5 episodes, correlated event concentration, result with biggest win removed. |
| Copyability | Delay sensitivity, achievable entry/exit, spread/depth, holding time, fill and minimum-order success rates. |
| Capital efficiency | Holding duration and net result relative to capital tied up; no mechanical reward for churn. |
| Strategy | Entry price bands, directional exposure, maker dependence, hedging, incentive share and category specialization. |

Count win rate over completed episodes, and cluster correlated markets for confidence intervals. Twenty fills of one prediction are not twenty independent wins. Confidence estimates must account for dependence and small samples.

For a binary share held to resolution, ignoring fees: buying at price `p` yields `(1-p)/p` profit on cost if it wins, and -100% if it loses. At 0.50 a win returns 100% profit, not 50%; at 0.20 it returns 400%. Expected profit per share is `q-p` when true success probability is `q`. Thus a high win rate can lose money at high entry prices, and a low win rate can be profitable at low prices. Early exits require their actual exit economics instead.

## 8. Classification and initial research gates

**Common gates:** verified threshold, sufficient accounting coverage, adequate independent evidence, bounded risk, practical execution and no unresolved data-quality failure. A large lifetime win does not waive evidence requirements.

Proposed baseline for experiments, not scientifically established cutoffs:

| Gate | Core candidate | Occasional sniper watchlist |
|---|---|---|
| History | At least 90 calendar days of covered evidence | At least 180 days; rarity needs longer observation |
| Sample | At least 100 completed episodes across at least 30 independent event clusters | At least 30 substantial completed episodes across at least 20 clusters |
| Activity | **User requirement: 2–30 trades/day.** Measure 7- and 30-day calendar averages and the daily distribution; no HFT/burst loophole. Proposed regularity: active on 5 of the last 7 full UTC days. | No daily-activity minimum; qualify the rare-trade subset separately |
| Recent performance | Positive net directional P&L in both trailing 7 and 30 days, with fresh marks and boundary observations | Positive longer-window directional results; do not require a gain every inactive week |
| Economics | Positive net expectancy and initial profit-factor hypothesis >= 1.3 after modeled costs | Same, evaluated only with a rule defined before the triggering trade |
| Outliers | Prefer positive result after removing largest win; test concentration limits such as top win <= 25% of gross profits | Require repeated independent profitable opportunities; one huge hit is insufficient |
| Risk | Initial hypothesis: <= 20% equity drawdown on a valid series; otherwise pending evidence, not a made-up pass | Same accounting standard, plus tighter account-level opportunity exposure |
| Copy evidence | Positive out-of-sample follower results and usable sample/confidence | Same, including historical detection of rare signals without hindsight |

These defaults intentionally favor evidence and may produce no eligible wallet. Compare nearby thresholds on training/validation periods; freeze a policy before its final test. Do not relax gates until something passes. High win rate is a preference conditional on price and payout, not a universal 70% admission rule.

Report raw fills, distinct transactions, entries, exits, and proven grouped orders separately. Use raw-fill counts as the conservative initial screen; do not silently reinterpret 4,000 fills as 20 decisions. Group fills only when event/order evidence supports it, not simply because timestamps are close. Apply the 2–30 band to established trade decisions once this grouping is validated; full-day bursts above 30 trigger exclusion or evidence review, even when the weekly average is in range. Tiny trades cannot be discarded merely to hide an HFT pattern. Meaningful-entry activity is an additional quality metric, not a way around the activity ceiling.

Treat high opposing exposure, rapid reversals, prices near resolution, short holding times and many fills as strategy flags. Buying both outcomes can be hedging or a position transition; one occurrence does not prove arbitrage or misconduct. Exclude strategies whose edge depends on multi-leg execution, maker rewards or speed we cannot reproduce. Do not automatically ban all near-boundary or high-frequency observations without grouping and context.

### Flat P&L despite many trades

Distinguish trading activity from profit generation. Require both recent gains and current copy economics for core admission. A positive $100 week is not automatically meaningful for a multimillion-dollar strategy. Compare net gain to capital exposure, costs and uncertainty, and separate stale provider marks from genuine flatness. A narrow band such as +/- $100 is not a universal cutoff.

### States

`pending_evidence`, `core_candidate`, `core_eligible`, `opportunistic_watchlist`, `paused`, `rejected`.

Data failures pause eligibility and trigger retry. Poor strategy evidence produces a dated rejection with reasons and reconsideration time. Rejected is not permanently blacklisted. Wallet classification does not itself authorize a trade.

## 9. Rare-sniper logic and funding

The request's suggestion that some wallets hide skill with tiny trades is a hypothesis about intent. We can test the observable pattern without claiming to know motive.

For each watchlisted wallet, build a trailing distribution of grouped entry sizes, categories, prices, holding times and outcomes. An initial signal rule to research is a new directional exposure in the top 10% of that wallet's trailing entry sizes, at least three times its median, in a historically supported category. Define the rule using only information available before the trade; aggregate split fills with an explicit short observation window and count that delay in replay.

A triggering trade must still pass current liquidity, price drift, expected net edge, account budget and concentration checks. A large trade is not evidence by itself. Never selectively remove earlier losses to create a “sniper” track record.

Funding priority:

1. Unreserved account cash within the opportunity risk allowance.
2. Uncommitted cash allocated to a core sleeve, provided that sleeve's existing obligations remain funded.
3. Proceeds from normal exits when they become available.
4. Otherwise skip. The first version should not force liquidation to chase a rare trade.

My recommendation is to reject automatic “sell the worst sleeve” funding. Recent loss alone says little about remaining expected value, and selling creates spread, fees and timing risk. A later reallocation policy could compare the new opportunity with the expected value of keeping an existing position, including exit costs and uncertainty, and would need its own validation.

Research ceiling: opportunistic positions together consume at most 10% of account equity, with at most 5% in one event. These are proposed maximums, not money that must remain reserved or spent. If minimum order sizes make those caps infeasible, the feature is unavailable for that account. All sleeve and opportunity exposures count toward the same account limits.

## 10. Capital sizing and number of wallets

Lifetime P&L is accumulated profit, not the leader's current bankroll. Do not scale a $300 leader trade by `$20 / leader lifetime P&L`.

**Revised recommendation following the user's September 17 concern: proportional copying first.** Arbitrary conviction multipliers, equal-dollar trades and increasing a sleeve because it recently won can change the whale's system. They are not the proposed default.

For a fully observed reference strategy, establish `k = our sleeve capital / leader strategy capital` and copy quantities at the same multiplier: `our shares = k × leader shares`. For example, leader entries of $100/$300/$600 at unchanged prices should retain a 1:3:6 exposure ratio, not become three equal trades. Copy partial exits against the actual attributable inventory. Repeated fills of one order must not create repeated independent size increases.

Hold the multiplier stable through an allocation episode; change it only at a documented rebalance with explicit handling of existing positions. Entry slippage means identical share ratios do not imply identical dollars or returns. Leader deposits/withdrawals and strategy capital changes require reconciliation before adjusting k.

**The denominator remains a data question.** Current marked positions exclude idle cash; lifetime P&L is not equity; external assets and hedges may be invisible. The audit tests public account-value/accounting sources, but we must establish which collateral, proxy and positions they cover before calling this exact equity-proportional copying. If full leader strategy capital is unknown, a constant share multiplier calibrated from observed inventory preserves relative quantities within that observed strategy, but not necessarily its fraction of total bankroll. Label that limitation and validate out of sample; do not silently claim exact copying.

The September 17 audit successfully read `/v1/accounting/snapshot` for two wallets: it supplies `cashBalance`, `positionsValue`, `equity` and valuation time. This is a stronger candidate denominator than `/v2/value`, which returned position value alone. It is a current provider snapshot, not proof of historical equity, capital dedicated to this strategy, or all external holdings. Verify collateral/proxy coverage and snapshot freshness before adopting it.

Risk checks apply to admission and execution feasibility. If the whale's portfolio cannot fit an account's minimum sizes, liquidity and exposure limits at one consistent multiplier, choose another wallet, reduce the entire allocation consistently, or do not copy. Avoid silently clipping selected trades and calling the remaining portfolio faithful. Any skipped/mismatched entry is logged as a replication deviation, and subsequent exits are bounded by what we actually hold.

Starting mid-strategy also needs an explicit rule: either reproduce existing inventory at acceptable current prices with its original cost basis clearly separated, or start at a flat/clean episode boundary. Copying only new additions while ignoring old hedges is not exact replication. No funded switch to this policy is included in the small-fix scope.

For a simple fully funded long binary position, test the proportional amount against capacity:

`target shares = k × leader shares`

`required cash = target shares × executable price + fees`

Approve only if the target fits sleeve/event/account limits, available cash and liquidity. A failure is a copy-feasibility failure, not permission to arbitrarily resize that one leg.

Round quantities only to venue precision; measure the resulting deviation and reject material distortions.

For long binary shares, the full purchase cost can be lost; calculate risk accordingly. Sum same-event/correlated exposure across wallets before approving more. No leverage or unsupported short exposure is assumed by this design.

Validate venue constraints at execution time: share minimum, price tick, precision, order-type notional minimum, fees and available depth. The order book exposes `min_order_size` and `tick_size`. [Order book contract](https://docs.polymarket.com/api-reference/market-data/get-order-book).

An illustrative minimum of 5 shares at $0.50 requires $2.50 before fees. At $20 equity that is 12.5% of the entire account. A proposed 5% per-event cap allows only $1, so that signal must be skipped. An advertised $1 floor cannot override the actual market/order constraints.

### Subminimum orders

- Never round upward through risk limits merely to reach the minimum.
- Net overlapping eligible same-outcome signals before ordering, with attribution and shared exposure caps.
- Accumulate only within a defined short signal-validity window, and recheck the price/edge. Do not save a stale trade for hours until enough signals appear.
- Skip and record an explicit reason if still too small. Measure whether skipping distorts performance.
- Reduce the wallet count if splitting capital prevents viable execution.

### How many wallets?

Estimate each wallet's minimum viable sleeve by replaying its signals across candidate budgets with real minimum sizes, concurrent inventory, fees and reserves. Require positive net follower performance and faithful representation of every material leg within an explicit rounding/execution tolerance. Report both signal coverage and exposure-weight deviations. The earlier suggested 80% signal-coverage target is withdrawn: it could omit crucial trades and should not qualify a strategy as faithfully copied. Inspect every missed leg and its effect on subsequent positions/exits.

Then choose a feasible, weakly correlated set whose sleeve requirements fit deployable capital. A rough bound for equal sleeve requirements is `floor(deployable capital / minimum viable sleeve)`, but the final check must replay the combined portfolio and its shared events.

| Capital | Product expectation, conditional on evidence |
|---|---|
| $20 | Zero or one wallet. At strict risk limits many markets may be infeasible. |
| $100 | Zero, one or two; choose two only if both sleeves remain executable. |
| Larger | Add wallets only when capital capacity and diversification improve results. |

More wallets following the same election outcome do not provide much diversification. Do not fill a wallet quota or force all cash into positions.

## 11. Signal execution, exits and re-evaluation

For every signal: verify source identity/event, freshness, wallet's latest decision, available cash, existing orders, venue status, token/outcome, event correlation, current executable price, fees and depth. A new leader fill does not imply we can trade at their historical fill price. Reject stale or excessively moved signals.

Reserve cash atomically, submit once, reconcile partial fills and retries, and keep separate intended/filled quantities. Prevent duplicate exposure across sleeves. The executor must preserve minimum-order and risk checks even if the selection layer is wrong.

Exits: copy source reductions proportionally to our attributable inventory, subject to executable liquidity; never sell more than held. Define and replay risk exits, event resolution/redemption, delisting and source disappearance. Removing a wallet blocks new entries but does not delete positions or blindly liquidate them. Small residual positions need an explicit dust/redemption policy.

Proposed schedules: retain the existing discovery cadence initially; collect new signals continuously; refresh evidence incrementally; run full strategy re-evaluation daily. Severe data, execution or risk failures pause new entries immediately. Soft deterioration can require two consecutive daily failures before removal, while new entry eligibility remains paused during review. Promotions require fresh evidence and shadow validation. Keep independent retry scheduling for provider errors.

Existing funded positions remain managed during every state transition. Store the decision that was actually known at each time to make replay possible.

## 12. Tests required before implementation is considered ready

The probe is an initial feasibility check. It does not replace this validation suite.

1. **API contracts:** active/inactive/sparse/dense wallets; missing profiles; ALL versus WEEK/MONTH; V1/V2 field normalization; zero versus null; maker/taker coverage; source freshness; fees and minimum sizes.
2. **Pagination:** 0/1/499/500/501/4,000/>4,000 rows; repeated pages/cursors; live inserts; timestamp ties; empty midstream pages; errors/timeouts/429; exhaustive windows and wrong-wallet contamination.
3. **Accounting fixtures:** partial sells, reopenings, starting inventory, transfers, splits/merges, redemptions, resolved-but-unredeemed losses, rebates/rewards, fees, reorgs and zero-cost/unknown-cost inventory. Verify no double counting.
4. **Reconciliation:** several wallets of each strategy type; compare platform values at matching source times, same timezone/window/metric and rounding. Investigate residuals; do not rescale a reconstructed curve to visually match. Establish justified tolerances before pass/fail.
5. **Classification counterexamples:** 99% tiny wins plus one large loss; low-win-rate positive expectancy; one-hit wonder; frequent flat trader; tiny filler trades; split fills; correlated event bets; hedging transitions; incentive-heavy maker; changing strategy; incomplete history.
6. **Account replay:** $20, $100 and larger accounts; full drawdowns, fees, actual minimums, partial fills, no fills, duplicates, cash contention, sleeve overlap, dust and exits. A $20 simulation must obey the same venue/risk constraints as a funded account.
7. **Historical research:** discover/select using only data available at each date. Include rejected and failed wallets in the study to avoid survivor bias. Separate parameter tuning, validation and a final untouched test. Bootstrap by independent event/time blocks rather than individual fills. Correct for searching many wallets/rules.
8. **Copy realism:** delay grid, historical spread/depth where available, fee schedule at the time, adverse price moves, missed entries/exits and capacity. If historical books are unavailable, disclose the approximation and collect forward shadow data; trades alone cannot prove executable historical returns.
9. **Shadow validation:** run the full signal-to-fill simulator on fresh live books without money, compare expected versus achieved behavior, and collect enough independent outcomes. A few profitable days are not proof.
10. **Alternatives:** compare core-only, core + opportunistic, and cash; compare proposed gates with simpler policies. The sniper layer must improve net results after its opportunity cost, not merely add winning anecdotes.

Launch evidence must show internally reconciled accounting, valid coverage, bounded account losses/exposure, executable order sizing, and credible out-of-sample copy economics. Failure or uncertainty means keep the affected strategy in research/shadow mode.

## 13. Proposed next implementation sequence

1. Finalize this policy, including P&L definition, faithful-copy denominator, activity grouping and account feasibility limits.
2. Build the provider/coverage and reconciliation harness; resolve the observed P&L differences.
3. Completed small fixes: discovery pagination and cheap gate before new candidate insertion, plus provider contract corrections. Existing admitted-wallet deep evaluation still needs the larger evidence pipeline.
4. Consolidate gates into one versioned evaluator with explicit missing-data states.
5. Implement core eligibility, shadow copying and account budget feasibility.
6. Evaluate occasional snipers as a separate experiment; enable only if they add measurable value.
7. Design the website around verified backend behavior and honest metrics.

The major strategy/website changes remain proposals. September 17 work adds broader public API tests, saved curves, small provider/discovery fixes and documentation cleanup. The audit separates tests run successfully from work requiring historical execution data, deployed infrastructure or future observation.
