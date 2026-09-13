# Live-readiness review — 2026-09-12

**Not ready to activate live copying.** This review replaces completion claims in the earlier Gemini reports. No deployment, real trade, owner-wallet authorization, or customer sandbox reset was performed. Tests below establish specific behavior; they do not establish profitability or universal scenario coverage.

## Completed corrections

- Paper resets archive account-owned runs and retain their trades and snapshots. A new run receives its own ID and source-time cutoff. Operational reads exclude archived personal runs; authenticated archive endpoints and exports retain evidence. The legacy global reset is disabled. Concurrent reset tests leave exactly one active run.
- Current prices require a fresh, timestamped observation. Missing fills, prices, fees, balances, and wallet statistics remain unavailable. Zero prices and zero recorded fees retain their meaning. Charts no longer invent a $10,000 baseline, move timestamps, or extend old observations to the present.
- Portfolio totals report incomplete valuation when any required position mark is absent. Known subtotals are identified separately. Win rates use completed outcomes; trading frequency no longer masquerades as holding duration. Public wallet details cannot expose private follower records.
- Legacy simulated “live” records remain audit records and no longer populate verified live balances, positions, P&L, or fills. CSV exports preserve recorded values, account/run identity, and evidence type instead of calculating unsupported historical marks.
- Scoped signing uses the pinned Polymarket SDK and verifies the Deposit Wallet signature wrapper, exchange domain, amounts, session identity, current CLOB-only grant, and expiration. Offline tests use newly generated fixture keys. The server does not receive an owner's private key.
- The live journal reserves cash/shares, commits submission state before network I/O, preserves uncertain orders, and applies confirmed fills idempotently. Submission additionally requires an explicit signing/risk gate; no production gate is connected yet.
- Reconciliation uses authenticated pagination, order/fill identity, collateral and known-token balances. Discrepancies disable new risk without fabricated balancing entries. One damaged credential record does not starve other accounts.
- Stop requests persist per order. Reconciliation requests cancellation of journal-owned hashes and preserves reservations until terminal status and fills are reconciled. Never-submitted stopped orders can be voided locally. Existing financial journals cannot be rebound through the credential form.
- Settings now displays account-scoped stored reconciliation, decimal cash/reservations, order states and pending cancellation requests. An available journal is not a readiness certificate.

## Verification evidence

Results are saved under `audit/live-readiness/`. Exchange network responses in automated tests are mocks, not actual exchange-account certification.

| Check | Evidence |
| --- | --- |
| Backend suite, including isolated local PostgreSQL | `backend_suite.txt` — 2,655 passed |
| Independent accounting invariants | `independent_checks.txt` — 14 passed |
| Listener decoder and durable queue | `listener_tests.txt` — 9 passed |
| Frontend production build | `frontend_build.txt` |
| Frontend lint | `frontend_lint.txt` — 0 errors, 107 warnings |
| Production backend/listener image | `production_image_build.txt` — built `8793e665017d` |
| Production image authentication/API smoke | `production_image_smoke.txt` — 11 checks; local PostgreSQL |
| PostgreSQL schema-v13 dump/restore | `restore_rehearsal.txt` |

Frontend adapter tests cover nullable balances, mixed valuation coverage, wallet statistics and execution-state values. Fresh browser acceptance remains outstanding: an earlier automatic approval review blocked starting the local frontend server. That restriction was not bypassed.

## Work still required before live activation

1. **Scoped wallet onboarding and custody implementation.** The user selected scoped authorization. Deposit Wallet ownership, builder/session-management access, owner-approved grant, session-key storage/rotation/revocation and the runtime SDK-client factory still need integration. The signing adapter alone is not an onboarding system.
2. **Production copy/risk coordinator.** Persist explicit account risk policy, connect canonical source events to signed intents, and enforce current policy/evidence again at submission. The deterministic risk module is tested but not connected to production order flow. Finish paper source-exit sizing and all account/mode/run exposure isolation; the existing paper poller still has global portfolio policy coupling and a legacy execution uniqueness constraint.
3. **Complete financial reconciliation.** Fee-bearing trades currently stop for missing authoritative settlement-fee evidence. Bootstrap must verify all holdings and account funding rather than seed live cash. Deposits, withdrawals, settlement/redemption, unknown external positions and complete real receipt replay remain required. Current token reconciliation covers journal-known tokens only.
4. **Protocol and operational coverage.** The scoped signature verifier supports the explicitly listed V2 exchanges; other deployments are blocked. Replay recorded real transactions and exercise owner-grant revocation, complete cancel/fill races, outages, restart and recovery against the intended exchange account.
5. **Final acceptance and bounded pilot.** Complete browser journeys and verify the actual deployment environment. A local build or `/ready` response proves neither listener health nor exchange readiness. Review the exact account and risk limits before an explicitly authorized real-order pilot. No pilot has been run.

Do not enable live execution, wipe Supabase, or hand these financial implementation gaps to Gemini as routine UI work. The immediate external information still needed is whether the intended Deposit Wallet and approved builder/session-management access exist; do not put secrets in chat or work reports.
