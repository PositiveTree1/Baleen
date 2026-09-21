# Gemini deployment and reset handoff — September 21, 2026

## Release status and scope

The paper pipeline is implemented locally: automatic capital-tier roster selection, visible monitored standby snipers, receipt-verified proportional paper copying, observed book fills/fees, durable journals, confirmed payouts, safe roster rotation, and dashboard audit reports. Schema **26** adds the roster-rotation audit after migrations 24–25 add account selection and sniper-allocation audits. This supersedes the September 18 research-only handoff.

Production repair is not yet confirmed. September 20 public checks showed zero active basket wallets and an unknown listener; the five UI selections were browser-only settings. Private Railway logs remain unavailable because Railway is signed out. Read [the incident report](TRADE_INGESTION_INCIDENT_2026-09-20.md).

## 1. Commit and deploy the complete release

Verify the GitHub origin, Railway/Vercel projects and deployment branches. Review and commit the relevant backend, frontend, listener, startup, migrations, tests and docs together. Do not deploy only the Procfile fix or blindly stage everything.

Exclude secrets, environment files, local databases, dependencies/build output, and unrelated modified backups:

- `backend/data/backups/baleen_all_trades_backup.csv`
- `backend/data/backups/baleen_all_trades_backup.json`

Preserve unrelated `BalanceCounter.tsx` edits for their owner to review separately. Keep `docs/WALLET_STRATEGY_LOGIC.md` as the current strategy authority and retain dated evidence/archives.

Local checks: 2,829 backend tests previously passed with isolated PostgreSQL; the current focused regression suite has 55 passing tests covering automatic ranking, standby monitoring, sniper allocations, retirement/exit handling, receipt-to-dashboard accounting and reset isolation. All 13 listener tests and the frontend production build pass. Review dated logs in `docs/research/` before pushing.

## 2. Verify production before any reset

1. Deploy the reviewed commit to Railway and Vercel; verify both deployed versions. Confirm Railway starts both Node and Python through `bash start.sh` (also the Dockerfile entrypoint).
2. Confirm the intended database, complete schema **26**, background workers, listener service authentication, Envio configuration and receipt RPC. Do not print secrets. Keep real-money execution gated.
3. Run `python -m app.paper_preflight` from `backend` in the deployed environment. Inspect `/ready`, private startup/error logs and failed inbox entries. Passing preflight alone does not prove copying or profitability.
4. Verify persisted listener health ONLINE, advancing delivered-block cursor and restart recovery. Investigate quarantined/failed signals; do not delete them to make health checks pass.
5. Start automatic paper copying with only a paper-cash amount. The server selects the capital-tier roster from fresh eligible candidates; there is no manual wallet selection. Verify active sources, standby snipers and their listener inclusion using service authentication.
6. Trace a **new post-start** active-wallet fill through listener → inbox → canonical event → receipt proof → journal → dashboard. Use am100 (`0x6e32312760e4604d45a8ae69cede9ef9a0b8ab65`) if current screening permits. Earlier fills are outside the new run cutoff. Do not bypass a fresh exclusion to force activity.
7. Verify ratio, book/depth, estimated fee, shares and cash. Also trace a standby sniper BUY: it must either move only free cash from the lowest current-P&L active sleeve or visibly record why no allocation was safe. Confirm roster rotation never closes existing positions and leaves retired wallets exit-only.

## 3. Optional global wallet-statistics reset

This archives statistics and preserves addresses. It does not clear balances, positions, executions or paper account history. Do it only after the release is verified and the user is ready.

1. Confirm the Supabase project, take a backup and verify access to it.
2. Stop all writers during maintenance: APIs, discovery/evaluation, listener and trading workers. Reconcile outstanding/uncertain real orders first; do not discard them. Resume exit monitoring promptly afterward.
3. With Python 3.12 and the new environment, confirm migrations, then preview using one stable reset ID:

   ```powershell
   python -m app.reset_wallet_statistics --reset-id wallet-evidence-2026-09-21
   ```

4. Check target/counts and apply with writers stopped:

   ```powershell
   python -m app.reset_wallet_statistics --reset-id wallet-evidence-2026-09-21 --apply --workers-stopped
   ```

5. Reusing the same ID is idempotent. Do not substitute TRUNCATE or a SQL wipe. Current statistics/evidence/scores are archived; addresses and first-seen dates remain. Derived statistics/identity metadata are cleared; retained wallets await fresh collection. Historical observations retain their generation. Financial records remain intact.
6. Resume only new binaries. Check retained addresses remain searchable, old cached scores/curves are invalidated, and new evidence uses the new generation. Re-evaluation handles 25 due wallets per batch. Do not force `execution_approved=true`.

## 4. Start a clean personal paper run

Use **Start fresh**, enter starting paper cash, then **Archive current run and start automatic paper copying**. Fresh equity baselines must succeed before archival. The server chooses the active roster and sets fixed ratios; standby snipers stay visible and monitored without idle sleeves. This is separate from the global statistics reset.

Verify server-saved selections and repeat the new-fill trace. Retain old audit records. The collapsed earlier simulator panels display separate results and are not the new journal's performance.

## Remaining research boundary

Forward paper copying supports trade fills and confirmed payouts, not arbitrary source transfers/splits/merges/conversions. Historical funding/inventory reconstruction, held-out comparisons and prospective profitability results remain unverified. Current equity snapshots are not historical capital. There is no automatic live approval or demonstrated profit guarantee.

Report commit/deployment versions, schema, listener/cursor evidence, source transaction and journal result, reset ID/counts if applied, preserved financial records and fresh evaluation progress. A reset is not an ingestion repair.
