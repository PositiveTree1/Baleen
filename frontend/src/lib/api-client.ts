import { 
  Wallet, 
  WalletDetail, 
  ExecutionLog, 
  User, 
  PlatformStats, 
  LiveTradingCredentials, 
  LiveTradingDashboard, 
  TestConnectionResult, 
  SystemEvent,
  LiveSessionSetup,
  LiveAccountInitialization,
  CopyPolicyLimits,
  LiveCopyPolicy,
  CopyPolicyRequest,
  PaperRun,
  PaperRunTrade
} from '../types';
import type { SessionOperation } from './session-wallet-approval';
import { getSession } from 'next-auth/react';

export type { 
  SessionOperation,
  LiveSessionSetup,
  LiveAccountInitialization,
  CopyPolicyLimits,
  LiveCopyPolicy,
  CopyPolicyRequest,
  PaperRun,
  PaperRunTrade
};

let rawBackendUrl = (
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://localhost:8000'
).trim().replace(/\/$/, '');

if (rawBackendUrl && !rawBackendUrl.startsWith('http://') && !rawBackendUrl.startsWith('https://')) {
  rawBackendUrl = `https://${rawBackendUrl}`;
}

const API_BASE_URL = rawBackendUrl;

// Global In-Memory Cache (persists across Next.js page navigations in browser)
const memoryCache = new Map<string, { data: unknown; ts: number }>();
const CACHE_PREFIX = 'baleen_cache_evidence_v2_';
let walletGeneration: string | null = null;

function observeWalletGeneration(response: Response): boolean {
  const generation = response.headers.get('X-Wallet-Generation');
  if (!generation) return false;
  let previous = walletGeneration;
  if (typeof window !== 'undefined' && previous === null) {
    try { previous = sessionStorage.getItem('baleen_wallet_generation'); } catch {}
  }
  const changed = previous !== generation;
  if (changed) clearAllCache();
  walletGeneration = generation;
  if (typeof window !== 'undefined') {
    try { sessionStorage.setItem('baleen_wallet_generation', generation); } catch {}
  }
  return changed;
}

function getCached<T>(key: string, maxAgeMs: number = 60000): T | null {
  const entry = memoryCache.get(key);
  if (entry && (Date.now() - entry.ts) < maxAgeMs) {
    return entry.data as T;
  }
  if (typeof window !== 'undefined') {
    try {
      const raw = sessionStorage.getItem(`${CACHE_PREFIX}${key}`);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Date.now() - parsed.ts < maxAgeMs) {
          memoryCache.set(key, parsed);
          return parsed.data as T;
        }
      }
    } catch {}
  }
  return null;
}

function setCached<T>(key: string, data: T) {
  const entry = { data, ts: Date.now() };
  memoryCache.set(key, entry);
  if (typeof window !== 'undefined') {
    try {
      sessionStorage.setItem(`${CACHE_PREFIX}${key}`, JSON.stringify(entry));
    } catch {}
  }
}

export function clearAllCache() {
  memoryCache.clear();
  if (typeof window !== 'undefined') {
    try {
      const keysToRemove: string[] = [];
      for (let i = 0; i < sessionStorage.length; i++) {
        const k = sessionStorage.key(i);
        if (k && k.startsWith('baleen_cache_')) {
          keysToRemove.push(k);
        }
      }
      keysToRemove.forEach(k => sessionStorage.removeItem(k));
    } catch {}
  }
}

// ---------------------------------------------------------------------------
// Bearer Token Management & Authenticated Fetch
// ---------------------------------------------------------------------------

let inMemoryAuthToken: string | null = null;
let pendingSession: ReturnType<typeof getSession> | null = null;

export function setAuthToken(token: string | null) {
  if (token && inMemoryAuthToken && token !== inMemoryAuthToken) {
    clearAllCache();
  }
  inMemoryAuthToken = token;
  if (typeof window !== 'undefined') {
    try {
      if (token) {
        sessionStorage.setItem('baleen_auth_token', token);
      } else {
        sessionStorage.removeItem('baleen_auth_token');
        localStorage.removeItem('baleen_auth_token');
      }
    } catch {}
  }
}

export function getAuthToken(): string | null {
  if (inMemoryAuthToken) return inMemoryAuthToken;
  if (typeof window !== 'undefined') {
    try {
      const saved = sessionStorage.getItem('baleen_auth_token');
      if (saved) {
        inMemoryAuthToken = saved;
        return saved;
      }
    } catch {}
  }
  return null;
}

export async function logoutBackend(): Promise<void> {
  const session = await getSession();
  const token = session?.user?.accessToken || session?.accessToken || getAuthToken();
  if (token) {
      const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: 'POST',
        signal: AbortSignal.timeout(10000),
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok && response.status !== 401) {
        throw new Error('Sign out could not be completed. Please retry.');
      }
  }
  setAuthToken(null);
  clearAllCache();
}

export async function fetchWithAuth(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  let token: string | null = getAuthToken();
  if (!token && typeof window !== 'undefined') {
    pendingSession ??= getSession().finally(() => { pendingSession = null; });
    const session = await pendingSession;
    const sessionToken = session?.user?.accessToken || session?.accessToken;
    if (sessionToken) {
      token = sessionToken;
      setAuthToken(token);
    }
  }

  const headers = new Headers(init?.headers || {});
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response = await fetch(input, {
    ...init,
    headers,
  });

  // On 401: Attempt silent token recovery for guest/paper sessions without disrupting the UI
  if (response.status === 401 && typeof window !== 'undefined') {
    try {
      const guestCreds = await guestLogin();
      if (guestCreds?.access_token) {
        token = guestCreds.access_token;
        setAuthToken(token);
        const retryHeaders = new Headers(init?.headers || {});
        retryHeaders.set('Authorization', `Bearer ${token}`);
        response = await fetch(input, {
          ...init,
          headers: retryHeaders,
        });
      }
    } catch (refreshErr) {
      console.debug("Silent guest refresh recovery note:", refreshErr);
    }
  }

  return response;
}


