# Missing copies: September 20 investigation

## September 21 local repair completed

The journal is now connected to authenticated server-saved selections, the scheduled receipt-verifying paper worker, observed books/fees, confirmed payouts and dashboard reports. Schema 24 is required. Listener delivery checkpoints and heartbeats persist across restarts; the startup supervisor restarts the service if either required process exits. The added eviction of wallets without a recorded last trade was reverted. Retained addresses remain selectable after statistics reset.

Local tests and browser verification are recorded in `WALLET_IMPLEMENTATION_REVIEW.md`. Deployment, private Railway logs and a production source-receipt-to-journal trace remain unverified. Follow `GEMINI_WALLET_CUTOVER.md`; do not reset production to diagnose missing ingestion. The following deployed-state observations are dated September 20, not a fresh health check.

## Confirmed deployed state

Read-only checks of `https://baleen-production-474b.up.railway.app` from the supplied Vercel dashboard:

- `/ready`: schema 22, listener UNKNOWN, database PostgreSQL.
- `/api/stats`: zero active basket wallets, indexer UNKNOWN.
- am100 (`0x6e32312760e4604d45a8ae69cede9ef9a0b8ab65`): tracked, not dormant; reason `ACCOUNT_REPLAY_AND_FORWARD_VALIDATION_REQUIRED`.
- The public Polymarket trades API returns recent am100 BUYs, including transaction `0x4efd2cf4fd7cde071876bb795ca789c385e3369d580683dd89069581d15ac94d`.
- Local commit e0886c4, dated September 18, includes the research gate and refresh changes despite its UI-oriented title. The journal integration is not deployed; its migration 23 is still local.

Raw responses: [deployed evidence](research/deployed-ingestion-am100-2026-09-20.json). No production data was modified.

## Established failure mechanisms

The research collector always leaves execution approval false. Research refresh sets wallets to tracked; basket refresh demotes wallets without approval. The legacy simulator requires active basket membership for new BUYs. The deployed zero-sized basket therefore blocks new copies irrespective of source-wallet activity. This is an incomplete strategy cutover, not evidence that the wallets went dormant.

Listener UNKNOWN means the serving process has no heartbeat. It does not prove whether the listener is stopped, failing authentication, or reporting to another instance. Railway uses a Dockerfile whose CMD already starts both services; changing Procfile alone does not establish a fix. Deployment overrides and runtime logs still need inspection.

An independent ingestion defect existed: creating a canonical event and then rejecting the copy caused an uncommitted transaction to roll back. The inbox could still mark it processed. Normal canonical creation also omitted block_time, required by the receipt-verification path.

## Local corrections

- Reverted Gemini's added eviction of wallets with no recorded last trade. Existing pre-change eviction behavior remains.
- Persist canonical detections before copy-policy evaluation; reacquire the PostgreSQL financial lock and recheck APPLIED status before proceeding.
- Populate canonical block_time.
- Refuse to mark an inbox item processed when no durable canonical event exists.
- Regression verifies an ineligible source BUY remains detected without creating a copied trade.

These changes do not reactivate the empty production basket or establish listener health.

## Completion order

1. Inspect deployed startup command, listener logs, heartbeat delivery, persisted cursor and inbox state. Trace the named am100 transaction through detection, receipt verification and copy decision.
2. Keep monitoring separate from allocation approval: quiet, tracked and held-source wallets must remain discoverable, with explicit reasons for uncopied signals.
3. Connect receipt-verified source events and timestamped book/fee observations to the durable paper journal. Add authenticated run controls with fixed allocations and explicit starting-inventory scope.
4. Switch the paper simulator and dashboard together. Show detected, copied, rejected and unavailable states, with independent balances and P&L from the journal. Preserve existing histories separately.
5. Verify end-to-end in staging, then perform one coherent deployment and observe an actual new source fill through the deployed system. Only then perform the planned statistics cutover with backups and retained addresses.

Do not treat test-suite success as deployed ingestion verification, fabricate approval to repopulate the basket, or reset production data as an outage fix.
