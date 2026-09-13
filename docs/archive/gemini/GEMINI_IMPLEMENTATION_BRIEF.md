# Baleen: audit and implementation brief for Gemini

Date: 7 September 2026. Scope: local working tree, not a verified production deployment.

## Manager's decision

Keep the product in explicitly labelled paper-trading mode while fixing security, ingestion, and accounting. Do not optimize strategies against the current performance numbers or enable real-money execution on this implementation. The source contains critical access-control failures, simulated executions labelled as live, and portfolio calculations that mix accounts.

This is an evidence-based implementation backlog, not a guarantee of exhaustive vulnerability discovery or investment success. A profitable whale is not necessarily profitable to copy after execution delay, fees, liquidity constraints, and sizing differences. The business objective should be sustainable, risk-adjusted net returns and trustworthy operations, not maximum displayed P&L.

Only this report was added. Existing changes to README.md, backend/mcp_server.py, package.json, and scripts/deploy-commit.mjs belong to the pre-existing working tree and must be preserved. No deployment, production database mutation, or live order was performed.

## Evidence and limitations

Reviewed the API/authentication boundary, listener delivery, central execution service, ledger/model definitions, valuation, scoring and backtest paths, deployment files, client caching, dashboard/settings, and shared modal implementation. This is a source-level UI review; responsive rendering, accessibility with assistive technology, and production browser journeys remain to be tested.

Verification performed:

- Frontend: `node node_modules/typescript/bin/tsc --noEmit --incremental false` passed.
- Frontend: `node node_modules/eslint/bin/eslint.js src --quiet` failed with 66 errors, including explicit `any` and React hook issues.
- Backend collection: 2,497 tests collected successfully.
- Selected backend execution: **1,065 passed in 7.07 seconds**. Files: test_live_trading_api.py, test_signals_and_drawer.py, test_idempotency.py, test_production_bugs_r4.py, test_quant_core_fixes_r1_r2_r3.py, test_backtesting_system.py, test_slippage.py, test_capital_tier.py, test_dynamic_sizing.py.
- Backend tests selected the isolated SQLite database through tests/conftest.py. Local Python is 3.10; pyproject.toml requires >=3.11 and the root deployment image uses 3.12. Rerun on the supported deployment version.
- Listener tests were not run; listener/node_modules is absent. No full production frontend build or PostgreSQL concurrency test was run.
- Railway/Vercel deployed revisions, Supabase permissions and migrations, production logs, secrets, backups, real exchange balances, and historical Parquet datasets were not inspected. Source findings are confirmed unless explicitly labelled an operational check or hypothesis; their production exposure depends on what is deployed and external access restrictions.

Existing tests are useful, but cannot serve as the complete specification: a test that expects fake live fills or unauthenticated requests to succeed preserves a defect.

## P0: contain immediately

### 01 — Backend authentication and authorization are missing

Evidence: backend/app/main.py mounts routers without authentication dependencies. backend/app/api/users.py accepts arbitrary user IDs; backend/app/api/admin.py exposes `/hard-wipe-all`, `/purge-and-rescan`, re-evaluation, exports, and worker triggers without administrator checks. backend/app/api/signals.py accepts trade signals without service authentication. These are reachable application routes, regardless of whether a frontend button is hidden.

Impact: if publicly reachable as written, an unauthenticated caller can reset/delete data, change account settings and credentials, fabricate trading signals, and trigger expensive jobs. CORS is not an authorization mechanism.

Gemini must:

1. Add one verified identity dependency and a separate administrator dependency. Choose a documented identity architecture: verified bearer tokens at FastAPI, or a server-side frontend proxy that authenticates the user and sends a short-lived verifiable backend identity. Never trust a client-supplied identity header or userId as authentication.
2. Derive account ownership from that identity; reject mismatches. Prefer `/api/me/...` for personal operations. Keep genuinely public market information in explicitly public routes.
3. Authenticate listener ingestion separately with a service credential or signed request. Validate signature, timestamp, replay identity, payload bounds, and permitted sender. Do not give listener credentials admin privileges.
4. Remove destructive factory-reset HTTP routes from production, or restrict the retained operational mechanism to explicitly authorized administrators with an audit trail and environment restrictions.
5. Rate-limit login, signup, guest creation, ingestion, diagnostics, discovery triggers, exports, and AI requests. Bound request sizes and work queues.
6. Replace wildcard credentialed CORS with explicit deployment origins appropriate to the chosen transport. Add CSRF protections where cookie-authenticated mutations are used.

Acceptance: anonymous sensitive requests return 401; normal users cannot access admin routes; user A cannot read, mutate, reset, export, or connect credentials for B. Invalid listener authentication causes no database changes. Test FastAPI directly, bypassing the frontend. Cover malformed/missing IDs and list/detail/export/chart paths, not just settings.

### 02 — Authentication contains deliberate bypasses and weak password storage