// Synchronous instant-read cache getters for initial component states
export function getCachedWallets(): Wallet[] | null {
  return getCached<Wallet[]>('wallets_list', 120000);
}

export function getCachedExecutionLogs(userId?: string): ExecutionLog[] | null {
  return getCached<ExecutionLog[]>(`exec_logs_${userId || 'all'}`, 60000);
}

export function getCachedPortfolioSummary(userId?: string, timeframe?: string): {
  startingBalance: number | null;
  currentBalance: number | null;
  totalPnlUsd: number | null;
  totalPnlPct: number | null;
  totalFeesPaidUsd?: number | null;
  filledTradesCount: number;
  totalNotionalInvested: number | null;
  valuationStatus?: 'COMPLETE' | 'INCOMPLETE' | string;
  unvaluedTradesCount?: number;
  knownPnlUsd?: number | null;
  knownFeesPaidUsd?: number | null;
} | null {
  return getCached(`portfolio_summary_${userId || 'all'}_${timeframe || 'all'}`, 60000);
}

export function getCachedPortfolioSnapshots(userId?: string, timeframe?: string): {
  id: string;
  timestamp: string;
  time: string;
  date: string;
  balance: number;
  pnl: number;
  activeTrades: number;
}[] | null {
  return getCached(`snapshots_${userId || 'all'}_${timeframe || 'all'}`, 60000);
}

interface RawWalletApi {
  address: string;
  name?: string | null;
  pseudonym?: string | null;
  profileImage?: string | null;
  tier: Wallet['tier'];
  win_rate_pct?: number | null;
  wilson_lb?: number | null;
  all_time_pnl_usd?: number | null;
  avg_trades_per_day?: number | null;
  trades_per_hour?: number | null;
  baleen_score?: number | null;
  is_hft?: boolean;
  dormant?: boolean;
  alpha_per_trade?: number | null;
  profit_factor?: number | null;
  first_trade_at?: string | null;
  last_trade_at?: string | null;
  ai_style_tag?: string | null;
  avg_hold_hours?: number | null;
  median_inter_trade_gap_hours?: number | null;
  max_drawdown_pct?: number | null;
  total_trades_analyzed?: number | null;
  status?: string | null;
}

export interface PaperCopyState {
  status: string; listener?: string; last_error?: string | null; selection_mode?: 'automatic' | 'manual';
  standby_snipers?: Array<{ address: string; name?: string | null; pseudonym?: string | null;
    classification: string; reasons: string[]; all_time_pnl_usd: string; recent_pnl_30d: string;
    realized_pnl_usd: string;
    fills_per_day_30d: string; observed_at: string; closed_position_win_rate_pct?: number | null;
    closed_position_profit_factor?: string | null; positive_pnl_day_rate_30d?: number | null;
    max_curve_drawdown_30d?: string | null; median_inter_fill_gap_hours?: number | null;
    evidence_quality_score?: number | null }>;
  active_candidates?: Array<{ address: string; name?: string | null; pseudonym?: string | null;
    classification: string; reasons: string[]; all_time_pnl_usd: string; recent_pnl_30d: string;
    realized_pnl_usd: string;
    fills_per_day_30d: string; observed_at: string; closed_position_win_rate_pct?: number | null;
    closed_position_profit_factor?: string | null; positive_pnl_day_rate_30d?: number | null;
    max_curve_drawdown_30d?: string | null; median_inter_fill_gap_hours?: number | null;
    evidence_quality_score?: number | null }>;
  sniper_allocations?: Array<{ source_event_id: string; source_wallet: string; donor_run_id?: string | null;
    sniper_run_id?: string | null; allocated_cash_usd?: string | null; status: string; reason?: string | null;
    created_at: string }>;
  roster_rotations?: Array<{ promoted: Array<{ wallet: string; cash?: string; replaced_wallet?: string }>;
    retired: Array<{ wallet: string; cash_transferred?: string }>; skipped: Array<{ wallet: string; reason: string }>;
    created_at: string }>;
  discovery?: { status?: string; progress_pct?: number; step_description?: string;
    wallets_scanned?: number; error_message?: string | null; addresses_found?: number;
    pnl_queue_total?: number; pnl_checked?: number; pnl_rejected_below_50k?: number;
    pnl_unavailable?: number; pnl_admitted?: number; evidence_audited?: number };
  roster_status?: { active_eligible: number; standby: number; needs_data: number;
    excluded: number; stale: number; legacy_retained: number; generation: string };
  runs: Array<{ id: string; wallet: string; name?: string; role?: 'active' | 'retired'; revision: number;
    policy: { ratio: string }; report: {
      valuation: { equity?: string | null; economic_pnl?: string | null; reason?: string };
      events: Array<{ source_id: string; status: string; quantity: string; reason?: string; fee_usd?: string }>;
    } }>;
}

export interface PaperCopyWallet { address: string; name?: string | null; pseudonym?: string | null; }
export async function fetchPaperCopyWallets(search = ''): Promise<PaperCopyWallet[]> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/paper-copy/wallets?search=${encodeURIComponent(search)}`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Wallet registry unavailable');
  return res.json();
}

export async function fetchPaperCopy(): Promise<PaperCopyState> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/paper-copy`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Paper account unavailable; no saved state assumed');
  return res.json();
}

