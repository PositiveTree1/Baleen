import { HypersyncClient } from '@envio-dev/hypersync-client';
import { POLYGON_HYPERSYNC_URL, ALL_EXCHANGE_ADDRESSES, ORDER_FILLED_TOPIC } from './constants';
import { parseOrderFilledLog } from './event-processor';
import { saveCheckpoint } from './checkpoint';
import { config } from './config';
import { OrderFilledEvent } from './types';

export function createHyperSyncClient(): HypersyncClient {
  return new HypersyncClient({
    url: POLYGON_HYPERSYNC_URL,
    apiToken: config.ENVIO_API_KEY || "",
  });
}

export function buildQuery(fromBlock: number) {
  return {
    fromBlock,
    logs: [
      {
        address: ALL_EXCHANGE_ADDRESSES,
        topics: [[ORDER_FILLED_TOPIC]],
      },
    ],
    fieldSelection: {
      log: [
        'Address',
        'Topic0',
        'Topic1',
        'Topic2',
        'Topic3',
        'Data',
        'BlockNumber',
        'TransactionHash',
        'LogIndex',
      ],
    },
  };
}

export async function streamEvents(
  client: HypersyncClient,
  fromBlock: number,
  onEvent: (event: OrderFilledEvent) => Promise<void>
) {
  let currentBlock = fromBlock;
  let isRunning = true;

  process.on('SIGINT', () => { isRunning = false; });
  process.on('SIGTERM', () => { isRunning = false; });

  while (isRunning) {
    try {
      const query = buildQuery(currentBlock);
      const res = await client.get(query as any);
      
      const logs = res.data.logs || [];
      for (const log of logs) {
        const parsedEvent = parseOrderFilledLog(log);
        await onEvent(parsedEvent);
      }

      const nextBlock = res.nextBlock;
      if (nextBlock && nextBlock > currentBlock) {
        currentBlock = nextBlock;
        saveCheckpoint(currentBlock);
        // Safe rate-limiting pause between catch-up queries to strictly stay well under 30 req/5s free limit
        await new Promise(resolve => setTimeout(resolve, 1600));
      } else {
        // At the chain tip, poll every 4.5 seconds (well within rate limit)
        await new Promise(resolve => setTimeout(resolve, 4500));
      }
    } catch (err: any) {
      console.error('Error in hypersync stream:', err?.message || err);
      // If error occurs (e.g. rate limit exhausted), wait 10 seconds before retrying
      await new Promise(resolve => setTimeout(resolve, 10000));
    }
  }
}
