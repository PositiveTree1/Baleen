# Live-readiness review — 2026-09-13

**Live activation remains gated.** Signing, copying, reconciliation and wallet setup code is now connected and tested locally. The operator has not yet set up a Deposit Wallet or approved builder session-management access. No deployment, real order, real owner authorization, funding transfer, or customer sandbox reset was performed. Automated venue responses and signing wallets are synthetic fixtures. Passing tests does not establish profitability or universal scenario coverage.

Current handoff: [GEMINI_FINISHING_WORK.md](GEMINI_FINISHING_WORK.md). Eleven previous briefs/reports and the previous readiness review were preserved in [the archive](docs/archive/gemini/README.md). External setup: [SCOPED_WALLET_SETUP.md](docs/SCOPED_WALLET_SETUP.md).

## Completed engineering

- The copy worker connects confirmed source events, explicit account policy, source-specific holdings, scoped signing and durable reservations. It rechecks policy revision, grant, quote freshness, liquidity, source age, exposure, fee bound and signed identity before submission. Events before policy/account initialization are ineligible. Stops or policy changes during signing prevent submission.
- Source trades are verified against canonical Polygon receipts: block identity/time, exchange, log, order owner, side, token and exact quantities. Receipt decimals drive sizing instead of stored floating-point projections.
- Fixed duplicate/incorrect attribution: only the owner of the order represented by an `OrderFilled` log is copied. Counterparty topics do not create another trade. This prevents duplicate taker copying and wrong token/side inference for mint/merge matches. Old queued counterparty entries are quarantined; previously applied history is not silently rewritten. Listener subscriptions include enabled live policies and sources with held shares.
- Fee-bearing fills use canonical V2 receipt quantities, collateral and fees. Multiple API matches in one transaction do not repeatedly book its aggregate fee. Exact settlement cash is persisted. Contract fee bounds use `getMaxFeeRate()`; zero means unlimited and blocks submission. SELL fee budgets allow for better execution prices.
- The journal preserves uncertain orders, commits submission state before network I/O, books confirmed fills idempotently, and reserves source-specific inventory for exits. One source cannot sell another source's allocation. Cancellation requests survive restart; reservations release after terminal status and fill reconciliation.
- Normal confirmation delays produce `WAITING`, pausing new submissions without permanently disabling the account. Mismatches produce `BLOCKED`; successful later reads never undo an explicit stop. Bootstrapped accounts scan complete supported wallet transfer history and compare all holdings, including tokens absent from the journal.
- Session material is account/wallet bound and encrypted. Credential rotation includes session keys; plaintext session keys have no migration opt-in. Credential forms cannot rebind a session or journal to another wallet/owner. Unverified wallet cash remains unavailable instead of zero.
- Owner authorization/revocation uses persisted, fixed-purpose EIP-712 challenges. The browser helper validates the exact wallet/session, chain, scope, call and expiry; the backend independently recovers the owner. Operations are journaled before relayer I/O. Unknown outcomes are not automatically resubmitted. Relayer acceptance stays pending; grant verification is separate. This flow accepts no owner private key.
- Account initialization reads confirmed pUSD funding and discovers supported ERC-1155 holdings from genesis, including counterfactual prefunding. It verifies venue cash, rejects existing orders and positions requiring basis import, and saves an immutable baseline with execution disabled. It never seeds live cash from paper funds.
- Earlier corrections remain: account-owned paper run archival/reset isolation; fresh/nullable valuations; no invented chart baseline/history; truthful aggregate coverage and completed-outcome win rates; simulated records excluded from verified live values; account-scoped journal/cancellation display; durable listener/inbox recovery and authentication isolation.

Primary references: [V2 Trading.sol](https://github.com/Polymarket/ctf-exchange-v2/blob/main/src/exchange/mixins/Trading.sol), [V2 Fees.sol](https://github.com/Polymarket/ctf-exchange-v2/blob/main/src/exchange/mixins/Fees.sol), [V1 Trading.sol](https://github.com/Polymarket/ctf-exchange/blob/main/src/exchange/mixins/Trading.sol), [session keys](https://docs.polymarket.com/trading/session-keys), [contract addresses](https://docs.polymarket.com/resources/contracts). SDK pinned to `polymarket-client==0.10.0`.

## Verification

Current logs are in `audit/live-readiness/` with the `_current.txt` suffix. Older logs remain historical.

| Check | Result / evidence |
| --- | --- |
| Backend, including isolated local PostgreSQL | **2,743 passed** — `backend_suite_current.txt` |
| Independent accounting invariants | **14 passed** — `independent_checks_current.txt` |
| Listener attribution/decoder/queue | **12 passed**, TypeScript build passed — `listener_tests_current.txt` |
| Frontend production build | Passed — `frontend_build_current.txt` |
| Frontend lint | 0 errors, 107 warnings — `frontend_lint_current.txt` |
| Wallet approval helper | 11 checks passed with a mock provider |
| Settings/value/execution adapters | 11 passed |
| PostgreSQL dump/restore | Schema **18**, preserved data, idempotent migrations — `restore_rehearsal_current.txt` |
| Production backend/listener image | Built `3792d2c2bfd9` — `production_image_build_current.txt` |
| Production image API smoke | **15 checks passed**, schema 18, disposable local PostgreSQL — `production_image_smoke_current.txt` |

Fresh browser acceptance remains outstanding. An earlier automatic approval review blocked starting the local frontend server; that restriction was not bypassed. A build, `/ready`, fixture signature or isolated database test is not exchange-account certification.

## Remaining release work

1. **External setup and real protocol acceptance.** Obtain the Deposit Wallet and approved builder access. Validate its actual owner grant, confirm revocation on-chain, and finish explicit key replacement/renewal and uncertain-operation recovery. Unresolved states are currently preserved. Gemini has Settings controls around the tested helper; cryptography is not assigned to Gemini.
2. **External cash flows and settlement accounting.** Post-baseline deposits/withdrawals, redemption/settlement, non-journal trades and existing-position basis import still need authoritative ledger entries and replay coverage. Current mismatches halt execution without fabricated balancing entries. The loss guard is conservative (negative realized fills plus negative marked inventory); complete calendar-day equity/cash-flow accounting remains part of this work.
3. **Paper strategy isolation.** The legacy paper poller still has global portfolio-policy coupling and execution uniqueness constraints. Complete account/mode/run exposure and source-exit sizing isolation before claiming every paper scenario represents the new live coordinator.
4. **Operational and real-account validation.** Validate archive-RPC completeness/range support, venue eligibility, actual account API coverage, deployment secrets, worker health, restart/outage recovery, cancellation/fill races and independent replay of real receipts. Complete browser journeys. A bounded real-order pilot requires the intended account and explicit risk/size approval; none has run.

Keep `LIVE_EXECUTION_ENABLED=false`. Activation remains server-gated even if a UI or environment flag changes. Do not remove the gate because Gemini finishes its UI file. A paper reset affects only the named paper run and cannot substitute for this release work.
