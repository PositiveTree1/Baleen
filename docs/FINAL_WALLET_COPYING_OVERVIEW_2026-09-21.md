# Baleen wallet-copying overview — September 21, 2026

## Where the project stands

The local codebase is ready to deploy as a complete **paper-copying** release. It contains the wallet discovery and evidence work, a reliable forward ingestion path, an authenticated server-owned paper configuration, receipt and order-book checks, a durable accounting journal, and dashboard reporting. The local release has passed its backend, listener, integration and frontend-build checks.

The currently deployed Baleen app has not received these changes yet. It is therefore expected to keep showing the earlier missing-trade behaviour until the full release is committed and deployed. The old deployment should not be used as evidence that this completed code is failing.

This release does not enable real-money trading. It produces a controlled, forward paper trial so that the system can prove it detects, verifies and models new source fills before any live-capital decision is considered.

## What caused the missing-copy incident

The September 20 production inspection found a real mismatch between what the dashboard displayed and what the backend was able to copy:

1. The dashboard's apparent followed-wallet list was stored in the browser. It displayed selected wallets, including am100, but did not create a server-side subscription or change the listener roster.
2. The deployed service reported zero active basket wallets and an unknown listener heartbeat. That meant there was no verified evidence that the listener was consuming source activity after deployment.
3. A research gate had correctly stopped new BUY entries until fresh research evidence existed, but the deployed UI did not clearly show that this policy was stopping entry copying. The result looked like an unexplained outage.
4. The old signal path could mark a source event processed even when a canonical record was unavailable, and a rejected copy could roll back its source detection. Both make troubleshooting and replay unreliable.

The investigation did confirm that am100 had recent public Polymarket BUY activity. The issue was not simply that the wallet was quiet. The earlier change that evicted wallets merely because `last_trade_at` was absent has been removed; hiding a wallet does not repair ingestion.

## What is now implemented

### Wallet selection and research

New wallets must pass the verified all-time P&L admission threshold before they are retained. The evaluator records cursor-based history coverage, activity rate, time span, P&L curve evidence and exclusions. It targets the requested 2–30 trades/day profile and explicitly identifies high-frequency behaviour as unsuitable for copying. Quiet watchlist and research candidates remain monitored even when they are not in a funded allocation.

Resetting wallet statistics archives derived statistics and keeps wallet addresses and first-seen history. This means a clean research cycle does not lose the niche wallets already found. Addresses with cleared statistics are still searchable and can be selected for a paper run.

### Copying and accounting

The follow list is now saved on the server for the signed-in account. Starting a new paper run archives the prior run, records each selected wallet, fetches a fresh current equity baseline, and fixes a proportional allocation ratio. The ratio is based on the allocated paper cash and current observed source equity; it is never increased because a wallet had a large lifetime P&L.

For every new source fill after that run's cutoff, the worker verifies the exact Polygon exchange receipt, waits for confirmation depth, checks the matching market and token, then observes the current order book, minimum order size, available depth and fee schedule. It records a copy decision even when the trade cannot be copied. Missed entry legs pause later entries, while valid exits for held inventory remain eligible. The worker never invents a fill or rounds a trade up just to satisfy a minimum order.

Paper cash, positions, partial exits, fees and settled binary payouts use a durable Decimal journal. The dashboard distinguishes a detected/copyable paper fill from a rejected, missed or unavailable one. It shows P&L only when current marks are fresh; otherwise it explicitly says the valuation is unavailable.

### Listener reliability

The Railway startup script supervises both the Node listener and Python backend, and fails the service if either required process exits. The listener refreshes the watched roster before it advances each batch, records a durable delivery checkpoint, and persists heartbeat/progress data in the database. A redeploy can resume from that confirmed cursor rather than silently jumping past work. Public health states now differentiate unknown, online, stalled and offline.

## Evidence from local verification

The local release passed 2,829 backend tests, 13 listener tests, an 18-test final integration suite, and the frontend production build. The final integration checks cover concurrent workers, reset isolation, source receipt through to dashboard accounting, partial exits, settlement payouts, stale valuations, and selectable retained addresses. A disposable browser run confirmed that a server-saved selection remains visible and checked even when that wallet has no current statistics.

These tests establish that the software paths behave as designed in controlled environments. They do not establish that Railway has the correct runtime configuration, that production has received the release, or that a strategy will make money.

## What must happen next

Gemini can now commit and deploy the reviewed complete release. It must include the backend, listener, frontend, startup script and migrations through schema 24 in one deployment. Do not deploy only the Procfile or only the frontend.

After deployment, the concrete acceptance check is to configure the desired paper wallets in the new dashboard and trace one **new** source trade end-to-end:

`wallet source fill → listener → signal inbox → canonical event → receipt verification → journal decision → dashboard`

That check must show the saved wallet in the server roster, an ONLINE listener with a moving delivery cursor, and a visible journal outcome. It will tell us whether the production service is actually repaired. The detailed sequence is in `GEMINI_WALLET_CUTOVER.md`.

Only after that check passes should the global wallet-statistics reset be run. The reset is optional and safe when done with writers stopped: it archives old scores and evidence, retains addresses, and does not erase user balances, positions, executions or paper history. A new personal paper run is a separate action from that global reset.

## What “profitability remains unproven” means

It does **not** mean the local implementation is unfinished or that it should not be deployed for paper verification. It means that reliable mechanics and profitable strategy performance are separate questions.

After deployment and the end-to-end trace, Baleen will be ready to run its clean forward paper trial: it should detect newly configured wallet trades, apply the fixed-copy policy, and report the result truthfully. We still need enough independent future trades and resolved outcomes to measure whether the wallet-selection rules, execution limits, fees and slippage produce positive results. A few trades, or a wallet's historical P&L, cannot prove that.

No automatic live-money approval is included in this release. The appropriate next milestone is a verified production paper run, followed by evidence from a meaningful prospective sample. That is the point at which a live-capital proposal can be assessed responsibly.
