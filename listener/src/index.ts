import { config } from './config';
import { getResumeBlock } from './checkpoint';
import { createHyperSyncClient, streamEvents } from './hypersync';
import { matchesBasketWallet } from './event-processor';
import { enqueueSignal, postSignalToBackend } from './queue';

async function fetchBasketWallets(): Promise<Set<string>> {
  try {
    const res = await fetch(`${config.BACKEND_URL}/api/wallets?status=active`);
    if (res.ok) {
      const wallets: any[] = await res.json();
      return new Set(wallets.map(w => (w.address || w).toLowerCase()));
    }
  } catch (e) {
    console.error('Failed to fetch basket wallets, using empty set', e);
  }
  return new Set();
}

async function main() {
  console.log('Starting Baleen Signal Listener...');
  
  let basketWallets = await fetchBasketWallets();
  console.log(`Loaded ${basketWallets.size} basket wallets.`);

  const startBlock = getResumeBlock() || 50000000;
  console.log(`Resuming from block: ${startBlock}`);

  const client = createHyperSyncClient();

  let eventsProcessed = 0;
  let matchesFound = 0;

  setInterval(async () => {
    basketWallets = await fetchBasketWallets();
  }, 60000);

  setInterval(() => {
    console.log(`Stats - Events: ${eventsProcessed}, Matches: ${matchesFound}, Block: ${getResumeBlock()}`);
  }, 10000);

  await streamEvents(client, startBlock, async (event) => {
    eventsProcessed++;
    const signal = matchesBasketWallet(event, basketWallets);
    
    if (signal) {
      matchesFound++;
      console.log('Match found!', signal);
      await enqueueSignal(signal);
      // await postSignalToBackend(signal); // Optionally enable posting directly
    }
  });

  console.log('Listener shut down.');
}

if (require.main === module) {
  main().catch(console.error);
}
