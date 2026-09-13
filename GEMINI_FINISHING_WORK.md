# Gemini: settings UI and verification only

This is the current Gemini work file. Earlier briefs and completion reports are historical in `docs/archive/gemini/`. Read `LIVE_READINESS_REVIEW.md` first. Preserve the existing dirty worktree.

## Boundaries

Work only on frontend controls, API client types/adapters, accessibility and their tests. Read `frontend/AGENTS.md` and the relevant installed Next.js guide before editing.

Do not change backend, listener, migrations, financial math, source attribution, signing algorithms, dependency versions, authorization rules, or live activation gates. Do not deploy, reset Supabase, reset an account, fund a wallet or place trades. Never ask for, store or display an owner private key. Never add sample balances, profits, wallet statistics, or fallback zeros to production screens.

## 1. Add a session setup panel to Settings

Use `backend/app/api/live_setup.py` as the exact API contract. Add typed, authenticated API functions to `frontend/src/lib/api-client.ts`; do not cache session/policy/operation responses across accounts. Treat non-2xx as an error and retain form input. Use the existing authentication transport.

| Operation | Endpoint | Body |
| --- | --- | --- |
| Read setup | GET `/api/live-trading/session` | None |
| Prepare an encrypted session key | POST `/api/live-trading/session` | None |
| Verify the actual owner grant | POST `/api/live-trading/session/verify` | None |
| Stop local signing | POST `/api/live-trading/session/disable` | None |
| Read owner operations | GET `/api/live-trading/session/operations` | None |
| Prepare owner approval | POST `/api/live-trading/session/operations` | `{"kind":"AUTHORIZE"}` or `{"kind":"REVOKE"}` |
| Submit owner signature | POST `/api/live-trading/session/operations/{id}/signature` | `{"signature":"0x..."}` |
| Save verified starting wallet balances | POST `/api/live-trading/initialize-account` | None |

Show wallet address, session address, CLOB scope, status, verification time, expiry, and local revocation time. Format dates as UTC with an explicit timezone; unknown remains unavailable. Explain that creating a key does not authorize it. `authorization_observed` means a previous check found the grant; it does not mean the app is live-ready. `locally_disabled` does not prove on-chain revocation.

For owner approvals:

1. Request the challenge after an explicit user action. Display operation type, owner wallet, Deposit Wallet, session address, CLOB-only scope and expiry for review.
2. On a separate explicit approve button, call the existing `signSessionOperation` from `frontend/src/lib/session-wallet-approval.ts` with the connected EIP-1193 wallet provider. Do not modify that helper, its selectors, types or signature validation. Do not sign automatically during page load, effect hooks, refresh, or retries.
3. Submit its returned signature to the operation endpoint once. Never log or persist the signature in browser storage. Refresh stored operation/session status afterward.
4. If no wallet provider exists, explain that the owner wallet must be connected. If the chain or account is wrong, show the helper's error. Do not silently change networks or select another account.
5. `PENDING`, `UNKNOWN` and `SUBMITTING` are unresolved. Show them accurately, with verification/refresh controls; never auto-submit again. `GRANT_OBSERVED` does not enable trading. A revocation submission remaining `PENDING` must not be labeled revoked on-chain.

Disable buttons while a request is in flight. Retain useful errors. Reload state after local disable or saved credentials. The operator has not yet set up the Deposit Wallet or approved builder access, so a setup-required error is expected in that environment. Do not work around it.

After grant verification, an explicit “Read and initialize wallet account” button may call `initialize-account`. It saves a confirmed funding baseline with live execution disabled. It requires complete RPC wallet history, no existing venue orders, and no positions needing cost-basis import. Display its actual `startingCash` and `blockNumber`; do not default to $10,000 or automatically run initialization during page load. Explain setup errors without bypassing these requirements.

Keep the existing owner API credential form. Clearly distinguish owner L2 API credentials from an owner private key; these are different things. Replace the obsolete “enable real money” confirmation flow with the server's unavailable/gated status. Keep a stop control where applicable. Do not add an enable-live action.

## 2. Add an explicit copy-policy form

GET/PUT `/api/live-trading/copy-policy`. GET returns `null` when unset; render an empty form with explanations, not a fabricated saved policy. PUT requires all these top-level fields:

- `source_wallets`: 1–20 unique valid wallet addresses.
- `copy_ratio`: decimal greater than 0 and at most 1; explain that 0.10 copies 10% of source shares.
- Positive decimal limits: `max_order_cash`, `max_total_exposure`, `max_token_exposure`, `max_daily_loss`, in pUSD.
- Integer `max_open_orders`: 1–100.
- Decimal `max_slippage_bps` and `max_fee_bps`: 0–10,000; label basis points (100 bps = 1%).
- Integer `max_quote_age_ms`: 1–60,000; integer `max_source_age_ms`: 1–3,600,000. Label units. Source age includes Polygon confirmation delay; a very short age can exclude every confirmed event.

Keep decimal inputs as strings until request serialization, and integers as integers. Do not multiply the copy ratio by 100 twice. Render the returned policy revision and limits. Saving policy stops current live execution and requests cancellation of pending orders; explain that reactivation is required. Saving is never an activation action.

## 3. Finish simple status and archive presentation

- Keep cash, equity, source fill and simulated fill distinct. Unknown values show unavailable; known zero remains zero.
- Use the existing account-owned paper archive endpoints described in `GEMINI_FRESH_SANDBOX_INSTRUCTIONS.md` to list past runs and link their exports if this UI is still missing. Never trigger a reset to test the screen.
- Existing stored live execution state is historical/accounting evidence, not a “ready” badge. Preserve pending cancellation reservations in the display.
- Reconciliation `WAITING` means confirmation is pending and new submissions are paused. It is distinct from a discrepancy marked `BLOCKED` and from an explicit user stop.
- Make errors and setup status readable by keyboard/screen-reader users. Do not build new promotional claims or profit projections.

## Acceptance

Run from `frontend`: `npm run build`, `npm run lint`, `node scripts/test-session-wallet-approval.cjs`, and relevant existing adapter scripts. Add focused mocked API/UI checks for: no session, awaiting grant, expired grant, local disable, wrong wallet, rejected signature, pending/unknown relay operation, missing policy, policy save failure, and account change clearing displayed private state.

If browser testing is available, check desktop/mobile settings with synthetic staging fixtures and capture results. Never operate a real wallet or bypass a tool denial. A prior automatic review blocked starting the local frontend server; record any remaining browser-test limitation accurately.

Write `GEMINI_FINISHING_REPORT.md` with changed files, exact check results and unresolved failures. Do not claim live readiness or profitability. Completing this UI file does **not** close full external-money reconciliation, deployment validation or real-account pilot work listed in the readiness review.
