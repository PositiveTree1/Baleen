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
      } else {
        await new Promise(resolve => setTimeout(resolve, 5000));
      }
    } catch (err) {
      console.error('Error in hypersync stream', err);
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
  }
}
