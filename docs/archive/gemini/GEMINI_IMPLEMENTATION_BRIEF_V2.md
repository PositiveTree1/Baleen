# Baleen — verification, financial integrity, and the next paper run

Audit date: 8 September 2026. This document supersedes the previous brief's delivery priorities; unresolved requirements in GEMINI_IMPLEMENTATION_BRIEF.md still apply.

**Current handoff:** For Batch B, read [GEMINI_BATCH_B_INSTRUCTIONS.md](GEMINI_BATCH_B_INSTRUCTIONS.md) first, then R3–R5 below. It clarifies implementation order and acceptance evidence without expanding the batch. Read [BATCH_A_RECHECK.md](BATCH_A_RECHECK.md) for current Batch A status; the original audit findings and test counts below are historical, not a description of the latest working tree. The user has authorized Batch B implementation while Batch A's fresh browser acceptance check remains tracked separately.

## Decision: do not approve the current paper results or enable real money

Gemini made useful improvements, but the implementation is not complete. There are reproducible errors that create extra paper buying power, inflate balances, double-count source performance, use another market's price, or execute rejected backtest trades. Strategy optimization on these results would optimize the bugs as well as the strategy.

Do not erase the current run to hide these problems. Archive it as an experimental run with known accounting/data defects. Fix and validate the system first, then start the designated guest benchmark again at exactly $10,000 using the protocol at the end of this document.

No claim of guaranteed profit, zero bias, or exhaustive security coverage is justified. The goal is a system with explicit assumptions, independently reconciled financial records, measurable uncertainty, and reproducible evidence that a strategy survives realistic costs. Even an accurate paper model cannot guarantee future live returns.

## What I actually verified

- Reviewed Gemini's uncommitted working-tree changes and traced remaining discovery, provider parsing, scoring, ingestion, accounting, valuation, settlement, backtesting, and API/client paths. Production deployments were not changed or inspected.
- Entire existing backend test suite: **2,509 passed in 12.06 seconds**.
- Frontend TypeScript check: passed. Frontend ESLint over src with --quiet: passed.
- Listener dependencies installed from its lockfile with lifecycle scripts disabled. Listener tests: **3 passed**. Listener TypeScript check: passed.
- Added independent checks using an in-memory database and mocked market/network I/O: **13 failed, 1 passed**. These run real application functions; they are not source-string assertions.
- Made small public, unauthenticated GET requests to Polymarket to test endpoint/filter behavior. No account credentials, signed orders, or production Baleen mutations were used.
- Derived event topics with ethers from the official V1/V2 event signatures and compared them with listener configuration.

Reproduction artifacts are in [audit/2026-09-08](audit/2026-09-08). Run from the repository root:

```text
python audit/2026-09-08/independent_checks.py
python audit/2026-09-08/public_api_checks.py
```

The first command intentionally exits nonzero while the invariants fail. It uses a disposable in-memory database and patches event logging and external market calls. Do not point it at production. The second command is a small public GET-only sample, not certification of every provider or response. Results: independent_results.json, public_api_results.json, listener_topics.json, backend_suite.txt, listener_tests.txt, and the lint/type output files.

Existing tests and these audit checks are complementary. Passing the existing suite does not excuse failed independent invariants. When refactoring changes the audit script's interfaces, preserve its economic expectations and port them into permanent integration tests; do not turn the incorrect observed values into expected values.

Remaining verification limits: no real PostgreSQL concurrency run, clean deployment-image build, browser end-to-end journey, production Supabase permissions/schema inspection, authenticated exchange execution, or full historical dataset replay was performed. The local backend interpreter is Python 3.10 whereas the declared/deployed versions differ. A passing local import does not prove the deployment image has all dependencies.

## Gemini's changes: what improved and what did not

| Area | Verification result |
| --- | --- |
| Login bypasses | Guest-prefix and fallback-password shortcuts removed. Good. Backend bearer tokens are still discarded by the frontend. |
| Passwords and stored credentials | Salted PBKDF2 and Fernet added. Good direction; production dependencies, configuration, legacy migration, and key lifecycle remain incomplete. |
| Admin routes | Role/key dependencies and destructive-operation flags added. Ordinary user settings now require auth. Several execution/live endpoints still bypass ownership through optional auth. |
| Guest sessions | Unique guest accounts added. Isolation improved, but every guest click creates a new account; the poller processes all users, and personal snapshots do not advance with valuation. |
| Live simulation | Default-off capability flag added and invented $2,500 fallback removed. Turning the flag on still enters simulated live execution; public reachability is still called credential verification. |
| On-chain units | Removed threshold-based scaling and minimum-$20 source notional. Correct direction; identity, ABI, precision and delivery remain broken. |
| Valuation | Removed the large-loss concealment rule and some platform-to-user fallback. Settlement can still inflate equity/HWM; zero balances are still substituted; marks and fees remain unreliable. |
| Fees | Optional rate/precision parameters added, but production callers do not supply them. Old title-based rates and two-decimal defaults are still active. |
| Scoring | Some invented values removed in basket.py; scanner.py still fabricates or misclassifies inputs. Backtest qualification fallback remains. |
| Frontend | Types/lint now pass; modal and cache work improved. Auth transport, stale/empty data, account snapshots, and financial semantics remain incorrect. |
| Infrastructure | Production guards/readiness improved when the environment is configured correctly. Durable queue, migrations, worker ownership, and reproducible packaging remain incomplete. |

