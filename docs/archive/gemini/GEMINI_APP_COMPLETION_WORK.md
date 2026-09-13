# Gemini: routine completion work only

Read `BATCH_B_REVIEW.md` and `LIVE_EXECUTION_PREPARATION.md` for the current review and API contract. Follow the frontend contract section when wiring status displays. Do not edit those backend endpoints or interpret readiness false as a UI bug.

Read `BATCH_A_RECHECK.md` and `GEMINI_FRESH_SANDBOX_INSTRUCTIONS.md` first. The owner is implementing the trading engine, financial accounting, exchange integration, migrations, and risk decisions separately. Work on the bounded tasks below so we do not edit those systems concurrently.

The app is being prepared for both paper and real execution. **Do not label it live-ready or profitable, turn on trading, reset Supabase, deploy, or place an order.** The earlier `BATCH_B_IMPLEMENTATION_REPORT.md` completion claim has not survived review.

## Allowed changes

Documentation and frontend presentation/accessibility, plus frontend tests of the behavior you change. Read `frontend/AGENTS.md` and the installed Next.js guide before frontend changes. Preserve existing uncommitted edits. Do not edit backend application code, database models/migrations, listener decoding/delivery, lockfiles, strategy thresholds, pricing, fee calculations, authentication/session logic, or financial formulas. If a task requires an API field that does not exist, report the dependency; do not invent the field or a fallback value.

## Task 1: honest status text and consistent terminology

Inventory dashboard, settings, landing page, wallet drawer, trade log, analytics, exports, and copilot labels. List file/line and proposed wording in `GEMINI_UI_INVENTORY.md`, then implement straightforward text corrections using actual returned state:

- “Paper” for simulated fills. Reserve “Live” for exchange-confirmed execution supplied by a reviewed backend contract.
- An API being reachable does not mean credentials or signing authority are verified.
- Zero cash, zero P&L, and empty positions are valid results. A failed request is “Unavailable”, not zero or a new $10,000 account.
- Show supplied as-of timestamps and pending/error state. Do not create freshness timestamps on render.
- Remove unsupported guaranteed-return, audited-performance, latency, uptime, and fee-certainty claims.
- Clearly distinguish source-wallet performance, copied paper results, and exchange-confirmed account results. Do not rename source profit as follower profit.

Do not recalculate account values in this task. If the API cannot distinguish the states above, keep the limitation visible in the inventory and wait for the owner's contract.

## Task 2: accessibility and responsive layout

Use the existing UI components/styles. Fix missing accessible names, focus visibility, keyboard close behavior, clipped text, horizontal overflow, and mobile layouts in the reviewed screens. Preserve authentication guards and existing loading/disabled state. Do not restyle the whole app.

Check keyboard navigation, modal focus/return focus, readable error messages, light/dark themes, and narrow/mobile widths. Record the exact pages, viewport widths, and interactions inspected. TypeScript/lint passing is not evidence that a browser interaction worked.

## Task 3: operating documentation

Create `docs/OPERATOR_CHECKLIST.md` with short sections for:

1. Development setup from the locked dependencies and required Python 3.12 runtime.
2. How to identify the deployment revision, schema version, environment, and `/ready` result without printing secrets.
3. Where inbox failures, unresolved events, and stale provider data are reported. If the screen/endpoint is absent, list that gap instead of inventing one.
4. Listener queue/checkpoint persistence: `LISTENER_QUEUE_FILE`, `LISTENER_CHECKPOINT_FILE`, a durable mounted directory, and one writer process per file. `LISTENER_CONFIRMATIONS` is confirmation depth, not proof against every reorg.
5. Credential handling: never paste private keys/API secrets into reports or chat; use the application's reviewed secure connection flow. Do not add a private-key input to the browser yourself.
6. Link the reset instructions. A new paper run does not erase the exchange account or require wiping the Supabase project.
7. Incident response: disable new entries, retain records/pending state, inspect reconciliation, and escalate unknown order outcomes. Do not blindly resend an order after a timeout.

Use commands and paths that exist in this checkout. If a startup command would connect to production, document that fact rather than running it.

## Task 4: deterministic UI regression coverage

Add focused tests for any UI behavior you change: empty successful response, valid zero, failed request, long wallet/market names, loading/retry, and keyboard controls. Use fixtures; do not make real exchange requests. Do not change expected financial values to match an observed defect.

Run the frontend's existing auth/identity/signup scripts, TypeScript, ESLint, and production build with isolated configuration. Record command, environment, result, and log location. Do not rewrite the owner's tests or weaken assertions to pass.

## Deliverables and stopping point

Deliver `GEMINI_UI_INVENTORY.md`, `docs/OPERATOR_CHECKLIST.md`, the small frontend changes/tests, and `GEMINI_ROUTINE_WORK_REPORT.md` summarizing changed files, actual checks, and dependencies still missing. Distinguish completed browser checks from component/unit checks.

Stop after these tasks. Leave financial logic, account/run isolation, canonical ingestion, exchange signing/submission, balance/fill reconciliation, kill switches, and database changes to the owner. Do not execute the fresh-run instructions merely because this work is complete.
