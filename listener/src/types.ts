export interface OrderFilledEvent {
  orderHash: string;
  maker: string;
  taker: string;
  makerAssetId: string;
  takerAssetId: string;
  makerAmountFilled: string;
  takerAmountFilled: string;
  fee: string;
  blockNumber: number;
  transactionHash: string;
  logIndex: number;
}

export interface WhaleTradeSignal {
  walletAddress: string;
  side: 'BUY' | 'SELL';
  assetId: string;
  amountFilled: string;
  price: string;
  transactionHash: string;
  logIndex: number;
  blockNumber: number;
  timestamp: number;
}

export interface Checkpoint {
  lastProcessedBlock: number;
  updatedAt: number;
}