## Independent failures, with concrete money examples

| Check | Correct result | Observed result |
| --- | --- | --- |
| Paper capital, default netted ledger enabled | A $100 account cannot buy more than $100 including fees without borrowing | $120 of open cost plus $3 fees accepted |
| Settlement after mark-to-market | $10,000 initial equity, $100 cost, 200 shares, prior $0.90 mark, then $1 payout: final equity/HWM $10,100 | $10,180 equity and HWM after settlement; repeated settlement did not add another payout in this sequential check |
| Both outcomes in wallet history | +$50 on one token and -$100 on the other: -$50 combined | +$50 curve; losing outcome omitted |
| Duplicate redemption observation | One $50 realized profit | $100 reconstructed profit |
| Missing redemption basis | Unknown/excluded from trusted realized return | Invented +$50 profit using a default 0.50 entry |
| Rejected backtest exit | Keep 100 shares and $950 cash | Position closed, cash $1,030, despite zero filled shares and REJECTED_SLIPPAGE |
| Zero account balance | $0 | $10,000 in user_to_response |
| Provider price identity | Reject a returned market with a different condition ID | Wrong market's 0.90/0.10 prices assigned to the requested ID |
| Guest snapshot | Settled account equity $10,100 appears in summary | Old genesis snapshot keeps summary at $10,000 |
| Duplicate provider observations | One intended copy for the same chain event observed through REST and listener | Two execution rows for the same account |
| Private execution read without auth | 401/403 | 200 with the synthetic user's execution |
| Credential write without auth, supplying user ID | 401/403 | 200; synthetic credentials stored |
| Paper reset without auth, supplying user ID | 401/403 | 200; synthetic account reset |

The settlement excess can be overwritten by a later MTM recomputation, but the inflated high-water mark is monotonic and can persist. Transient wrong equity is also dangerous if sizing consumes it before correction. Do not dismiss this as a cosmetic flicker.

## Required work, in dependency order

### R1 — Complete authentication across frontend and backend

Files: backend/app/auth.py; api/users.py, execution_logs.py, live_trading.py, wallets.py, copilot.py; frontend/src/lib/auth.ts, api-client.ts, proxy.ts; frontend account/admin flows.

The new backend login returns access_token. NextAuth authorize keeps id/email/admin status but drops that token, and client fetches never attach Authorization. Settings/admin/reset requests can therefore fail after a successful frontend sign-in. Some public financial endpoints still work, disguising the integration failure.

Separately, live `_resolve_user` accepts a supplied UUID/email even without authentication. Execution reset checks mismatch only when current_user exists. Personal execution reads and copied-wallet statistics accept IDs without verified ownership. Test-only fixture-user fallback was added inside production code; remove it.

Implement one complete identity transport. Prefer a server-side frontend proxy retaining the backend token securely, or explicitly implement a reviewed bearer flow. Require get_current_user for every personal mutation/read; derive account identity from it. Explicitly authorize admin inspection. Keep public benchmark data separate. Do not trust supplied userId, email, or an unsigned forwarded identity. Handle expiry/logout consistently and clear cached personal data. Add endpoint-level rate and payload bounds, including guest provisioning and AI.

Acceptance: real browser signup/login/guest login → settings read/save → reset → logout → login as another user. API checks must reject anonymous requests with a valid target ID and cross-account requests. Test invalid tokens, expired sessions, spoofed email, missing auth, and direct API access. Anonymous public benchmark access must never authorize a reset or credential change.

UI: show session-expired/error states and retry/re-login, not silent defaults. Admin page protection must use verified role; no browser-stored admin service key.

### R2 — Make deployment reproducible before accepting a release

Files: backend/requirements.txt, pyproject.toml/uv.lock, Dockerfile, database.py, config.py, deployment configuration.

New auth.py directly imports jwt and cryptography, but the dependency manifests were not updated. Installed local packages let tests pass; a clean image is not established. Backtesting also imports duckdb/pandas without a clear declared research environment. Newly added model fields use ad hoc startup ALTER statements; there is still no complete migration system for the required ledger changes.

Declare and lock direct dependencies, align test/build/deploy runtimes, verify a clean image import and startup, and use a versioned migration runner. Fail closed on missing production configuration; ENVIRONMENT still defaults to development, so verify it is explicitly production on Railway rather than assuming host detection. Prohibit TESTING in deployed production. Separate signing/encryption keys, support rotation, and stop treating arbitrary legacy plaintext as indefinitely acceptable credential storage.

