# Fresh sandbox paper run instructions

Use these instructions to prepare a clean, account-scoped paper run for review.

**Do not execute the reset yet.** First close the outstanding readiness gates below and attach the evidence. The current review has found defects despite Gemini's earlier completion report.

## Default safety boundary

- Archive the previous paper run and create a new account-scoped paper run.
- Do not wipe the whole Supabase project, shared users, credentials, source evidence, or audit history.
- Pause new work and drain/settle the prior run before archiving it. Preserve authentication, ownership, credentials, and recorded source evidence.
- Record the exact project, account, run ID, environment, schema/migration version, code revision, and timestamp in the run manifest.
- Verify a backup and a restore before any reset or archival mutation.

A full disposable-project wipe is allowed only after the exact project is identified and the user gives explicit destructive authorization following a concrete plan and target review.

## New-run baseline

Create one paper run with:

- Starting cash: **$10,000.00**
- Starting equity: **$10,000.00**
- Starting positions: **zero**
- Starting fees: **$0.00**
- Starting realized/unrealized PnL: **$0.00**
- Live execution: disabled

This artificial $10,000 belongs only to a new paper run. Never modify `LiveExecutionAccount`, `LiveOrderIntent`, `LivePosition`, or `LiveConfirmedFill`, seed a live balance, release a live reservation, or erase pending exchange evidence during a paper reset. Read [the current readiness review](LIVE_READINESS_REVIEW.md) before preparing the reset plan; historical batch reports are archived under `docs/archive/gemini/`.

Use an explicit old-event boundary: record the cutoff block/time and exclude observations before it unless they are deliberately imported as read-only history. Do not invent cost basis, fills, settlements, or profit.

## Required checks

Before accepting the run, verify through persistence, API, and UI:

1. The run belongs to the intended account and has a unique run ID and mode.
2. Cash, equity, positions, fees, and PnL match the baseline in the database and API.
3. The dashboard displays the same baseline and identifies the active run.
4. A recorded source event can be traced through inbox, canonical event, intent/fill, and ledger records.
5. Replaying the same event is idempotent; conflicting identity is quarantined or rejected.
6. A second account or run cannot read or mutate this run’s exposure.
7. Restart/reconnect checks retain pending work and do not duplicate effects.
8. Fault-injection/replay tests use disposable staging data. The authorized final reset changes only the named paper account/run; it never invokes a live exchange.

Do not claim readiness, profitability, or a profit guarantee from a clean baseline. Do not activate live trading.

## Outstanding readiness gates

Fresh sandbox setup does not close the remaining gates:

- Batch B, R3–R5: provider completeness, real receipts, durable canonical effects, account/mode/run isolation.
- Batch C, R6–R8: cash/share/fee accounting, exits, settlement, marks, and snapshots.
- Batch D, R9–R11: wallet history, evidence-based qualification, and enforced roster/risk policy.
- Batch E, R12–R13: rejected-fill handling, historical replay, future-data exclusion, and execution realism.
- Batch F, R14–R15: benchmark run lifecycle, operations, and financial UI.
- Real PostgreSQL migration/concurrency/recovery evidence, browser acceptance, and reconciled cash/shares/fees remain required where outstanding.

Attach the run manifest, backup/restore evidence, persistence/API/UI check results, and unresolved failures to the review record.

## Implemented account archive API (2026-09-12)

Read `LIVE_READINESS_REVIEW.md` first. The account endpoint `POST /api/users/{user_id}/reset-sandbox` with `newBalance: 10000` now archives the prior paper run and starts a new one. `GET /api/users/{user_id}/paper-runs` and `GET /api/users/{user_id}/paper-runs/{run_id}/trades` provide authenticated retained history. The legacy global reset returns 409. Do not replace these operations with SQL deletes or a Supabase project wipe. No reset has been performed by this review.
