import { Wallet, WalletDetail, ExecutionLog, User, PlatformStats } from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function fetchWallets(params?: Record<string, string>): Promise<Wallet[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/wallets`);
    if (params) {
      Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
    }
    const res = await fetch(url.toString(), { next: { revalidate: 60 } });
    if (!res.ok) return [];
    const data = await res.json();
    return data.map((w: any) => ({
      address: w.address,
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
  } catch (error) {
    return [];
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
      recentTrades: data.recent_trades || []
    };
  } catch (error) {
    return null;
  }
}

export async function fetchExecutionLogs(userId?: string, params?: Record<string, string>): Promise<ExecutionLog[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/executions`);
    if (userId) url.searchParams.append('userId', userId);
    if (params) {
      Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
    }
    const res = await fetch(url.toString());
    if (!res.ok) return [];
    const data = await res.json();
    return data.map((log: any) => ({
      id: log.id,
      timestamp: log.timestamp || log.executed_at,
      walletAddress: log.walletAddress || log.source_wallet_address,
      marketQuestion: log.marketQuestion || log.market_question,
      marketConditionId: log.marketConditionId || log.market_condition_id,
      side: log.side,
      entryPrice: log.entryPrice ?? log.whale_entry_price ?? 0,
      fillPrice: log.fillPrice ?? log.user_fill_price ?? 0,
      currentPrice: log.currentPrice ?? log.fillPrice ?? log.user_fill_price ?? 0,
      size: log.size ?? log.notional_usd ?? 0,
      status: log.status,
      pnl: log.pnl ?? log.realized_pnl_usd ?? 0,
      pnlPct: log.pnlPct ?? 0,
      consensus: log.consensus ?? { whale_count: 1, total_cash: 0, is_consensus: false },
      polymarketUrl: log.polymarketUrl ?? (log.marketConditionId ? `https://polymarket.com/event/${log.marketConditionId}` : 'https://polymarket.com'),
    }));
  } catch (error) {
    return [];
  }
}

export async function fetchPortfolioSummary(userId?: string): Promise<{
  startingBalance: number;
  currentBalance: number;
  totalPnlUsd: number;
  totalPnlPct: number;
  filledTradesCount: number;
  totalNotionalInvested: number;
} | null> {
  try {
    const url = userId 
      ? `${API_BASE_URL}/api/executions/summary?userId=${encodeURIComponent(userId)}`
      : `${API_BASE_URL}/api/executions/summary`;
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
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

export async function fetchAdminStatus(): Promise<any> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/status`);
    if (!res.ok) return null;
    return await res.json();
  } catch { return null; }
}

export async function fetchAdminWallets(status?: string): Promise<any[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/admin/wallets`);
    if (status) url.searchParams.append('status', status);
    const res = await fetch(url.toString());
    if (!res.ok) return [];
    return await res.json();
  } catch { return []; }
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

