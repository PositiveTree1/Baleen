import { config } from './config';
import { getResumeBlock } from './checkpoint';
import { createHyperSyncClient, streamEvents } from './hypersync';
import { matchesBasketWallet } from './event-processor';
import { enqueueSignal, postSignalToBackend } from './queue';

async function fetchBasketWallets(retries = 5, backoffMs = 2000): Promise<Set<string>> {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const url = `${config.BACKEND_URL}/api/wallets?status=active`;
      const res = await fetch(url, { signal: AbortSignal.timeout(8000) });
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
    if (!startBlock || (currentHeight - startBlock > 5000)) {
      startBlock = Math.max(1, currentHeight - 500);
      console.log(`[INFO] Starting at recent chain height: ${startBlock} (tip is ${currentHeight})`);
    } else {
      console.log(`Resuming from block: ${startBlock} (tip is ${currentHeight})`);
    }
  } catch (e: any) {
    console.warn(`[WARN] Could not fetch chain height, starting from ${startBlock || 'tip'}: ${e?.message || e}`);
    if (!startBlock) startBlock = 68000000;
  }

  let eventsProcessed = 0;
  let matchesFound = 0;

  setInterval(async () => {
    basketWallets = await fetchBasketWallets();
  }, 60000);

  setInterval(() => {
    console.log(`Stats - Events: ${eventsProcessed}, Matches: ${matchesFound}, Block: ${getResumeBlock()}`);
    // Send heartbeat to backend
    fetch(`${config.BACKEND_URL}/api/admin/heartbeat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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
    const signal = matchesBasketWallet(event, basketWallets);
    
    if (signal) {
      matchesFound++;
      console.log('Match found!', signal);
      await enqueueSignal(signal);
      await postSignalToBackend(signal);
    }
  });

  console.log('Listener shut down.');
}

if (require.main === module) {
  main().catch(console.error);
}
