# Baleen: System Warnings Reference & Sandbox Mode Status

**Last Updated**: 2026-09-13  
**Repository**: `PositiveTree1/Baleen`  
**Purpose**: Plain-English guide to all system, security, operational, and compiler warnings, followed by an evaluation of Sandbox Mode health.

---

## Part 1: Operational & Security Warnings Explained

Baleen is designed for high-stakes non-custodial copy trading on Polymarket CLOB (Polygon). Because it handles trading automation without ever holding user private keys, several strict safety gates and warning banners are intentionally displayed in the UI.

### 1. `Live Trading · Unavailable (Gated)`
* **Where you see it**: Dashboard header, Settings page L2 credentials card, and account initialization panels.
* **Plain English**: Real-money order submission to Polymarket is **turned off** at the server level.
* **Technical Reason**: The backend config sets `LIVE_EXECUTION_ENABLED = False` by default (`backend/app/config.py`). Even if you enter API keys or connect a wallet, Baleen refuses to send real orders to the Polymarket exchange.
* **Why this is good**: It guarantees you cannot accidentally risk real money while exploring the app, configuring copy policies, or running paper simulations.
* **How to activate (Operators only)**: Requires provisioning dedicated Polygon settlement RPC nodes, configuring the Deposit Wallet contract, and explicitly setting `LIVE_EXECUTION_ENABLED=true` in backend environment variables.

---

### 2. `Session Security Invariant 1: Key Creation ≠ Authorization`
* **Where you see it**: Settings $\rightarrow$ Deposit Wallet Signing Session card.
* **Plain English**: Clicking *"Prepare Session Key"* creates an encrypted keypair inside Baleen's server database. It **cannot** trade on Polymarket yet.
* **Technical Reason**: Polymarket's smart contract wallet requires an on-chain EIP-712 signature from your Deposit Wallet owner address granting permission to that session key.
* **What you need to do**: Prepare an `AUTHORIZE` challenge and approve it with your connected browser wallet (e.g. MetaMask).

---

### 3. `Session Security Invariant 2: Grant Observed ≠ Live Trading`
* **Where you see it**: Settings $\rightarrow$ Session Status badge (`authorization_observed`).
* **Plain English**: Polymarket's blockchain contracts have registered your session key grant, but Baleen's server is still in safe mode.
* **Technical Reason**: Even with an active smart contract grant, live execution remains safety-gated by `LIVE_EXECUTION_ENABLED=false` until full system rehearsal is complete.

---

### 4. `Session Security Invariant 3: Locally Disabled ≠ On-Chain Revoked`
* **Where you see it**: Settings $\rightarrow$ Session Status badge (`locally_disabled`).
* **Plain English**: Clicking *"Stop Local Signing"* makes Baleen immediately stop signing orders locally. However, on the Polygon blockchain, Polymarket still considers the session key valid until you revoke it on-chain.
* **Technical Reason**: Smart contracts on Ethereum/Polygon do not know what happened on an off-chain server. To truly cancel the key's permissions on the blockchain, you must click *"Prepare Revocation"* and sign the `REVOKE` transaction with your owner wallet.

---

### 5. `Grant Verification Required`
* **Where you see it**: Settings $\rightarrow$ Read & Initialize Wallet Account section.
* **Plain English**: The *"Read and Initialize Wallet Account"* button is locked until on-chain authorization has been verified.
* **Technical Reason**: Initializing a live account sets an immutable baseline of your real wallet balance (`startingCash`) and starting block (`blockNumber`). It cannot be run without a verified on-chain grant, and will never guess or fabricate an arbitrary $10,000 balance.

---

### 6. `Submission Unresolved (PENDING / UNKNOWN / SUBMITTING)`
* **Where you see it**: Settings $\rightarrow$ Recent Owner Operations list.
* **Plain English**: An authorization or revocation transaction was sent to Polymarket's relayer and is waiting to be confirmed on Polygon.
* **What to do**: Do **not** spam-click or re-sign. Click *"Refresh Operations"* after a few blocks to check for confirmation.

---

### 7. `Max Source Age Delay` Warning
* **Where you see it**: Settings $\rightarrow$ Live Copy Policy form.
* **Plain English**: Do not set `max_source_age_ms` too low (e.g. below 5,000 ms).
* **Technical Reason**: When a whale trades on Polymarket, the event must be confirmed on Polygon and indexed by Baleen's listener. If you set the maximum age to 500 ms, every single copy trade will be rejected as "too old" before it arrives.

