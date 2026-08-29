# Ingestion Listener & Envio HyperSync Pipeline Survey Report

**Document**: Handoff Survey Report — Ingestion Listener & HyperSync Pipeline  
**Author**: Explorer Agent (`explorer_listener`)  
**Target Repository**: `c:\Users\arthu\Documents\Baleen-master`  
**Date**: 2026-08-29  

---

## 1. Observation

Direct examination of the entire `listener/` module and connected backend ingestion services revealed the following inventory, configurations, code implementations, and operational characteristics:

### 1.1 File & Module Inventory

| File Path | Type | Purpose | Core Classes / Functions / Exports |
| :--- | :--- | :--- | :--- |
| `listener/package.json` | Config | Node package manifest, scripts (`build`, `start`, `dev`, `test`), dependencies | Dependencies: `@envio-dev/hypersync-client`, `dotenv`, `ethers`; Dev: `jest`, `ts-jest`, `typescript` |
| `listener/tsconfig.json` | Config | TypeScript compiler configuration | Target: `ES2022`, Module: `NodeNext`, `strict: true`, `outDir: ./dist` |
| `listener/jest.config.js` | Config | Jest test runner configuration | Preset: `ts-jest`, testEnvironment: `node`, match: `**/tests/**/*.test.ts` |
| `listener/src/constants.ts` | Source | Contract addresses and event topic constants | `POLYGON_HYPERSYNC_URL`, `CTF_EXCHANGE_V1`, `NEGRISK_CTF_EXCHANGE_V1`, `CTF_EXCHANGE_V2`, `ORDER_FILLED_TOPIC`, `ALL_EXCHANGE_ADDRESSES` |
| `listener/src/types.ts` | Source | TypeScript interfaces for events, signals, and checkpoints | `OrderFilledEvent`, `WhaleTradeSignal`, `Checkpoint` |
| `listener/src/config.ts` | Source | Environment variable loader (`dotenv`) and runtime configs | `config.ENVIO_API_KEY`, `config.DATABASE_URL`, `config.BACKEND_URL` |
| `listener/src/checkpoint.ts` | Source | File-based block checkpoint persistence | `saveCheckpoint(blockNumber)`, `getResumeBlock()` |
| `listener/src/queue.ts` | Source | Local signal queueing, deduplication set, backend HTTP dispatcher | `enqueueSignal(signal)`, `dequeueSignals(limit)`, `postSignalToBackend(signal)` |
| `listener/src/hypersync.ts` | Source | Envio HyperSync client initialization, HTTP fallback client, event polling loop | `IHyperSyncClient`, `HyperSyncHttpClient`, `createHyperSyncClient()`, `buildQuery(fromBlock)`, `streamEvents(...)` |
| `listener/src/event-processor.ts`| Source | ABI decoding of `OrderFilled` events, whale basket matching | `parseOrderFilledLog(log)`, `matchesBasketWallet(event, basketAddresses)` |
| `listener/src/index.ts` | Source | Main service entry point, basket syncing, heartbeat loop, startup block logic | `fetchBasketWallets()`, `main()` |
| `listener/tests/envio.test.ts` | Test | Unit tests for query builder, checkpointing, and client instantiation | 3 Jest tests (`buildQuery`, `checkpoint`, `createHyperSyncClient`) |

---

### 1.2 Verbatim Code Observations & Ingestion Mechanics

#### A. Event Decoding & Topic Extraction (`listener/src/event-processor.ts#L6-L50`)
```typescript
6: export function parseOrderFilledLog(log: any): OrderFilledEvent {
7:   const orderHash = log.topics[1] || '0x';
8:   
9:   const makerTopic = log.topics[2] || '0x';
10:   const maker = makerTopic.length >= 66 ? '0x' + makerTopic.slice(26) : '0x';
11: 
12:   const takerTopic = log.topics[3] || '0x';
13:   const taker = takerTopic.length >= 66 ? '0x' + takerTopic.slice(26) : '0x';
14: 
15:   let makerAssetId = '0';
16:   let takerAssetId = '0';
17:   let makerAmountFilled = '0';
18:   let takerAmountFilled = '0';
19:   let fee = '0';
20: 
21:   if (log.data && log.data !== '0x') {
22:     try {
23:       const decoded = abiCoder.decode(
24:         ['uint256', 'uint256', 'uint256', 'uint256', 'uint256'],
25:         log.data
26:       );
27:       makerAssetId = decoded[0].toString();
28:       takerAssetId = decoded[1].toString();
29:       makerAmountFilled = decoded[2].toString();
30:       takerAmountFilled = decoded[3].toString();
31:       fee = decoded[4].toString();
32:     } catch (e) {
33:       console.error('Failed to decode log data', e);
34:     }
35:   }
```