export interface PaperResearchWallet {
  address: string; name?: string | null; pseudonym?: string | null; classification: string; fresh: boolean;
  is_hft: boolean; reasons: string[]; observed_at?: string | null; all_time_pnl_usd: string;
  realized_pnl_usd: string;
  recent_pnl_7d: string; recent_pnl_30d: string; fills_per_day_7d: string; fills_per_day_30d: string;
  active_days_7d?: number | null; trade_coverage_complete?: boolean | null; trade_coverage_reason?: string | null;
  closed_position_win_rate_pct?: number | null; closed_position_profit_factor?: number | null;
  positive_pnl_day_rate_30d?: number | null; median_inter_fill_gap_hours?: number | null;
  evidence_quality_score?: number | null;
}
export interface PaperResearchState {
  registry: { generation: string; total: number; displayed: number; legacy_retained: number; wallets: PaperResearchWallet[] };
  discovery: PaperCopyState['discovery'];
}
export async function fetchPaperCopyResearch(): Promise<PaperResearchState> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/paper-copy/research`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Wallet research registry unavailable');
  return res.json();
}

export async function startPaperCopy(wallets: string[], starting_cash: string): Promise<PaperCopyState> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/paper-copy/start`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ wallets, starting_cash })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not start paper copying');
  return data;
}

export async function startAutomaticPaperCopy(starting_cash: string): Promise<PaperCopyState> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/paper-copy/start-automatic`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ starting_cash })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not build the automatic roster');
  return data;
}

export async function fetchWallets(params?: Record<string, string>): Promise<Wallet[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/wallets`);
    if (params) {
      Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
    } else {
      url.searchParams.append('limit', '250');
    }
    const res = await fetch(url.toString(), { cache: 'no-store' });
    observeWalletGeneration(res);
    if (!res.ok) return getCachedWallets() || [];
    const data = await res.json();
    const result = data.map((w: RawWalletApi) => ({
      address: w.address,
      name: w.name || null,
      pseudonym: w.pseudonym || null,
      profileImage: w.profileImage || null,
      tier: w.tier,
      winRate: w.win_rate_pct ?? null,
      wilsonLb: w.wilson_lb ?? null,
      pnl: w.all_time_pnl_usd ?? null,
      tradesPerDay: w.avg_trades_per_day ?? null,
      tradesPerHour: w.trades_per_hour ?? null,
      score: w.baleen_score ?? null,
      isHft: Boolean(w.is_hft),
      dormant: Boolean(w.dormant),
      alphaPerTrade: w.alpha_per_trade ?? null,
      profitFactor: w.profit_factor ?? null,
      firstTradeAt: w.first_trade_at || null,
      lastTradeAt: w.last_trade_at || null,
      aiStyleTag: w.ai_style_tag || null,
      avgHoldHours: w.avg_hold_hours ?? null,
      medianInterTradeGapHours: w.median_inter_trade_gap_hours ?? null,
      totalTradesAnalyzed: w.total_trades_analyzed ?? null,
      status: w.status || null
    }));
    setCached('wallets_list', result);
    return result;
  } catch (error) {
    return getCachedWallets() || [];
  }
}

export interface CopiedWhaleStat {
  address: string;
  name: string;
  pseudonym?: string;
  profileImage?: string;
  tier: string;
  score?: number;
  aiStyleTag?: string;
  tradesCopied: number;
  fillsCount: number;
  totalNotional: number | null;
  netPnl: number | null;
  mirroredPnl: number | null;
  roiPct: number | null;
  winRateCopied: number | null;
  profitFactor: number | null;
  wins: number;
  losses: number;
  unvaluedTradesCount?: number;
  knownPnlUsd?: number | null;
  copyRatePct?: number;
}

