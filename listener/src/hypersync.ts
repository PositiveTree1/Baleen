import { POLYGON_HYPERSYNC_URL, ALL_EXCHANGE_ADDRESSES, ORDER_FILLED_TOPIC, ALL_ORDER_FILLED_TOPICS } from './constants';
import { parseOrderFilledLog } from './event-processor';
import { saveCheckpoint } from './checkpoint';
import { config } from './config';
import { OrderFilledEvent } from './types';

export interface IHyperSyncClient {
  get(query: any): Promise<{ data: { logs: any[]; blocks?: any[] }; nextBlock?: number }>;
  getHeight(): Promise<number>;
}

class HyperSyncHttpClient implements IHyperSyncClient {
  private url: string;
  private apiToken: string;

  constructor(url: string, apiToken: string = '') {
    this.url = url;
    this.apiToken = apiToken;
  }

  async getHeight(): Promise<number> {
    try {
      const res = await fetch(`${this.url}/height`, {
        headers: this.apiToken ? { Authorization: `Bearer ${this.apiToken}` } : {},
      });
      if (res.ok) {
        const json: any = await res.json();
        const height = json.height ?? json.block_number ?? json.last_block;
        if (Number.isSafeInteger(height) && height >= 0) return height;
      }
    } catch {
      // Ignore network errors on fallback
    }

    // Fallback: Query public Polygon RPC endpoints
    const rpcEndpoints = [
      'https://polygon-bor-rpc.publicnode.com',
      'https://polygon-rpc.com',
    ];
    for (const endpoint of rpcEndpoints) {
      try {
        const rpcRes = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ jsonrpc: '2.0', method: 'eth_blockNumber', params: [], id: 1 }),
        });
        if (rpcRes.ok) {
          const rpcData: any = await rpcRes.json();
          if (rpcData && rpcData.result) {
            const height = parseInt(rpcData.result, 16);
            if (Number.isSafeInteger(height) && height > 0) return height;
          }
        }
      } catch {
        // Try next fallback
      }
    }

    throw new Error('Source height unavailable');
  }

  async get(query: any): Promise<{ data: { logs: any[]; blocks?: any[] }; nextBlock?: number }> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (this.apiToken) {
      headers['Authorization'] = `Bearer ${this.apiToken}`;
    }

    const payload = {
      from_block: query.fromBlock || query.from_block || 0,
      to_block: query.toBlock,
      logs: (query.logs || []).map((l: any) => ({
        address: l.address,
        topics: l.topics,
      })),
      field_selection: {
        block: ['number', 'hash', 'timestamp'],
        log: [
          'address',
          'topic0',
          'topic1',
          'topic2',
          'topic3',
          'data',
          'block_number',
          'block_hash',
          'transaction_hash',
          'log_index',
        ],
      },
    };

    const res = await fetch(`${this.url}/query`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`HyperSync HTTP query failed with status ${res.status}: ${res.statusText}`);
    }

    const json = await res.json();
    const rawLogs = json.data?.logs || (Array.isArray(json.data) ? json.data.flatMap((d: any) => d.logs || []) : []);
    const blocks = json.data?.blocks || (Array.isArray(json.data) ? json.data.flatMap((d: any) => d.blocks || []) : []);
    const normalizedLogs = rawLogs.map((l: any) => ({
      address: l.address || l.Address,
      topics: [l.topic0 || l.Topic0, l.topic1 || l.Topic1, l.topic2 || l.Topic2, l.topic3 || l.Topic3].filter(Boolean),
      data: l.data || l.Data,
      blockNumber: l.block_number ?? l.blockNumber ?? l.BlockNumber ?? 0,
      blockHash: l.block_hash ?? l.blockHash,
      transactionHash: l.transaction_hash || l.transactionHash || l.TransactionHash || '0x',
      logIndex: l.log_index ?? l.logIndex ?? l.LogIndex ?? 0,
    }));

    return {
      data: { logs: normalizedLogs, blocks },
      nextBlock: json.next_block ?? json.nextBlock ?? query.fromBlock,
    };
  }
}

export function createHyperSyncClient(): IHyperSyncClient {
  try {
    const { HypersyncClient } = require('@envio-dev/hypersync-client');
    return new HypersyncClient({
      url: POLYGON_HYPERSYNC_URL,
      apiToken: config.ENVIO_API_KEY || '',
    });
  } catch (err) {
    return new HyperSyncHttpClient(POLYGON_HYPERSYNC_URL, config.ENVIO_API_KEY || '');
  }
}

export function buildQuery(fromBlock: number) {
  return {
    fromBlock,
    logs: [
      {
        address: ALL_EXCHANGE_ADDRESSES,
        topics: [ALL_ORDER_FILLED_TOPICS],
      },
    ],
    fieldSelection: {
      block: ['Number', 'Hash', 'Timestamp'],
      log: [
        'Address',
        'Topic0',
        'Topic1',
        'Topic2',
        'Topic3',
        'Data',
        'BlockNumber',
        'BlockHash',
        'TransactionHash',
        'LogIndex',
      ],
    },
  };
}

export async function streamEvents(
  client: IHyperSyncClient,
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
      // Delay execution until a configurable confirmation depth. Deep reorg
      // reconciliation still requires explicit operational handling.
      const confirmations = Number(process.env.LISTENER_CONFIRMATIONS || '128');
      if (!Number.isSafeInteger(confirmations) || confirmations < 1) throw new Error('Invalid confirmation depth');
      const confirmedEnd = (await client.getHeight()) - confirmations + 1;
      if (confirmedEnd <= currentBlock) {
        await new Promise(resolve => setTimeout(resolve, 4500));
        continue;
      }
      Object.assign(query, { toBlock: confirmedEnd });
      const res = await client.get(query as any);
      
      const logs = res.data.logs || [];
      for (const log of logs) {
        const block = res.data.blocks?.find((b: any) => (b.number ?? b.block_number) === log.blockNumber);
        const timestamp = block?.timestamp;
        const parsedEvent = parseOrderFilledLog({ ...log,
          blockHash: log.blockHash || block?.hash,
          blockTimestamp: timestamp == null ? undefined : Number(timestamp) * 1000 });
        await onEvent(parsedEvent);
      }

      const nextBlock = res.nextBlock;
      if (nextBlock && nextBlock > currentBlock && nextBlock <= confirmedEnd) {
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