#### B. Whale Matching, Side Determination, Price and Timestamp (`listener/src/event-processor.ts#L52-L96`)
```typescript
52: export function matchesBasketWallet(
53:   event: OrderFilledEvent,
54:   basketAddresses: Set<string>
55: ): WhaleTradeSignal | null {
56:   const makerLower = event.maker.toLowerCase();
57:   const takerLower = event.taker.toLowerCase();
58:   
59:   const isMakerBasket = basketAddresses.has(makerLower);
60:   const isTakerBasket = basketAddresses.has(takerLower);
61: 
62:   if (!isMakerBasket && !isTakerBasket) {
63:     return null;
64:   }
65: 
66:   let side: 'BUY' | 'SELL';
67:   let walletAddress: string;
68:   let assetId: string;
69:   let amountFilled: string;
70: 
71:   if (isTakerBasket) {
72:     side = 'BUY';
73:     walletAddress = takerLower;
74:     assetId = event.makerAssetId;
75:     amountFilled = event.makerAmountFilled;
76:   } else {
77:     side = 'SELL';
78:     walletAddress = makerLower;
79:     assetId = event.makerAssetId;
80:     amountFilled = event.makerAmountFilled;
81:   }
82: 
83:   const price = '0'; // Placeholder
84: 
85:   return {
86:     walletAddress,
87:     side,
88:     assetId,
89:     amountFilled,
90:     price,
91:     transactionHash: event.transactionHash,
92:     logIndex: event.logIndex,
93:     blockNumber: event.blockNumber,
94:     timestamp: Date.now(),
95:   };
96: }
```

#### C. Backend Ingestion Consumer (`backend/app/services/live_poller.py#L400-L429`)
```python
400:     async def process_onchain_signal(
401:         self,
402:         wallet_address: str,
403:         side: str,
404:         asset_id: str,
405:         amount_filled: str,
406:         price_str: str,
407:         tx_hash: str,
408:         log_index: int,
409:         block_number: int,
410:         timestamp_ms: Optional[int] = None
411:     ):
412:         """Handler for on-chain Envio HyperSync events."""
413:         ts_sec = (timestamp_ms / 1000.0) if timestamp_ms else datetime.utcnow().timestamp()
414:         
415:         # Real-time guard
416:         if ts_sec < self.started_at:
417:             return
...
424:         try:
425:             price = float(price_str) if price_str and float(price_str) > 0 else 0.5
426:             amount = float(amount_filled) / 1e6 if float(amount_filled) > 1e10 else float(amount_filled)
427:             cash_usd = max(amount * price, 20.0)
428:             dt = datetime.fromtimestamp(ts_sec, timezone.utc).replace(tzinfo=None)
```

#### D. Queue Implementation & File I/O Concurrency (`listener/src/queue.ts#L6-L33`)
```typescript
6: const QUEUE_FILE = path.join(__dirname, '../queue.jsonl');
7: const processedKeys = new Set<string>();
8: 
9: export async function enqueueSignal(signal: WhaleTradeSignal): Promise<void> {
10:   const key = `${signal.transactionHash}:${signal.logIndex}`;
11:   if (processedKeys.has(key)) {
12:     return;
13:   }
14:   
15:   processedKeys.add(key);
16:   const line = JSON.stringify(signal) + '\n';
17:   await fs.promises.appendFile(QUEUE_FILE, line, 'utf-8');
18: }
19: 
20: export async function dequeueSignals(limit: number): Promise<WhaleTradeSignal[]> {
21:   if (!fs.existsSync(QUEUE_FILE)) {
22:     return [];
23:   }
24:   
25:   const content = await fs.promises.readFile(QUEUE_FILE, 'utf-8');
26:   const lines = content.trim().split('\n').filter(Boolean);
27:   
28:   const toProcess = lines.slice(0, limit);
29:   const remaining = lines.slice(limit);
30:   
31:   await fs.promises.writeFile(QUEUE_FILE, remaining.join('\n') + (remaining.length > 0 ? '\n' : ''), 'utf-8');
32:   return toProcess.map(line => JSON.parse(line));
33: }
```