export async function fetchCopiedWhalesStats(userId?: string): Promise<CopiedWhaleStat[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/wallets/copied-stats`);
    if (userId) {
      url.searchParams.append('userId', userId);
      url.searchParams.append('user_id', userId);
    }
    const res = await fetchWithAuth(url.toString());
    if (!res.ok) return [];
    return await res.json();
  } catch (error) {
    return [];
  }
}

interface RawScoreHistory {
  snapshot_at?: string;
  date?: string;
  baleen_score?: number;
  score?: number;
}

interface RawDailyPnL {
  date: string;
  won_usd?: number;
  lost_usd?: number;
  net_pnl?: number;
  daily_pnl?: number;
  cumulative_pnl?: number;
  trades_count?: number;
}

interface RawTrade {
  id: string;
  executed_at: string;
  market_id?: string;
  side: ExecutionLog['side'];
  fill_price?: number | null;
  size_usd?: number;
  status: ExecutionLog['status'];
  pnl_usd?: number | null;
}

interface RawExecutionLog {
  id: string;
  timestamp?: string;
  executed_at?: string;
  walletAddress?: string;
  source_wallet_address?: string;
  whaleName?: string | null;
  whalePseudonym?: string | null;
  whaleAvatar?: string | null;
  whaleTier?: string | null;
  marketQuestion?: string;
  market_question?: string;
  marketConditionId?: string;
  market_condition_id?: string;
  eventSlug?: string;
  icon?: string;
  side: ExecutionLog['side'];
  outcome?: string;
  entryPrice?: number;
  whale_entry_price?: number;
  fillPrice?: number | null;
  user_fill_price?: number | null;
  currentPrice?: number | null;
  size?: number;
  notional_usd?: number;
  status: ExecutionLog['status'];
  pnl?: number | null;
  realized_pnl_usd?: number | null;
  grossPnl?: number | null;
  pnlPct?: number | null;
  feeUsd?: number | null;
  markStatus?: string;
  markObservedAt?: number | null;
  marketCategory?: string;
  categoryRate?: number;
  consensus?: ExecutionLog['consensus'];
  polymarketUrl?: string;
}

export function getCachedWalletDetail(address: string): WalletDetail | null {
  return getCached<WalletDetail>(`wallet_detail_${address.toLowerCase()}`, 120000);
}

export async function fetchWallet(address: string): Promise<WalletDetail | null> {
  const cached = getCachedWalletDetail(address);
  try {
    const res = await fetch(`${API_BASE_URL}/api/wallets/${address}`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(15000)
    });
    const generationChanged = observeWalletGeneration(res);
    if (!res.ok) return generationChanged ? null : cached || null;
    const data = await res.json();
    const w = data.wallet || data;
    const detail: WalletDetail = {
      address: w.address,
      name: w.name || null,
      pseudonym: w.pseudonym || null,
      profileImage: w.profile_image || w.profileImage || null,
      tier: w.tier,
      winRate: w.win_rate_pct ?? null,
      wilsonLb: w.wilson_lb ?? null,
      pnl: w.all_time_pnl_usd ?? null,
      tradesPerDay: w.avg_trades_per_day ?? null,
      tradesPerHour: w.trades_per_hour ?? null,
      score: w.baleen_score ?? null,
      isHft: Boolean(w.is_hft),
      dormant: Boolean(w.dormant),
      alphaPerTrade: w.alpha_per_trade ?? null,
      profitFactor: w.profit_factor ?? null,
      firstTradeAt: w.first_trade_at || null,
      lastTradeAt: w.last_trade_at || null,
      aiStyleTag: w.ai_style_tag || null,
      aiSummary: w.ai_summary || null,
      avgHoldHours: w.avg_hold_hours ?? null,
      medianInterTradeGapHours: w.median_inter_trade_gap_hours ?? null,
      totalTradesAnalyzed: w.total_trades_analyzed ?? null,
      maxDrawdown: w.max_drawdown_pct ?? null,
      pnlMetadata: data.pnl_metadata,
      research: data.research ?? null,
      scoreHistory: (data.score_history || []).map((s: RawScoreHistory) => ({
        date: s.snapshot_at || s.date || new Date().toISOString(),
        score: s.baleen_score ?? s.score ?? 0
      })),
      dailyPnLHistory: (data.daily_pnl_history || []).map((d: RawDailyPnL) => ({
        dailyChangeKnown: d.daily_pnl != null,
        date: d.date,
        wonUsd: d.won_usd ?? Math.max(0, d.daily_pnl ?? 0),
        lostUsd: d.lost_usd ?? ((d.daily_pnl ?? 0) < 0 ? (d.daily_pnl ?? 0) : 0),
        netPnL: d.net_pnl ?? d.daily_pnl ?? 0,
        dailyPnL: d.daily_pnl ?? 0,
        cumulativePnL: d.cumulative_pnl ?? 0,
        tradesCount: d.trades_count ?? 0
      })),
      recentTrades: (data.recent_trades || []).map((t: RawTrade) => ({
        id: t.id,
        timestamp: t.executed_at,
        walletAddress: address,
        marketQuestion: t.market_id || 'Polymarket Condition',
        marketConditionId: t.market_id,
        side: t.side,
        entryPrice: t.fill_price ?? null,
        fillPrice: t.fill_price ?? null,
        size: t.size_usd || 0,
        status: t.status,
        pnl: t.pnl_usd ?? null,
        polymarketUrl: t.market_id ? `https://polymarket.com/market/${t.market_id}` : 'https://polymarket.com'
      }))
    };
    setCached(`wallet_detail_${address.toLowerCase()}`, detail);
    return detail;
  } catch (error) {
    return cached || null;
  }
}

export async function fetchExecutionLogs(userId?: string, params?: Record<string, string>): Promise<ExecutionLog[]> {
  const cacheKey = `exec_logs_${userId || 'all'}`;
  try {
    const url = new URL(`${API_BASE_URL}/api/executions`);
    if (userId) url.searchParams.append('userId', userId);
    if (params) {
      Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
    } else {
      url.searchParams.append('limit', '500');
    }
    const res = await fetchWithAuth(url.toString());
    if (!res.ok) return getCachedExecutionLogs(userId) || [];
    const data = await res.json();
    if (!Array.isArray(data)) {
      return getCachedExecutionLogs(userId) || [];
    }
    if (data.length === 0) {
      setCached(cacheKey, []);
      return [];
    }
    const result = data.map((log: RawExecutionLog) => ({
      id: log.id,
      timestamp: log.timestamp || log.executed_at || '',
      walletAddress: log.walletAddress || log.source_wallet_address || '',
      whaleName: log.whaleName || null,
      whalePseudonym: log.whalePseudonym || null,
      whaleAvatar: log.whaleAvatar || null,
      whaleTier: log.whaleTier || null,
      marketQuestion: log.marketQuestion || log.market_question || 'Prediction Market',
      marketConditionId: log.marketConditionId || log.market_condition_id,
      eventSlug: log.eventSlug,
      icon: log.icon,
      side: log.side,
      outcome: log.outcome || 'Yes',
      entryPrice: log.entryPrice ?? log.whale_entry_price ?? null,
      fillPrice: log.fillPrice ?? log.user_fill_price ?? null,
      currentPrice: log.currentPrice ?? null,
      size: log.size ?? log.notional_usd ?? 0,
      status: log.status,
      pnl: log.pnl ?? log.realized_pnl_usd ?? null,
      grossPnl: log.grossPnl ?? null,
      pnlPct: log.pnlPct ?? null,
      feeUsd: log.feeUsd ?? null,
      markStatus: log.markStatus,
      markObservedAt: log.markObservedAt ?? null,
      marketCategory: log.marketCategory ?? 'General',
      categoryRate: log.categoryRate ?? 0.05,
      consensus: log.consensus ?? { whale_count: 1, total_cash: 0, is_consensus: false },
      polymarketUrl: log.polymarketUrl ?? (log.eventSlug ? `https://polymarket.com/event/${log.eventSlug}` : (log.marketConditionId ? `https://polymarket.com/market/${log.marketConditionId}` : 'https://polymarket.com')),
    }));
    setCached(cacheKey, result);
    return result;
  } catch (error) {
    return getCachedExecutionLogs(userId) || [];
  }
}

