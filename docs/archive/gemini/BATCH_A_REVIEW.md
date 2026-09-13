# Batch A review — 8 September 2026

> Follow-up: [BATCH_A_RECHECK.md](BATCH_A_RECHECK.md) records the completed technical fixes and latest verification (2,533 backend tests passed). The findings below describe the earlier review state; the fresh browser acceptance check remains open.

**Verdict: useful progress, but Batch A is not ready for acceptance.** Reviewed the existing uncommitted implementation against R1–R2 in `GEMINI_IMPLEMENTATION_BRIEF_V2.md`, exercised the local app, and made targeted fixes. No production deployment, real orders, benchmark reset, or user-data deletion was performed. Existing unrelated working-tree changes are preserved.

## What Gemini completed successfully

- NextAuth now retains backend bearer tokens; settings, execution lists, summaries, snapshots, copied-wallet statistics and credential operations gained ownership checks.
- Anonymous and cross-account requests covered by the Batch A endpoint tests are rejected; administrator inspection is covered.
- Authentication/encryption dependencies were added to the manifests. Production configuration checks, encryption-key separation and previous-key decryption support were added.
- Valid zero balances and successful empty execution responses are preserved. The independent personal-summary check now passes.
- Before this review's edits, the full backend suite passed: **2,515 tests**. Those tests did not cover all of the defects below.

## Defects fixed in this review

| Priority | Reproduction / impact | Change |
| --- | --- | --- |
| High | An anonymous request to `/api/executions/{private_trade_id}/chart` returned 200 with private trade information. The condition-ID fallback could select an arbitrary account's trade. | Check trade ownership before provider I/O; return 401/403 for private reads and scope condition lookup to the caller/public records. Attach bearer auth in the chart client. |
| High | A migration against a nonexistent table logged a warning, inserted its version and reported success. | Unexpected migration failures now abort without recording success. SQLite skips only an actual duplicate-column error; PostgreSQL migration runners acquire a transaction advisory lock. |
| High | The browser kept a second bearer identity in both localStorage and sessionStorage, separate from NextAuth. Account changes could leave stale authority/caches; expiry handling existed only in settings. | Resolve authenticated requests from the signed session; remove legacy persistent bearer storage, clear caches when tokens change, discard late responses from another token, and handle 401 globally with sign-out and an explanatory login message. |
| Medium | Supplying a new `X-Forwarded-For` header selected another auth/guest/anonymous-AI rate-limit bucket. | Use the ASGI client identity resolved by the server's trusted-proxy configuration. Deployment must still configure proxy trust correctly. |
| Medium | Sparse chart history was padded with invented prices; zero provider prices were discarded. | Remove invented history and retain valid zero price observations. This does not complete the separate token-identity/freshness work. |
| Medium | The rendered landing page claimed audited traders, sub-second live execution, 99.98% uptime and 1.5x alpha without supporting implementation evidence. The paper dashboard used live-fill labels and an unconditional fee health claim. | Replace the active landing-page claims with paper-preview descriptions; add a persistent experimental-paper notice; label simulated fills and unvalidated fees honestly. Hide the admin link for ordinary users. |
| Low | Repeated guest-button clicks remained possible while provisioning. | Disable the button during both ordinary and guest login. |

The migration and anonymous-chart regressions failed against the reviewed implementation before the fixes and passed afterward. Added behavioral tests run the actual application/client code with isolated database, provider and session boundaries; they do not merely match source strings.

## Batch A acceptance items still open

1. **Packaging is still not reproducible.** `backend/uv.lock` lacks the newly declared PyJWT, cryptography, duckdb and pandas dependencies. The lock declares Python >=3.11; pyproject declares >=3.10; Docker uses 3.12. Docker installs unpinned `>=` requirements instead of a frozen lock. Regenerate a reviewed lock for the chosen runtime and make the production build consume it. A clean Linux image must import and start the complete application.
2. **PostgreSQL migration/recovery evidence is missing.** The new regression checks use isolated SQLite. Run an old-schema upgrade, concurrent startup, failure/rollback and restore rehearsal on isolated PostgreSQL. `create_all` still precedes the migration lock. Previously recorded versions are not proof that all columns exist, especially if the old runner swallowed failures. `/ready` checks connectivity, not migration completeness.
3. **Rate limiting remains process-local.** It resets on restart and multiplies across replicas. Expired per-key entries are not globally pruned. Use a shared bounded store or gateway and exercise real proxy paths; normal NextAuth server requests may share an IP bucket.
4. **Identity lifecycle needs further coverage.** The frontend still receives a JavaScript-accessible bearer by design; this change is not a server-only proxy. NextAuth's session lifetime and the backend's 72-hour token are separate, and logout does not revoke an already-issued backend bearer. Complete the required browser signup, returning-user, expiry, cross-tab, direct-admin and reset journeys with isolated fixtures before accepting R1. API and client-unit coverage are not substitutes for those journeys.
5. **Credential migration remains partial.** Previous-key decryption and rejection of production plaintext are implemented, but there is no demonstrated inventory/backfill/rotation-and-retirement rehearsal for existing credentials.

