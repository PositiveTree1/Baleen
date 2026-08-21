import { Wallet, WalletDetail, ExecutionLog, User, PlatformStats } from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

// Global In-Memory Cache (persists across Next.js page navigations in browser)
const memoryCache = new Map<string, { data: any; ts: number }>();

function getCached<T>(key: string, maxAgeMs: number = 60000): T | null {
  const entry = memoryCache.get(key);
  if (entry && (Date.now() - entry.ts) < maxAgeMs) {
    return entry.data as T;
  }
  if (typeof window !== 'undefined') {
    try {
      const raw = sessionStorage.getItem(`baleen_cache_${key}`);
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

function setCached(key: string, data: any) {
  const entry = { data, ts: Date.now() };
  memoryCache.set(key, entry);
  if (typeof window !== 'undefined') {
    try {
      sessionStorage.setItem(`baleen_cache_${key}`, JSON.stringify(entry));
    } catch {}
  }
}

// Synchronous instant-read cache getters for initial component states
export function getCachedWallets(): Wallet[] | null {
  return getCached<Wallet[]>('wallets_list', 120000);
}

export function getCachedExecutionLogs(userId?: string): ExecutionLog[] | null {
  return getCached<ExecutionLog[]>(`exec_logs_${userId || 'all'}`, 60000);
}

export function getCachedPortfolioSummary(userId?: string): {
  startingBalance: number;
  currentBalance: number;
  totalPnlUsd: number;
  totalPnlPct: number;
  totalFeesPaidUsd?: number;
  filledTradesCount: number;
  totalNotionalInvested: number;
} | null {
  return getCached(`portfolio_summary_${userId || 'all'}`, 60000);
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

export async function fetchWallets(params?: Record<string, string>): Promise<Wallet[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/wallets`);
    if (params) {
      Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
    }
    const res = await fetch(url.toString(), { next: { revalidate: 60 } });
    if (!res.ok) return getCachedWallets() || [];
    const data = await res.json();
    const result = data.map((w: any) => ({
      address: w.address,
      name: w.name || null,
      pseudonym: w.pseudonym || null,
      profileImage: w.profileImage || null,
      tier: w.tier,
      winRate: w.win_rate_pct || 0,
      wilsonLb: w.wilson_lb ?? null,
      pnl: w.all_time_pnl_usd || 0,
      tradesPerDay: w.avg_trades_per_day || 0,
      tradesPerHour: w.trades_per_hour ?? null,
      score: w.baleen_score || 0,
      isHft: Boolean(w.is_hft),
      dormant: Boolean(w.dormant),
      alphaPerTrade: w.alpha_per_trade ?? null,
      profitFactor: w.profit_factor ?? null,
      firstTradeAt: w.first_trade_at || null,
      lastTradeAt: w.last_trade_at || null,
      aiStyleTag: w.ai_style_tag || null
    }));
    setCached('wallets_list', result);
    return result;
  } catch (error) {
    return getCachedWallets() || [];
  }
}

export async function fetchWallet(address: string): Promise<WalletDetail | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/wallets/${address}`);
    if (!res.ok) return null;
    const data = await res.json();
    const w = data.wallet || data;
    return {
      address: w.address,
      name: w.name || null,
      pseudonym: w.pseudonym || null,
      profileImage: w.profileImage || null,
      tier: w.tier,
      winRate: w.win_rate_pct || 0,
      wilsonLb: w.wilson_lb ?? null,
      pnl: w.all_time_pnl_usd || 0,
      tradesPerDay: w.avg_trades_per_day || 0,
      tradesPerHour: w.trades_per_hour ?? null,
      score: w.baleen_score || 0,
      isHft: Boolean(w.is_hft),
      dormant: Boolean(w.dormant),
      alphaPerTrade: w.alpha_per_trade ?? null,
      profitFactor: w.profit_factor ?? null,
      firstTradeAt: w.first_trade_at || null,
      lastTradeAt: w.last_trade_at || null,
      aiStyleTag: w.ai_style_tag || null,
      aiSummary: w.ai_summary || null,
      maxDrawdown: w.max_drawdown_pct || 0,
      scoreHistory: (data.score_history || []).map((s: any) => ({ 
        date: s.snapshot_at || s.date || new Date().toISOString(), 
        score: s.baleen_score ?? s.score ?? 75 
      })),
      dailyPnLHistory: (data.daily_pnl_history || []).map((d: any) => ({
        date: d.date,
        wonUsd: d.won_usd ?? Math.max(0, d.daily_pnl ?? 0),
        lostUsd: d.lost_usd ?? (d.daily_pnl < 0 ? d.daily_pnl : 0),
        netPnL: d.net_pnl ?? d.daily_pnl ?? 0,
        dailyPnL: d.daily_pnl ?? 0,
        cumulativePnL: d.cumulative_pnl ?? 0,
        tradesCount: d.trades_count ?? 1
      })),
      recentTrades: (data.recent_trades || []).map((t: any) => ({
        id: t.id,
        timestamp: t.executed_at,
        walletAddress: address,
        marketQuestion: t.market_id || 'Polymarket Condition',
        marketConditionId: t.market_id,
        side: t.side,
        entryPrice: t.fill_price || 0.5,
        fillPrice: t.fill_price || 0.5,
        size: t.size_usd || 0,
        status: t.status,
        pnl: t.pnl_usd || 0,
        polymarketUrl: t.market_id ? `https://polymarket.com/market/${t.market_id}` : 'https://polymarket.com'
      }))
    };
  } catch (error) {
    return null;
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
    const res = await fetch(url.toString());
    if (!res.ok) return getCachedExecutionLogs(userId) || [];
    const data = await res.json();
    const result = data.map((log: any) => ({
      id: log.id,
      timestamp: log.timestamp || log.executed_at,
      walletAddress: log.walletAddress || log.source_wallet_address,
      whaleName: log.whaleName || null,
      whalePseudonym: log.whalePseudonym || null,
      whaleAvatar: log.whaleAvatar || null,
      whaleTier: log.whaleTier || null,
      marketQuestion: log.marketQuestion || log.market_question,
      marketConditionId: log.marketConditionId || log.market_condition_id,
      eventSlug: log.eventSlug,
      icon: log.icon,
      side: log.side,
      outcome: log.outcome || 'Yes',
      entryPrice: log.entryPrice ?? log.whale_entry_price ?? 0,
      fillPrice: log.fillPrice ?? log.user_fill_price ?? 0,
      currentPrice: log.currentPrice ?? log.fillPrice ?? log.user_fill_price ?? 0,
      size: log.size ?? log.notional_usd ?? 0,
      status: log.status,
      pnl: log.pnl ?? log.realized_pnl_usd ?? 0,
      grossPnl: log.grossPnl ?? 0,
      pnlPct: log.pnlPct ?? 0,
      feeUsd: log.feeUsd ?? 0,
      marketCategory: log.marketCategory ?? 'General',
      categoryRate: log.categoryRate ?? 0.05,
      consensus: log.consensus ?? { whale_count: 1, total_cash: 0, is_consensus: false },
      polymarketUrl: log.polymarketUrl ?? (log.eventSlug ? `https://polymarket.com/event/${log.eventSlug}` : (log.marketConditionId ? `https://polymarket.com/market/${log.marketConditionId}` : 'https://polymarket.com')),
    }));
    if (result.length > 0 || !getCachedExecutionLogs(userId)) {
      setCached(cacheKey, result);
    }
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
    const res = await fetch(`${API_BASE_URL}/api/executions/${tradeId}/chart`);
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
  }
}

export async function fetchPortfolioSummary(userId?: string, timeframe?: string): Promise<{
  startingBalance: number;
  currentBalance: number;
  totalPnlUsd: number;
  totalPnlPct: number;
  totalFeesPaidUsd?: number;
  filledTradesCount: number;
  totalNotionalInvested: number;
} | null> {
  const cacheKey = `portfolio_summary_${userId || 'all'}`;
  try {
    const url = new URL(`${API_BASE_URL}/api/executions/summary`);
    if (userId) url.searchParams.append('userId', userId);
    if (timeframe) url.searchParams.append('timeframe', timeframe);
    const res = await fetch(url.toString());
    if (!res.ok) return getCachedPortfolioSummary(userId);
    const data = await res.json();
    if (data) {
      setCached(cacheKey, data);
    }
    return data;
  } catch (error) {
    return getCachedPortfolioSummary(userId);
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
    if (userId) url.searchParams.append('userId', userId);
    if (timeframe) url.searchParams.append('timeframe', timeframe);
    url.searchParams.append('limit', '200');
    const res = await fetch(url.toString());
    if (!res.ok) return getCachedPortfolioSnapshots(userId, timeframe) || [];
    const data = await res.json();
    if (Array.isArray(data) && data.length > 0) {
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
  tradesCopied: number;
  totalNotional: number;
  netPnl: number;
  roiPct: number;
  winRateCopied: number;
  profitFactor: number;
  wins: number;
  losses: number;
}[]> {
  const cacheKey = `copied_stats_${userId || 'all'}`;
  try {
    const url = userId 
      ? `${API_BASE_URL}/api/wallets/copied-stats?userId=${encodeURIComponent(userId)}`
      : `${API_BASE_URL}/api/wallets/copied-stats`;
    const res = await fetch(url);
    if (!res.ok) return getCached(cacheKey) || [];
    const data = await res.json();
    setCached(cacheKey, data);
    return data;
  } catch (error) {
    return getCached(cacheKey) || [];
  }
}

export async function fetchUserSettings(userId: string): Promise<User | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/users/${userId}`);
    if (!res.ok) return null;
    const data = await res.json();
    return {
      id: data.id,
      email: data.email,
      startingBalance: data.startingBalance ?? data.sandbox_starting_balance_usd ?? 10000,
      currentBalance: data.currentBalance ?? data.sandbox_balance_usd ?? 10000,
      riskProfile: data.riskProfile ?? data.risk_profile ?? 'Balanced',
      dailyDigestOptIn: data.dailyDigestOptIn ?? data.daily_digest_opt_in ?? true,
    };
  } catch (error) {
    return null;
  }
}

export async function updateUserSettings(userId: string, data: Partial<User>): Promise<User | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/users/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        risk_profile: data.riskProfile,
        daily_digest_opt_in: data.dailyDigestOptIn,
      }),
    });
    if (!res.ok) return null;
    const result = await res.json();
    return {
      id: result.id,
      email: result.email,
      startingBalance: result.startingBalance ?? result.sandbox_starting_balance_usd ?? 10000,
      currentBalance: result.currentBalance ?? result.sandbox_balance_usd ?? 10000,
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
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ newBalance }),
    });
    return res.ok;
  } catch (error) {
    return false;
  }
}

export async function resetSandboxLedger(userId?: string): Promise<boolean> {
  try {
    const url = new URL(`${API_BASE_URL}/api/executions/reset-sandbox`);
    if (userId) url.searchParams.append('userId', userId);
    const res = await fetch(url.toString(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
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

export async function guestLogin(): Promise<{ email: string; password: string } | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/guest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
  }
}

export function getCachedAdminStatus(): any {
  return getCached('admin_status', 30000);
}

export function getCachedAdminWallets(status?: string): any[] | null {
  return getCached(`admin_wallets_${status || 'all'}`, 30000);
}

export async function fetchAdminStatus(): Promise<any> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/status`);
    if (!res.ok) return getCachedAdminStatus();
    const data = await res.json();
    setCached('admin_status', data);
    return data;
  } catch { return getCachedAdminStatus(); }
}

export async function fetchAdminWallets(status?: string): Promise<any[]> {
  const cacheKey = `admin_wallets_${status || 'all'}`;
  try {
    const url = new URL(`${API_BASE_URL}/api/admin/wallets`);
    if (status) url.searchParams.append('status', status);
    const res = await fetch(url.toString());
    if (!res.ok) return getCachedAdminWallets(status) || [];
    const data = await res.json();
    setCached(cacheKey, data);
    return data;
  } catch { return getCachedAdminWallets(status) || []; }
}

export async function reEvaluateWallets(): Promise<{ status: string; evaluated?: number; active?: number; message?: string } | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/re-evaluate`, {
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
    const res = await fetch(`${API_BASE_URL}/api/admin/purge-and-rescan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchDiscoveryProgress(): Promise<any> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/discovery-progress`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function hardWipeAllDatabase(): Promise<{ status: string; message: string } | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/hard-wipe-all`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchSystemEvents(limit: number = 100, eventType?: string): Promise<{
  id: string;
  eventType: string;
  severity: string;
  title: string;
  detail?: string;
  relatedAddress?: string;
  relatedMarket?: string;
  createdAt: string;
}[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/events`);
    url.searchParams.append('limit', String(limit));
    if (eventType) url.searchParams.append('event_type', eventType);
    const res = await fetch(url.toString());
    if (!res.ok) return [];
    return await res.json();
  } catch (error) {
    return [];
  }
}


