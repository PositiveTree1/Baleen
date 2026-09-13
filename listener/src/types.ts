export interface OrderFilledEvent {
  version: 'V1' | 'V2';
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
  contractAddress: string;
  blockTimestamp?: number;
  blockHash?: string;
  side?: number; // V2: 0 = BUY, 1 = SELL for maker
  conditionId?: string; // V2
  token?: string; // V2
  nonce?: string; // V2
}

export interface WhaleTradeSignal {
  walletAddress: string;
  side: 'BUY' | 'SELL';
  assetId: string;
  conditionId?: string;
  amountFilled: string;
  amountUnit?: 'raw_6';
  chainId?: number;
  blockHash?: string;
  price: string;
  transactionHash: string;
  logIndex: number;
  blockNumber: number;
  timestamp: number;
  sourceVersion?: 'V1' | 'V2';
  contractAddress?: string;
  isMaker?: boolean;
}

export interface Checkpoint {
  lastProcessedBlock: number;
  updatedAt: number;
}
