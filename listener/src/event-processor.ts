import { ethers } from 'ethers';
import { ORDER_FILLED_V1_TOPIC, ORDER_FILLED_V2_TOPIC, CTF_EXCHANGE_V1,
  NEGRISK_CTF_EXCHANGE_V1, CTF_EXCHANGE_V2, NEGRISK_CTF_EXCHANGE_V2 } from './constants';
import { OrderFilledEvent, WhaleTradeSignal } from './types';

const abiCoder = new ethers.AbiCoder();
const versions = new Map([
  [CTF_EXCHANGE_V1.toLowerCase(), 'V1'], [NEGRISK_CTF_EXCHANGE_V1.toLowerCase(), 'V1'],
  [CTF_EXCHANGE_V2.toLowerCase(), 'V2'], [NEGRISK_CTF_EXCHANGE_V2.toLowerCase(), 'V2'],
]);

export function parseOrderFilledLog(log: any): OrderFilledEvent {
  const contractAddress = String(log.address || '').toLowerCase();
  const version = versions.get(contractAddress);
  const topic = log.topics?.[0]?.toLowerCase();
  if (!version || topic !== (version === 'V1' ? ORDER_FILLED_V1_TOPIC : ORDER_FILLED_V2_TOPIC)) {
    throw new Error('Unsupported exchange/topic combination');
  }
  if (log.topics.length !== 4 || log.topics.some((t: string) => !/^0x[0-9a-f]{64}$/i.test(t)) ||
      !/^0x[0-9a-f]{64}$/i.test(log.transactionHash) ||
      !Number.isSafeInteger(log.logIndex) || log.logIndex < 0 ||
      !Number.isSafeInteger(log.blockNumber) || log.blockNumber < 0) {
    throw new Error('Incomplete chain log identity');
  }
  const common = {
    orderHash: log.topics[1], maker: '0x' + log.topics[2].slice(26).toLowerCase(),
    taker: '0x' + log.topics[3].slice(26).toLowerCase(), contractAddress,
    blockNumber: log.blockNumber, transactionHash: log.transactionHash.toLowerCase(),
    logIndex: log.logIndex, blockTimestamp: log.blockTimestamp, blockHash: log.blockHash,
  };
  if (version === 'V2') {
    // Official Events.sol: side, tokenId, makerAmount, takerAmount, fee, builder, metadata.
    // Neither trailing bytes32 is a condition ID or token ID.
    const d = abiCoder.decode(['uint8', 'uint256', 'uint256', 'uint256', 'uint256', 'bytes32', 'bytes32'], log.data);
    const side = Number(d[0]);
    if (side !== 0 && side !== 1) throw new Error('Invalid maker side');
    const token = d[1].toString();
    return { ...common, version: 'V2', side, token,
      makerAssetId: side === 0 ? '0' : token, takerAssetId: side === 0 ? token : '0',
      makerAmountFilled: d[2].toString(), takerAmountFilled: d[3].toString(), fee: d[4].toString() };
  }
  const d = abiCoder.decode(['uint256', 'uint256', 'uint256', 'uint256', 'uint256'], log.data);
  return { ...common, version: 'V1', makerAssetId: d[0].toString(), takerAssetId: d[1].toString(),
    makerAmountFilled: d[2].toString(), takerAmountFilled: d[3].toString(), fee: d[4].toString() };
}

export function matchesBasketWallets(event: OrderFilledEvent, basket: Set<string>): WhaleTradeSignal[] {
  const makerBuy = event.makerAssetId === '0';
  if (makerBuy === (event.takerAssetId === '0')) throw new Error('Expected one collateral asset');
  const cash = BigInt(makerBuy ? event.makerAmountFilled : event.takerAmountFilled);
  const shares = BigInt(makerBuy ? event.takerAmountFilled : event.makerAmountFilled);
  if (shares <= 0n || cash <= 0n || cash > shares) throw new Error('Invalid fill amounts');
  if (!Number.isSafeInteger(event.blockTimestamp) || event.blockTimestamp! <= 0) {
    throw new Error('Source block timestamp is required');
  }
  // Ratio rounded down to 18 decimal places without converting uint256 to Number.
  const fraction = (cash * 10n ** 18n / shares).toString().padStart(19, '0');
  const price = fraction.slice(0, -18) + '.' + fraction.slice(-18);
  const signals: WhaleTradeSignal[] = [];
  // Trading.sol emits each signed order's own fill with its owner as `maker`,
  // including the aggregate taker order. Reading the counterparty here would
  // duplicate taker trades and infer the wrong token/side for mint/merge matches.
  for (const [wallet, isMaker] of [[event.maker, true]] as const) {
    if (!basket.has(wallet.toLowerCase())) continue;
    signals.push({ walletAddress: wallet.toLowerCase(), isMaker,
      side: (isMaker === makerBuy) ? 'BUY' : 'SELL',
      assetId: makerBuy ? event.takerAssetId : event.makerAssetId,
      amountFilled: shares.toString(), amountUnit: 'raw_6', price,
      transactionHash: event.transactionHash, logIndex: event.logIndex,
      blockNumber: event.blockNumber, blockHash: event.blockHash,
      timestamp: event.blockTimestamp!, sourceVersion: event.version,
      contractAddress: event.contractAddress, chainId: 137 });
  }
  return signals;
}

export function matchesBasketWallet(event: OrderFilledEvent, basket: Set<string>): WhaleTradeSignal | null {
  return matchesBasketWallets(event, basket)[0] || null;
}
