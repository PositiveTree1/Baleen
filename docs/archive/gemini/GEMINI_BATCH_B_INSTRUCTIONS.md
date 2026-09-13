# Gemini handoff: implement Batch B only

Implement **R3–R5** from `GEMINI_IMPLEMENTATION_BRIEF_V2.md`: provider contracts, correct chain decoding, durable delivery, canonical event identity, and account-specific exposure. This file clarifies those requirements; it does not replace them.

Read `BATCH_A_RECHECK.md` first. Batch A has 2,533 passing backend tests, 15 passing frontend regression tests, successful image builds, and real PostgreSQL migration/restore evidence. Its fresh browser acceptance check remains open. The user has authorized starting Batch B; do not claim this closes the browser check or approves a release.

## Working rules

- Inspect the current working tree and applicable `AGENTS.md` files before editing. Many files already contain uncommitted Gemini and review changes. Preserve them; do not reset the checkout or blindly commit everything.
- Preserve Batch A authentication, ownership checks, durable logout/rate limits, production configuration guards, Python 3.12 packaging, and readiness checks. Extend the versioned migration system after its current latest version; do not rewrite applied migrations. The reviewed baseline ends at migration 6, but check the actual checkout.
- Implement and verify in the order below. Do not stop after writing interfaces or tests if the production callers still use the old paths.
- Do not deploy, enable live trading, reset the benchmark, delete historical records, or change production data. Use isolated fixtures and disposable PostgreSQL for writes and fault injection.
- Keep R6–R15 financial/strategy/UI redesign out of this batch. Add the identity, persistence, and ownership foundations they require. Do not present existing accounting as repaired merely because duplicate processing is prevented.

## 1. R3: fix provider adapters and all their callers

Start with `backend/app/discovery/polymarket_client.py`. Trace every caller, including discovery, diagnostics, charts, price lookup, and the poller. The checkout inspected for this handoff still contains `/leaderboard`, a `maker_address` fallback, a `conditionId` trade filter, and a `condition_id` Gamma fallback. Changing only one occurrence will leave bypasses.

1. Verify the current official contracts linked in R3 before implementation. Record the source URL and retrieval date with fixtures. The original audit's endpoint results are historical evidence, not a guarantee that today's contract is unchanged.
2. Apply the documented endpoint/filter/field names throughout: the audit found `/v1/leaderboard`, `user`, `market`, and Gamma `condition_ids` appropriate. Preserve leaderboard `userName`, `vol`, the actual period, and valid zero values. Never describe MONTH fallback data as ALL-time data.
3. Validate returned identity **before** any cache write, price use, qualification, or execution. A valid HTTP status and nonempty list do not prove that a filter worked. For a wallet-scoped query validate the requested wallet; for a market/token lookup validate the requested condition/token and their mapping. Reject or quarantine mismatches rather than attaching the requested ID to an unrelated row.
4. Return a typed result that distinguishes complete-empty, complete-with-data, partial, and unavailable. Include source/endpoint version, requested scope/window, observed/source timestamps where available, coverage bounds, page count, completeness/reason, and evidence hash/reference. Unknown source timestamps remain unknown. Propagate this status to consumers; partial/unavailable history must not become an empty successful history or improve eligibility.
5. Validate required identity and numeric fields, including finite values and stated units. Do not reject harmless additional response fields merely because the provider added them. Missing required fields, malformed money, and contradictory identity must never receive invented defaults.
6. Bound pagination and retries. Handle duplicate/reordered pages without duplicating rows; detect non-progress and mark truncated results incomplete. Honor applicable Retry-After with bounded retries for transient errors; permanent contract errors stop with an explicit reason. Explain the maker/taker inclusion policy and reconcile it with chain ingestion. Never replace an empty wallet history with market-wide trades.

**Prove:** wrong condition and wrong wallet are rejected; zero survives; empty differs from outage; failure on page 2 retains page 1 as incomplete; repeated/reordered pages do not inflate counts; retry limits work for 429/500; malformed required fields fail closed. Use recorded responses and actual adapter/consumer calls, not only assertions about query strings. Network probes, if needed, must be small, public, and read-only.

