# Gemini operational handoff — September 18, 2026

## What is ready, and what this deployment does

This is a **research/data cutover**, not approval to activate the proposed trading strategy. The implementation adds a fresh wallet registry evaluation path, archived statistics reset, current accounting snapshots, fixed-share sizing checks, independent accounting/replay tools and forward book observation. It does not establish profitable future copying.

New roster allocations remain gated. After the statistics reset, the account-owned live coordinator also rejects new BUY entries without fresh generation-matching research approval, checked before signing and again before submission. Existing SELL eligibility, holdings, balances and executions are preserved. Do not set `execution_approved=true` to make the roster start trading.

The legacy paper simulator still contains P&L-as-capital estimates and synthetic fill assumptions. It is not the new validated copying implementation. Its old reports must not be represented as validation of the new strategy. The new replay explicitly consumes supplied venue observations and never submits orders.

## GitHub scope

Inspected local checkout: branch `master`, origin `https://github.com/PositiveTree1/Baleen.git`. Verify the actual Railway and Vercel linked branches/projects before pushing; local branch names do not prove deployment settings.

Review and commit the relevant application, tests, migrations, README and strategy/research documentation changes from the recent sessions. Preserve the existing frontend edits. Do not use a blind `git add .`.

**Exclude these existing, unrelated modified financial backups:**

- `backend/data/backups/baleen_all_trades_backup.csv`
- `backend/data/backups/baleen_all_trades_backup.json`

Also exclude credentials, `.env` files, local databases, dependency directories and build output. The recorded wallet API research is public data, but inspect staged files before publishing. Keep the exact original request and the archived strategy documents; they explain superseded behavior. `docs/WALLET_STRATEGY_LOGIC.md` is the main strategy document.

## Controlled Supabase cutover

1. Confirm the intended production Supabase project and schema. Take a database backup/snapshot and verify it is accessible. Do not print database credentials in logs or commit them.
2. Review the diff and prepare the commit locally before changing production. Do not push yet if that starts deployment automatically.
3. Quiesce the old application writers: discovery/scoring jobs, API writers, listener and trading workers. Stop new submissions and reconcile outstanding/uncertain orders first. Do not delete or relabel pending orders to make this step pass. Plan a short maintenance window and resume exit monitoring promptly afterward.
4. Run the **new checkout's** migrations against the intended database with the existing approved production environment. Do not start the API/background workers yet. From `backend`, using Python 3.12:

   ```powershell
   python -c "import asyncio; import app.models; from app.database import init_db; asyncio.run(init_db())"
   ```

   Confirm schema version 22. Migrations 20–22 add reset archives, immutable research observations and forward book observations. Migration 19 adds current wallet evidence.

5. Use one stable reset ID. Preview first:

   ```powershell
   python -m app.reset_wallet_statistics --reset-id wallet-evidence-2026-09-18
   ```

   Verify the wallet count and target database, then apply while writers are stopped:

   ```powershell
   python -m app.reset_wallet_statistics --reset-id wallet-evidence-2026-09-18 --apply --workers-stopped
   ```

   Repeating the same ID is idempotent and does not clear newly collected statistics. The transaction archives wallet rows, current evidence and score snapshots; retains addresses and first-seen dates; clears current derived statistics, identity metadata, cached curves, scores, summaries and qualification; removes old current evidence and score snapshots; and marks wallets tracked for fresh collection. Historical observation tables stay available under their original generation. **No user, balance, position, trade, execution, settlement or account policy table is deleted/reset.** Do not substitute `TRUNCATE`, a SQL editor wipe, or the existing full sandbox reset.

6. Push the reviewed commit and allow Railway/Vercel to deploy the new code. Resume workers only on the new version. Old binaries do not understand the generation fence and must not write after reset.
7. Verify startup health and schema version; the generation response header; frontend cache invalidation; no old scores/curves returning; preserved account/position counts; active exit monitoring; new `wallet_evidence` and `wallet_evidence_observations` rows; and blocked unapproved BUYs. Re-evaluation processes 25 due wallets per batch, so rebuilding is gradual, not immediate.
8. After eligible research candidates/watchlist wallets receive fresh evidence, the 30-second observation job rotates through five wallets per batch. It records observed books/fee responses and partial-window errors, not invented fills or profits. Empty complete windows advance monitoring checkpoints without generating observation rows.

If cutover fails, keep new allocations paused and preserve the archives. Do not roll back to old writer binaries against the reset database without a reviewed recovery plan. Existing financial accounting was intentionally not modified by the reset.

## Validation and remaining work

Read `docs/WALLET_IMPLEMENTATION_REVIEW.md` and the latest test logs before deployment. Passing tests establish software behavior, not profitable copying.

Still required for strategy activation: receipt-level mapping of provider history to the independent ledger, historical funding/inventory and marks, independently verified account-specific capital/allocation baselines, prospective resolved outcomes, held-out comparison against cash/simpler policies, and replacement of the legacy paper simulation with the verified replay/execution path. A current accounting ZIP is not historical strategy capital. The forward recorder is the start of observation, not a completed experiment.

Report the commit hash, deployment URLs/versions, reset ID, archived/retained wallet counts, preserved financial-record checks and fresh-evidence progress. State plainly that new strategy allocations remain paused.
