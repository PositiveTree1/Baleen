export type Tier = 'gold_sniper' | 'standard' | 'dormant';

export interface Wallet {
  address: string;
  name?: string | null;
  pseudonym?: string | null;
  profileImage?: string | null;
  tier: Tier;
  winRate: number | null;
  wilsonLb?: number | null;
  pnl: number | null;
  tradesPerDay: number | null;
  tradesPerHour?: number | null;
  score: number | null;
  isHft?: boolean;
  dormant?: boolean;
  alphaPerTrade?: number | null;
  profitFactor?: number | null;
  firstTradeAt?: string | null;
  lastTradeAt?: string | null;
  aiStyleTag?: string | null;
  avgHoldHours?: number | null;
  medianInterTradeGapHours?: number | null;
  totalTradesAnalyzed?: number | null;
  status?: string | null;
}

export interface DailyPnLPoint {
  dailyChangeKnown?: boolean;
  date: string;
  wonUsd?: number;
  lostUsd?: number;
  netPnL?: number;
  dailyPnL: number;
  cumulativePnL: number;
  tradesCount: number;
}

export interface WalletDetail extends Wallet {
  pnlMetadata?: { metric: string; status: string; source_fidelity: string | null };
  research?: { classification: string; reasons: string[]; observed_at: number; metrics: { fills_per_day_7d: number; fills_per_day_30d: number; max_daily_fills: number; distinct_markets_lifetime: number | null; closed_position_win_rate_pct?: number | null; evidence_quality_score?: number | null; median_inter_fill_gap_hours?: number | null } } | null;
  aiSummary: string | null;
  maxDrawdown: number | null;
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
  whaleName?: string | null;
  whalePseudonym?: string | null;
  whaleAvatar?: string | null;
  whaleTier?: string | null;
  whaleStakeUsd?: number;
  whaleBankrollPct?: number;
  marketQuestion: string;
  marketConditionId?: string;
  eventSlug?: string;
  icon?: string;
  side: 'BUY' | 'SELL';
  outcome?: string;
  entryPrice: number | null;
  fillPrice: number | null;
  currentPrice?: number | null;
  size: number;
  status: 'PENDING' | 'FILLED' | 'RESOLVED' | 'CLOSED' | 'FAILED';
  pnl?: number | null;
  grossPnl?: number | null;
  pnlPct?: number | null;
  feeUsd?: number | null;
  markStatus?: 'observed' | 'unavailable' | string;
  markObservedAt?: number | null;
  marketCategory?: string;
  categoryRate?: number;
  consensus?: {
    whale_count: number;
    total_cash: number;
    is_consensus: boolean;
    multiplier?: number;
    whales?: string[];
    whale_details?: {
      address: string;
      name?: string | null;
      pseudonym?: string | null;
      profileImage?: string | null;
      tier?: string | null;
    }[];
    detail?: string;
  };
  polymarketUrl?: string;
}

export interface MarketAttributionItem {
  key?: string;
  question?: string;
  conditionId?: string;
  outcome?: string;
  totalPnl?: number;
  totalNotional?: number;
  fillsCount?: number;
  avgFillPrice?: number;
  whaleName?: string;
  drawdownUsd?: number;
}

export interface PortfolioSummary {
  startingBalance: number | null;
  currentBalance: number | null;
  totalPnlUsd: number | null;
  totalPnlPct: number | null;
  totalFeesPaidUsd?: number | null;
  filledTradesCount: number;
  holdingTradesCount?: number;
  closedTradesCount?: number;
  totalNotionalInvested: number | null;
  valuationStatus?: 'COMPLETE' | 'INCOMPLETE' | string;
  unvaluedTradesCount?: number;
  knownPnlUsd?: number | null;
  knownFeesPaidUsd?: number | null;
  topAlphaMarkets?: MarketAttributionItem[];
  topDrawdownMarkets?: MarketAttributionItem[];
  allTimeWinRate?: number;
  allTimeWins?: number;
  allTimeLosses?: number;
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

export interface SystemEvent {
  id: string;
  eventType: string;
  severity: 'info' | 'warning' | 'success' | 'error';
  title: string;
  detail?: string;
  relatedAddress?: string;
  relatedMarket?: string;
  createdAt: string;
}

export interface LiveTradingCredentials {
  is_configured: boolean;
  polymarket_wallet_address: string;
  clob_api_key_masked: string;
  is_live_active: boolean;
  live_balance_usdc: number | null;
  last_verified_at: string | null;
  signer_address?: string | null;
  signature_type?: number | null;
}

export interface TestConnectionResult {
  connected: boolean;
  wallet_address: string;
  balance_usdc: number | null;
  verified_at: string;
  status_message: string;
  credentials_verified?: boolean;
  wallet_binding_verified?: boolean;
  collateral_currency?: string;
  balance_source?: string;
  live_execution_ready?: boolean;
}

export interface LiveTradingDashboard {
  is_configured: boolean;
  is_live_active: boolean;
  status_badge: string;
  polymarket_wallet_address: string;
  clob_api_key_masked: string;
  usdc_balance: number | null;
  open_positions_value: number | null;
  portfolio_net_worth: number | null;
  live_pnl: number | null;
  last_verified_at: string | null;
  live_execution_ready?: boolean;
  execution_evidence?: string;
  balance_source?: string;
  execution_logs: ExecutionLog[];
  active_positions: {
    id: string;
    marketQuestion: string;
    conditionId: string;
    outcome: string;
    entryPrice: number;
    notionalUsd: number;
    executedAt: string;
    sourceWallet: string;
  }[];
}

export interface LiveSessionSetup {
  walletAddress?: string | null;
  sessionAddress?: string | null;
  verifiedAt?: string | null;
  validUntil?: string | null;
  revokedAt?: string | null;
  scope?: string;
  status: 'not_configured' | 'awaiting_owner_authorization' | 'authorization_observed' | 'expired' | 'locally_disabled' | string;
  ownerAuthorizationRequired?: boolean;
  liveExecutionReady: false;
}

export interface LiveAccountInitialization {
  runId: string;
  startingCash: string;
  blockNumber: number;
  liveExecutionReady: false;
}

export interface CopyPolicyLimits {
  max_order_cash: string;
  max_total_exposure: string;
  max_token_exposure: string;
  max_daily_loss: string;
  max_open_orders: number;
  max_slippage_bps: string;
  max_quote_age_ms: number;
  max_source_age_ms: number;
  max_fee_bps: string;
}

export interface LiveCopyPolicy {
  revision: number;
  source_wallets: string[];
  copy_ratio: string;
  limits: CopyPolicyLimits;
  requiresReactivation?: boolean;
}

export interface CopyPolicyRequest {
  source_wallets: string[];
  copy_ratio: string;
  max_order_cash: string;
  max_total_exposure: string;
  max_token_exposure: string;
  max_daily_loss: string;
  max_open_orders: number;
  max_slippage_bps: string;
  max_quote_age_ms: number;
  max_source_age_ms: number;
  max_fee_bps: string;
}

export interface PaperRun {
  id: string;
  status: string;
  startedAt: string;
  endedAt: string | null;
  startingBalance: number;
}

export interface PaperRunTrade {
  id: string;
  runId: string;
  side: string;
  status: string;
  tokenId: string;
  sourceWallet: string;
  executedAt: string;
  fillPrice: number | null;
  notionalUsd: number | null;
  feeUsd: number | null;
  realizedPnlUsd: number | null;
}

export type { SessionOperation } from '../lib/session-wallet-approval';