## 2. R4: decode each supported contract correctly

Inspect `listener/src/constants.ts`, `hypersync.ts`, `event-processor.ts`, and `types.ts`. The existing single topic and shared five-integer decoder are not sufficient for the V1/V2 layouts described in R4.

- Pin reviewed ABI sources to a commit/version. Verify deployed addresses, chain IDs, and activation ranges against authoritative evidence; include normal and negative-risk exchange coverage. Do not assume the existing address list is complete or correct. Generate event topics from each ABI.
- Route decoding by verified contract/version and block range. Unsupported combinations enter an explicit unsupported/quarantine state; they must not be guessed using another layout.
- Store raw integer amounts and token IDs losslessly. JavaScript `Number` is unsuitable for arbitrary uint256 values. Use bigint internally and lossless strings at JSON boundaries; apply documented decimal scaling exactly once. Use matching Decimal/integer handling on the backend.
- Preserve chain ID, emitting contract/version, block number/hash/time, transaction hash, log index, participants, assets, side, quantities, and observation time. Wall-clock receipt time is not chain event time.
- Use real recorded receipts for supported versions and exchange variants. Save provenance and independently calculated expected participants, assets, direction, shares, and notional. Synthetic ABI round trips may supplement these; they do not replace real receipts. If a required receipt cannot be obtained, name the missing coverage and leave that gate open.
- Include maker/taker, BUY/SELL, both tracked participants, and multiple logs in one transaction. One log can concern two tracked wallets: decoding or queue deduplication must not silently discard one participant. Represent the source log once and its participant-specific actions explicitly.

## 3. R4: make delivery recoverable before acknowledging it

Inspect `listener/src/queue.ts`, `index.ts`, `backend/app/api/signals.py`, and the consuming worker. Currently the queue removes rows before delivery, remembers keys before persistence succeeds, and posting catches errors without reporting failure. Fix the complete path rather than adding an unused replay function.

Write down the implemented state transitions and transaction boundaries in the delivery notes:

1. Source observation becomes durable locally or in the chosen durable store before the source cursor can advance beyond it.
2. An authenticated backend request validates the envelope and commits a durable inbox record before returning an acceptance response. Acceptance means persisted, not necessarily executed. A retry of an already accepted identical observation returns a safe acknowledgement; conflicting payloads under the same identity are recorded/rejected explicitly.
3. The sender retires its pending item only after that acknowledgement. Timeouts and non-success responses retain retryable work. Use atomic durable storage with clear ownership; an ephemeral container file is not durable across replacement.
4. Workers claim persisted work transactionally, recover expired claims, and acknowledge completion only after committing the intended effects. If an external side effect cannot share the transaction, use an outbox/idempotent receiver boundary and test it. Do not rely on an in-memory seen set for correctness.
5. Persist cursors and a bounded replay overlap. Define confirmation/finality and reorg handling, including block-hash mismatch detection and orphan handling. The simplest acceptable policy may defer executable effects until the configured confirmation threshold. Document residual deep-reorg limits; do not claim they cannot happen.

Retain monitoring needed for exits from held/demoted wallets. Health must distinguish process heartbeat from last decoded relevant event, source cursor lag, oldest pending item, and quarantined/failed work. A quiet market alone must not be reported as a dead worker.

**Prove with injected failures:** before/after observation persistence, inbox commit, acknowledgement receipt, worker claim, effect commit, and completion acknowledgement. Restart the responsible process/worker and show recovery. An HTTP response from an in-memory background task is not proof of persistence.

## 4. R5: canonical identity and isolated account effects

Start with `backend/app/models.py`, `services/live_poller.py`, `sizing/netted_ledger.py`, signal ingestion, and price/settlement consumers. Inventory every old ingestion route and ensure it enters the same canonical pipeline.