#### E. Startup Block Clamping & Catch-Up Policy (`listener/src/index.ts#L40-L52`)
```typescript
40:   let startBlock = getResumeBlock();
41:   try {
42:     const currentHeight = await client.getHeight();
43:     if (!startBlock || (currentHeight - startBlock > 5000)) {
44:       startBlock = Math.max(1, currentHeight - 500);
45:       console.log(`[INFO] Starting at recent chain height: ${startBlock} (tip is ${currentHeight})`);
46:     } else {
47:       console.log(`Resuming from block: ${startBlock} (tip is ${currentHeight})`);
48:     }
49:   } catch (e: any) {
50:     console.warn(`[WARN] Could not fetch chain height, starting from ${startBlock || 'tip'}: ${e?.message || e}`);
51:     if (!startBlock) startBlock = 68000000;
52:   }
```

---

## 2. Logic Chain

From the observations above, the end-to-end data flow, execution mechanics, and systemic vulnerabilities are derived through the following logic steps:

### 2.1 Complete Ingestion Pipeline Architecture & Data Flow

```
[ Polygon Blockchain ]
         │
         ▼
[ Envio HyperSync Gateway ] (https://polygon.hypersync.xyz)
         │  (Filtered by CTF Exchange addresses & OrderFilled topic0)
         ▼
[ HyperSync Client / Polling Loop ] (`listener/src/hypersync.ts:streamEvents`)
         │  (Fetches batches of logs; rate-limited 1.6s catch-up / 4.5s tip)
         ▼
[ ABI Event Decoder ] (`listener/src/event-processor.ts:parseOrderFilledLog`)
         │  (Decodes topics 1..3 and data 5x uint256 into OrderFilledEvent)
         ▼
[ Whale Basket Filter & Signal Builder ] (`listener/src/event-processor.ts:matchesBasketWallet`)
         │  (Checks against active basket Set refreshed every 60s from Backend)
         ├──► [ Local Disk Queue ] (`listener/src/queue.ts:enqueueSignal` -> queue.jsonl)
         └──► [ HTTP Dispatcher ] (`listener/src/queue.ts:postSignalToBackend` -> POST /api/signals)
                                                 │
                                                 ▼
                              [ Backend FastAPI Server ] (`backend/app/api/signals.py`)
                                                 │
                                                 ▼ (BackgroundTasks)
                              [ Live Trade Mirror Engine ] (`backend/app/services/live_poller.py:process_onchain_signal`)
                                                 │
                                                 ▼
                              [ Fee / Slippage / Cash / Sniper Simulation & Paper Execution ] (`process_trade_fill`)
```

---

### 2.2 Detailed Failure Mechanics & Impact Analysis

#### 1. CRITICAL: Hardcoded `'0'` Price Enforcing Arbitrary 0.50 Synthetic Default
- **Observation Reference**: `listener/src/event-processor.ts#L83`, `backend/app/services/live_poller.py#L425`
- **Logic Chain**:
  1. `matchesBasketWallet` explicitly hardcodes `const price = '0'; // Placeholder`.
  2. The resulting signal payload has `price: "0"`.
  3. When `backend/app/api/signals.py` receives `price: "0"`, it delegates to `process_onchain_signal`.
  4. In `live_poller.py:425`, `float(price_str) > 0` evaluates to `False` (0 is not > 0).
  5. The backend falls back to `price = 0.50` (50 cents).
  6. **Impact**: Every real-world on-chain whale trade (whether executed at 95 cents or 5 cents) is ingested into the paper trading simulation at exactly 50 cents. This distorts fill simulation, EV gates, slippage calculations, drawdown modeling, and Kelly sizing.

