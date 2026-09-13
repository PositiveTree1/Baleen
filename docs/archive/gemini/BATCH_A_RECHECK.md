# Batch A recheck — 8 September 2026

**Implementation and automated verification completed; final browser acceptance remains open.** This supersedes the open technical findings in `BATCH_A_REVIEW.md`. Batch B planning can proceed, but the V2 plan's complete browser journey is still required before an unconditional Batch A sign-off. This is not production release approval.

## Fixes completed

- Persisted rate-limit buckets and logout revocations in the database, shared across workers and restarts. Added unique token IDs and aligned the frontend session maximum with the backend's 72-hour token lifetime. Quota acquisition reuses the request connection to avoid pool starvation; fixed-window limits may admit a boundary burst.
- Added migration 6 for security state. PostgreSQL startup locks now cover table creation and migration. Failed migrations roll back; readiness verifies migration history and actual required tables/columns rather than trusting a version stamp. Railway health checks use `/ready`.
- Aligned the supported Python runtime to 3.12, regenerated the dependency lock, and made both Docker builds install the complete hash-checked pinned dependency export. Added the missing matplotlib dependency, constrained pandas, corrected package discovery, and excluded local credentials/databases from image build contexts. OS/base images are not digest-pinned, so this does not claim bit-for-bit image reproducibility.
- Rehearsed credential inventory, rotation, and old-key retirement. Plaintext backfill requires an explicit operator option; unreadable ciphertext aborts and rolls back the rotation.
- Logout now uses the current signed session and reports failed revocation instead of silently succeeding. Signup stays on the form after signup/login failure and displays the error; it navigates only after successful authentication.
- Fixed a real PostgreSQL guest-provisioning failure: explicitly flush the new user before inserting its foreign-key-dependent initial snapshot, within the same transaction. SQLite had concealed this insertion-order problem.
- Added `RUN_BACKGROUND_WORKERS` (default true) to permit API-only processes. The isolated production-mode startup smoke disables workers without using a production `TESTING` bypass.

## Verification evidence

All database exercises used disposable local PostgreSQL data; no production database, real order, or benchmark reset was involved.

| Check | Result | Evidence under `audit/2026-09-08/` |
| --- | --- | --- |
| Full backend suite, Python 3.12, real PostgreSQL tests enabled | **2,533 passed** | `batch_a_recheck_python312.txt` |
| Dedicated real PostgreSQL checks | **4 passed**: concurrent startup/old-schema upgrade, migration rollback, durable security with a small connection pool, guest FK ordering | `batch_a_real_postgres.txt` |
| PostgreSQL dump/restore | Passed; schema 6 and fixture balance 4321.25 retained | `batch_a_restore_result.txt`, `restore_rehearsal.py` |
| Root Docker image | Built; application import and listener compilation succeeded | `batch_a_clean_full_image.txt`; image `baleen-batch-a-full-review:latest` |
| Backend Docker image | Built; application import succeeded | `batch_a_clean_api_image.txt`; image `baleen-batch-a-api-review:latest` |
| Production-mode image startup with real PostgreSQL | `/ready` 200, schema 6; 11 API scenarios passed | `batch_a_production_image_smoke.txt`, `production_image_smoke.py` |
| Frontend actual-code regression harnesses | **15 passed** | `batch_a_recheck_frontend_tests.txt` |
| Frontend production build | Passed | `batch_a_recheck_frontend_build.txt` |
| Frontend TypeScript and quiet ESLint checks | Passed during recheck | Terminal verification |

The image smoke covers signup, login, settings save, anonymous/cross-account/admin rejection, expired tokens, isolated account reset, durable logout after database connection disposal, guest login, and payload bounds. It invokes the application via ASGI in the built image; it does not establish browser behavior or chain connectivity. Listener status was UNKNOWN because background workers were deliberately disabled. Build logs retain earlier failed attempts before their successful final builds.

The frontend harnesses execute real application code with mocked session/network/framework boundaries. They are not browser end-to-end tests, even where an older test title calls them a journey.

## Remaining acceptance and next batch

Automatic approval review rejected starting the local frontend, stating only “blocked by policy.” The fresh full browser journey could therefore not be completed. An earlier guest/settings/save/logout/second-guest browser check passed, but the latest signup changes need a fresh isolated browser run covering signup/login/guest → settings read/save → reset → logout → another account, plus expiry and direct admin access.

After that check, proceed to Batch B (R3–R5: provider contracts, chain decoding, canonical ingestion). Keep later accounting fixes in their planned batches. The prior independent financial audit still records **6 passed / 8 failed** in `batch_a_review_independent.txt`; it was not rerun in this final recheck. Those failures include overspending paper capital, inflated settlement, incorrect wallet returns/redemption handling, rejected exits removing positions, unrelated market prices, and duplicate REST/listener copies. Passing Batch A does not resolve those defects or establish profitable trading.

Highest-value product work remains trustworthy net copied returns (fees, price drag, missed fills, occupied capital), explicit stale/unavailable financial data, and preserved challenger-run history. These are hypotheses to evaluate after accounting correctness, not promises of higher returns.

All changes remain in the existing working tree alongside Gemini's unrelated changes. No commit or deployment was made.
