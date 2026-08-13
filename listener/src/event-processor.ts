import { ethers } from 'ethers';
import { OrderFilledEvent, WhaleTradeSignal } from './types';

const abiCoder = new ethers.AbiCoder();

export function parseOrderFilledLog(log: any): OrderFilledEvent {
  const orderHash = log.topics[1] || '0x';
  
  const makerTopic = log.topics[2] || '0x';
  const maker = makerTopic.length >= 66 ? '0x' + makerTopic.slice(26) : '0x';

  const takerTopic = log.topics[3] || '0x';
  const taker = takerTopic.length >= 66 ? '0x' + takerTopic.slice(26) : '0x';

  let makerAssetId = '0';
  let takerAssetId = '0';
  let makerAmountFilled = '0';
  let takerAmountFilled = '0';
  let fee = '0';

  if (log.data && log.data !== '0x') {
    try {
      const decoded = abiCoder.decode(
        ['uint256', 'uint256', 'uint256', 'uint256', 'uint256'],
        log.data
      );
      makerAssetId = decoded[0].toString();
      takerAssetId = decoded[1].toString();
      makerAmountFilled = decoded[2].toString();
      takerAmountFilled = decoded[3].toString();
      fee = decoded[4].toString();
    } catch (e) {
      console.error('Failed to decode log data', e);
    }
  }

  return {
    orderHash,
    maker: maker.toLowerCase(),
    taker: taker.toLowerCase(),
    makerAssetId,
    takerAssetId,
    makerAmountFilled,
    takerAmountFilled,
    fee,
    blockNumber: log.blockNumber || 0,
    transactionHash: log.transactionHash || '0x',
    logIndex: log.logIndex || 0,
  };
}

export function matchesBasketWallet(
  event: OrderFilledEvent,
  basketAddresses: Set<string>
): WhaleTradeSignal | null {
  const makerLower = event.maker.toLowerCase();
  const takerLower = event.taker.toLowerCase();
  
  const isMakerBasket = basketAddresses.has(makerLower);
  const isTakerBasket = basketAddresses.has(takerLower);

  if (!isMakerBasket && !isTakerBasket) {
    return null;
  }

  let side: 'BUY' | 'SELL';
  let walletAddress: string;
  let assetId: string;
  let amountFilled: string;

  if (isTakerBasket) {
    side = 'BUY';
    walletAddress = takerLower;
    assetId = event.makerAssetId;
    amountFilled = event.makerAmountFilled;
  } else {
    side = 'SELL';
    walletAddress = makerLower;
    assetId = event.makerAssetId;
    amountFilled = event.makerAmountFilled;
  }

  const price = '0'; // Placeholder

  return {
    walletAddress,
    side,
    assetId,
    amountFilled,
    price,
    transactionHash: event.transactionHash,
    logIndex: event.logIndex,
    blockNumber: event.blockNumber,
    timestamp: Date.now(),
  };
}
