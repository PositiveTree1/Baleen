import fs from 'fs';
import os from 'os';
import path from 'path';
import { drainQueue, enqueueSignal, postSignalToBackend } from '../src/queue';
import { WhaleTradeSignal } from '../src/types';

const signal = (id: string): WhaleTradeSignal => ({
  walletAddress: '0x' + '1'.repeat(40), side: 'BUY', assetId: id,
  amountFilled: '1.000000', price: '0.5000', transactionHash: '0x' + id.padStart(64, '0'),
  logIndex: 0, blockNumber: 1, timestamp: 1,
});

describe('durable signal queue', () => {
  let dir: string;
  let file: string;
  const fetchMock = jest.fn();

  beforeEach(async () => {
    dir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'baleen-queue-'));
    file = path.join(dir, 'queue.jsonl');
    process.env.LISTENER_QUEUE_FILE = file;
    global.fetch = fetchMock as unknown as typeof fetch;
    fetchMock.mockReset();
  });
  afterEach(async () => {
    delete process.env.LISTENER_QUEUE_FILE;
    await fs.promises.rm(dir, { recursive: true, force: true });
  });

  it('requires accepted:true and retains 409, invalid ACK, and network failures', async () => {
    await enqueueSignal(signal('1'));
    await enqueueSignal(signal('2'));
    await enqueueSignal(signal('3'));
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({ accepted: true }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ accepted: false }), { status: 200 }))
      .mockResolvedValueOnce(new Response('', { status: 409 }));
    const result = await drainQueue();
    expect(result).toEqual({ delivered: 1, remaining: 2 });
    const remaining = (await fs.promises.readFile(file, 'utf8')).trim().split('\n').map(line => JSON.parse(line));
    expect(remaining.map((x: WhaleTradeSignal) => x.assetId)).toEqual(['2', '3']);
  });

  it('quarantines malformed lines instead of dropping them', async () => {
    await fs.promises.writeFile(file, '{malformed}\n' + JSON.stringify(signal('4')) + '\n');
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({ accepted: true }), { status: 201 }));
    expect((await drainQueue()).remaining).toBe(1);
    expect(await fs.promises.readFile(path.join(dir, 'queue.jsonl.invalid'), 'utf8')).toContain('{malformed}');
    expect((await fs.promises.readFile(file, 'utf8')).trim()).toBe('');
    expect((await drainQueue()).remaining).toBe(1); // Never checkpoint beyond unresolved corrupt work.
  });

  it('serializes append with drain so an in-flight append is preserved', async () => {
    await enqueueSignal(signal('5'));
    let release!: () => void;
    const gate = new Promise<void>(resolve => { release = resolve; });
    fetchMock.mockImplementation(async () => { await gate; return new Response(JSON.stringify({ accepted: true }), { status: 200 }); });
    const draining = drainQueue();
    const appending = enqueueSignal(signal('6'));
    release();
    await draining;
    await appending;
    const result = await drainQueue();
    expect(result.delivered).toBe(1);
  });
});