Evidence: frontend/src/lib/auth.ts accepts email addresses starting with `guest` without validating the password, accepts fallback demo passwords after backend failure, and supplies a hardcoded auth-secret fallback. backend/app/api/users.py hashes passwords with unsalted SHA-256. Its guest endpoint returns shared credentials; its database guest UUID is different from the frontend's hardcoded guest UUID.

Gemini must remove all credential bypasses and require an environment-provided secret at startup. Invalid credentials, backend failures, and timeouts must not authenticate. Replace password hashing with an established adaptive password-hashing library; migrate legacy hashes on successful verification or require password reset. Normalize email consistently at signup/login, validate email and password lengths, handle signup races through the unique constraint, and return controlled errors. Implement a real isolated demo identity or a read-only demo dataset; never a shared mutable customer account. Add explicit admin route protection; frontend/src/proxy.ts currently matches dashboard/settings but not admin, and route matching alone is not role authorization.

Acceptance: guest-like email addresses and old fallback passwords do not bypass login. Missing auth secret fails startup. Legacy hash migration is tested. Two demo sessions cannot change one another's state. A backend outage produces a useful error, not a signed-in session.

### 03 — “Live trading” is simulated and credential verification invents money

Evidence: backend/app/api/live_trading.py `test_connection` uses public endpoints without authenticating the supplied CLOB credentials. It combines cash and position value using `max`, fetches only 20 positions, and falls back to a fabricated $2,500 balance when the result is zero. It then reports success. In backend/app/services/live_poller.py around lines 985–1034, the live loop reduces a database balance and inserts `is_sandbox=False, status="FILLED"` records using a simulated fill price; it does not submit an exchange order in that path. Dashboard/settings describe these as real-money CLOB executions.

Gemini must:

1. Add a server-enforced live-execution capability flag, default off. Disable credential collection and activation until a real adapter is ready; show a clear unavailable state.
2. Remove invented balances and success fallbacks. Represent disconnected, verification failed, verified zero, stale, and connected as distinct states.
3. Keep cash, reserved funds, position value, and equity separate. Use authenticated exchange balance/allowance and order queries with proper pagination and timestamps.
4. Build a real signer/delegation and execution adapter following the current exchange contract. API strings being present is not proof of signing authority or tradeability.
5. Persist intent before submission; track submitted, acknowledged, partial, filled, cancelled, rejected, expired, and uncertain states. Store exchange order IDs and fill IDs. Reconcile an uncertain submission before retrying it.
6. Update live balances from reconciled exchange executions; never label local simulation as an exchange fill. Treat already-stored purported live records as unverified historical simulation until actual fills can be matched. Archive/relabel through a reviewed migration instead of silently erasing history.

Acceptance: arbitrary credentials fail verification; a genuine zero remains zero; exchange 401/429/timeouts never become success. No FILLED event without exchange evidence. A crash after submit but before response does not create a second economic order. A disabled capability blocks activation at the API even if the UI is bypassed.

