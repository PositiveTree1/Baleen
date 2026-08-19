'use client';
import { useEffect, useState, useMemo } from 'react';
import { ExecutionLog } from '@/types';
import { fetchPortfolioSnapshots } from '@/lib/api-client';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';
import { TrendingUp, TrendingDown, Award, AlertTriangle, ShieldCheck, DollarSign, PieChart, Zap, Calendar } from 'lucide-react';

interface PortfolioAnalyticsProps {
  logs: ExecutionLog[];
  userId?: string;
  startingBalance?: number;
  currentBalance?: number;
  onSelectTrade?: (trade: ExecutionLog) => void;
}

export function PortfolioAnalytics({
  logs,
  userId,
  startingBalance = 10000.0,
  currentBalance = 10000.0,
  onSelectTrade
}: PortfolioAnalyticsProps) {
  const [timeframe, setTimeframe] = useState<'1D' | '1W' | '1M' | 'YTD' | 'ALL'>('ALL');
  const [snapshots, setSnapshots] = useState<{
    id: string;
    timestamp: string;
    time: string;
    date: string;
    balance: number;
    pnl: number;
    activeTrades: number;
  }[]>([]);

  useEffect(() => {
    async function loadSnapshots() {
      const data = await fetchPortfolioSnapshots(userId, timeframe === 'ALL' ? undefined : timeframe.toLowerCase());
      if (data && data.length > 0) {
        setSnapshots(data);
      } else {
        setSnapshots([]);
      }
    }
    loadSnapshots();
    const interval = setInterval(loadSnapshots, 8000);
    return () => clearInterval(interval);
  }, [userId, timeframe]);

  // Filter logs by selected timeframe
  const filteredLogs = useMemo(() => {
    if (timeframe === 'ALL') return logs;
    const now = Date.now();
    let cutoff = 0;
    if (timeframe === '1D') cutoff = now - 24 * 60 * 60 * 1000;
    else if (timeframe === '1W') cutoff = now - 7 * 24 * 60 * 60 * 1000;
    else if (timeframe === '1M') cutoff = now - 30 * 24 * 60 * 60 * 1000;
    else if (timeframe === 'YTD') cutoff = new Date(new Date().getFullYear(), 0, 1).getTime();

    return logs.filter(l => {
      if (!l.timestamp) return true;
      const t = new Date(l.timestamp).getTime();
      return t >= cutoff;
    });
  }, [logs, timeframe]);

  // 1. Calculate Winners and Losers and timeline
  const { topWinner, topLoser, winCount, lossCount, winRate, totalResolved, pnlTimeline, periodNetPnL } = useMemo(() => {
    let bestWin: ExecutionLog | null = null;
    let worstLoss: ExecutionLog | null = null;
    let wins = 0;
    let losses = 0;
    let pnlSum = 0;

    for (const log of filteredLogs) {
      const pnl = log.pnl ?? 0;
      pnlSum += pnl;
      if (pnl > 0) {
        wins++;
        if (!bestWin || pnl > (bestWin.pnl ?? 0)) {
          bestWin = log;
        }
      } else if (pnl < 0) {
        losses++;
        if (!worstLoss || pnl < (worstLoss.pnl ?? 0)) {
          worstLoss = log;
        }
      }
    }

    const totalResolved = wins + losses;
    const wr = totalResolved > 0 ? (wins / totalResolved) * 100 : 0.0;

    let timeline = [];
    if (snapshots.length >= 2) {
      timeline = snapshots.map(s => ({
        time: s.time || '00:00',
        balance: s.balance,
        pnl: s.pnl,
        date: s.date || 'Today'
      }));
    } else {
      // Build chronological curve from trades
      const sortedLogs = [...filteredLogs].sort((a, b) => {
        const ta = a.timestamp ? new Date(a.timestamp).getTime() : 0;
        const tb = b.timestamp ? new Date(b.timestamp).getTime() : 0;
        return ta - tb;
      });

      let running = startingBalance;
      timeline.push({
        time: 'Start',
        balance: startingBalance,
        pnl: 0,
        date: 'Base'
      });

      for (const log of sortedLogs) {
        const pnl = log.pnl ?? 0;
        running += pnl;
        const dateStr = log.timestamp ? new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
        timeline.push({
          time: dateStr || `T-${timeline.length}`,
          balance: Math.round(running * 100) / 100,
          pnl: Math.round(pnl * 100) / 100,
          date: log.timestamp ? new Date(log.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' }) : ''
        });
      }
    }

    return {
      topWinner: bestWin,
      topLoser: worstLoss,
      winCount: wins,
      lossCount: losses,
      winRate: wr,
      totalResolved,
      pnlTimeline: timeline,
      periodNetPnL: pnlSum
    };
  }, [filteredLogs, snapshots, startingBalance]);

  const isNetPositive = currentBalance >= startingBalance;
  const netPnL = timeframe === 'ALL' ? (currentBalance - startingBalance) : periodNetPnL;
  const netPnLPct = startingBalance > 0 ? (netPnL / startingBalance) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Top Banner: Chart + Win/Loss Ratio */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Net Worth Performance Area Chart */}
        <div className="lg:col-span-2 p-6 rounded-3xl bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_16px_36px_-6px_rgba(0,0,0,0.05)] space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Sandbox Capital Curve</span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                  <Zap size={10} /> Live Blockchain MTM
                </span>
              </div>
              <div className="flex items-baseline gap-3 mt-1">
                <span className="text-3xl font-extrabold font-mono text-slate-950">
                  ${currentBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className={`text-sm font-mono font-bold ${netPnL >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {netPnL >= 0 ? '+' : ''}${netPnL.toFixed(2)} ({netPnL >= 0 ? '+' : ''}{netPnLPct.toFixed(2)}%)
                </span>
              </div>
            </div>

            {/* Timeframe selector */}
            <div className="flex items-center gap-2">
              <div className="flex rounded-xl bg-slate-100 p-0.5 border border-black/[0.06] text-xs font-mono font-semibold">
                {(['1D', '1W', '1M', 'YTD', 'ALL'] as const).map((tf) => (
                  <button
                    key={tf}
                    onClick={() => setTimeframe(tf)}
                    className={`px-2.5 py-1 rounded-lg transition-all cursor-pointer ${
                      timeframe === tf 
                        ? 'bg-white text-slate-950 font-bold shadow-xs' 
                        : 'text-slate-500 hover:text-slate-900'
                    }`}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Area Chart */}
          <div className="h-56 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={pnlTimeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="balanceGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={netPnL >= 0 ? '#10B981' : '#F43F5E'} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={netPnL >= 0 ? '#10B981' : '#F43F5E'} stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis 
                  dataKey="time" 
                  tick={{ fontSize: 10, fill: '#94A3B8' }} 
                  axisLine={false} 
                  tickLine={false}
                />
                <YAxis 
                  domain={['auto', 'auto']} 
                  tick={{ fontSize: 10, fill: '#94A3B8' }} 
                  axisLine={false} 
                  tickLine={false}
                  tickFormatter={(val) => `$${Math.round(val).toLocaleString()}`}
                />
                <Tooltip 
                  isAnimationActive={false}
                  cursor={{ stroke: '#6366F1', strokeWidth: 1.5, strokeDasharray: '3 3' }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload;
                      return (
                        <div className="bg-slate-950 text-white px-3.5 py-2.5 rounded-2xl text-xs font-mono shadow-2xl border border-white/10">
                          <div className="text-[10px] text-slate-400">{d.date} • {d.time}</div>
                          <div className="text-base font-bold text-white mt-0.5">${d.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                          <div className={`text-[11px] font-bold ${d.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {d.pnl >= 0 ? '+' : ''}${d.pnl.toFixed(2)} Trade Impact
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Area 
                  type="monotone" 
                  dataKey="balance" 
                  stroke={netPnL >= 0 ? '#10B981' : '#F43F5E'} 
                  strokeWidth={2.5}
                  fillOpacity={1} 
                  fill="url(#balanceGradient)"
                  dot={false}
                  activeDot={{ r: 5, fill: netPnL >= 0 ? '#10B981' : '#F43F5E', stroke: '#FFFFFF', strokeWidth: 2 }}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right: Portfolio Win/Loss & Execution Health Card */}
        <div className="p-6 rounded-3xl bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_16px_36px_-6px_rgba(0,0,0,0.05)] flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Execution Scorecard</span>
              <span className="text-[10px] font-mono font-bold bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                {timeframe} Window
              </span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold font-mono text-slate-900">
                {winRate.toFixed(1)}%
              </span>
              <span className="text-xs font-mono font-semibold text-slate-500">
                Win Rate ({winCount}W / {lossCount}L)
              </span>
            </div>
          </div>

          {/* Win/Loss Bar Visualizer */}
          <div className="space-y-1.5">
            <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden flex p-0.5 border border-black/[0.04]">
              <div 
                className="h-full bg-emerald-500 rounded-full transition-all duration-500" 
                style={{ width: `${Math.max(4, winRate)}%` }} 
              />
              <div 
                className="h-full bg-rose-500 rounded-full transition-all duration-500" 
                style={{ width: `${Math.max(4, 100 - winRate)}%` }} 
              />
            </div>
            <div className="flex justify-between text-[10px] font-mono font-semibold text-slate-400">
              <span className="text-emerald-700">{winCount} Profitable Fills</span>
              <span className="text-rose-700">{lossCount} Unprofitable Fills</span>
            </div>
          </div>

          {/* Sizing & Dynamic Fee Statistics */}
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-black/[0.06]">
            <div className="p-2.5 rounded-2xl bg-slate-50 border border-black/[0.04] space-y-0.5">
              <div className="text-[10px] font-bold text-slate-400 uppercase">Resolved Trades</div>
              <div className="text-sm font-mono font-bold text-slate-900">{totalResolved} Fills</div>
            </div>
            <div className="p-2.5 rounded-2xl bg-slate-50 border border-black/[0.04] space-y-0.5">
              <div className="text-[10px] font-bold text-slate-400 uppercase">Starting Principal</div>
              <div className="text-sm font-mono font-bold text-slate-900">${startingBalance.toLocaleString()}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Section: Top Winner vs Top Loser Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Top Winner Card */}
        <div 
          onClick={() => topWinner && onSelectTrade && onSelectTrade(topWinner)}
          className={`p-5 rounded-3xl bg-emerald-50/40 border border-emerald-200/80 transition-all ${
            topWinner ? 'hover:shadow-md cursor-pointer hover:border-emerald-300' : 'opacity-60'
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-800 border border-emerald-200">
                <Award size={16} />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-900">Highest Alpha Trade ({timeframe})</span>
            </div>
            {topWinner && (
              <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-100/60 px-2 py-0.5 rounded-full border border-emerald-300">
                +${(topWinner.pnl ?? 0).toFixed(2)} (+{(topWinner.pnlPct ?? 0).toFixed(1)}%)
              </span>
            )}
          </div>

          {topWinner ? (
            <div className="space-y-2">
              <div className="text-sm font-bold text-slate-900 leading-snug truncate" title={topWinner.marketQuestion}>
                {topWinner.marketQuestion}
              </div>
              <div className="flex items-center gap-3 text-xs font-mono text-slate-600">
                <span>Filled @ ${(topWinner.fillPrice ?? 0.5).toFixed(3)}</span>
                <span>•</span>
                <span>Live MTM @ ${(topWinner.currentPrice ?? 0.5).toFixed(3)}</span>
                <span>•</span>
                <span>Size ${topWinner.size?.toLocaleString()}</span>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-400 font-medium">No profitable trade in selected timeframe.</p>
          )}
        </div>

        {/* Top Loser Card */}
        <div 
          onClick={() => topLoser && onSelectTrade && onSelectTrade(topLoser)}
          className={`p-5 rounded-3xl bg-rose-50/40 border border-rose-200/80 transition-all ${
            topLoser ? 'hover:shadow-md cursor-pointer hover:border-rose-300' : 'opacity-60'
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-xl bg-rose-100 flex items-center justify-center text-rose-800 border border-rose-200">
                <AlertTriangle size={16} />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-rose-900">Largest Drawdown Trade ({timeframe})</span>
            </div>
            {topLoser && (
              <span className="text-xs font-mono font-bold text-rose-700 bg-rose-100/60 px-2 py-0.5 rounded-full border border-rose-300">
                ${(topLoser.pnl ?? 0).toFixed(2)} ({(topLoser.pnlPct ?? 0).toFixed(1)}%)
              </span>
            )}
          </div>

          {topLoser ? (
            <div className="space-y-2">
              <div className="text-sm font-bold text-slate-900 leading-snug truncate" title={topLoser.marketQuestion}>
                {topLoser.marketQuestion}
              </div>
              <div className="flex items-center gap-3 text-xs font-mono text-slate-600">
                <span>Filled @ ${(topLoser.fillPrice ?? 0.5).toFixed(3)}</span>
                <span>•</span>
                <span>Live MTM @ ${(topLoser.currentPrice ?? 0.5).toFixed(3)}</span>
                <span>•</span>
                <span>Size ${topLoser.size?.toLocaleString()}</span>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-400 font-medium">No negative trade in selected timeframe.</p>
          )}
        </div>
      </div>
    </div>
  );
}
