# Batch B review and corrective work

Latest continuation: [LIVE_READINESS_REVIEW.md](LIVE_READINESS_REVIEW.md), 2026-09-12.

Reviewed 2026-09-10. Supersedes `BATCH_B_IMPLEMENTATION_REPORT.md`.

**Verdict: substantial defects fixed; Batch B and the full app are not yet certified complete. Live activation remains disabled.** Tests establish specific invariants, not profitability or end-to-end exchange operation.

## Material corrections

- Corrected V2 exchange address/topic routing and event layout. The earlier decoder interpreted token IDs as amounts and metadata as market identity. Raw six-decimal share units now cross the listener/API boundary explicitly, with integer decoding and original block timestamps.
- Queue/checkpoint writes are durable; acknowledgements must explicitly accept delivery. Failed deliveries remain queued, malformed records are quarantined, and restart drains pending work. Queue files require one writer. Confirmations constrain the scan boundary.
- Inbox acceptance survives API callback loss. PostgreSQL claims pending records, persists retries, and quarantines ambiguous legacy units. Concurrent identical acceptance creates one inbox record; conflicting payloads are rejected.
- Canonical application status commits with effects. Unindexed REST observations cannot independently execute and duplicate an indexed chain fill. Held source wallets remain monitored for exits after roster demotion/restart.
- Provider outages and incomplete/repeated pagination no longer masquerade as complete history. Wallet identity and token matching are checked. Discovery no longer invents seed profit, invents unknown redemption basis, or deletes all wallet history on refresh.
- Paper sizing checks cash including fees instead of spending marked equity. Settlement recomputes balances instead of adding already marked gains again. Zero marks remain valid, and price lookup uses token identity.
- Backtests reject unsuccessful SELL fills; zero or malformed executed quantity cannot close an entire position.
- Removed the paper poller's ability to fabricate live fills or debit cached live cash. Credential checks require authenticated CLOB responses; public endpoint reachability cannot certify credentials.

## Verification

Evidence paths are relative to this repository. Disposable databases and mocked exchange I/O were used. No customer account was traded or reset.

| Check | Result | Evidence under `audit/2026-09-10/` |
| --- | --- | --- |
| Backend pytest | 2,592 passed, including local real-PostgreSQL cases | `backend_suite.txt` |
| Listener | 9 passed; TypeScript build passed | `listener_tests.txt`, `listener_build.txt` |
| Independent financial checks | 14 passed, zero failed | `independent_recheck.json` |
| Frontend auth/identity/signup scripts | 15 passed | `frontend_regressions.txt` |
| Root production image | Build passed | `full_image.txt` |
| Production-mode image smoke | 11 auth/account-isolation checks; local PostgreSQL schema 10 | `production_image_smoke.txt` |
| Local PostgreSQL dump/restore | Schema 10 and known balance restored | `restore_rehearsal.txt` |

The image smoke disables background workers. Listener ABI fixtures are synthetic, not real receipts. Frontend scripts are not browser acceptance.

Test isolation was repaired: each pytest invocation uses a unique disposable SQLite file; fixtures that erase financial effects also erase their canonical replay markers. The duplicate-event audit now starts with its own funded account rather than reusing the preceding exhausted-budget scenario. Financial expected values were not relaxed.

## Remaining release gates

1. **R3 provider evidence:** recorded fixtures, complete provenance and period labeling, coverage status through every scoring/UI consumer. Partial history cannot establish qualification.
2. **R4 chain evidence:** independently sourced V1/V2 receipts, activation boundaries, and deep-reorg recovery. The attempted public RPC receipt request returned HTTP 403. Synthetic fixtures do not close this gate.
3. **R5 isolation/replay:** the old paper path still selects a global active run and retains legacy uniqueness/exposure assumptions. Migrate effects to non-null account/mode/run identities, including both source participants; prove replay across users/runs. The new live journal does not automatically repair this path.
4. **R6–R15:** finish immutable paper accounting, consistent marks/snapshots, historical replay without future data, roster/risk enforcement, benchmark lifecycle, and financial UI acceptance. Compatibility cash reconstruction is not the final immutable ledger.
5. **Live execution:** signing, continuous authenticated reconciliation, market/risk checks, and bounded pilot evidence remain required. See `LIVE_EXECUTION_PREPARATION.md`.
6. **Browser acceptance:** repeat the current guest/settings/wallet/copy/exit/error journey. Automatic approval review blocked starting the local frontend with the stated reason “blocked by policy”; this was not bypassed.

Routine frontend work may proceed using `GEMINI_APP_COMPLETION_WORK.md`. Reset remains gated by `GEMINI_FRESH_SANDBOX_INSTRUCTIONS.md`. Do not advance solely because a prior report labels a batch complete.