## Financial release blockers reproduced again

The original independent check script now reports **6 passed, 8 failed** (previous audit: 1 passed, 13 failed). Current output is saved separately in `audit/2026-09-08/batch_a_review_independent.txt`; the original JSON evidence was retained.

| Remaining failure | Observed result |
| --- | --- |
| Paper cash conservation | $100 starting cash accepts $120 open cost plus $3 fees. |
| Settlement after mark-to-market | $10,180 equity/HWM where $10,100 is correct. |
| Both outcomes in wallet history | +$50 where combined performance is -$50. |
| Duplicate redemption observation | $100 reconstructed profit for one $50 profit. |
| Missing redemption cost basis | Invented +$50 instead of unknown/excluded performance. |
| Rejected backtest exit | Position disappears and cash rises to $1,030 despite no fill; correct cash remains $950. |
| Wrong-market provider response | Unrelated 0.90/0.10 prices accepted for the requested market. |
| REST/listener duplicate event | Two execution rows for one intended account copy. |

These are later-batch tasks, not evidence that Gemini was supposed to complete the entire V2 plan in Batch A. They still prevent using current simulated profits to select a winning strategy or approve a new benchmark run.

## Additional app defects and useful next improvements

- **Unavailable data can still look like a funded account.** Dashboard calculations ultimately fall back to $10,000/zero P&L. Add explicit loading, stale and unavailable states across all financial components; show the last successful timestamp on retained data. Test an outage on first load and after a real loss.
- **Settings still invite live credentials.** The live view and credential workflow need a complete capability-driven redesign; a feature flag is not a reconciled exchange adapter. Do not interpret the revised paper labels as completion of R15.
- **Reduce duplicate polling.** The guest dashboard requests executions at several limits (30, 100, 500, 1000), plus summaries, snapshots and wallet statistics. A shared account/run query layer could reduce backend load and prevent panels from describing different moments. Measure requests per active user and backend cost before/after.
- **Build copyability attribution after ledger repair.** A wallet card should separate source opportunity, copied price drag, fees, missed fills, capital occupied and net copied result. This would make wallet selection more informative than headline source P&L; improvement in returns is a hypothesis to test, not a promise.
- **Preserve experiment history.** Put strategies into separate challenger runs with a fixed benchmark and record all rejected opportunities. This makes product performance claims reviewable and avoids choosing policies because of a favorable reset or incomplete sample.

## Verification

- Backend after fixes: **2,519 passed**, including four independent review tests. Output: `audit/2026-09-08/batch_a_review_backend_after.txt`.
- Actual frontend API-client behavior: **4 tests passed** (`node --test frontend/scripts/test-auth-client.cjs`). Covers current-session authority, legacy storage cleanup, logout/401, empty-response cache replacement and late prior-account response rejection.
- Local browser used a separate `batch_a_review_browser.db` with background workers disabled. Guest login showed $10,000 and an empty ledger; settings read successfully and saving existing preferences returned HTTP 200. Logout returned to login, and a second guest session loaded its own later genesis timestamp. This is a basic journey, not exhaustive account-switch validation with populated portfolios.
- Frontend TypeScript and ESLint passed after the edits. `npm run build` also passed with a disposable build secret and localhost backend configuration; output is in `audit/2026-09-08/batch_a_review_frontend_build.txt`.
- Visually inspected the updated desktop dashboard and landing page. The paper notice, simulated-fill labels, revised fee wording and removal of the ordinary guest's admin link were visible. Mobile, keyboard and theme regression journeys remain unverified.
- Docker engine was unavailable. No clean-image startup or PostgreSQL concurrency/restore certification is claimed.

## Handoff

Finish the outstanding Batch A gates before marking A complete, then follow B → C from the V2 brief. Keep the existing run archived as unvalidated; do not reset it as part of this review. The fixes here are local, uncommitted changes. Review them alongside Gemini's pre-existing changes before choosing a commit boundary.
