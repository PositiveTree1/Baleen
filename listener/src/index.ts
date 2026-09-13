import { config } from './config';
import { getResumeBlock } from './checkpoint';
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
        if (set.size > 0) {
          return set;
        }
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
  return new Set();
}

async function main() {
  console.log('Starting Baleen Signal Listener...');
  console.log(`Connecting to Backend at: ${config.BACKEND_URL}`);
  
  let basketWallets = await fetchBasketWallets(6, 2000);
  console.log(`Loaded ${basketWallets.size} basket wallets.`);

  const client = createHyperSyncClient();
  let startBlock = getResumeBlock();
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
  let matchesFound = 0;
  let draining = false;
  const deliver = async () => {
    if (draining) return;
    draining = true;
    try { await drainQueue(); } finally { draining = false; }
  };
  await deliver();
  setInterval(() => { void deliver().catch(console.error); }, 5000);

  setInterval(async () => {
    const updated = await fetchBasketWallets();
    // Retain monitored wallets for exits until a holdings-aware roster exists.
    for (const wallet of updated) basketWallets.add(wallet);
  }, 60000);

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
        timestamp: Date.now()
      })
    }).catch(() => {});
  }, 15000);

  await streamEvents(client, startBlock, async (event) => {
    eventsProcessed++;
    const signals = matchesBasketWallets(event, basketWallets);
    
    for (const signal of signals) {
      matchesFound++;
      console.log('Match found!', signal);
      await enqueueSignal(signal);
    }
  });

  console.log('Listener shut down.');
}

if (require.main === module) {
  main().catch(console.error);
}
