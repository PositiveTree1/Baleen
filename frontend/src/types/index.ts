export type Tier = 'gold_sniper' | 'standard' | 'dormant';

export interface Wallet {
  address: string;
  tier: Tier;
  winRate: number;
  wilsonLb?: number | null;
  pnl: number;
  tradesPerDay: number;
  tradesPerHour?: number | null;
  score: number;
  isHft?: boolean;
  dormant?: boolean;
  alphaPerTrade?: number | null;
  profitFactor?: number | null;
  firstTradeAt?: string | null;
  lastTradeAt?: string | null;
  aiStyleTag?: string | null;
}

export interface DailyPnLPoint {
  date: string;
  wonUsd?: number;
  lostUsd?: number;
  netPnL?: number;
  dailyPnL: number;
  cumulativePnL: number;
  tradesCount: number;
}

export interface WalletDetail extends Wallet {
  aiSummary: string | null;
  maxDrawdown: number;
  scoreHistory: { date: string; score: number }[];
  dailyPnLHistory?: DailyPnLPoint[];
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
  marketConditionId?: string;
  side: 'BUY' | 'SELL';
  entryPrice: number;
  fillPrice: number;
  currentPrice?: number;
  size: number;
  status: 'PENDING' | 'FILLED' | 'FAILED';
  pnl?: number;
  grossPnl?: number;
  pnlPct?: number;
  feeUsd?: number;
  marketCategory?: string;
  categoryRate?: number;
  consensus?: {
    whale_count: number;
    total_cash: number;
    is_consensus: boolean;
  };
  polymarketUrl?: string;
}

export interface PortfolioSummary {
  startingBalance: number;
  currentBalance: number;
  totalPnlUsd: number;
  totalPnlPct: number;
  totalFeesPaidUsd?: number;
  filledTradesCount: number;
  totalNotionalInvested: number;
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