export async function fetchTradePriceChart(tradeId: string): Promise<{
  tradeId: string;
  marketQuestion: string;
  side: string;
  outcome?: string;
  fillPrice: number;
  currentPrice: number;
  minPrice: number;
  maxPrice: number;
  history: { timestamp: number; date: string; price: number }[];
} | null> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}/api/executions/${encodeURIComponent(tradeId)}/chart`);
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
  }
}

export async function fetchPortfolioSummary(userId?: string, timeframe?: string): Promise<{
  startingBalance: number | null;
  currentBalance: number | null;
  totalPnlUsd: number | null;
  totalPnlPct: number | null;
  totalFeesPaidUsd?: number | null;
  filledTradesCount: number;
  totalNotionalInvested: number | null;
  topAlphaMarkets?: {
    key: string;
    question: string;
    conditionId: string;
    outcome: string;
    totalPnl: number;
    totalNotional: number;
    fillsCount: number;
    avgFillPrice: number;
    whaleName: string;
  }[];
  topDrawdownMarkets?: {
    key: string;
    question: string;
    conditionId: string;
    outcome: string;
    totalPnl: number;
    totalNotional: number;
    fillsCount: number;
    avgFillPrice: number;
    whaleName: string;
  }[];
  allTimeWinRate?: number;
  allTimeWins?: number;
  allTimeLosses?: number;
} | null> {
  const cacheKey = `portfolio_summary_${userId || 'all'}_${timeframe || 'all'}`;
  try {
    const url = new URL(`${API_BASE_URL}/api/executions/summary`);
    if (userId) url.searchParams.append('userId', userId);
    if (timeframe) url.searchParams.append('timeframe', timeframe);
    const res = await fetchWithAuth(url.toString());
    if (!res.ok) return getCachedPortfolioSummary(userId, timeframe);
    const data = await res.json();
    if (data) {
      setCached(cacheKey, data);
    }
    return data;
  } catch (error) {
    return getCachedPortfolioSummary(userId, timeframe);
  }
}

export async function fetchPortfolioSnapshots(userId?: string, timeframe?: string): Promise<{
  id: string;
  timestamp: string;
  time: string;
  date: string;
  balance: number;
  pnl: number;
  activeTrades: number;
}[]> {
  const cacheKey = `snapshots_${userId || 'all'}_${timeframe || 'all'}`;
  try {
    const url = new URL(`${API_BASE_URL}/api/executions/snapshots`);
    if (userId) {
      url.searchParams.append('userId', userId);
      url.searchParams.append('user_id', userId);
    }
    if (timeframe) url.searchParams.append('timeframe', timeframe);
    url.searchParams.append('limit', '5000');
    const res = await fetchWithAuth(url.toString());
    if (!res.ok) return getCachedPortfolioSnapshots(userId, timeframe) || [];
    const data = await res.json();
    if (Array.isArray(data)) {
      setCached(cacheKey, data);
    }
    return data;
  } catch (error) {
    return getCachedPortfolioSnapshots(userId, timeframe) || [];
  }
}

export async function fetchCopiedWalletStats(userId?: string): Promise<{
  address: string;
  tier: string;
  score: number;
  aiStyleTag: string;
  pnl: number | null;
  roi: number | null;
  winRate: number | null;
  profitFactor: number | null;
  wins: number;
  losses: number;
  totalNotional?: number | null;
  unvaluedTradesCount?: number;
  knownPnlUsd?: number | null;
}[]> {
  const cacheKey = `copied_stats_${userId || 'all'}`;
  try {
    const url = userId
      ? `${API_BASE_URL}/api/wallets/copied-stats?userId=${encodeURIComponent(userId)}`
      : `${API_BASE_URL}/api/wallets/copied-stats`;
    const res = await fetchWithAuth(url);
    if (!res.ok) return getCached(cacheKey) || [];
    const data = await res.json();
    setCached(cacheKey, data);
    return data;
  } catch (error) {
    return getCached(cacheKey) || [];
  }
}

function parseUserSettingsResponse(data: Record<string, unknown>): { startingBalance: number; currentBalance: number } | null {
  const startingBalance = data.startingBalance ?? data.sandbox_starting_balance_usd;
  const currentBalance = data.currentBalance ?? data.sandbox_balance_usd;
  if (typeof startingBalance !== 'number' || !Number.isFinite(startingBalance) ||
      typeof currentBalance !== 'number' || !Number.isFinite(currentBalance)) {
    return null;
  }
  return { startingBalance, currentBalance };
}

export async function fetchUserSettings(userId: string): Promise<User | null> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}/api/users/${userId}`);
    if (!res.ok) return null;
    const data = await res.json();
    const parsed = parseUserSettingsResponse(data);
    if (!parsed) return null;
    return {
      id: data.id,
      email: data.email,
      startingBalance: parsed.startingBalance,
      currentBalance: parsed.currentBalance,
      riskProfile: data.riskProfile ?? data.risk_profile ?? 'Balanced',
      dailyDigestOptIn: data.dailyDigestOptIn ?? data.daily_digest_opt_in ?? true,
    };
  } catch (error) {
    return null;
  }
}