Current external reference: Polymarket describes signed orders, authenticated account setup, fill monitoring, and settlement in its [trading workflow](https://docs.polymarket.com/trading/overview). Recheck current SDK, wallet model, collateral, contract addresses, and approvals before implementation; do not assume older USDC/proxy-wallet integration instructions still describe the target venue.

### 04 — Secrets are stored as plaintext and user selection fails open

Evidence: backend/app/api/live_trading.py writes raw credentials into `clob_api_key_enc`, `clob_api_secret_enc`, and `clob_api_passphrase_enc`. `_resolve_user` falls back to the first registered user when input is absent or unresolvable; credentials can create a default trader. backend/app/database.py interpolates the full database URL into some failure logs. frontend/src/app/api/debug-env/route.ts exposes internal configuration/connection diagnostics without an auth check; it does not expose the auth secret itself.

Gemini must remove first-user/default-user fallbacks, encrypt stored credentials using authenticated encryption with versioned keys outside the database, restrict decryption to the execution service, support revoke/replace, and redact database URLs and credential-bearing exceptions. Audit logs and exported data for historical exposure before deciding which real credentials require rotation. Remove or administrator-protect debug endpoints. Do not log secrets during this investigation.

Acceptance: missing account identity never selects somebody else; raw secrets do not appear in database exports or logs; encryption key rotation preserves access to existing ciphertext; unauthorized reads and writes fail.

### 05 — Sandbox resets delete unrelated and live records

Evidence: backend/app/api/execution_logs.py `reset_sandbox` accepts a userId but deletes all PortfolioSnapshot, ExecutionLog, and SystemEvent rows and resets every user. This also deletes `is_sandbox=False` execution rows. backend/app/api/users.py has additional reset implementations; the per-user route has a global fallback for nonexistent users and changes the global poller start time/caches. Reset paths do not comprehensively reset ExposureLedger; SandboxRun has no account owner.

Gemini must replace these paths with one account- and mode-scoped reset service. Prefer closing a paper run and opening a new run over destructive deletion. Store account, mode, and run identity on dependent records. Reset the relevant exposures, pending actions, snapshots, and caches atomically. Invalid users must return 404/401 rather than operate globally. A personal reset must never advance global ingestion cursors or change another user's processing.

Acceptance: seed two users, demo records, live records, exposure accumulations, and pending events. Reset A's paper run and verify everything else is byte-for-byte/economically unchanged. A queued pre-reset event cannot unexpectedly repopulate the new run. Reset failures roll back consistently.

## P1: trading and financial correctness

### 06 — On-chain raw amounts are converted incorrectly

Evidence: backend/app/services/live_poller.py `process_onchain_signal` divides amountFilled by 1e6 only if the numeric value is greater than 1e10. listener/src/event-processor.ts supplies raw integer share amounts. For example, raw `1000000` means one share in a six-decimal representation, but the backend treats it as one million shares. It also forces `cash_usd` to at least $20.

Gemini must declare units in the signal schema and normalize exactly once using integer/Decimal arithmetic. Remove heuristic conversion, price 0.5 substitution for bad inputs, and the minimum-$20 transformation of source trade size. Apply minimum user order rules after correct sizing, preserving true source amounts. Validate finite positive shares, bounded prices, valid side, hashes, addresses, and indices. Verify current contract units against the venue's ABI.

Acceptance: one share at $0.50 yields source notional $0.50, not $500,000 or $20. Test raw amounts below, at, and above 1e10; dust; huge values; malformed decimals; negative values; NaN/infinity; and invalid prices. Retain raw amounts for auditability.

### 07 — On-chain condition IDs remain empty; token IDs and transaction hashes are conflated

Evidence: process_onchain_signal passes `condition_id=""` with a comment that it will be resolved. `_resolve_market_metadata` returns title, slug, icon, and outcome, but no condition ID, and process_trade_fill never fills it in. ExecutionLog lacks a dedicated asset/token column. Valuation and API code often pass `onchain_tx_hash` as an asset ID.

Impact: different markets can share an empty condition key; FIFO, exposure accumulation, consensus, valuation, and settlement can match the wrong records or fail. On-chain and polling representations disagree.

Gemini must introduce explicit chain ID, contract, condition ID, outcome token ID, source transaction hash, log index, source wallet, and event identity fields. Resolve and verify token-to-market/outcome mapping before creating trade intent. Quarantine unresolved metadata for retry. Never default an unresolved outcome to Yes for execution. Backfill legacy records only with reliable evidence; otherwise mark unresolved and exclude from trusted statistics.

Acceptance: two distinct Yes tokens from different markets cannot share exposure or FIFO lots. A No token retains its outcome. The on-chain signal resolves to a nonempty canonical market identity. Its position is priced by token ID and settled by condition ID. Failed metadata lookup creates no trade.

### 08 — Listener delivery is not durable or retry-safe

Evidence: listener/src/index.ts enqueues then posts directly. Nothing in that main path drains queued failures. queue.ts catches HTTP errors without propagating them, does not acknowledge successful queue records, and its read/rewrite dequeue can race appends. In-memory processedKeys is set before append succeeds. `/api/signals` acknowledges a FastAPI BackgroundTasks action rather than a durable job. Backend seen keys are added before processing succeeds. Restart guards skip events older than service start, while the listener stamps events with Date.now(), obscuring actual chain event time. Polling fetches only 50 recent trades per wallet.

Gemini must use a durable inbox/queue with pending, leased, retry, completed, and dead-letter states. Return acceptance only after durable persistence. Persist source cursor, event time, receive time, and processing attempts. Acknowledge delivery separately from successful processing. Add bounded backoff, timeouts, pagination/backfill, and a stale-entry policy that still reconciles exits and holdings. Preserve the last valid basket on transient refresh failure, but explicitly expire stale roster data. Handle process shutdown and chain reorganization/finality according to a documented policy.

Acceptance: inject HTTP 500, timeout, database failure, append/storage failure, and process termination before/after every acknowledgement boundary. Every accepted signal is completed once or visibly pending/dead-lettered. Restart can recover backlog without masquerading old events as new. A burst beyond 50 trades is accounted for.

### 09 — Idempotency and concurrency keys do not match economic actions

Evidence: ExecutionLog has UNIQUE(tx_hash, log_index, user_id), omitting mode, wallet, and action identity. NULL platform user IDs or NULL log indices do not provide the intended ordinary unique protection. A single user receiving both paper and live rows for the same indexed source event can collide. The database read-before-write guard uses platform rows; polling has no chain log index while listener signals do. ExposureLedger is keyed only by whale/condition/outcome; helpers commit independently. No row-level balance lock appears in the central fill path.

Gemini must separate source-event deduplication from account execution idempotency. Persist a canonical source event, map alternative provider observations to it, and create account/mode/run-specific execution intents with stable unique IDs. Include the correct wallet attribution when both maker and taker are tracked; listener currently returns only the taker in that case. Do not invent equality between ambiguous provider events; reconcile them explicitly.

Make cash reservation, position update, fee entry, fill record, and intent completion a transactional unit. Lock account/exposure state or use atomic conditional updates with conflict handling. Move commit ownership out of nested ledger helpers. Model source whale holdings separately from each user's desired and executed exposure. Restore pending state after crashes.

Acceptance on real PostgreSQL: deliver one event concurrently 100 times via two workers/providers; each account/mode gets one intended economic effect. Two orders competing for the last available cash cannot overspend. A user can have both paper and live state without uniqueness collision. Nullable legacy records are migrated safely. Test opposite tracked participants and partial fills.

### 10 — Portfolio views mix customer accounts, demo state, and trading modes

Evidence: execution_logs.py list/summary/snapshot routes fall back to global records when the requested user has none. Summary explicitly fetches the latest global snapshot and sets starting balance to $10,000. mark_to_market.py substitutes platform positions/P&L for users with none. Several execution queries do not constrain is_sandbox. live_trading.py also includes NULL-user records in personal dashboard queries.

Gemini must require explicit account/mode/run context throughout financial reads and writes. A new account has zero trades and its own initial balance. A paper endpoint cannot query live records. Provide a separate public demo/index endpoint if needed; label it distinctly. Generate snapshots and summaries from the same canonical accounting service, including per-period opening equity and cash flows. Do not calculate timeframe performance merely by filtering execution timestamps; positions opened earlier still affect period returns.

Acceptance: accounts with different initial balances, holdings, and no trades return different correct summaries. Live and paper data remain separate. Trade table, exported CSV, chart, AI overview, and dashboard reconcile to the same as-of timestamp and accounting definition. Actual zero balances are not replaced by $10,000.

### 11 — Cash, equity, cost basis, fees, and loss reporting need one ledger

Evidence: User.sandbox_balance_usd is rewritten as initial balance plus P&L in mark_to_market.py and used as sizing/cash input elsewhere. The live BUY path subtracts notional without the calculated fee. Exposure uses dollars rather than explicit share inventory. mark_to_market.py preserves an older balance when computed equity falls below $5,000 and the prior balance exceeds $12,000; this could suppress a real loss. Missing marks fall back to entry price, and zero stored fees are recomputed during valuation.

Gemini must define and persist cash available, cash reserved, shares held, cost basis, realized P&L, unrealized P&L, fees, and equity separately. Use Decimal/Numeric or integer monetary units with explicit rounding boundaries. Keep fills/fees immutable; corrections use linked adjustment entries. Valuation must not rewrite historical fees using today's schedule. Remove threshold-based loss concealment. On missing marks, preserve the last observed mark with stale status and an as-of timestamp; report uncertainty and restrict new risk rather than fabricate stable profit.

Core invariants: cash reconciles to deposits/withdrawals, buys, sells, settlements, fees and reservations; shares reconcile to fills and payouts; equity equals cash plus marked positions (with a consistent reservation convention). FIFO partial closes conserve remaining shares, basis, and allocated fees. Settlement credits proceeds exactly once. A user's cash never comes from another user's P&L.

Acceptance: independently calculated fixtures for partial exits, zero payouts, total losses, fee-free fills, mixed modes, withdrawals, repeated settlements, and crash/retry. A verified drop from $13,000 to $4,000 is displayed as a loss. Unknown price is distinguishable from a zero settlement value. All fees reconcile at exchange precision.

### 12 — Fee parameters and precision differ from current venue documentation

Evidence: backend/app/services/polymarket_fees.py derives fees from title keywords, hardcodes crypto 0.072, sports 0.030, economics/finance 0.060, and rounds to cents. The current [Polymarket fee documentation](https://docs.polymarket.com/trading/fees) lists different rates for several categories and five-decimal fee precision. For example, it lists sports 0.05 and crypto 0.07. The algebraic share-price formula is not the primary problem; parameter source and rounding are.

Gemini must fetch authoritative market fee parameters and cache them with version/as-of metadata. Titles may be display labels but cannot determine financial charges. Use actual fill fees when available. Preserve historical fee regimes in backtests and stored fills; do not apply a current schedule retroactively to 2024 data. Independently verify rounding semantics against venue examples/SDK behavior rather than inferring the tie-breaking rule.

Acceptance: fixtures from the documented venue examples, maker/taker distinctions, fee-free markets, precision boundaries, ambiguous titles, and fee changes. A $50 sports notional at 0.5 using the currently documented 0.05 coefficient yields $1.25 before any additional applicable terms; the current code yields $0.75. Recheck the source at implementation time because the schedule can change.

### 13 — Sizing and gates are inconsistent and partially disconnected

Evidence: central sizing uses `all_time_pnl_usd` as whale net worth. Lifetime profit is not current portfolio capital. It calls calculate_pure_proportional_order_size rather than the risk-profile path, so Conservative/Balanced/Aggressive is not passed into this execution calculation. Global demo capital/roster checks happen before per-user sizing. Polling uses a 0.04–0.96 boundary filter on both sides while the fill path's BUY filter is 0.02–0.98; upstream polling can therefore discard exits. Trade-frequency limits differ across scoring/polling/execution. The anti-conflict query is global rather than per account. Consensus/sniper multipliers are calculated but not applied to the current proportional sizing path.

Gemini must implement one versioned policy object consumed by discovery, qualification, roster selection, signal handling, sizing, replay, and UI descriptions. Use verified whale equity/holdings for proportional replication or explicitly choose a different strategy. Track copied share exposure so exits reduce owned inventory proportionally. Separate entry gates from risk-reducing exits and settlement. Apply user risk policies to actual account budgets, including per-market, per-event, per-whale, aggregate exposure, liquidity, and maximum loss controls. Do not blindly enable dead multipliers just because they exist.

Acceptance: changing a supported risk setting changes permitted exposure; frontend descriptions match enforced values. A demoted whale's exit still closes an existing holding, including a price near zero or one. One customer's opposing position does not block another. Tests cover different capital tiers and platform-vs-user roster disagreement. Existing limit differences are either removed or documented as deliberately distinct policies.

### 14 — Expected edge and execution quality are not measured reliably

Evidence: live_poller.py forces expected edge to at least 0.015 or substitutes 0.02 even when the implied estimate is unfavorable. It calls a 2.5-times-fee gate but skips only when edge is also below one fee rate. Wallet-wide win rate is treated as the probability of an individual contract. Latency is clipped/randomized: sufficiently old trades are assigned a roughly 280ms base. Slippage is a heuristic formula, receives the source whale notional before user sizing, and does not walk an observed book in this path.

Gemini must allow zero/negative/unknown edge and reject unsupported estimates. Keep probability edge and expected monetary return in consistent units; use calibrated out-of-sample estimates conditional on price/category/horizon only if evidence supports them. Record actual event, observation, decision, submission, acknowledgement, and fill timestamps. Keep simulated latency explicitly simulated and seedable. Simulate each user's intended order against available contemporaneous depth; account for cumulative demand from all followers. Re-evaluate adverse-price constraints at the resulting executable price.

Acceptance: negative edge never becomes positive by fallback; the documented gate multiplier is enforced; a ten-second delay remains ten seconds in telemetry. Book exhaustion, spread spikes, stale quotes, partial depth, and favorable price movement have explicit outcomes. Missing book history is disclosed as a simulation limitation rather than described as authentic CLOB replay.

## P1/P2: research validity and strategy development

### 15 — Scoring invents metrics when inputs are missing

Evidence: backend/app/scoring/basket.py compute_raw_factors assigns a positive Sharpe-like value when history is absent, estimates profit factor from lifetime dollars, and substitutes pnl/30 for recency. `or` fallbacks also confuse valid zeros with missing values. These are not measured risk statistics.

Gemini must persist metric provenance, observation windows, independent resolved-market counts, and data quality. Missing data should reduce confidence or disqualify a wallet; it should not fabricate quality. Use return-normalized equity histories with cash-flow treatment, not unnormalized daily dollar P&L labelled Sharpe. Include open losses, age of positions, concentration, drawdown, copy latency sensitivity, and evidence that gains are reproducible for a follower. Evaluate entity/strategy correlation, not only address count. Avoid interpreting frequent fills within one event as independent trials.

Acceptance: deleting history cannot improve score; zero drawdown stays zero rather than defaulting to 10%; metrics can be reconstructed from stored evidence. Rank changes identify policy version and input window. No UI label calls an imputed value an observed metric.

### 16 — Backtest qualification and execution need point-in-time validation

Evidence: backend/app/backtesting/data_loader.py progressively relaxes requested qualification thresholds and, if empty, manufactures curated-wallet metrics such as $50,000 P&L, 75% win rate, and Sharpe 2.5. It filters by market end_date but uses final closed/outcome metadata; scheduled end time is not proof the outcome was known then. parse_outcome_prices selects the larger outcome price without itself checking final resolution. Predefined windows focus on 2024. The execution model uses heuristic liquidity/latency rather than full historical books. `lookback_days` is accepted in qualification but the implementation uses all prior history plus recent-trade sampling.

Gemini must remove fabricated qualification and silently relaxed gates. Empty qualified universes should produce an explicit no-trade result. Store source availability and resolution-observed times; only use information known at the decision time. Keep scheduled end, actual resolution, and redemption availability separate. A backtest without those timestamps cannot claim proven absence of look-ahead bias. Audit curated-wallet selection dates for survivorship bias. Honor configuration parameters or remove them. Preserve 2024 as one regime, not the entire evidence base.

Acceptance: modifying future trades/outcomes cannot alter earlier selection or trades. A market ending today but resolving tomorrow is not treated as known today. Thresholds remain fixed unless an explicitly named experiment changes them. Curated fallback never creates fake metrics. Repeatable runs carry dataset checksum, data cutoff, strategy commit, seed, fee version, and unresolved limitations.

### 17 — Strategy experiment plan, after accounting is trustworthy

These are hypotheses to test, not promises or recommended live allocations.

| Experiment | Question | Comparison and guardrails |
| --- | --- | --- |
| Equal-budget copying of qualified wallets | Does copying add net value at all? | Cash/no-trade baseline, simple equal allocation, fixed disclosed entry/exit rules. |
| Copyability-ranked roster | Does follower execution performance beat source-wallet P&L ranking? | Rank using prior follower net returns, fill capture, liquidity and delay sensitivity; keep evaluation periods untouched. |
| Smaller independent roster | Does fewer genuinely independent strategies improve capital efficiency? | Match total exposure and event concentration; do not confound wallet count with risk. |
| Price/depth-aware skipping | Does refusing stale or expensive copies improve returns? | Evaluate missed winners as well as avoided losers; track rejection opportunity cost. |
| Whale exit versus resolution hold | Is the source trader's exit timing valuable? | Include capital lock-up, settlement delay, fees, and identical initial signals. |
| Confidence-weighted sizing | Does sizing using conservative evidence outperform fixed fractions? | Shrink weak estimates; cap market/event exposures; evaluate loss tails and calibration. |
| Independent-wallet consensus | Does agreement predict an edge after costs? | Separate correlated/common-control wallets; measure added cost from waiting and crowding. |

Use chronological training, validation, and untouched test periods; use walk-forward evaluation with appropriate gaps for overlapping positions. Record every tried configuration to expose selection bias. Compare several market regimes. Bootstrap uncertainty in blocks by event/time, not by treating every fill as independent. Report net return, drawdown, tail loss, exposure, turnover, fill rate, missed-signal rate, fee/slippage drag, time underwater, capital utilization, and capacity at different follower counts.

Promote only strategies that beat declared baselines on untouched data and forward paper observation under realistic costs and stress. Duration alone is insufficient: require enough independent opportunities and a documented uncertainty assessment. Keep a champion/challenger registry and instant rollback. An AI-generated explanation is not evidence of predictive edge.

## P1/P2: database, operations, and maintainability

### 18 — Railway can fall back to a different database

Evidence: backend/app/database.py refuses SQLite fallback only when RENDER or RENDER_EXTERNAL_URL is set. The project is now on Railway. Settings default to SQLite, and failed PostgreSQL initialization can configure a SQLite engine. `/health` still returns status ok and does not query the database.

Gemini must add an explicit environment mode and require PostgreSQL configuration for every production deployment, independent of hosting vendor. Disable production fallback. Separate liveness from readiness; readiness must verify database access, required schema version, and relevant execution dependencies. Missing listener heartbeat must be unknown/offline, not the current default ONLINE in admin status. `/api/stats` must not hardcode indexer ONLINE.

Acceptance: missing/invalid/unreachable production PostgreSQL makes readiness fail and never creates a replacement local database. Broken database connections are detected after startup. Listener silence and backlog appear accurately. Trading stops accepting new risk when dependencies are not ready.

### 19 — Schema deployment is incomplete and Supabase isolation is unverified

Evidence: startup uses create_all plus a short NEW_COLS list with swallowed exceptions. This does not migrate existing constraints/indexes or all model changes. db/schema.sql contains indexes not represented equivalently in model declarations. No RLS policies appear in that reference schema, but this does not establish the actual Supabase state.

Gemini must establish Alembic as the schema source of truth, create a baseline from an inspected database, and write incremental expand/backfill/validate/contract migrations. Detect existing duplicates before adding idempotency constraints. Migrate monetary precision, mode/run ownership, and new identifiers carefully. Never use hard-wipe/rescan as schema repair. Review Supabase grants, exposed schemas, table RLS, storage policies if relevant, and the actual database role used by FastAPI.

Supabase's [RLS documentation](https://supabase.com/docs/guides/database/postgres/row-level-security) explains policy protection and bypass roles. An application connection with elevated privileges still needs correct backend authorization; merely enabling RLS does not fix a privileged service trusting arbitrary user IDs.

Acceptance: migrate an empty database and a representative old database containing data; run constraints/index verification and restore drills. Anonymous and customer access through Supabase APIs is tested with their actual roles. Application-role privileges are minimal and documented. Migration failure blocks release visibly rather than silently succeeding.

### 20 — Worker lifecycle and scaling are coupled to API processes

Evidence: main.py launches discovery, valuation, polling, backups, and startup rescoring inside every API process. start.sh launches the listener in the background without supervising its continued health. In-memory caches and scheduler state are process-local. Scaling replicas or overlapping deployments can duplicate work, while a listener crash may leave the web API healthy.

Gemini must separate API, ingestion, and execution/valuation jobs into supervised workloads, or initially enforce a single elected worker with a database-backed lease. Give scheduled work stable job IDs and idempotency. Persist cursors and job progress; implement graceful shutdown, lease expiration, retries, and reconciliation after deploys. Define a bounded job concurrency policy and avoid long network calls while holding transaction locks.

Acceptance: two replicas do not duplicate scheduled economic work; killing a worker transfers ownership safely; listener failure raises readiness/alerts; rolling deploys retain pending jobs. Capture p50/p95/p99 ingestion and execution delays, backlog age, failed jobs, reconciliation differences, API errors, stale prices, and database pool saturation.

### 21 — Build reproducibility and backup recovery need a release gate

Evidence: root Dockerfile runs pip against open-ended requirements and npm install with only listener/package.json copied before dependency installation. HyperSync is `latest`. pyproject.toml/requirements.txt omit directly used backtesting packages such as duckdb/pandas. Repo contains trading backups, but those files do not demonstrate a current restorable production backup. README still describes older framework/deployment details; root test:frontend has no corresponding frontend test script, and test:all omits frontend.

Gemini must lock the deployed dependency graph, use deterministic installs, align supported Python/Node versions, and define separate optional research dependencies. Review dependency advisories with current tooling; this audit did not establish a specific package CVE. Add a CI pipeline for backend, PostgreSQL integration/concurrency, listener, frontend types/lint/build, and browser journeys. Keep production customer exports out of tracked source; inspect retention and permissions without printing sensitive records. Establish automated external backups and a timed restore exercise with documented recovery objectives.

Acceptance: a clean checkout builds and tests on the deployment runtime without undeclared packages. CI fails on auth/accounting regression or migration mismatch. Restore a backup to an isolated database and reconcile account totals. Existing historical audit documents are not treated as evidence that present code is safe.

## P2: frontend correctness and UI quality

### 22 — Cache and loading behavior can show the wrong financial state

Evidence: frontend/src/lib/api-client.ts silently returns cached/empty data on failure, treats a successful empty trade list as a reason to return old trades, and omits timeframe from portfolio-summary cache keys. Dashboard loads global/default data before identity is resolved, polls every six seconds, and calls signOut without clearing this cache at that call site. Its fallback percentage suppresses negative returns below $10,000. Repeated request intervals have no general cancellation or response-order protection.

Gemini must use explicit query state: loading, success, empty, stale, and error. Key personal data by identity/mode/run/timeframe/filter. Wait for identity before personal requests; clear personal caches on logout/account change/reset. Accept successful empty results. Cancel old requests and prevent out-of-order responses from overwriting newer state. Coalesce shared requests and invalidate affected keys after mutations. Display as-of timestamps and stale badges; never replace failed money reads with invented zeros or $10,000.

Acceptance: A→logout→B never flashes A's data; reset→empty remains empty; changing timeframe while requests race shows the last selected timeframe. API failure displays stale/error state with retry. Negative performance renders correctly for custom initial balances. Amounts and P&L agree across settings, dashboard, tables, and charts.

### 23 — Simplify the trading experience around trustworthy decisions

Source targets: frontend/src/app/dashboard/page.tsx, settings/page.tsx, dashboard components, charts, DESIGN.md, and brand-identity/BRAND_GUIDELINES.md. These are design requirements pending rendered review, not claims that a particular screen is visually broken.

Gemini must preserve the existing brand while simplifying the hierarchy: account and mode, equity/cash/P&L, freshness and execution status, positions and pending orders, then performance attribution and whale research. Put advanced analytics in secondary views. Separate “source whale traded,” “copy considered,” “copy skipped,” “paper fill,” and “exchange fill.” Show why a trade was skipped and why a whale is in the basket. Distinguish historical whale performance from the user's copied returns.

Use consistent units and names; distinguish dollar P&L, return %, percentage points, shares, notional, and available cash. Charts need clearly defined periods, realized/unrealized labels, stale/gap treatment, and readable empty states. Avoid marketing labels such as verified, authentic, live, or guaranteed unless the displayed data justifies them. Remove unsupported profitability projections or label illustrative assumptions explicitly.

Settings must expose only controls that actually work. Show risk-profile effects in concrete exposure terms. Credential verification needs separate status for wallet ownership, authentication, balance freshness, allowances, and execution capability. Destructive reset wording must identify the exact paper account/run affected. Every success message must follow a confirmed successful mutation.

Acceptance: record browser journeys at mobile and desktop sizes, both themes, slow network, API failure, empty account, large trade history, and stale market data. Test signup/login, settings save, paper reset, table filters, drawers, exports, logout/account switching, and disabled live controls. Verify numbers against API fixtures, not screenshots alone. Establish performance budgets and profile before adding streaming or animation complexity.

### 24 — Accessibility and frontend maintainability need finishing

Evidence: shared frontend/src/components/ui/Modal.tsx implements Escape handling and dialog semantics, but no focus trap, initial focus, focus return, or background inertness. components/common/Modal.tsx is a re-export, not an independent implementation needing deletion. Separate reset components also exist and require a usage/behavior comparison. Lint currently reports 66 errors; TypeScript passing does not resolve those errors.

Gemini must consolidate actual duplicated behavior, adopt a robust accessible dialog implementation or complete those behaviors, ensure visible keyboard focus, accessible form errors, appropriate live-region announcements, sufficient contrast, reduced motion, and non-color status cues. Fix lint defects without globally disabling rules or replacing everything with any. Generate API types from an agreed OpenAPI contract and validate external responses at the boundary; reduce ad hoc snake_case/camelCase fallbacks.

Acceptance: full keyboard-only dialog flow, focus restored to trigger, screen-reader labels/errors, mobile scrolling, reduced motion, and an automated accessibility pass plus manual review. Lint and types pass. A contract test detects an API field/unit change before release. Follow frontend/AGENTS.md and the installed Next.js documentation before changing framework-specific code.

### 25 — AI copilot is unscoped and unbounded

Evidence: backend/app/api/copilot.py accepts arbitrary roles and unbounded message lists without authentication. services/copilot.py reads the global portfolio rather than a caller's account. Its financial responses inherit the existing accounting defects.

Gemini must scope tools to authenticated account/mode, restrict allowed client message roles, bound context and cost, and protect against prompt injection from market text and user messages. Keep the copilot read-only; authorization must remain in the tool implementation regardless of what the model requests. Compute metrics deterministically before asking the model to explain them. Display scope, as-of date, stale-data warnings, and links to the underlying evidence. Avoid allowing AI summaries to change risk settings or rank wallets without a separate validated policy.

Acceptance: requests cannot impersonate system/tool messages, access another account, run destructive operations, or exceed rate/context limits. Copilot totals match the dashboard's canonical data and distinguish uncertain interpretation from measured results.

## Delivery sequence: small reviewable changes

Do not hand this document to Gemini as permission to rewrite the entire system in one pass. Work in these batches; preserve data and stage migrations before cutover.

| Batch | Scope | Required gate |
| --- | --- | --- |
| 1 | Contain dangerous routes, disable pseudo-live execution and false connection success; remove login bypasses | Direct API auth/role tests; no fabricated live results; existing data preserved |
| 2 | Complete identity flow, credential handling, per-user reset and demo isolation | Two-user/mode/reset regression matrix |
| 3 | Schema migrations: canonical identifiers, account/mode/run ownership, numeric types, inbox/intents | Old-database migration and restore rehearsal |
| 4 | Correct units/metadata, durable ingestion, deduplication and transactional reservations | Crash/replay/duplicate tests on PostgreSQL |
| 5 | Unified accounting, fees, valuation and summaries | Independent ledger reconciliation fixtures and stale/zero/loss cases |
| 6 | Shared execution/risk policy and exit handling | Paper replay with real account budgets; risk settings demonstrably enforced |
| 7 | Worker supervision, readiness, deployment locks, CI and observability | Two-worker and rolling-deploy fault tests |
| 8 | API contract/client cache correction, accessibility, dashboard simplification | Browser journeys, lint/types/build, financial consistency checks |
| 9 | Honest scoring and point-in-time backtesting | No future-data influence, no invented metrics, reproducible experiment artifacts |
| 10 | Controlled strategy comparisons and forward paper observation | Baseline comparison, uncertainty, cost/capacity stress, enough independent observations |
| 11 | Real exchange adapter, if still desired | Venue contract tests, authenticated reconciliation, scoped signer, kill switch, tiny explicitly approved pilot |

Some hardening and UI work can proceed independently, but no strategy promotion should precede accounting and data-validity gates. Batch 1 is urgent containment; it does not mean all authorization work is complete.

## Prompt to give Gemini for each batch

“Implement only Batch [N] from GEMINI_IMPLEMENTATION_BRIEF.md. First read the relevant source and reproduce the listed defects in isolated tests. Preserve unrelated working-tree changes. Describe the API/schema contract before changing it. Trace each changed field and rule through producer, persistence, consumer, UI, tests, configuration, and documentation. Use the canonical implementation rather than adding another fallback or duplicate calculation. Preserve historical records and provide migrations where needed. Never access production money or run destructive production actions as a test. Do not weaken tests to preserve behavior the audit identifies as wrong. Finish with changed files, migrations, test results, remaining uncertainties, and rollback steps. Stop after this batch for review; do not claim profitability or production readiness from a green unit suite.”

For every PR, require: concrete defect and expected new behavior; scoped diff; failing-before/passing-after test when meaningful; relevant integration tests; schema/config/deployment changes; updated UI wording if semantics changed; and any operational evidence still missing. Commit and deploy only through the agreed project workflow, not by blindly committing all unrelated modifications.

## Production verification still required

Inspect Railway and Vercel deployed commit SHAs, environment modes, service topology, origin restrictions, worker replicas, logs, resource limits, and secret redaction. Inspect Supabase schema/constraints/grants, RLS and actual application role, pool configuration, backups and restoreability. Compare deployed configuration with the versioned contract. Perform any endpoint security proof on staging with synthetic accounts, not by invoking destructive routes against production.

Before real-money launch, obtain an appropriate review of target-user eligibility, venue terms, custody/delegated authority, and the proposed fee/business model. This report does not determine legal availability or regulatory obligations. Define per-account and global kill switches, uncertain-order reconciliation, exposure limits, a support/incident procedure, and an explicit capital limit for the pilot. Shipping a clean UI is not sufficient evidence to accept customer funds.

The first success criterion is a safe paper system whose records are correct, reproducible, isolated by account, and honest about uncertainty. Only then can strategy improvements be measured credibly.
