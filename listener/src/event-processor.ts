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
  let sharesFilled: string;
  let priceStr: string;

  const isMakerCollateral = event.makerAssetId === '0';
  const isTakerCollateral = event.takerAssetId === '0';

  if (isTakerBasket) {
    walletAddress = takerLower;
    if (isTakerCollateral) {
      side = 'BUY';
      assetId = event.makerAssetId;
      sharesFilled = event.makerAmountFilled;
      const collateral = parseFloat(event.takerAmountFilled);
      const shares = parseFloat(event.makerAmountFilled);
      priceStr = shares > 0 ? (collateral / shares).toFixed(4) : '0.5';
    } else {
      side = 'SELL';
      assetId = event.takerAssetId;
      sharesFilled = event.takerAmountFilled;
      const collateral = parseFloat(event.makerAmountFilled);
      const shares = parseFloat(event.takerAmountFilled);
      priceStr = shares > 0 ? (collateral / shares).toFixed(4) : '0.5';
    }
  } else {
    walletAddress = makerLower;
    side = isMakerCollateral ? 'BUY' : 'SELL';
    assetId = isMakerCollateral ? event.takerAssetId : event.makerAssetId;
    sharesFilled = isMakerCollateral ? event.takerAmountFilled : event.makerAmountFilled;
    const collateral = parseFloat(isMakerCollateral ? event.makerAmountFilled : event.takerAmountFilled);
    const shares = parseFloat(isMakerCollateral ? event.takerAmountFilled : event.makerAmountFilled);
    priceStr = shares > 0 ? (collateral / shares).toFixed(4) : '0.5';
  }

  return {
    walletAddress,
    side,
    assetId,
    amountFilled: sharesFilled,
    price: priceStr,
    transactionHash: event.transactionHash,
    logIndex: event.logIndex,
    blockNumber: event.blockNumber,
    timestamp: Date.now(),
  };
}