export async function updateUserSettings(userId: string, data: Partial<User>): Promise<User | null> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}/api/users/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        risk_profile: data.riskProfile,
        daily_digest_opt_in: data.dailyDigestOptIn,
      }),
    });
    if (!res.ok) return null;
    const result = await res.json();
    const parsed = parseUserSettingsResponse(result);
    if (!parsed) return null;
    return {
      id: result.id,
      email: result.email,
      startingBalance: parsed.startingBalance,
      currentBalance: parsed.currentBalance,
      riskProfile: result.riskProfile ?? result.risk_profile ?? 'Balanced',
      dailyDigestOptIn: result.dailyDigestOptIn ?? result.daily_digest_opt_in ?? true,
    };
  } catch (error) {
    return null;
  }
}

export async function resetSandboxAmount(userId?: string, newBalance: number = 10000): Promise<boolean> {
  try {
    const url = userId
      ? `${API_BASE_URL}/api/users/${userId}/reset-sandbox`
      : `${API_BASE_URL}/api/users/reset-sandbox`;
    const res = await fetchWithAuth(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ newBalance }),
    });
    if (res.ok) {
      clearAllCache();
    }
    return res.ok;
  } catch (error) {
    return false;
  }
}

export async function resetSandboxLedger(userId?: string): Promise<boolean> {
  try {
    const url = new URL(`${API_BASE_URL}/api/executions/reset-sandbox`);
    if (userId) url.searchParams.append('userId', userId);
    const res = await fetchWithAuth(url.toString(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (res.ok) {
      clearAllCache();
    }
    return res.ok;
  } catch (error) {
    return false;
  }
}

export async function signUp(email: string, password: string, startingBalance: number): Promise<User | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, startingBalance }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (data.access_token) {
      setAuthToken(data.access_token);
    }
    return {
      id: data.id,
      email: data.email,
      startingBalance: data.startingBalance ?? data.sandbox_starting_balance_usd ?? startingBalance,
      currentBalance: data.currentBalance ?? data.sandbox_balance_usd ?? startingBalance,
      riskProfile: data.riskProfile ?? data.risk_profile ?? 'Balanced',
      dailyDigestOptIn: data.dailyDigestOptIn ?? data.daily_digest_opt_in ?? true,
    };
  } catch (error) {
    return null;
  }
}

export async function fetchPlatformStats(): Promise<PlatformStats | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/stats`, { next: { revalidate: 10 } });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
  }
}

export async function guestLogin(): Promise<{ email: string; password: string; access_token?: string; id?: string } | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/guest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
      const errDetail = await res.text().catch(() => '');
      console.error(`[Baleen Auth] Guest session request failed at ${API_BASE_URL}/api/auth/guest (status ${res.status}):`, errDetail);
      return null;
    }
    const data = await res.json();
    if (data.access_token) {
      setAuthToken(data.access_token);
    }
    return data;
  } catch (error) {
    console.error(`[Baleen Auth] Network error reaching backend at ${API_BASE_URL}/api/auth/guest:`, error);
    return null;
  }
}

export interface DiscoveryProgress {
  status?: string;
  step_description?: string;
  wallets_scanned?: number;
  gold_snipers?: number;
  progress_pct?: number;
}

export interface AdminStatus {
  discovery_state?: DiscoveryProgress;
  uptime_seconds?: number;
  last_cron_ping?: number | null;
  database?: {
    type?: string;
    using_sqlite_fallback?: boolean;
    totalUsers?: number;
    totalTrades?: number;
  };
  db?: {
    users?: number;
    trades?: number;
  };
  db_stats?: {
    total?: number;
    active?: number;
    pending?: number;
    rejected?: number;
  };
  audit?: {
    last_discovery_at?: string;
    last_scoring_at?: string;
    gold_snipers?: number;
    standard_whales?: number;
    rejection_breakdown?: { reason: string; count: number }[];
  };
}

export interface AdminWallet {
  address: string;
  status?: string;
  tier?: string;
  score?: number;
  baleenScore?: number;
  baleen_score?: number;
  winRatePct?: number;
  win_rate_pct?: number;
  allTimePnlUsd?: number;
  all_time_pnl_usd?: number;
  rejectionReason?: string;
  rejection_reason?: string;
  aiStyleTag?: string;
}

export function getCachedAdminStatus(): AdminStatus | null {
  return getCached<AdminStatus>('admin_status', 30000);
}

export function getCachedAdminWallets(status?: string): AdminWallet[] | null {
  return getCached<AdminWallet[]>(`admin_wallets_${status || 'all'}`, 30000);
}

export async function fetchAdminStatus(): Promise<AdminStatus | null> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}/api/admin/status`);
    if (!res.ok) return getCachedAdminStatus();
    const data = await res.json();
    setCached('admin_status', data);
    return data;
  } catch { return getCachedAdminStatus(); }
}

export async function fetchAdminWallets(status?: string): Promise<AdminWallet[]> {
  const cacheKey = `admin_wallets_${status || 'all'}`;
  try {
    const url = new URL(`${API_BASE_URL}/api/admin/wallets`);
    if (status) url.searchParams.append('status', status);
    const res = await fetchWithAuth(url.toString());
    if (!res.ok) return getCachedAdminWallets(status) || [];
    const data = await res.json();
    setCached(cacheKey, data);
    return data;
  } catch { return getCachedAdminWallets(status) || []; }
}