- Separate provider observations from immutable canonical source events. A chain log identity includes chain, emitting contract, transaction hash, and log index, with block hash/canonicality retained for reorg handling. Participant-specific source actions must remain distinguishable.
- REST rows without log indices are observations, not automatically new executions. Resolve them to chain evidence using sufficient verified identity, or retain them unresolved/non-executable. Never merge by transaction hash alone, fabricate logIndex=0, or use approximate price/time matching to authorize execution. Multiple fills in one transaction must remain distinct.
- Persist condition ID, dedicated outcome token ID, outcome mapping, source wallet, and contract identity. Resolve contradictory/missing metadata before executable state. Never use transaction hashes as token IDs. Update all producers and consumers, not only model columns.
- Give executable copy intents a non-null account/mode/run scope and participant-action identity. Enforce uniqueness on the complete intended-effect identity with PostgreSQL constraints and transactional claiming/reservation. A read-before-write query, nullable uniqueness key, or application mutex is insufficient.
- Scope desired follower exposure by account/mode/run/token/source as required by the chosen model. Keep source-whale holdings separate: two followers do not double the whale's holdings. Preserve legitimate distinct source actions while preventing repeated observations from applying the same action twice.
- Introduce the necessary run identity foundation now; the benchmark reset/archive UX remains R14. Legacy rows lacking reliable scope or metadata stay explicitly legacy/unvalidated and non-executable for replay until reconciled. Do not invent mappings, silently discard duplicates, or rewrite historical profit to make migration pass.
- Separate intent/fill/lot/accounting references as required by R5 and link partial closes to stable lot identity. Batch C still owns full cash/share/fee reconciliation. For Batch B, existing effect writes and their completion marker must be retry-safe; a test-only no-op consumer does not establish this for the real path.
- Implement additive versioned migrations, review existing nullable/duplicate data handling, and document safe rollback compatibility. Rehearse on disposable PostgreSQL with old-schema fixtures and concurrent startup. Never clean up production duplicates automatically.

## Acceptance matrix and delivery

Run these through the actual producer → inbox → canonicalization → consumer path on PostgreSQL, with external market I/O replaced by recorded fixtures:

| Scenario | Required result |
| --- | --- |
| Same event repeated, including REST + listener concurrently | One intended effect per eligible account/mode/run/source action; duplicate observations remain traceable |
| Two users; two paper/test modes; two runs | Isolated effects/exposure; retries never spill into another scope; no live exchange call |
| Two outcome tokens in one condition | Separate token identities/positions; no condition-only collapse |
| Multiple fills in one transaction | Each genuine action retained; no transaction-only deduplication |
| Both participants tracked | Each relevant participant action retained with correct direction |
| Missing or conflicting identity | Persisted unresolved/quarantine state; no executable intent or financial mutation |
| Worker crash after acceptance or around commit | Recovery without lost work or repeated effects |
| Cursor replay, reconnect, and simulated reorg | Documented replay/finality policy enforced; duplicates harmless; orphaned observations handled |
| Existing Batch A paths | Authentication, revocation, ownership, migrations, readiness, and packaging still pass |

Port the independent wrong-market and dual-provider duplicate reproductions into permanent regression tests. Their correct expectations remain rejection of unrelated prices and one intended copy, respectively. Do not weaken assertions or disable netting to hide failures. Other later-batch financial failures may remain; report them explicitly rather than claiming the entire audit is green.

Deliver a concise `BATCH_B_IMPLEMENTATION_REPORT.md` containing:

1. R3/R4/R5 completed versus open requirements, affected producers/consumers, and remaining limitations.
2. Failing-before/passing-after examples and commands/results for backend tests (Python 3.12), listener tests/build, real PostgreSQL concurrency/recovery/migrations, and relevant clean-image checks. Run frontend checks if shared contracts affect it. Report actual results; do not reuse Batch A counts as new evidence.
3. Fixture/ABI provenance, maker/taker policy, canonical identity rules, durable storage/acknowledgement boundaries, finality policy, and health semantics.
4. Migration/configuration instructions and rollback/recovery limitations. Update dependency locks and pinned exports if dependencies change.
5. A list of unfinished gates. Unit mocks, a build, or a healthy process alone do not establish end-to-end durability or financial correctness.

Stop after Batch B implementation and its report. Do not begin Batch C or restart the benchmark automatically.