#### 2. CRITICAL: Inverted Trade Side & Corrupted Asset IDs for CTF Maker/Taker Trades
- **Observation Reference**: `listener/src/event-processor.ts#L71-L81`
- **Logic Chain**:
  1. Polymarket CTF exchange executes bilateral token swaps between USDC (`assetId = 0` or collateral) and ERC1155 outcome tokens.
  2. If a Whale maker places a resting limit bid (Maker offers USDC `makerAssetId = 0`, requesting outcome token `takerAssetId = outcomeTokenId`), when filled:
     - The whale is **BUYING** outcome tokens.
     - But `matchesBasketWallet` evaluates `else { side = 'SELL'; assetId = event.makerAssetId; }`.
     - It marks the trade as a **`SELL`** of asset `"0"` (USDC)!
  3. If a Whale taker market-sells outcome shares (Taker offers outcome token `takerAssetId = outcomeTokenId`, requesting USDC `makerAssetId = 0`):
     - The whale is **SELLING** outcome tokens.
     - But `matchesBasketWallet` evaluates `if (isTakerBasket) { side = 'BUY'; assetId = event.makerAssetId; }`.
     - It marks the trade as a **`BUY`** of asset `"0"` (USDC)!
  4. Furthermore, in both maker and taker branches, `assetId` is hardcoded to `event.makerAssetId`. Whenever `makerAssetId` is USDC (`0`), `assetId` is passed as `"0"`, preventing the backend from resolving the prediction market condition ID.
  5. **Impact**: Whales buying shares are simulated as selling, whales selling shares are simulated as buying, and asset IDs are corrupted to `"0"` in half of all trade types.

#### 3. HIGH: Wall-Clock `Date.now()` Timestamp Breaking Historical Replay & Real-Time Guards
- **Observation Reference**: `listener/src/event-processor.ts#L94`, `backend/app/services/live_poller.py#L413-L417`
- **Logic Chain**:
  1. `matchesBasketWallet` constructs the signal with `timestamp: Date.now()`.
  2. When the listener resumes and processes 500 past blocks (representing ~15-20 minutes of blockchain history), each past trade is assigned the current system timestamp.
  3. In `live_poller.py`, the backend checks `if ts_sec < self.started_at: return` to prevent historical re-execution.
  4. Because `timestamp_ms` is `Date.now()`, `ts_sec >= started_at` is always true.
  5. **Impact**: Catch-up trades from 15 minutes ago immediately execute in paper trading as if they were instantaneous live signals, creating severe lookahead bias and stale order book executions.

#### 4. HIGH: 5,000 Block Silent Discard Window on Restart
- **Observation Reference**: `listener/src/index.ts#L43-L46`
- **Logic Chain**:
  1. Polygon produces a block every ~2 seconds (43,200 blocks/day; 5,000 blocks ≈ 2.7 hours).
  2. If the listener process is stopped or restarted after a maintenance window or outage > 2.7 hours, `currentHeight - startBlock > 5000` evaluates to true.
  3. The listener clamps `startBlock = Math.max(1, currentHeight - 500)`.
  4. **Impact**: All blockchain events between `startBlock` and `currentHeight - 500` (up to tens of thousands of blocks) are silently discarded without logging missing ranges or alerting administrators.

#### 5. HIGH: File Queue Concurrency Race Condition & Dead Storage Leak
- **Observation Reference**: `listener/src/queue.ts#L20-L33`, `listener/src/index.ts#L83`
- **Logic Chain**:
  1. `enqueueSignal` calls `fs.promises.appendFile(QUEUE_FILE, line)`.
  2. `dequeueSignals` reads the whole file (`readFile`), splits lines, slices `limit`, and writes the remaining content back (`writeFile`).
  3. If an event is appended during `readFile` and `writeFile`, the new event is overwritten and permanently lost.
  4. Furthermore, `dequeueSignals` is never called anywhere in the codebase. `enqueueSignal` is called on every match, causing `queue.jsonl` to grow indefinitely on disk.