export async function reEvaluateWallets(): Promise<{ status: string; evaluated?: number; active?: number; message?: string } | null> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}/api/admin/re-evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function purgeAndRescanWallets(): Promise<{ status: string; message: string } | null> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}/api/admin/purge-and-rescan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchDiscoveryProgress(): Promise<DiscoveryProgress | null> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}/api/admin/discovery-progress`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function hardWipeAllDatabase(): Promise<{ status: string; message: string } | null> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}/api/admin/hard-wipe-all`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchSystemEvents(limit: number = 100, eventType?: string): Promise<SystemEvent[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/events`);
    url.searchParams.append('limit', String(limit));
    if (eventType) url.searchParams.append('event_type', eventType);
    const res = await fetchWithAuth(url.toString());
    if (!res.ok) return [];
    return await res.json();
  } catch (error) {
    return [];
  }
}

export async function fetchCopilotChat(messages: { role: string; content: string }[]): Promise<{
  message: string;
  tool_calls_executed?: { name: string; args: Record<string, unknown>; summary: string }[];
} | null> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}/api/copilot/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages })
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    console.error('Copilot API error:', error);
    return null;
  }
}

// ---------------------------------------------------------------------------
// L2 Live Trading & CLOB Credentials
// ---------------------------------------------------------------------------

export async function saveLiveCredentials(data: {
  userId?: string;
  polymarketWalletAddress: string;
  clobApiKey: string;
  clobApiSecret: string;
  clobApiPassphrase: string;
  signerAddress?: string;
  signatureType?: number;
}): Promise<LiveTradingCredentials | null> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}/api/live-trading/credentials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: data.userId,
        polymarket_wallet_address: data.polymarketWalletAddress,
        clob_api_key: data.clobApiKey,
        clob_api_secret: data.clobApiSecret,
        clob_api_passphrase: data.clobApiPassphrase,
        signer_address: data.signerAddress,
        signature_type: data.signatureType,
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to save live credentials');
    }
    return await res.json();
  } catch (error) {
    console.error('Error saving live credentials:', error);
    throw error;
  }
}

export async function fetchLiveCredentials(userId?: string): Promise<LiveTradingCredentials | null> {
  try {
    const url = new URL(`${API_BASE_URL}/api/live-trading/credentials`);
    if (userId) url.searchParams.append('user_id', userId);
    const res = await fetchWithAuth(url.toString());
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    console.debug('Error fetching live credentials:', error);
    return null;
  }
}

export async function testLiveConnection(data: {
  userId?: string;
  polymarketWalletAddress?: string;
  clobApiKey?: string;
  clobApiSecret?: string;
  clobApiPassphrase?: string;
  signerAddress?: string;
  signatureType?: number;
}): Promise<TestConnectionResult> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}/api/live-trading/test-connection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: data.userId,
        polymarket_wallet_address: data.polymarketWalletAddress,
        clob_api_key: data.clobApiKey,
        clob_api_secret: data.clobApiSecret,
        clob_api_passphrase: data.clobApiPassphrase,
        signer_address: data.signerAddress,
        signature_type: data.signatureType,
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Connection test failed');
    }
    return await res.json();
  } catch (error: unknown) {
    console.error('Test connection error:', error);
    throw error;
  }
}

export async function toggleLiveTrading(enabled: boolean, userId?: string): Promise<{ success: boolean; is_live_active: boolean; status: string }> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}/api/live-trading/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        enabled
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to toggle live trading');
    }
    return await res.json();
  } catch (error) {
    console.error('Toggle live trading error:', error);
    throw error;
  }
}

export async function fetchLiveDashboard(userId?: string): Promise<LiveTradingDashboard | null> {
  try {
    const url = new URL(`${API_BASE_URL}/api/live-trading/dashboard`);
    if (userId) url.searchParams.append('user_id', userId);
    const res = await fetchWithAuth(url.toString(), { cache: 'no-store' });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    console.debug('Error fetching live dashboard:', error);
    return null;
  }
}

export interface LiveExecutionState {
  status: string;
  reason?: string | null;
  liveExecutionReady?: false;
  runId?: string | null;
  cash?: string | null;
  reservedCash?: string | null;
  availableCash?: string | null;
  reconciledAt?: string | null;
  collateralCurrency?: string | null;
  reconciliation?: {
    status?: string | null;
    detail?: string | null;
    finishedAt?: string | null;
  } | null;
  positions?: {
    tokenId?: string | null;
    quantity?: string | null;
    reservedQuantity?: string | null;
    costBasis?: string | null;
  }[] | null;
  orders?: {
    id?: string | null;
    tokenId?: string | null;
    side?: string | null;
    state?: string | null;
    quantity?: string | null;
    filledQuantity?: string | null;
    limitPrice?: string | null;
    cancelRequestedAt?: string | null;
  }[] | null;
}

export async function fetchLiveExecutionState(): Promise<LiveExecutionState | null> {
  try {
    const res = await fetchWithAuth(`${API_BASE_URL}/api/live-trading/execution-state`, { cache: 'no-store' });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export function getLiveOrderStateLabel(order: Pick<NonNullable<LiveExecutionState['orders']>[number], 'state' | 'cancelRequestedAt'>): string {
  if (!order.state) return 'Unavailable';
  const terminalStates = new Set(['CANCELLED', 'FILLED', 'VOID']);
  if (order.cancelRequestedAt && !terminalStates.has(order.state.toUpperCase())) {
    return 'Pending cancellation';
  }
  return order.state;
}

// ---------------------------------------------------------------------------
// Error & Date Formatting Helpers
// ---------------------------------------------------------------------------

export function extractApiErrorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === 'object') {
    const detail = (err as { detail?: unknown }).detail ?? (err as { message?: unknown }).message;
    if (typeof detail === 'string' && detail.trim()) return detail.trim();
    if (Array.isArray(detail)) {
      const messages = detail
        .map(item => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object') {
            const msg = (item as { msg?: unknown }).msg;
            const loc = (item as { loc?: unknown }).loc;
            const field = Array.isArray(loc) ? loc.slice(1).join('.') : '';
            if (typeof msg === 'string') {
              return field ? `${field}: ${msg}` : msg;
            }
          }
          return null;
        })
        .filter((m): m is string => Boolean(m));
      if (messages.length > 0) return messages.join('; ');
    }
  }
  return fallback;
}

export function formatUtcDate(dateInput?: string | number | Date | null): string {
  if (dateInput === null || dateInput === undefined || dateInput === '') return 'Unavailable';
  let d: Date;
  if (dateInput instanceof Date) {
    d = dateInput;
  } else if (typeof dateInput === 'number') {
    d = new Date(dateInput > 1e11 ? dateInput : dateInput * 1000);
  } else if (typeof dateInput === 'string') {
    const s = dateInput.trim();
    if (!s) return 'Unavailable';
    if (/^\d+$/.test(s)) {
      const num = Number(s);
      d = new Date(num > 1e11 ? num : num * 1000);
    } else {
      // If ISO format without explicit timezone offset or Z suffix, append Z so it is parsed as UTC
      const isoCandidate = !/[zZ]$/.test(s) && !/[+-]\d{2}(:\d{2})?$/.test(s)
        ? s.replace(' ', 'T') + 'Z'
        : s;
      d = new Date(isoCandidate);
    }
  } else {
    d = new Date(dateInput);
  }
  if (isNaN(d.getTime())) return 'Unavailable';
  const pad = (n: number) => String(n).padStart(2, '0');
  const year = d.getUTCFullYear();
  const month = pad(d.getUTCMonth() + 1);
  const day = pad(d.getUTCDate());
  const hours = pad(d.getUTCHours());
  const mins = pad(d.getUTCMinutes());
  const secs = pad(d.getUTCSeconds());
  return `${year}-${month}-${day} ${hours}:${mins}:${secs} UTC`;
}

// ---------------------------------------------------------------------------
// Account-Bound Deposit Wallet Session Setup & Owner Operations
// ---------------------------------------------------------------------------

export async function fetchSessionSetup(): Promise<LiveSessionSetup> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/live-trading/session`, { cache: 'no-store' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(extractApiErrorMessage(err, 'Failed to fetch signing session'));
  }
  return await res.json();
}

