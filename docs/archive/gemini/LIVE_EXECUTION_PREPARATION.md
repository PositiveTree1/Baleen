# Live execution preparation

**Current status and remaining work: [LIVE_READINESS_REVIEW.md](LIVE_READINESS_REVIEW.md), reviewed 2026-09-12. The historical checklist below predates the scoped-signing, reconciliation, run-isolation and cancellation changes.**

As of 2026-09-10, real execution is **not activated or certified ready**. No real order was submitted.

## Implemented foundations

- `backend/app/services/clob_gateway.py`: authenticated HMAC transport for private collateral balance and order lookup; signs the exact outgoing body; distinguishes authentication failure from unavailable data. A successful acknowledgement is never a fill. HTTP tests use mocks.
- `backend/app/services/live_order_journal.py`: PostgreSQL account locks, cash/share reservations, stable intent replay checks, submission state committed before I/O, and uncertain-outcome retention without blind retries. Confirmed fills update cash/inventory atomically and idempotently. Reservation release requires terminal cancellation and reconciled fill quantity. Fee/limit discrepancies disable new risk while recording reported movement.
- Migrations 9–10 add signer identity and separate live account, intent, position and fill tables with decimal financial columns. Journal tests exercise real local PostgreSQL, not an exchange account.
- Credential changes and the disable control disable the order account while retaining reservations. Prepare and submit reject disabled or stale-reconciliation accounts. A local switch cannot retract an order already transmitted.
- Authenticated `/api/live-trading/capabilities` and `/execution-state` expose account-scoped preparation state. Missing cash is null, not an invented $10,000. They expose no signed envelopes or secrets.
- The old paper poller cannot produce live executions even when the old feature flag is enabled. Activation remains blocked until the real pipeline is connected.

## Core work before activation — Codex ownership

1. **Choose signing authorization.** User selected scoped wallet authorization keeping the main private key out of Baleen. Verify current wallet/SDK support before implementation. Never request private keys in chat or Gemini reports. L2 API credentials alone cannot sign orders.
2. **Implement and verify signing.** Bind signer, funding wallet, account and chain; check the signed order hash and complete EIP-712 payload, expiration, venue, owner, signature type and delegated limits. The journal currently trusts a future reviewed internal signer for cryptographic validity. An arbitrary envelope is not authorization.
3. **Build continuous reconciliation.** Authenticated open orders, paginated trades, per-order fills/fees, collateral/allowances and token balances, durable cursors, restart recovery, websocket gaps and unknown submissions. Bootstrap from the real account; never seed live cash artificially. Halt on discrepancies, preserve evidence, and never treat absence from an incomplete page as cancellation.
4. **Connect risk-approved copy intents.** Finish account/mode/run isolation first. Enforce quote age, current ticks/minimum size, fees, liquidity, slippage, exposure/loss limits, source exits and settlements at submission. Reject stale prepared orders and revoked signing authority. UI settings alone cannot enforce risk.
5. **Complete operational controls.** Emergency stop prevents new submissions and requests exchange cancellation while reconciliation stays alive for in-flight orders. Exercise rotation, network loss, process crash and multiple workers. The current cancellation method relies on a trusted caller supplying verified terminal/fill evidence; it is not an automated reconciler.
6. **Validate rollout.** Replay recorded real receipts; finish paper conservation and browser acceptance; reconcile a controlled exchange account. Review the exact account, limits and bounded pilot plan with the user before any real order. Expand only after cash, shares and fees match exchange evidence.

## Frontend contract for Gemini

Read the actual fields in `backend/app/api/live_trading.py`. `capabilities` uses snake_case; `execution-state` uses camelCase. Both report readiness false. Numeric strings preserve decimal values; missing values must not become zero. An available execution-state response is a stored snapshot: display its `reconciledAt`, not an invented freshness time.

The legacy `/dashboard` labels records `legacy_unverified`; do not present them as confirmed exchange history or derive real profit from them. Compatibility fields such as `usdc_balance` are not the current collateral specification; capabilities/gateway explicitly name pUSD.

Credential requests accept optional `signer_address` and `signature_type`. Proxy/deposit binding is not automatically proven by a successful private API response. Do not add key custody, signing, deposit or approval flows as routine frontend work.

## Official protocol references

Reviewed [authentication](https://docs.polymarket.com/getting-started/api), [wallet/signature types](https://docs.polymarket.com/trading/wallets-auth), [order placement](https://docs.polymarket.com/trading/place-orders), [contracts](https://docs.polymarket.com/resources/contracts), and [V2 event definitions](https://raw.githubusercontent.com/Polymarket/ctf-exchange-v2/main/src/exchange/mixins/Events.sol). Documentation and mock verification are not live-account certification.
