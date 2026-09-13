import { ethers } from 'ethers';
import { parseOrderFilledLog, matchesBasketWallets } from '../src/event-processor';
import { ORDER_FILLED_V1_TOPIC, ORDER_FILLED_V2_TOPIC, CTF_EXCHANGE_V1, CTF_EXCHANGE_V2 } from '../src/constants';
import { enqueueSignal, drainQueue, postSignalToBackend } from '../src/queue';
import fs from 'fs';
import path from 'path';
import os from 'os';

describe('V1 and V2 Event Processor & Deduplication Tests', () => {
  const abiCoder = new ethers.AbiCoder();
  const queueFile = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'baleen-decoder-test-')), 'queue.jsonl');
  const queueTmpFile = queueFile + '.tmp';
  beforeAll(() => { process.env.LISTENER_QUEUE_FILE = queueFile; });
  afterAll(() => { delete process.env.LISTENER_QUEUE_FILE; });

  afterEach(() => {
    if (fs.existsSync(queueFile)) fs.unlinkSync(queueFile);
    if (fs.existsSync(queueTmpFile)) fs.unlinkSync(queueTmpFile);
  });

  it('correctly decodes synthetic V1 OrderFilled logs', () => {
    const orderHash = '0x' + '1'.repeat(64);
    const makerAddr = '0x' + 'a'.repeat(40);
    const takerAddr = '0x' + 'b'.repeat(40);

    const makerTopic = '0x000000000000000000000000' + makerAddr.slice(2);
    const takerTopic = '0x000000000000000000000000' + takerAddr.slice(2);

    // V1: makerAssetId (0 = USDC collateral), takerAssetId, makerAmountFilled (50 USDC), takerAmountFilled (100 shares), fee
    const data = abiCoder.encode(
      ['uint256', 'uint256', 'uint256', 'uint256', 'uint256'],
      [0, 111, 50000000, 100000000, 0]
    );

    const rawLog = {
      address: CTF_EXCHANGE_V1,
      topics: [ORDER_FILLED_V1_TOPIC, orderHash, makerTopic, takerTopic],
      data,
      blockNumber: 123456, blockTimestamp: 1788880000000,
      transactionHash: '0x' + 'c'.repeat(64),
      logIndex: 2,
    };

    const parsed = parseOrderFilledLog(rawLog);
    expect(parsed.version).toBe('V1');
    expect(parsed.maker).toBe(makerAddr.toLowerCase());
    expect(parsed.taker).toBe(takerAddr.toLowerCase());
    expect(parsed.makerAssetId).toBe('0');
    expect(parsed.takerAssetId).toBe('111');
    expect(parsed.makerAmountFilled).toBe('50000000');
    expect(parsed.takerAmountFilled).toBe('100000000');

    // Test matching: Maker is in basket (BUY shares at $0.50)
    const signals = matchesBasketWallets(parsed, new Set([makerAddr.toLowerCase()]));
    expect(signals.length).toBe(1);
    expect(signals[0].walletAddress).toBe(makerAddr.toLowerCase());
    expect(signals[0].side).toBe('BUY');
    expect(signals[0].assetId).toBe('111');
    expect(signals[0].price).toBe('0.500000000000000000');
    expect(signals[0].amountFilled).toBe('100000000');
    expect(signals[0].isMaker).toBe(true);
  });

  it('correctly decodes synthetic V2 OrderFilled layout from official Events.sol', () => {
    const orderHash = '0x' + '2'.repeat(64);
    const makerAddr = '0x' + 'd'.repeat(40);
    const takerAddr = '0x' + 'e'.repeat(40);
    const conditionId = '0x' + 'f'.repeat(64);
    const tokenBytes32 = '0x0000000000000000000000000000000000000000000000000000000000000309'; // 777 in hex

    const makerTopic = '0x000000000000000000000000' + makerAddr.slice(2);
    const takerTopic = '0x000000000000000000000000' + takerAddr.slice(2);

    // V2: side, tokenId, makerAmountFilled, takerAmountFilled, fee, builder, metadata
    const data = abiCoder.encode(
      ['uint8', 'uint256', 'uint256', 'uint256', 'uint256', 'bytes32', 'bytes32'],
      [0, 777, 60000000, 100000000, 1, conditionId, tokenBytes32]
    );

    const rawLog = {
      address: CTF_EXCHANGE_V2,
      topics: [ORDER_FILLED_V2_TOPIC, orderHash, makerTopic, takerTopic],
      data,
      blockNumber: 234567, blockTimestamp: 1788880000000,
      transactionHash: '0x' + '8'.repeat(64),
      logIndex: 5,
    };

    const parsed = parseOrderFilledLog(rawLog);
    expect(parsed.version).toBe('V2');
    expect(parsed.maker).toBe(makerAddr.toLowerCase());
    expect(parsed.taker).toBe(takerAddr.toLowerCase());
    expect(parsed.side).toBe(0);
    expect(parsed.conditionId).toBeUndefined();
    expect(parsed.token).toBe('777');

    // Only the signed order owner is represented by this log.
    const dualSignals = matchesBasketWallets(parsed, new Set([makerAddr.toLowerCase(), takerAddr.toLowerCase()]));
    expect(dualSignals.length).toBe(1);

    const makerSig = dualSignals.find(s => s.walletAddress === makerAddr.toLowerCase())!;
    expect(makerSig.side).toBe('BUY');
    expect(makerSig.price).toBe('0.600000000000000000');
    expect(makerSig.assetId).toBe('777');
    expect(makerSig.amountFilled).toBe('100000000');
    expect(makerSig.isMaker).toBe(true);

    expect(dualSignals.find(s => s.walletAddress === takerAddr.toLowerCase())).toBeUndefined();
  });

  it.each(['complementary', 'mint', 'merge'])('copies each order owner once in a %s transaction', (mode) => {
    const maker = '0x'+'a'.repeat(40), taker = '0x'+'b'.repeat(40);
    const topic = (address: string) => '0x'+'0'.repeat(24)+address.slice(2);
    const sell = mode === 'merge';
    const log = (owner: string, counterparty: string, index: number, side: number, token: number, cash: number) => parseOrderFilledLog({
      address: CTF_EXCHANGE_V2, blockNumber: 100, blockTimestamp: 1788880000000,
      blockHash: '0x'+'c'.repeat(64), transactionHash:'0x'+'d'.repeat(64), logIndex:index,
      topics:[ORDER_FILLED_V2_TOPIC, '0x'+String(index+1).repeat(64), topic(owner), topic(counterparty)],
      data:abiCoder.encode(['uint8','uint256','uint256','uint256','uint256','bytes32','bytes32'],
        [side, token, side === 0 ? cash : 100000000, side === 0 ? 100000000 : cash, 0, ethers.ZeroHash, ethers.ZeroHash])
    });
    const logs = [log(maker, taker, 0, sell ? 1 : 0, 111, 40000000),
      log(taker, CTF_EXCHANGE_V2, 1, mode === 'complementary' || sell ? 1 : 0,
        mode === 'complementary' ? 111 : 222, mode === 'complementary' ? 40000000 : 60000000)];
    const signals = logs.flatMap(event => matchesBasketWallets(event, new Set([maker, taker])));
    expect(signals).toHaveLength(2);
    expect(signals.filter(s => s.walletAddress === taker)).toHaveLength(1);
    expect(signals[1].assetId).toBe(mode === 'complementary' ? '111' : '222');
    expect(signals[1].side).toBe(mode === 'mint' ? 'BUY' : 'SELL');
    expect(signals[1].amountFilled).toBe('100000000');
  });

  it('durable queue enqueues signals to file', async () => {
    const sig = {
      walletAddress: '0x' + '1'.repeat(40),
      side: 'BUY' as const,
      assetId: '12345',
      amountFilled: '50.000000',
      price: '0.500000000000000000',
      transactionHash: '0x' + 'a'.repeat(64),
      logIndex: 0,
      blockNumber: 100,
      timestamp: Date.now(),
    };

    await enqueueSignal(sig);
    expect(fs.existsSync(queueFile)).toBe(true);
    const content = fs.readFileSync(queueFile, 'utf-8');
    expect(content).toContain(sig.transactionHash);
  });
});