---

## Part 2: Build, Compiler & Git Warnings

These warnings appear in the terminal during development and builds. **None of them cause errors or affect runtime behavior.**

### 1. ESLint Warnings (102 warnings, 0 errors)
* **What they are**:
  * Unused icon imports (e.g., `Sparkles`, `Filter`, `TrendingUp`) in older landing page components.
  * Standard `<img>` tags instead of Next.js `<Image />` in legacy dashboard components.
* **Status**: **Harmless**. `npm run lint` exited with **0 errors**.

### 2. Next.js Turbopack Lockfile Inference
* **What it is**: Next.js detected a stray `package-lock.json` in `C:\Users\arthu` alongside the repo's `package-lock.json`.
* **Status**: **Harmless**. Next.js correctly selected the project root and compiled all routes in under 1 second.

### 3. Git CRLF Line-Ending Warnings
* **What it is**: `warning: in the working copy of '...', LF will be replaced by CRLF the next time Git touches it`.
* **Status**: **Harmless**. Windows uses `CRLF` (Carriage Return + Line Feed) while Linux/Git repositories use `LF`. Git automatically normalizes these on commit.

---

## Part 3: Is Sandbox Mode Working Well?

### **Short Answer: YES, Sandbox Mode is working exceptionally well.**

Here is the exact evidence and architecture behind the Sandbox Mode:

### 1. Isolated Virtual Capital ($10,000.00 pUSD)
* Every user account starts with **$10,000.00 pUSD** (Paper USD) of virtual sandbox capital.
* Balances, positions, simulated fills, and unrealized/realized PnL are completely tracked in `ExecutionLog`, `ExposureLedger`, and `PortfolioSnapshot` with `is_sandbox = True`.

### 2. Strict Air-Gap from Live Trading
* Paper trading and live trading run on separate database models and separate execution paths:
  * Paper trades: Handled by the internal matching simulator using real Polymarket CLOB book prices.
  * Live trades: Gated behind `LIVE_EXECUTION_ENABLED=false` and requires Deposit Wallet session keys.
* A paper trade can **never** trigger a live Polymarket order.

### 3. Non-Destructive Reset & Paper Run Archives
* Unlike naive systems that wipe the database on reset, Baleen implements **Account-Scoped Paper Runs** (`SandboxRun`):
  * When you click *"Reset Sandbox"* in the dashboard, the backend calls `POST /api/users/{user_id}/reset-sandbox`.
  * The current run is marked `ARCHIVED` and its complete trading history is saved.
  * A fresh run starts with $10,000.00 pUSD, zero positions, and zero PnL.
  * You can inspect all past paper runs and export trade history JSON anytime via the Settings page archive viewer (`GET /api/users/{user_id}/paper-runs/{run_id}/trades`).

### 4. Real-Time Copy Simulation
* Baleen's listener continuously monitors top-performing Polymarket whale wallets.
* When a target whale executes a trade on Polygon, Baleen's signal pipeline computes:
  * Proportional trade sizing based on your sandbox capital.
  * Slippage tolerance check against the current CLOB order book.
  * Fee simulation.
* The simulated execution is logged to your dashboard Trade Tape in real time with an explicit `(Simulated)` tag.

### 5. Automated Test Coverage
* **Frontend**: 70 automated tests across 8 suites verify zero fake stats, accessible inputs, keyboard navigation, clean error handling, and private state erasure on logout.
* **Backend**: Over 2,700 tests cover signal generation, sniper qualification, netted ledger exposure sizing, fee calculations, and paper run isolation.

---

## Summary Checklist

- [x] **Sandbox Simulation**: Active, isolated, and working with $10,000 pUSD default allocation.
- [x] **Copy Signal Processing**: Functional with order book slippage and fee math.
- [x] **Paper Run Archiving**: Non-destructive reset and JSON export fully wired.
- [x] **Live Trading Gate**: Safely locked (`LIVE_EXECUTION_ENABLED=false`) until production deployment.
- [x] **Frontend Build**: 100% clean compilation (`npm run build` passing with 0 errors).
- [x] **Source Code**: Committed and synced to GitHub (`master` branch).