export async function prepareSession(): Promise<LiveSessionSetup> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/live-trading/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(extractApiErrorMessage(err, 'Failed to prepare signing session'));
  }
  return await res.json();
}

export async function verifySession(): Promise<LiveSessionSetup> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/live-trading/session/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(extractApiErrorMessage(err, 'Owner-approved CLOB session authorization is not verified'));
  }
  return await res.json();
}

export async function disableSession(): Promise<{ localSigningDisabled: boolean; ownerRevocationRequired: boolean; message: string }> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/live-trading/session/disable`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(extractApiErrorMessage(err, 'Failed to stop local signing session'));
  }
  return await res.json();
}

export async function fetchSessionOperations(): Promise<SessionOperation[]> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/live-trading/session/operations`, { cache: 'no-store' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(extractApiErrorMessage(err, 'Failed to fetch session operations'));
  }
  return await res.json();
}

export async function prepareSessionOperation(kind: 'AUTHORIZE' | 'REVOKE'): Promise<SessionOperation> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/live-trading/session/operations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(extractApiErrorMessage(err, 'Session operation unavailable'));
  }
  return await res.json();
}

export async function submitSessionSignature(operationId: string, signature: string): Promise<SessionOperation> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/live-trading/session/operations/${operationId}/signature`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signature }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(extractApiErrorMessage(err, 'Operation signature could not be confirmed'));
  }
  return await res.json();
}

export async function initializeLiveAccount(): Promise<LiveAccountInitialization> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/live-trading/initialize-account`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(extractApiErrorMessage(err, 'Live account initialization failed'));
  }
  return await res.json();
}

// ---------------------------------------------------------------------------
// Explicit Copy Policy & Enforced Risk Limits
// ---------------------------------------------------------------------------

export async function fetchCopyPolicy(): Promise<LiveCopyPolicy | null> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/live-trading/copy-policy`, { cache: 'no-store' });
  if (!res.ok) {
    if (res.status === 404) return null;
    const err = await res.json().catch(() => ({}));
    throw new Error(extractApiErrorMessage(err, 'Failed to fetch copy policy'));
  }
  return await res.json();
}

export async function saveCopyPolicy(policy: CopyPolicyRequest): Promise<LiveCopyPolicy> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/live-trading/copy-policy`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(policy),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(extractApiErrorMessage(err, 'Failed to save copy policy'));
  }
  return await res.json();
}

// ---------------------------------------------------------------------------
// Account-Owned Paper Run Archive & Retained Journals
// ---------------------------------------------------------------------------

export async function fetchPaperRuns(userId: string): Promise<PaperRun[]> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/users/${userId}/paper-runs`, { cache: 'no-store' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(extractApiErrorMessage(err, 'Failed to fetch paper runs'));
  }
  return await res.json();
}

export async function fetchPaperRunTrades(userId: string, runId: string): Promise<PaperRunTrade[]> {
  const res = await fetchWithAuth(`${API_BASE_URL}/api/users/${userId}/paper-runs/${runId}/trades`, { cache: 'no-store' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(extractApiErrorMessage(err, 'Failed to fetch paper run trades'));
  }
  return await res.json();
}