#### 6. MEDIUM: Unbounded Memory Leak in In-Memory Deduplication Set
- **Observation Reference**: `listener/src/queue.ts#L7`
- **Logic Chain**:
  1. `const processedKeys = new Set<string>();` is instantiated at module scope.
  2. Every matching transaction hash and log index is added with `processedKeys.add(key)`.
  3. Keys are never purged, TTL-expired, or capped with an LRU cache.
  4. **Impact**: In a high-volume live environment, the process memory footprint will monotonically increase until node V8 heap exhaustion or process OOM crash.

#### 7. MEDIUM: Non-Atomic Synchronous Checkpoint Persistence
- **Observation Reference**: `listener/src/checkpoint.ts#L7-L13`
- **Logic Chain**:
  1. `saveCheckpoint` executes `fs.writeFileSync(CHECKPOINT_FILE, JSON.stringify(checkpoint, null, 2))`.
  2. If the Node.js process is terminated (SIGKILL, OOM, container restart) during the write operation, `checkpoint.json` is left in an empty (0 bytes) or corrupted JSON state.
  3. On restart, `getResumeBlock()` catches the JSON parse exception, logs an error, and returns block `0`.
  4. On block `0`, `startBlock` clamps to `currentHeight - 500`, losing historical resume continuity.

#### 8. MEDIUM: Zero-Retry HTTP Forwarding
- **Observation Reference**: `listener/src/queue.ts#L35-L49`
- **Logic Chain**:
  1. `postSignalToBackend` performs a single `fetch()` to `${config.BACKEND_URL}/api/signals`.
  2. If the backend is restarting, cold-starting on Render, or returns 502/503/500, `response.ok` is false.
  3. The function logs `Failed to post signal to backend` and exits. The signal is never retried or queued for re-dispatch.

#### 9. LOW/MEDIUM: Hardcoded Polygon Block Height Fallback (68,000,000)
- **Observation Reference**: `listener/src/hypersync.ts#L34`
- **Logic Chain**:
  1. `HyperSyncHttpClient.getHeight()` defaults to `68000000` on network error.
  2. Polygon PoS block height is continuously increasing (~75M+).
  3. If network fails during initial height query, the listener may attempt queries from an obsolete block height.

---

## 3. Caveats

1. **Host Environment Node.js Availability**: Node.js and `npm` are not present in the Windows system environment PATH of this specific agent runner, so live runtime execution of `npm test` or `ts-node` was not possible directly on this host. However, all source code and test code were fully inspected statically.
2. **Envio Cloud Endpoints**: Live query responsiveness of `https://polygon.hypersync.xyz` is subject to Envio Cloud free tier rate limits (30 requests per 5 seconds). The code incorporates a 1.6s delay in catch-up mode and 4.5s delay at the chain tip.
3. **Database Schema Direct Writes**: `listener/src/config.ts` defines `DATABASE_URL`, but the listener codebase contains no direct PostgreSQL client (e.g. `pg` or `prisma`). All data forwarding is performed via HTTP to the backend API (`/api/signals` and `/api/admin/heartbeat`).

---

## 4. Conclusion

The Baleen Signal Listener (`listener/`) provides a clean architectural foundation with HyperSync native/HTTP fallback streaming and backend HTTP forwarding. However, the survey identified **two Critical mathematical/logic bugs and multiple High-severity reliability risks** that directly undermine paper trading realism and pipeline stability:

### Summary of Audit Findings by Severity

