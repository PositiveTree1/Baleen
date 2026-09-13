# Operator Checklist & Production Runbook

**Document:** `docs/OPERATOR_CHECKLIST.md`  
**Standard:** Antigravity / Baleen Operational Integrity  
**Applicability:** Baleen Backend, Blockchain Listener, and Frontend Web Application

---

## 1. Development Setup & Locked Dependencies

### Python Runtime
- **Required Runtime:** Python **3.12** (Python 3.13+ is unsupported due to C-extension compatibility in cryptographic and async libraries).
- **Dependency Locking:** Use `backend/uv.lock` or pinned requirements `backend/requirements-pinned.txt` (fallback: `backend/requirements.txt`).
- **Backend Setup Command:**
  ```bash
  # Using uv (recommended)
  cd backend
  uv sync

  # Or using standard pip in a virtual environment
  python3.12 -m venv .venv
  source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```

### Frontend Runtime
- **Required Runtime:** Node.js **20+** LTS (Next.js 16 with React 19).
- **Frontend Setup Command:**
  ```bash
  npm --prefix frontend install
  ```

### Listener Runtime
- **Required Runtime:** Node.js **20+** LTS / TypeScript.
- **Listener Setup Command:**
  ```bash
  npm --prefix listener install
  ```

> [!WARNING]
> Do not upgrade package versions or alter lockfiles (`backend/uv.lock`, `package-lock.json`) during routine maintenance.

---

## 2. Deployment Revision, Schema Version, Environment & Health (`/ready`)

Never print or log cleartext secrets when inspecting application or system status.

### Revision Identification
```bash
git rev-parse --short HEAD
# If running in container: inspect $GIT_COMMIT or $RAILWAY_GIT_COMMIT_SHA
```

### Database Schema Version
The application enforces durable database migrations. Check the schema version programmatically or via migration helper:
```bash
python -c "import asyncio; from app.database import engine; from app.migrations import check_schema_version; asyncio.run(check_schema_version(engine))"
```
Or check Alembic / migration table:
```bash
# On PostgreSQL
psql -d $DATABASE_URL -c "SELECT version_num FROM alembic_version;"
```

### Environment Verification
Confirm that `ENVIRONMENT` is set appropriately (`development`, `staging`, or `production`):
```bash
python -c "from app.config import settings; print(f'Environment: {settings.ENVIRONMENT}, LiveTradingEnabled: {settings.LIVE_EXECUTION_ENABLED}')"
```

### Readiness Healthcheck (`/ready`)
The backend provides an unauthenticated `/ready` healthcheck probe that validates database connectivity and core readiness without exposing environment variables or credentials:
```bash
curl -i http://localhost:8000/ready
```
**Expected 200 OK Response:**
```json
{
  "status": "ready",
  "database": "connected",
  "timestamp": "2026-09-10T12:00:00Z"
}
```
If the database connection fails, `/ready` responds with HTTP 503 and `{"status": "unavailable", "database": "disconnected"}`.

---

## 3. Incident Logging: Inbox Failures, Unresolved Events & Stale Data

### Inbox Event Failures & Quarantined Payloads
Indexed blockchain events from the listener are processed through the `inbox_events` table in PostgreSQL.
- **Query Failed or Quarantined Events:**
  ```sql
  SELECT id, event_id, event_type, status, retry_count, error_message, created_at, updated_at
  FROM inbox_events
  WHERE status IN ('failed', 'quarantined')
  ORDER BY created_at DESC
  LIMIT 50;
  ```
- **Operator Gap:** The frontend admin panel currently displays discovery audit summaries, but does **not** have a dedicated UI table for raw quarantined inbox events. Operators must inspect the `inbox_events` table directly via SQL or container logs.

### Stale Provider Data & Discovery Audits
- Discovery freshness is tracked in database metadata and exposed via `GET /api/admin/status`:
  ```bash
  curl -s http://localhost:8000/api/admin/status | jq '.audit'
  ```
- If `last_discovery_at` or `last_scoring_at` exceeds the operational threshold (default: 4 hours), check background worker logs:
  ```bash
  grep -E "discovery_scanner|scoring_pipeline" /var/log/baleen/backend.log
  ```

---

## 4. Listener Queue & Checkpoint Persistence

The blockchain listener writes indexed HyperSync events to an append-only queue file before delivery to the backend API.

### Configuration
```env
LISTENER_QUEUE_FILE=/var/data/baleen/listener_queue.jsonl
LISTENER_CHECKPOINT_FILE=/var/data/baleen/listener_checkpoint.json
LISTENER_CONFIRMATIONS=64
```

