export type Tier = 'gold_sniper' | 'standard' | 'dormant';

export interface Wallet {
  address: string;
  tier: Tier;
  winRate: number;
  pnl: number;
  tradesPerDay: number;
  score: number;
  aiStyleTag?: string | null;
}

export interface WalletDetail extends Wallet {
  aiSummary: string | null;
  maxDrawdown: number;
  scoreHistory: { date: string; score: number }[];
  recentTrades: ExecutionLog[];
}

export interface WalletSnapshot {
  timestamp: string;
  walletAddress: string;
  score: number;
}

export interface User {
  id: string;
  email: string;
  startingBalance: number;
  currentBalance: number;
  riskProfile: 'Conservative' | 'Balanced' | 'Aggressive';
  dailyDigestOptIn: boolean;
}

export interface ExecutionLog {
  id: string;
  timestamp: string;
  walletAddress: string;
  marketQuestion: string;
  side: 'BUY' | 'SELL';
  entryPrice: number;
  fillPrice: number;
  size: number;
  status: 'PENDING' | 'FILLED' | 'FAILED';
  pnl?: number;
}

export interface FeeCharge {
  id: string;
  timestamp: string;
  amount: number;
  reason: string;
}

export interface PlatformStats {
  totalVolumeMirrored: number;
  activeBasketWhales: number;
  indexerStatus: 'ONLINE' | 'OFFLINE' | 'SYNCING';
}