Acceptance: clean install, full tests, frontend production build with representative configuration, API readiness, schema version checks, and migrate/restore rehearsal on isolated PostgreSQL. Preserve unrelated working-tree changes; do not commit everything blindly.

### R3 — Fix provider contracts and reject unrelated responses

Files: backend/app/discovery/polymarket_client.py and every caller, including discovery, price charts, poller and diagnostics.

Public checks on this audit date:

| Request behavior in source | Result sampled | Required change |
| --- | --- | --- |
| Data API /leaderboard | 404 | Use documented /v1/leaderboard; respect page limits and explicit period/category/order. |
| /trades?conditionId=... | 200 containing other markets | Use market=...; validate every returned condition ID. |
| /trades?maker_address=... | 200 containing other wallets | Remove this fallback; use user=... and validate proxyWallet. |
| Gamma /markets?condition_id=... | 200 containing other markets | Use condition_ids=... and verify returned identity before using prices. |
| Correct market/user/condition_ids filters | Sampled rows matched | Preserve validation anyway; success status alone is insufficient. |
| Closed positions sortBy=timestamp and TIMESTAMP | Both returned 200 in the sample | Prefer the documented enum, but do not misreport lowercase as a proven failure. |

Discovery reads name/username and volume but the sampled leaderboard returns userName and vol. It may therefore lose names and manufacture volume. Profile lookup falls back from ALL to MONTH without retaining the period, while callers describe the result as all-time P&L. Valid zero values are treated as missing. Fix all of these together.

Build typed provider adapters with explicit units, requested account/market IDs, endpoint version, observation time, source time, requested interval, coverage bounds, page count, completeness, and a response hash/raw evidence reference. Unknown fields or malformed values are errors/quarantine, not silently substituted identity or money. A failed page must produce incomplete coverage, not successful empty history. Distinguish no positions from unavailable positions. Retry transient failures with bounded backoff, including Retry-After; do not repeatedly retry permanent contract errors as if they were outages.