### Critical Operational Rules
1. **Durable Volume Mount:** `LISTENER_QUEUE_FILE` and `LISTENER_CHECKPOINT_FILE` must reside on persistent, durable storage (e.g. mounted persistent volume or EBS volume), **never** on ephemeral container scratch disks.
2. **Single Writer Concurrency:** Exactly **one** listener process may write to the queue and checkpoint file at any time. Running concurrent listener instances pointing to the same file path will cause interleaved corruption and lost event acknowledgments.
3. **Reorg Boundaries (`LISTENER_CONFIRMATIONS`):** `LISTENER_CONFIRMATIONS` configures the scan block lag behind the latest tip (e.g., 64 blocks on Polygon). This ensures high confidence against common shallow reorganizations, but is **not** an absolute mathematical proof against deep chain reorgs (> 64 blocks). Deep reorg handling requires operator validation against confirmed canonical RPC receipts.

---

## 5. Credential Handling & Zero-Custody Security

1. **No Cleartext Secrets:** Never paste Polymarket CLOB API keys, secrets, passphrases, or private keys into terminal transcripts, pull request reviews, chat windows, or Gemini prompt contexts.
2. **Encrypted Storage:** L2 API credentials entered in Settings (`/settings`) are encrypted in the application layer using authenticated AES-GCM (`encrypt_secret`) before storage in PostgreSQL (`live_wallet_links`).
3. **No Browser Private Keys:** The browser UI must **never** prompt for or store a user's private key. Baleen order submission is designed to rely on scoped authorization signatures or dedicated signing modules, not browser-held private keys.
4. **Reachability vs Authorization:** Successfully testing connection to the CLOB private REST API confirms reachability and credential syntax only. It does **not** certify that the signer address is authorized to bind orders or withdraw funds.

---

## 6. Sandbox Reset Procedures

When resetting or restarting a simulation environment:

1. **Procedure Reference:** Consult [`GEMINI_FRESH_SANDBOX_INSTRUCTIONS.md`](file:///c:/Users/arthu/repos/Baleen/GEMINI_FRESH_SANDBOX_INSTRUCTIONS.md) for full clean-room reset steps.
2. **Paper Isolation:** A paper sandbox reset (via `ResetSandboxModal` or `POST /api/executions/reset-sandbox`) clears past paper fills and resets mark-to-market performance curves.
3. **Exchange Safety:** A paper reset **never** affects real exchange balances, does **not** cancel orders on Polymarket CLOB, and does **not** require dropping the production Supabase or PostgreSQL database.
4. **Zero Account Resets:** Never run destructive database resets (`DROP TABLE`, `TRUNCATE users`, or Supabase dashboard project deletion) during routine operation.

---

## 7. Incident Response & Kill-Switch Runbook

If anomalous order behavior, desynchronized fills, or pricing feed failures occur:

### Step 1: Disable Execution (Emergency Stop)
Immediately disable order submission across all live accounts:
```bash
# Programmatic disable
python -c "import asyncio; from app.database import get_db; from app.api.live_trading import _disable_order_account; ..."
```
Or toggle live execution off in Settings or database:
```sql
UPDATE live_execution_accounts SET enabled = FALSE;
```

### Step 2: Retain State & Pending Reservations
- **Do NOT flush or delete records:** Preserving order intents and cash reservations is mandatory for reconciliation.
- In-flight orders transmitted to Polymarket CLOB may have been matched even if an HTTP connection timed out.
- Cash reservations (`reserved_cash`) prevent double-spending while orders remain unconfirmed.

### Step 3: Inspect Reconciliation Status
Query pending intents:
```sql
SELECT id, user_id, token_id, side, state, quantity, filled_quantity, limit_price, created_at, updated_at
FROM live_order_intents
WHERE state IN ('PENDING', 'SUBMITTED')
ORDER BY created_at DESC;
```

### Step 4: Unknown Order Outcomes (No Blind Retries)
> [!CAUTION]
> **NEVER blindly resend an order that experienced an HTTP timeout or network disconnect.**
> Retrying an unconfirmed order will cause catastrophic duplicate order placement.

1. Query Polymarket CLOB order endpoint using the original client order ID:
   ```bash
   # Inspect order status directly via CLOB gateway with authenticated request
   ```
2. If confirmed filled on exchange: record the fill in `live_order_journal` and release the reservation.
3. If confirmed cancelled/rejected on exchange: cancel the local intent and release the cash reservation.
4. If unknown: keep the intent marked as uncertain until exchange reconciliation confirms the terminal state.
