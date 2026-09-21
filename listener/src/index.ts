import { config } from './config';
import { getResumeBlock, saveCheckpoint } from './checkpoint';
import { createHyperSyncClient, streamEvents } from './hypersync';
import { matchesBasketWallets } from './event-processor';
import { enqueueSignal, drainQueue } from './queue';

async function fetchBasketWallets(retries = 5, backoffMs = 2000): Promise<Set<string>> {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const url = `${config.BACKEND_URL}/api/signals/watched-wallets`;
      const headers: Record<string, string> = {};
      if (config.LISTENER_SERVICE_KEY) headers['X-Service-Key'] = config.LISTENER_SERVICE_KEY;
      const res = await fetch(url, { headers, signal: AbortSignal.timeout(8000) });
      if (res.ok) {
        const wallets: any[] = await res.json();
        const set = new Set<string>(wallets.map(w => (w.address || w).toLowerCase()));
        return set;
      } else {
        throw new Error(`Watched-wallet request failed: HTTP ${res.status}`);
      }
    } catch (e: any) {
      if (attempt === retries) {
        console.warn(`[WARN] Failed to fetch basket wallets after ${retries} attempts: ${e?.message || e}`);
      } else {
        console.log(`[INFO] Backend not ready yet (${e?.message || 'waiting'}), retrying in ${backoffMs / 1000}s...`);
        await new Promise(r => setTimeout(r, backoffMs));
        backoffMs *= 1.5;
      }
    }
  }
  throw new Error('Cannot load the server-owned watched-wallet list');
}

async function main() {
  console.log('Starting Baleen Signal Listener...');
  console.log(`Connecting to Backend at: ${config.BACKEND_URL}`);
  
  let basketWallets = await fetchBasketWallets(6, 2000);
  console.log(`Loaded ${basketWallets.size} basket wallets.`);

  const client = createHyperSyncClient();
  let startBlock = getResumeBlock();
  const checkpointResponse = await fetch(`${config.BACKEND_URL}/api/signals/checkpoint`, {
    headers: { 'X-Service-Key': config.LISTENER_SERVICE_KEY }, signal: AbortSignal.timeout(8000)
  });
  if (!checkpointResponse.ok) throw new Error(`Cannot read durable cursor: HTTP ${checkpointResponse.status}`);
  const checkpoint: any = await checkpointResponse.json();
  if (!Number.isSafeInteger(checkpoint.deliveredBlock) || checkpoint.deliveredBlock < 0) throw new Error('Invalid durable cursor');
  if (checkpoint.deliveredBlock > 0) startBlock = startBlock ? Math.min(startBlock, checkpoint.deliveredBlock) : checkpoint.deliveredBlock;
  try {
    const currentHeight = await client.getHeight();
    if (!startBlock) {
      startBlock = Math.max(1, currentHeight - 500);
      console.log(`[INFO] First run: starting at recent chain height ${startBlock} (tip is ${currentHeight})`);
    } else if (currentHeight - startBlock > 5000) {
      console.warn(`[WARN] Large block lag detected: catching up from block ${startBlock} (${currentHeight - startBlock} blocks behind tip ${currentHeight})`);
    } else {
      console.log(`Resuming from block: ${startBlock} (tip is ${currentHeight})`);
    }
  } catch (e: any) {
    console.warn(`[WARN] Could not fetch chain height, starting from ${startBlock || 'tip'}: ${e?.message || e}`);
    if (!startBlock) throw new Error('Cannot initialize cursor without verified chain height');
  }

  let eventsProcessed = 0;
  // Local state may be ahead of the backend after an ephemeral queue loss.
  // Never advertise that abandoned cursor as delivered before replaying it.
  saveCheckpoint(startBlock);
  let matchesFound = 0;
  let draining = false;
  let deliveredBlock = checkpoint.deliveredBlock;
  const deliver = async () => {
    if (draining) return;
    draining = true;
    const candidate = getResumeBlock();
    try {
      const result = await drainQueue();
      if (result.remaining === 0) deliveredBlock = Math.max(deliveredBlock, candidate);
    } finally { draining = false; }
  };
  await deliver();
  setInterval(() => { void deliver().catch(console.error); }, 5000);

  setInterval(() => {
    console.log(`Stats - Events: ${eventsProcessed}, Matches: ${matchesFound}, Block: ${getResumeBlock()}`);
    // Send heartbeat to backend
    const hbHeaders: Record<string, string> = { 'Content-Type': 'application/json' };
    if (config.LISTENER_SERVICE_KEY) {
      hbHeaders['X-Service-Key'] = config.LISTENER_SERVICE_KEY;
    }
    fetch(`${config.BACKEND_URL}/api/admin/heartbeat`, {
      method: 'POST',
      headers: hbHeaders,
      body: JSON.stringify({
        eventsProcessed,
        matchesFound,
        block: getResumeBlock(),
        deliveredBlock,
        timestamp: Date.now()
      })
    }).then(res => {
      if (!res.ok) console.error(`Listener heartbeat rejected: HTTP ${res.status}`);
    }).catch(error => console.error('Listener heartbeat failed:', error.message));
  }, 15000);

  await streamEvents(client, startBlock, async (event) => {
    eventsProcessed++;
    const signals = matchesBasketWallets(event, basketWallets);
    
    for (const signal of signals) {
      matchesFound++;
      console.log('Match found!', signal);
      await enqueueSignal(signal);
    }
  }, async () => { basketWallets = await fetchBasketWallets(1, 0); });

  console.log('Listener shut down.');
}

if (require.main === module) {
  main().catch(error => {
    console.error('Fatal listener failure:', error);
    process.exit(1);
  });
}