| ID | Title | Severity | Location | Primary Impact |
| :--- | :--- | :--- | :--- | :--- |
| **LST-01** | Hardcoded `'0'` Price Enforcing 0.50 Synthetic Default Fill | **CRITICAL** | `listener/src/event-processor.ts#L83` | Distorts all on-chain trade prices to $0.50 in simulation |
| **LST-02** | Inverted Trade Side & Asset ID Corruption (Maker vs Taker) | **CRITICAL** | `listener/src/event-processor.ts#L71-L81` | Inverts BUY/SELL signals; corrupts assetId to `"0"` |
| **LST-03** | Wall-Clock Timestamp Assigned to Historical Blocks | **HIGH** | `listener/src/event-processor.ts#L94` | Stale block catch-up bypasses real-time guards |
| **LST-04** | 5,000 Block Silent Discard Policy | **HIGH** | `listener/src/index.ts#L43-L46` | Silently drops whale signals after >2.7h downtime |
| **LST-05** | Queue File Race Condition & Dead Disk Accumulation | **HIGH** | `listener/src/queue.ts#L20-L33` | Data loss on concurrent dequeue; uncollected disk growth |
| **LST-06** | Unbounded Memory Leak in In-Memory Deduplication Set | **MEDIUM** | `listener/src/queue.ts#L7` | Memory leak over long-running deployments |
| **LST-07** | Non-Atomic Synchronous Checkpoint Persistence | **MEDIUM** | `listener/src/checkpoint.ts#L7-L13` | Checkpoint file corruption on unclean shutdown |
| **LST-08** | Zero-Retry HTTP Forwarding to Backend | **MEDIUM** | `listener/src/queue.ts#L35-L49` | Dropped signals during transient backend unreachability |
| **LST-09** | Outdated Hardcoded Fallback Block Height (68M) | **LOW** | `listener/src/hypersync.ts#L34` | Incorrect start block if height API temporarily fails |
| **LST-10** | 0% Unit Test Coverage on Core Event Matching Logic | **MEDIUM** | `listener/tests/envio.test.ts#L1-L38` | No regression test suite for decoding, prices, or sides |

---

### Key Remediation Recommendations

1. **Fix `matchesBasketWallet` Pricing and Asset Calculation**:
   - Parse `makerAssetId` vs `takerAssetId`: If `makerAssetId === '0'` (USDC), Maker is BUYING `takerAssetId` at `price = (makerAmountFilled / 1e6) / (takerAmountFilled / 1e6)`.
   - If `takerAssetId === '0'` (USDC), Taker is BUYING `makerAssetId` at `price = (takerAmountFilled / 1e6) / (makerAmountFilled / 1e6)`.
   - Calculate exact decimal price and pass accurate conditional token `assetId`.
2. **Propagate Block Timestamps**:
   - Extract block timestamp or approximate from block number (`blockTimestamp = blockNumber * 2.0 + genesisOffset`) rather than `Date.now()`.
3. **Atomic Checkpointing & LRU Cache**:
   - Write checkpoint to a temporary file (`checkpoint.json.tmp`) and atomically rename (`fs.renameSync`).
   - Replace unbounded `processedKeys = new Set()` with a bounded LRU/FIFO ring buffer (e.g. 50,000 keys).
4. **Retry Loop for Backend Forwarding**:
   - Implement exponential backoff retry in `postSignalToBackend` before giving up.
5. **Comprehensive Unit Tests**:
   - Expand `listener/tests/` to include full test suites for `parseOrderFilledLog`, `matchesBasketWallet` (both Maker and Taker BUY/SELL cases), and rate-limiting loops.

---

## 5. Verification Method

To independently verify all findings and test suite behavior:

1. **Static Code Inspection**:
   - Inspect `listener/src/event-processor.ts#L71-L96` to confirm price hardcoding (`'0'`), side assumption (`isTakerBasket ? 'BUY' : 'SELL'`), and timestamp assignment (`Date.now()`).
   - Inspect `backend/app/services/live_poller.py#L425` to confirm that incoming `price: "0"` forces the `price = 0.5` fallback.
   - Inspect `listener/src/queue.ts#L20-L33` and `listener/src/index.ts` to confirm `dequeueSignals` is never called and file writes are non-atomic.
2. **Unit Test Execution**:
   - In an environment with Node.js/npm installed:
     ```bash
     cd listener
     npm install
     npm test
     ```
   - Observe that `listener/tests/envio.test.ts` executes only 3 tests and contains no tests for `matchesBasketWallet` or `parseOrderFilledLog`.
3. **Backend Signal Verification**:
   - Run backend tests:
     ```bash
     cd backend
     pytest tests/test_signals_and_drawer.py
     ```