Official references: [trades](https://docs.polymarket.com/api-reference/core/get-trades-for-a-user-or-markets), [leaderboard](https://docs.polymarket.com/api-reference/core/get-trader-leaderboard-rankings), [closed positions](https://docs.polymarket.com/api-reference/core/get-closed-positions-for-a-user). Documented trades default to takerOnly=true; explicitly decide whether qualification/ingestion includes maker trades, then reconcile that choice with on-chain observations. Closed-position rows expose realizedPnl and totalBought, not the same fields as current positions.

Acceptance: recorded fixtures for correct/incorrect IDs, successful empty responses, partial pagination, 429/500, missing fields, valid zeros, duplicate/reordered pages, maker and taker fills. Contract probes are bounded and read-only. Never substitute market-wide trades for an empty wallet history.

### R4 — Repair on-chain decoding and durable delivery

Files: listener/src/constants.ts, hypersync.ts, event-processor.ts, types.ts, queue.ts, index.ts; backend/app/api/signals.py and services/live_poller.py.

Configured topic:

```text
0xd7b90a501d51c05d762e84c9809939e088167f40e06ae38c64cfb31e9a3b6807
```

Derived official V1 and V2 topics, respectively:

```text
0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65bfec0f6
0xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee
```

The official [V1 interface](https://github.com/Polymarket/ctf-exchange/blob/main/src/exchange/interfaces/ITrading.sol) and [V2 event implementation](https://github.com/Polymarket/ctf-exchange-v2/blob/main/src/exchange/mixins/Events.sol) have different event layouts. The listener filters one incorrect topic across all configured exchanges and decodes five uint256 fields. Simply correcting a topic string is insufficient: V2 has side/token identity and additional fields requiring its own decoder.

Pin reviewed ABIs and deployed contract addresses with chain/block activation ranges. Generate topics from ABI rather than hand-copying. Verify normal/negative-risk exchange coverage. Decode actual receipts for BUY/SELL, maker/taker, both tracked participants, multi-fill transactions and both versions. Normalize raw integers exactly once; preserve Decimal/integer precision. Capture block timestamp/hash, transaction hash, log index and contract/version.

Use a durable authenticated inbox and worker acknowledgement. Current queue appends files but main delivery does not replay failed entries; posting catches failures, background processing is acknowledged before durability, and seen keys are set before success. Maintain source cursors, replay windows and explicit finality/reorg policy. Do not label replayed old blocks with Date.now() as event time. A server restart must not discard all intervening source events or lose exits from previously held/demoted whales.

Acceptance: real receipt fixtures match independent expected participants/assets/shares/notional. Failure after every persistence/ack boundary yields recoverable work, not loss. Replayed events and overlapping providers have one economic effect. Health must report actual last decoded relevant event and cursor/backlog age, not merely a live process heartbeat. Mock query-shape tests alone are insufficient.

### R5 — Canonical identity, exactly-once effects, and account-specific exposure

Files: models.py, live_poller.py, sizing/netted_ledger.py, price/settlement callers, migrations.

On-chain events still enter process_trade_fill with an empty condition ID; metadata resolution never supplies it. ExecutionLog still lacks a dedicated token ID; transaction hashes are reused as token IDs by price consumers. The uniqueness key is still tx/log/user, omitting mode/run, with nullable values. REST observations without logIndex and on-chain observations with logIndex produce duplicate copies in the independent check. A plain read-before-write check is not concurrency protection.

Separate immutable source events, provider observations, account/mode/run intents, order fills, lots, and accounting entries. Map provider observations to a canonical event; quarantine ambiguity instead of merging unrelated fills by transaction alone. Persist token, condition, outcome, source wallet and contract identity. Never execute before metadata identity is resolved. Replace global ExposureLedger amounts with account/mode/run desired exposure, backed by a separate source-whale holdings model.

Use database uniqueness plus transactional ownership/reservation; one worker's retry must not duplicate cash, fills or inventory. A missing user cannot mean a global mutable account. Partial closes require linked lot IDs, not synthetic transaction hash suffixes as financial identity.

Acceptance on PostgreSQL: repeated/concurrent dual-provider delivery, two users, two modes, two tokens in one condition, many logs in one transaction, and crash after acceptance/before commit. One account/mode receives one intended economic effect. No ambiguous identity or empty condition is allowed into executable state.

### R6 — Replace implicit paper leverage with an explicit accounting ledger

Files: live_poller.py, mark_to_market.py, models.py, sizing helpers, settlement and summary services.

The user BUY path sizes from sandbox_balance_usd and passes it as available_cash, but does not debit/reserve it. Mark-to-market treats the same field as equity. Repeated purchases reuse invested funds. The independent default-netting test accepted $123 of cost plus fees from $100. This invalidates capacity, drawdown and profit comparisons.

Implement separate cash, reserved cash, inventory, cost basis and equity. For an unlevered portfolio, reserve notional plus fees before fills, debit exactly filled cost/fees, release unfilled reserves, credit sells/redemptions once. Use Numeric/Decimal or integer units. Enforce per-account cash and exposure atomically; round only at defined venue boundaries. Do not use lifetime whale P&L as current whale net worth. If equity cannot be established, use an explicitly different strategy rather than a fake proportional denominator.

Define invariants in an independent reference ledger: cash conservation; nonnegative available cash; shares conserved; no naked sales; costs and fees conserved through partial closes; equity = cash + marked inventory (with reserves consistently included); initial capital/external flows + realized + unrealized P&L reconcile to equity.

Acceptance: repeated buys cannot spend the same dollar twice, including during valuation/settlement/reset races. Tests cover insufficient cash for fees, partial fills, price improvement, rejection, cancellation, total loss, zero balance and rounding dust. Do not clamp negative cash to zero to hide overspending. Track a real reconciliation difference and halt new risk when it exceeds the currency tolerance.

### R7 — Correct exit sizing, settlement and every alternative execution path

The current FIFO closes cost-notional against a sell-notional estimate instead of explicit copied share quantities. Sizing an exit from current account equity and lifetime whale P&L can change the fraction sold incorrectly. Both the BUY lot and SELL log carry realized P&L, requiring fragile downstream deduplication.

Settlement adds the full realized gain to equity already containing unrealized gain. Fix it as a transfer from held shares to cash; realized/unrealized classification changes must not create additional equity. Correct high-water marks from reconciled equity, retaining an audit trail for corrections. Confirmed payouts must support the venue's actual payout vector, including nonstandard/split/void states when applicable; do not infer a winner from scheduled end time or a last-traded price.

Expiry flush currently fabricates platform-only fills directly, bypasses normal sizing/book/risk checks, and marks executed exposure equal to intent before economic execution. Out-of-order matching can retrospectively fabricate an immediately profitable round trip; it must respect what the follower actually held and knew at the time. Route all normal, replay, expiry, correction and exit actions through one execution/accounting path. A skipped/missed BUY cannot become a retroactive real or forward-paper fill after its profitable SELL is known.

Acceptance: $100 cost/200 shares at 0.5, marked at 0.9 and then settled at 1, yields $10,100 from $10,000 initial capital, not $10,180. Sequential and concurrent duplicate settlement produce one payout. A sell of 25% of source inventory closes the corresponding copied fraction according to the documented strategy. An expiry below the minimum is skipped or re-evaluated, not silently rounded into excess risk. Paused entries and demoted rosters still allow needed exits.

### R8 — Make marks, fees and guest summaries honest and consistent

Files: polymarket_client.py price methods; mark_to_market.py; api/execution_logs.py and wallets.py; frontend charts/analytics.

The Gamma fallback uses an ignored condition_id parameter and labels the first returned market as the requested one. This can price a losing holding using another market's price. Mark caches can remain usable for an hour, the first 150 conditions are selected without guaranteed fair refresh, exact 0/1 values are rejected in price helpers, and missing prices revert to cost. None is a sound basis for claiming executable portfolio value.

Fetch exact token books/marks with verified identity and source time. Show book-mid equity separately from liquidation value at executable bid/depth, net of costs; midpoint is not cash available. Rotate/batch all held tokens fairly and maintain freshness. If data is missing, label the mark and portfolio stale/incomplete. Zero final payouts are real values, not missing data. Preserve settlement prices separately from tradeable quotes.

Guest creation/reset writes a personal genesis snapshot, but ongoing MTM writes platform snapshots and only updates User balances. Summary prefers the stale personal snapshot. It can remain at $10,000 indefinitely while holdings change. Write versioned account/mode/run snapshots from the canonical ledger and read those consistently. Do not let GET requests synthesize supposedly observed performance. The summary timeframe parameter is now accepted without actually applying a period return calculation.

Fees: optional fee_rate/precision arguments do not solve the issue when callers still use title keywords and default cents. The [current fee documentation](https://docs.polymarket.com/trading/fees) gives market-dependent parameters and five-decimal precision; use market metadata and actual fill fees, with historical versions for replay. Test rounding against independent examples. Do not recompute an immutable zero historical fee as a nonzero fee during valuation. Summaries currently skip SELL records when deduplicating round trips and thereby omit exit fees from totalFeesPaidUsd; derive fees from accounting entries instead.

Acceptance: wrong market data rejected; confirmed zero rendered; stale marks visibly stale; no starvation after 150 tokens; all financial surfaces reconcile to the same snapshot sequence. Period return uses opening equity and cash flows, including pre-existing positions. Entry + exit fees match ledger totals. A flat-price trade can still show a loss from fees. Updated fee code must actually be used by paper, replay, EV gates, exports, attribution and UI.

### R9 — Reconstruct wallet history without dropping losses or inventing gains

Files: discovery/scanner.py calculate_authentic_wallet_stats and provider adapters.

Confirmed failures:

- Closed-position processing marks an entire condition accounted after seeing one token, then skips the other token. +50 and -100 becomes +50.
- Redemption observations are not deduplicated and do not consistently consume holdings; repeated observations add profit twice.
- Unknown redemption basis defaults to 0.50, fabricating profit. Redemption cash and shares are conflated; activity may identify a condition without the token needed for basis.
- Trades are processed before redemptions rather than as one chronological event stream.
- A successful partial SELL can mark an entire asset accounted, suppressing other realized history for that asset.

Implement a chronological inventory reconstruction with unique economic event IDs, outcome-token ownership, share quantities, cash, fees, redemptions, splits, merges and transfers. Use opening holdings/basis when the historical window starts mid-position; otherwise label the affected return unknown. Closed-position summaries are reconciliation evidence, not an additional cash-flow feed to be added to trade/redemption P&L. Reconcile overlaps by token and lifecycle, not by condition-wide exclusion. Never rescale an entire historical curve to force it to equal a leaderboard number.

Acceptance: the independent opposing-token and duplicate-redemption checks pass. Include partial sell then redemption, repeated buy/close cycles in the same token, both outcomes, duplicated pages, zero-basis legitimate receipts, unknown-basis transfers, sell-first truncated histories, and interleaved split/merge/redeem. Each economic gain/loss appears exactly once. Reconstructed and provider totals may differ, but the difference must be explained by coverage/semantics instead of calibrated away.

### R10 — Qualification must use measured, comparable inputs

scanner.py still uses cashPnl/initialValue/size fallbacks for closed-position data whose documented schema is different. Trade size sometimes treats shares as dollars instead of shares × price. Open positions may count as resolved outcomes; missing closed history falls back to all open positions. A partial realized gain can mark an open position closed. Losing nearly-worthless open positions can fall outside the open-loss filter. An “anomaly guard” invents a number of losses from aggregate P&L. Scarce history still gets invented positive Sharpe values in scanner.py, even though basket.py was changed.

Separate current positions, closed position summaries, trades, and activity schemas. Preserve measured zeros with explicit None checks. Record how many independent markets, days and complete lifecycles support each metric. Compute win rate on an explicitly stated definition; do not equate profitable exits with binary resolution wins. Missing data yields insufficient evidence, not an attractive default. A trustworthy 50% win rate with larger gains than losses can outperform an 85% win rate on expensive favorites; qualify using net expected return and drawdown evidence, not win rate alone.

Compute drawdown on cash-flow-adjusted portfolio equity with an actual starting denominator. Current scanner drawdown starts at zero cumulative profit and divides the largest dollar decline by a later global peak, which is not standard maximum percentage drawdown. Use a full dated return grid; calendar-day EMA decay must account for missing/inactive days. Do not anchor a “last 90 days” metric to an old last-observed profit date. Distinguish inter-trade gap from holding duration (wallet API currently presents median_inter_trade_gap_hours as avg_hold_hours).

Acceptance: missing fields, valid zero, open loss, partial realization, and incomplete history cannot improve eligibility. Reorder closed-position rows without changing results. Metrics reconstruct from evidence with window, method, sample size and uncertainty. Qualification returns eligible/ineligible/insufficient-data with reason codes and policy version.

### R11 — One enforced roster and risk policy, including exits

Files: scoring/engine.py, basket.py, discovery gates, live_poller.py, capital_tier.py, settings and strategy UI.

Roster selection and active thresholds differ across services. The basket's diversity backfill can reintroduce candidates excluded by correlation; execution independently fetches gold-first top wallets. Risk-profile settings are still not consumed by the central proportional path. Entry price filters in polling also remove SELLs near boundaries, and active-roster-only ingestion can miss demoted-whale exits. Global anti-conflict checks can let one account's holding block another.

Persist a versioned executable roster and explain why it differs from discovery candidates/bench. Apply per-account budgets and per-event/category/whale concentration limits using actual inventory. Keep entry permissions separate from close/reconcile permissions. Missing return overlap is unknown correlation, not evidence of independence. Do not force a fixed roster count by relaxing safety filters; hold cash if too few candidates qualify. Test consensus on actual source holdings by token/outcome/entity, not duplicated customer execution rows. Current consensus sums follower notionals and groups by condition, which does not prove aligned source conviction.

Acceptance: UI, listener, poller and backtest select the same versioned eligible roster. Changing an implemented risk profile demonstrably changes permitted exposure. A removed whale's existing holdings still unwind correctly. Correlation caps remain enforced after backfill. Multiple accounts do not multiply source whale conviction.

### R12 — Fix rejected backtest fills before any strategy comparison

Files: backtesting/engine.py and portfolio.py, especially close_position_on_whale_sell.

The engine calls the close function after a SELL simulation without requiring an executable status. The close function interprets zero filled shares as “sell the entire position.” The independent test has 100 shares bought for $50; a rejected exit at 0.8 still produces $80 cash proceeds and clears the holding.

Require an accepted fill state and positive confirmed filled shares before any inventory/cash mutation. Never use an intended amount as a fallback actual fill. Bound proceeds and fee allocations to the executed quantity. Test all rejection/skip/cancel/expired/partial states at both engine and portfolio layers, including zero/NaN/negative quantities.

The replay currently attempts a full follower exit on a source SELL rather than reproducing an explicit source fraction. Decide and label that strategy, or change it to match forward paper behavior. Remove artificial redemption taker fees unless the relevant venue operation actually incurs them; trading and redemption are different operations. Match order minimum/tick precision using actual market constraints, not a universal $1 dollar rule. The [order-book contract](https://docs.polymarket.com/api-reference/market-data/get-order-book) exposes relevant market constraints that must be interpreted in their stated units.

Acceptance: the rejected-exit check leaves $950 cash and one 100-share holding. Identical canonical fills must produce identical accounting in replay and forward paper. Rejections never free capital or create profitable exits.

### R13 — Remove future information and simulation optimism

Files: backtesting/data_loader.py, engine.py, execution.py, optimizer.py, strategies.py; live_poller.py simulation.

Backtesting still uses final market metadata with end_date as if it were the observed resolution time, progressively relaxes qualification, and manufactures curated-wallet stats. It ranks trials on the same evaluated output. Historical windows mainly use 2024 while fee assumptions are current. These are not evidence of no look-ahead or selection bias.

Store both event time and time known to Baleen; replay decisions at observation time plus measured processing/order delay. Scheduled end is not settlement availability. Fills timestamped in the future must not modify balances before intervening events are processed. Keep unknown historical resolution/mark timestamps as limitations or exclude affected intervals. Do not use today's winning-wallet list to select yesterday's candidates without an as-of record.

Remove fabricated qualification and silent relaxation. Use separate chronological training, validation and untouched test periods, with gaps for overlapping positions. Register all trials and preserve losing configurations. Keep a final holdout untouched until selection is frozen. Future-data mutation tests must not alter earlier decisions.

Forward paper latency remains clipped/randomized, and fees/edge gates retain optimistic fallbacks: negative or unsupported edge can become +0.02; the advertised 2.5x gate is not enforced as described. Replace this with calibrated estimates or an explicit no-edge-estimate baseline. Use observed quotes/depth at the follower's arrival time, not the whale's print plus a small heuristic labelled authentic. Capture historical books going forward if no complete old book dataset exists. Stress missed fills, partial fills, adverse movement, downtime, stale data and aggregate follower demand. “Always slightly worse than the whale” is not proof of realistic execution.

Acceptance: fixed seed/data/config produce the same run; modifying future outcomes cannot change prior entries/roster; delayed fills do not execute early; insufficient data produces uncertainty/no trade. Costs are versioned for the historical date. Fee/slippage/latency/quantity units match across engines. A no-edge strategy need not be profitable for the test to pass.

### R14 — Reset and guest lifecycle must support a real experiment

Guest login now creates a new account every time, and the central poller fans out to all users with no explicit active subscription/expiry filter. This can grow simulated work indefinitely, while it becomes hard to follow one benchmark across sessions. Reset still deletes history, leaves global exposure/pending work outside the reset boundary, and lacks run-specific ownership.

Define a persistent operator-controlled guest benchmark portfolio, publicly readable if desired, with authenticated reset controls. Personal demo sessions may remain isolated; do not give anonymous visitors authority over the benchmark. Add explicit account participation, expiration and retention policies so abandoned guest accounts stop receiving new intents while open positions are handled according to policy. Avoid turning every page visit into a permanent trading subscriber.

Implement account/mode/run IDs and immutable run archives. A reset closes the old run and creates a new run; it is not a global DELETE. User reset and global ingestion are separate. Pending prior-run actions must never be applied to the new run. Preserve raw source observations for audit while assigning executable eligibility using the run start boundary.

Acceptance: fresh and returning visitors see the designated benchmark run consistently; two private guests remain isolated; only authorized operators can reset the benchmark. Restart preserves run ID/cash/positions/cursor. An old queued event cannot leak into the new account run.

### R15 — Operations, UI and AI must expose uncertainty instead of disguising it

Finish durable workers, migrations and recovery from the original brief. Scheduled work still starts with API processes, and in-memory state is not a cross-replica lock. Use explicit worker ownership/leases, retry policy, durable event journals and reconciliation. Track source completeness, event lag, unresolved identity, stale marks, duplicate attempts, failed fills, cash mismatch and current configuration version. An empty account must not trigger a platform-data fallback in copied-wallet statistics.

UI requirements across dashboard, settings, wallet drawer, analytics, trade log, exports and copilot:

1. Persistent Paper trading label and run ID/start time. Live remains unavailable; toggling a feature flag must not be presented as implementation of a real exchange adapter.
2. Separate equity, available cash, reserved cash, invested cost, liquidation estimate, realized/unrealized P&L and fees. A ledger reconciliation indicator links to detail.
3. Data as-of time, mark source, freshness, pagination completeness and uncertainty. Do not show fake zero/$10,000 on failure. Keep valid empty lists empty; api-client.ts still returns old executions for a successful empty response.
4. Separate source event, copy decision, pending/partial/filled/rejected execution and settlement. Show source price, achievable copied price, measured delay, quantity, both-side fees and reason codes.
5. Wallet research distinguishes source performance from copied returns, closed sample from open marks, and observed metrics from insufficient evidence. Rename incorrect holding-duration labels.
6. Timeframe controls compute actual period return; benchmark/account/mode/run/filter are part of cache identity. Handle out-of-order requests and cache clearing on auth/run changes.
7. AI uses the same scoped canonical data, identifies assumptions, and cannot authorize trades or alter financial records. Existing role/message bounds are useful but optional authentication and absent rate limits still need work.
8. Keep historical defective runs visible as archived/unvalidated, excluded from headline proven performance. Do not silently rewrite them to look clean.

Acceptance: browser journeys with new/returning guest, logout/account switch, API outage, empty reset, zero balance, partial fill, loss settlement, slow requests and stale prices. Validate displayed numbers against independent fixtures. Types/lint passing is not a visual or financial acceptance test. Retain accessibility work and test keyboard/mobile/theme flows after UI changes.

## Brainstorming: what might actually improve net returns

These are competing hypotheses to evaluate after R1–R15, not instructions to increase risk immediately. The default must be allowed to hold cash; “no trade” is a valid outcome.

### A. Rank whales by evidence that they can be copied

A high lifetime P&L can come from bankroll size, one extraordinary event, maker rebates, inventory hedges, or prices a follower cannot obtain. Measure the follower's attainable return after each source event, rejection rate, liquidity, delays, time held, and event concentration. Compare source-P&L ranking with copyability ranking using prior data only. Downweight small samples and correlated wallets rather than assuming every address is an independent expert.

Deliverable: a per-wallet attribution card showing gross source opportunity, follower price drag, fees, skipped/missed opportunities, capital occupied, and net copied return with uncertainty. Do not infer beneficial wallet changes from a few lucky trades.

### B. Test whether slower strategies survive delay better

Compare cohorts by genuine holding period, category, spread and depth. Short-horizon gains may disappear before detection; patient traders might be more copyable, but that is a hypothesis. Replay the same opportunities across measured latency quantiles and outage scenarios. Report the break-even delay and the capacity curve. Avoid selecting only filled winners when comparing cohorts.

### C. Separate source skill from entry timing

Test immediate crossing versus capped-price entry versus skipping when the book has moved. Each alternative has missed-fill costs. A passive order requires queue/partial-fill modelling and may fill selectively when the market moves against it. Do not assume a touched limit price means a fill. Preserve all rejected opportunities for unbiased comparison.

### D. Compare exit policies with equal starting exposure

Whale-proportional exits, fixed time horizons and resolution hold can have different capital lock-up and tail-risk profiles. Compare them on the same entries and exposure limits. Account for partial exits, collateral recycling, settlement delay, liquidation fees and market concentration. Never compare a levered paper policy with an unlevered baseline.

### E. Use shrinking confidence estimates instead of multiplying conviction

Rather than multiplying orders for gold badges or address consensus, estimate conservative edge with uncertainty and a capped risk budget. Shrink sparse/outlier-heavy performance toward zero. Correlated agreement is not independent evidence. Compare this with a simple fixed-fraction/equal-budget strategy; complexity must earn its operational cost.

### F. Measure capacity and business economics separately

Ten followers cannot all consume the same small ask. Model aggregate intended demand, partial fills and queue ordering. If distribution is required, specify fair allocation instead of letting the first account always get the best price. Report follower net performance separately from Baleen operating profit: data/API/compute costs, support cost, retention, and any applicable product fees. Subscription or performance-fee assumptions belong in a separate business model, not in trading alpha. Do not describe unrealized or simulated gains as revenue.

For every experiment, pre-register the hypothesis, baseline, parameter range, risk limits, sample inclusion rules and evaluation metric. Report net returns, maximum drawdown, tail losses, time underwater, turnover, independent event count, exposure, fill rate, capacity, and confidence intervals using event/time-block resampling. Do not promise one strategy will win. Prefer the simpler policy if additional complexity does not produce robust out-of-sample benefit.

## Release gates and Gemini task sequence

| Batch | Tasks | Evidence required before moving on |
| --- | --- | --- |
| A | R1–R2: complete auth and clean packaging | Browser auth journey; anonymous/cross-account rejection; clean-image startup and migration checks |
| B | R3–R5: provider contracts, ABIs, durable canonical events | Public contract fixtures; real V1/V2 receipts; wrong-ID rejection; restart/replay/concurrent idempotency |
| C | R6–R8: ledger, exits, settlement, marks, fees, snapshots | Independent cash/share/fee/P&L reconciliation; zero/loss/stale cases; personal snapshots update |
| D | R9–R11: history reconstruction, measured qualification and enforced risk | No missing losing outcomes or duplicate redemptions; complete-data gates; roster/risk parity |
| E | R12–R13: honest replay and execution model | Rejected fill has no effect; no future information; reproducible replay; historical cost provenance |
| F | R14–R15: guest runs, observability and financial UI | Run isolation, restart continuity, visible freshness and consistent figures across UI/export/AI |
| G | Fresh $10,000 benchmark run | All accounting/security/data gates passed; startup manifest and smoke evidence saved |
| H | Strategy experiments and forward observation | Frozen champion plus isolated challengers; no resetting losses; pre-registered comparisons |

Require small reviewable PRs. Each must identify failing-before/passing-after independent examples, affected producers/consumers, schema migration, configuration, UI meaning, and rollback. Track unresolved checks explicitly. Do not add TESTING exceptions to application logic to make tests green. Test production paths with dependency injection and isolated infrastructure instead.

## Gemini: start the new guest run only after validation

This is the requested operational instruction, conditional on completing the gates above. Do not invoke any existing reset endpoint until R1/R14 are fixed and tested.

1. Identify the designated persistent guest benchmark account and its mode. It must not be an arbitrary newly provisioned visitor account or a NULL-user platform fallback. Save exact account ID in the run manifest.
2. Archive the current run with its actual final raw records, known defect labels, cutoff timestamp and configuration. Do not infer its returns are trustworthy, repair it by guessing, or delete other users/live records.
3. Temporarily pause new entries for that benchmark only. Drain/quarantine pending old-run actions. Ensure workers and the deployment version are consistent. Keep global source ingestion running so events are not lost.
4. Atomically create a new run with initial cash **10,000.00000 USD**, zero reserved cash, zero positions, zero realized/unrealized P&L, zero fees, initial equity/HWM **10,000.00000**, and a genesis snapshot. User-facing currency can display two decimals; accounting retains defined precision. Record currency/collateral semantics explicitly.
5. Persist run ID, account ID, UTC start time, policy and code versions, migrations, source cursor/observation cutoff, selected roster and qualification evidence, fee version, execution model, random seed if any, and validation results.
6. Existing whale holdings at run start are observation context only: do not create free copied positions. Copy only newly eligible post-start observations under the chosen policy; define treatment of events observed after start but executed earlier. Keep exits for any future held positions monitored even after roster removal.
7. Verify API, dashboard, charts, exports and copilot all show the same run, $10,000 equity/cash, no positions, zero fees/P&L, and Paper mode. Clear only the relevant account/run client caches. Display a run-start event in history.
8. Resume paper entries. Check the first accepted event through source evidence → intent → fill → cash/fee/share entries → mark → snapshot. Reconcile after the first exit/settlement and after a worker restart. Run fault-injection smoke checks in staging, not by creating fake production fills.
9. Report the run ID, account identity, start time, initial values, roster/policy version, enabled paper services, and remaining limitations. Do not declare the run profitable or live-ready merely because it started correctly.

After this reset, keep the official benchmark uninterrupted. Put experiments in separate challenger runs rather than resetting away losses or changing the champion mid-evaluation. Real-money activation is a separate milestone requiring a real exchange adapter, authenticated fill/balance reconciliation, risk controls, and an explicitly bounded pilot; no setting in the current code provides that evidence.
