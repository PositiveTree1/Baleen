'use client';
import { useEffect, useState, useMemo } from 'react';
import { ExecutionLog } from '@/types';
import { fetchPortfolioSnapshots } from '@/lib/api-client';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';
import { TrendingUp, TrendingDown, Award, AlertTriangle, Zap, HelpCircle, Flame, Compass, ArrowUpRight, ArrowDownRight, Sparkles, Filter, CheckCircle2 } from 'lucide-react';
import { formatCompactPnL, formatExactPnL } from '@/lib/formatters';

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
  const [timeframe, setTimeframe] = useState<'1H' | '6H' | '1D' | '1W' | '1M' | 'YTD' | 'ALL'>('ALL');
  const [viewMode, setViewMode] = useState<'curve' | 'attribution'>('curve');
  const [attributionTab, setAttributionTab] = useState<'both' | 'alpha' | 'drawdown'>('both');
  const [snapshots, setSnapshots] = useState<{
    id: string;
    timestamp: string;
    time: string;
    date: string;
    balance: number;
    pnl: number;
    activeTrades: number;
  }[]>([]);

  // Load authentic backend snapshot history
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
    const interval = setInterval(loadSnapshots, 6000);
    return () => clearInterval(interval);
  }, [userId, timeframe]);

  // Filter logs by selected timeframe
  const filteredLogs = useMemo(() => {
    if (timeframe === 'ALL') return logs;
    const now = Date.now();
    let cutoff = 0;
    if (timeframe === '1H') cutoff = now - 60 * 60 * 1000;
    else if (timeframe === '6H') cutoff = now - 6 * 60 * 60 * 1000;
    else if (timeframe === '1D') cutoff = now - 24 * 60 * 60 * 1000;
    else if (timeframe === '1W') cutoff = now - 7 * 24 * 60 * 60 * 1000;
    else if (timeframe === '1M') cutoff = now - 30 * 24 * 60 * 60 * 1000;
    else if (timeframe === 'YTD') cutoff = new Date(new Date().getFullYear(), 0, 1).getTime();

    return logs.filter(l => {
      if (!l.timestamp) return true;
      const t = new Date(l.timestamp).getTime();
      return t >= cutoff;
    });
  }, [logs, timeframe]);

  // Active unique positions count
  const activePositionsCount = useMemo(() => {
    const activeCids = new Set<string>();
    for (const l of logs) {
      if (l.side === 'BUY' && l.status === 'FILLED') {
        activeCids.add(l.marketConditionId || l.id);
      }
    }
    return activeCids.size;
  }, [logs]);

  // Aggregate Market Positions (Eliminates duplicate slice spam)
  const { 
    alphaDrivers, 
    drawdownCulprits, 
    topWinnerLog, 
    topLoserLog, 
    winCount, 
    lossCount, 
    winRate, 
    pnlTimeline, 
    periodNetPnL,
    topSignificantTrades
  } = useMemo(() => {
    let wins = 0;
    let losses = 0;
    let pnlSum = 0;
    let bestWinLog: ExecutionLog | null = null;
    let worstLossLog: ExecutionLog | null = null;

    // 1. Unique Market Position Aggregator
    interface MarketSummary {
      key: string;
      question: string;
      conditionId: string;
      outcome: string;
      totalPnl: number;
      totalNotional: number;
      fillsCount: number;
      avgFillPrice: number;
      currentPrice: number;
      whaleName: string;
      sampleTrade: ExecutionLog;
    }

    const marketMap = new Map<string, MarketSummary>();

    for (const log of filteredLogs) {
      const pnl = log.pnl ?? 0;
      const fillP = log.fillPrice ?? log.entryPrice ?? 0.5;
      const curP = log.currentPrice ?? fillP;
      const notional = log.size ?? 0;
      pnlSum += pnl;

      if (pnl > 0) {
        wins++;
        if (!bestWinLog || pnl > (bestWinLog.pnl ?? 0)) bestWinLog = log;
      } else if (pnl < 0) {
        losses++;
        if (!worstLossLog || pnl < (worstLossLog.pnl ?? 0)) worstLossLog = log;
      }

      const key = log.marketQuestion || log.marketConditionId || log.id;
      if (!marketMap.has(key)) {
        marketMap.set(key, {
          key,
          question: log.marketQuestion || 'Prediction Contract',
          conditionId: log.marketConditionId || '',
          outcome: log.outcome || 'Yes',
          totalPnl: pnl,
          totalNotional: notional,
          fillsCount: 1,
          avgFillPrice: fillP,
          currentPrice: curP,
          whaleName: log.whaleName || log.whalePseudonym || 'Whale',
          sampleTrade: log
        });
      } else {
        const m = marketMap.get(key)!;
        m.totalPnl += pnl;
        m.totalNotional += notional;
        m.fillsCount += 1;
        m.currentPrice = curP;
      }
    }

    const allMarkets = Array.from(marketMap.values());
    const alphaDrivers = allMarkets.filter(m => m.totalPnl > 0).sort((a, b) => b.totalPnl - a.totalPnl).slice(0, 3);
    const drawdownCulprits = allMarkets.filter(m => m.totalPnl < 0).sort((a, b) => a.totalPnl - b.totalPnl).slice(0, 3);

    const totalResolved = wins + losses;
    const wr = totalResolved > 0 ? (wins / totalResolved) * 100 : 0.0;

    // Top 50 significant individual fills for heatpoints
    const topSignificantTrades = [...filteredLogs]
      .sort((a, b) => Math.abs(b.pnl ?? 0) - Math.abs(a.pnl ?? 0))
      .slice(0, 50);

    // 2. Build High-Fidelity Timeline from Backend Snapshots
    interface TimelinePoint {
      time: string;
      balance: number;
      pnl: number;
      date: string;
      isSignificant?: boolean;
      heatColor?: string;
    }

    let timeline: TimelinePoint[] = [];

    if (snapshots.length >= 2) {
      timeline = snapshots.map((s, idx) => ({
        time: s.time || '00:00',
        balance: s.balance,
        pnl: s.pnl,
        date: s.date || 'Today',
        isSignificant: idx % Math.max(1, Math.floor(snapshots.length / 10)) === 0,
        heatColor: s.pnl >= 0 ? '#10B981' : '#F43F5E'
      }));

      // Lock final timeline point to live currentBalance
      const lastSnap = timeline[timeline.length - 1];
      if (Math.abs(lastSnap.balance - currentBalance) > 0.01) {
        timeline.push({
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          balance: Math.round(currentBalance * 100) / 100,
          pnl: Math.round((currentBalance - startingBalance) * 100) / 100,
          date: 'Now'
        });
      }
    } else {
      // Fallback: Chronological trajectory from execution logs
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
        const dObj = log.timestamp ? new Date(log.timestamp) : null;
        timeline.push({
          time: dObj ? dObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : `T-${timeline.length}`,
          balance: Math.round(running * 100) / 100,
          pnl: Math.round((running - startingBalance) * 100) / 100,
          date: dObj ? dObj.toLocaleDateString([], { month: 'short', day: 'numeric' }) : ''
        });
      }

      if (Math.abs(running - currentBalance) > 0.01) {
        timeline.push({
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          balance: Math.round(currentBalance * 100) / 100,
          pnl: Math.round((currentBalance - startingBalance) * 100) / 100,
          date: 'Now'
        });
      }
    }

    return {
      alphaDrivers,
      drawdownCulprits,
      topWinnerLog: bestWinLog,
      topLoserLog: worstLossLog,
      winCount: wins,
      lossCount: losses,
      winRate: wr,
      pnlTimeline: timeline,
      periodNetPnL: pnlSum,
      topSignificantTrades
    };
  }, [filteredLogs, snapshots, startingBalance, currentBalance]);

  const netPnL = timeframe === 'ALL' ? (currentBalance - startingBalance) : periodNetPnL;
  const netPnLPct = startingBalance > 0 ? (netPnL / startingBalance) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Top Banner: Capital Curve + Scorecard */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Net Worth Performance Area Chart */}
        <div className="lg:col-span-2 p-6 rounded-3xl bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_16px_36px_-6px_rgba(0,0,0,0.05)] space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Sandbox Capital Curve</span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                  <Zap size={10} /> Live Blockchain MTM
                </span>
                {/* View Mode Toggle */}
                <div className="flex rounded-xl bg-slate-100 p-0.5 border border-black/[0.06] text-[11px] font-semibold">
                  <button
                    onClick={() => setViewMode('curve')}
                    className={`px-2.5 py-0.5 rounded-lg transition-all cursor-pointer ${
                      viewMode === 'curve' ? 'bg-white text-slate-900 shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    Smooth Curve
                  </button>
                  <button
                    onClick={() => setViewMode('attribution')}
                    className={`px-2.5 py-0.5 rounded-lg transition-all cursor-pointer flex items-center gap-1.5 ${
                      viewMode === 'attribution' ? 'bg-indigo-600 text-white shadow-2xs font-bold' : 'text-slate-500 hover:text-slate-800'
                    }`}
                    title="Top 50 significant trade markers & heatpoints"
                  >
                    <Compass size={11} /> Top 50 Heatpoints
                  </button>
                </div>
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

            {/* Timeframe selector: 1H, 6H, 1D, 1W, 1M, YTD, ALL */}
            <div className="flex items-center gap-1.5">
              <div className="flex rounded-xl bg-slate-100 p-0.5 border border-black/[0.06] text-xs font-mono font-semibold">
                {(['1H', '6H', '1D', '1W', '1M', 'YTD', 'ALL'] as const).map((tf) => (
                  <button
                    key={tf}
                    onClick={() => setTimeframe(tf)}
                    className={`px-2 py-1 rounded-lg transition-all cursor-pointer ${
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

          {/* Area Chart: Clean Smooth Curve without trade popups */}
          <div className="h-56 w-full pt-2 outline-none focus:outline-none ring-0 focus:ring-0 [&_*]:outline-none [&_*]:focus:outline-none select-none">
            <ResponsiveContainer width="100%" height="100%" className="outline-none">
              <AreaChart data={pnlTimeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }} className="outline-none">
                <defs>
                  <linearGradient id="balanceGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={netPnL >= 0 ? '#10B981' : '#F43F5E'} stopOpacity={0.25} />
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
                        <div className="bg-slate-950 text-white px-4 py-3 rounded-2xl text-xs font-mono shadow-2xl border border-white/10 max-w-xs space-y-1">
                          <div className="flex items-center justify-between text-[10px] text-slate-400">
                            <span>{d.date} • {d.time}</span>
                            <span className="font-bold text-slate-300">Sandbox MTM</span>
                          </div>
                          <div className="text-base font-bold text-white">${d.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                          <div className={`text-[11px] font-bold ${d.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {d.pnl >= 0 ? '+' : ''}${d.pnl.toFixed(2)} Mark-to-Market P&amp;L
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Area 
                  type="monotoneX" 
                  dataKey="balance" 
                  stroke={netPnL >= 0 ? '#10B981' : '#F43F5E'} 
                  strokeWidth={2.5}
                  fillOpacity={1} 
                  fill="url(#balanceGradient)"
                  dot={viewMode === 'attribution' ? { r: 3.5, fill: netPnL >= 0 ? '#10B981' : '#F43F5E', stroke: '#FFFFFF', strokeWidth: 1.5 } : false}
                  activeDot={{ r: 6, fill: netPnL >= 0 ? '#10B981' : '#F43F5E', stroke: '#FFFFFF', strokeWidth: 2.5 }}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Quick-Select Top 50 Significant Fills (Attribution Mode) */}
          {viewMode === 'attribution' && topSignificantTrades.length > 0 && (
            <div className="pt-2 border-t border-black/[0.06] space-y-2">
              <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500">
                <span className="flex items-center gap-1.5">
                  <Sparkles size={12} className="text-indigo-600" />
                  Top Significant Alpha &amp; Drawdown Fills ({topSignificantTrades.length})
                </span>
                <span className="text-[10px] text-slate-400 font-mono">1-click to inspect trade details</span>
              </div>
              <div className="flex gap-2 overflow-x-auto pb-1.5 scroll-smooth">
                {topSignificantTrades.slice(0, 20).map((t) => {
                  const pnl = t.pnl ?? 0;
                  const isWin = pnl >= 0;
                  return (
                    <button
                      key={t.id}
                      onClick={() => onSelectTrade && onSelectTrade(t)}
                      className={`px-3 py-1.5 rounded-xl text-[10px] font-mono font-bold whitespace-nowrap flex items-center gap-2 border transition-all cursor-pointer shadow-2xs hover:scale-105 ${
                        isWin 
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100' 
                          : 'bg-rose-50 text-rose-800 border-rose-200 hover:bg-rose-100'
                      }`}
                    >
                      <span className="truncate max-w-[110px]">{t.marketQuestion || 'Event'}</span>
                      <span className={isWin ? 'text-emerald-700' : 'text-rose-700'}>{formatCompactPnL(pnl)}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Right: Execution Scorecard */}
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

          {/* Sizing, Active Positions vs Order Fills */}
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-black/[0.06]">
            <div className="p-2.5 rounded-2xl bg-slate-50 border border-black/[0.04] space-y-0.5">
              <div className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1">
                Active Positions
                <span title="A Position is your active aggregated contracts in an open prediction market." className="cursor-help text-slate-400 hover:text-slate-600">
                  <HelpCircle size={10} />
                </span>
              </div>
              <div className="text-sm font-mono font-bold text-emerald-700">{activePositionsCount} Open</div>
            </div>
            <div className="p-2.5 rounded-2xl bg-slate-50 border border-black/[0.04] space-y-0.5">
              <div className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1">
                Order Fills
                <span title="A Fill is an individual buy or sell transaction executed on the orderbook." className="cursor-help text-slate-400 hover:text-slate-600">
                  <HelpCircle size={10} />
                </span>
              </div>
              <div className="text-sm font-mono font-bold text-slate-900">{filteredLogs.length} Executed</div>
            </div>
          </div>
        </div>
      </div>

      {/* Unique Market Attribution Card (Grouped by Prediction Event) */}
      {(alphaDrivers.length > 0 || drawdownCulprits.length > 0) && (
        <div className="p-6 rounded-3xl bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_16px_36px_-6px_rgba(0,0,0,0.05)] space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-black/[0.06] pb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center border border-indigo-200">
                <Sparkles size={15} />
              </div>
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                  Market Valuation Attribution (Aggregated by Prediction Event)
                </h4>
                <span className="text-[11px] text-slate-500 font-mono">Net Realized + MTM Gains &amp; Losses per Market</span>
              </div>
            </div>

            {/* Filter Tabs */}
            <div className="flex rounded-xl bg-slate-100 p-0.5 border border-black/[0.04] text-[11px] font-semibold">
              {(['both', 'alpha', 'drawdown'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setAttributionTab(t)}
                  className={`px-2.5 py-0.5 rounded-lg transition-all cursor-pointer ${
                    attributionTab === t 
                      ? 'bg-white text-slate-950 font-bold shadow-2xs border border-black/[0.04]' 
                      : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  {t === 'both' ? 'All Markets' : t === 'alpha' ? '🚀 Top Alpha' : '⚠️ Top Drawdown'}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Top Alpha Markets (Winners) */}
            {(attributionTab === 'both' || attributionTab === 'alpha') && alphaDrivers.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-800">
                  <ArrowUpRight size={14} className="text-emerald-600" />
                  <span>Top Alpha Markets (Aggregated Gains)</span>
                </div>
                <div className="space-y-2">
                  {alphaDrivers.map((m) => (
                    <div 
                      key={m.key} 
                      onClick={() => onSelectTrade && onSelectTrade(m.sampleTrade)}
                      className="p-3.5 rounded-2xl bg-emerald-50/40 hover:bg-emerald-50/80 border border-emerald-200/80 transition-all cursor-pointer space-y-1.5 shadow-2xs"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-slate-900 truncate max-w-[210px]" title={m.question}>
                          {m.question}
                        </span>
                        <span className="font-mono font-bold text-emerald-700">+{formatCompactPnL(m.totalPnl, false)}</span>
                      </div>
                      <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                        <span>Avg Fill: ${(m.avgFillPrice).toFixed(3)} → Live: ${(m.currentPrice).toFixed(3)}</span>
                        <span className="text-slate-700 font-bold">{m.fillsCount} fill{m.fillsCount > 1 ? 's' : ''} • {m.whaleName}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Top Drawdown Markets (Losses) */}
            {(attributionTab === 'both' || attributionTab === 'drawdown') && drawdownCulprits.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center gap-1.5 text-xs font-bold text-rose-800">
                  <ArrowDownRight size={14} className="text-rose-600" />
                  <span>Top Drawdown Markets (Aggregated Losses)</span>
                </div>
                <div className="space-y-2">
                  {drawdownCulprits.map((m) => (
                    <div 
                      key={m.key} 
                      onClick={() => onSelectTrade && onSelectTrade(m.sampleTrade)}
                      className="p-3.5 rounded-2xl bg-rose-50/40 hover:bg-rose-50/80 border border-rose-200/80 transition-all cursor-pointer space-y-1.5 shadow-2xs"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-slate-900 truncate max-w-[210px]" title={m.question}>
                          {m.question}
                        </span>
                        <span className="font-mono font-bold text-rose-700">{formatCompactPnL(m.totalPnl)}</span>
                      </div>
                      <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                        <span>Avg Fill: ${(m.avgFillPrice).toFixed(3)} → Live: ${(m.currentPrice).toFixed(3)}</span>
                        <span className="text-slate-700 font-bold">{m.fillsCount} fill{m.fillsCount > 1 ? 's' : ''} • {m.whaleName}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Bottom Section: Top Single Winner vs Top Single Loser */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Top Winner Card */}
        <div 
          onClick={() => topWinnerLog && onSelectTrade && onSelectTrade(topWinnerLog)}
          className={`p-5 rounded-3xl bg-emerald-50/40 border border-emerald-200/80 transition-all ${
            topWinnerLog ? 'hover:shadow-md cursor-pointer hover:border-emerald-300' : 'opacity-60'
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-800 border border-emerald-200">
                <Award size={16} />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-900">Highest Alpha Single Fill ({timeframe})</span>
            </div>
            {topWinnerLog && (
              <span className="text-xs font-mono font-bold text-emerald-700 bg-emerald-100/60 px-2 py-0.5 rounded-full border border-emerald-300">
                +{formatCompactPnL(topWinnerLog.pnl, false)} (+{(topWinnerLog.pnlPct ?? 0).toFixed(1)}%)
              </span>
            )}
          </div>

          {topWinnerLog ? (
            <div className="space-y-2">
              <div className="text-sm font-bold text-slate-900 leading-snug truncate" title={topWinnerLog.marketQuestion}>
                {topWinnerLog.marketQuestion}
              </div>
              <div className="flex items-center gap-3 text-xs font-mono text-slate-600">
                <span>Filled @ ${(topWinnerLog.fillPrice ?? 0.5).toFixed(3)}</span>
                <span>•</span>
                <span>Live MTM @ ${(topWinnerLog.currentPrice ?? 0.5).toFixed(3)}</span>
                <span>•</span>
                <span>Size ${topWinnerLog.size?.toLocaleString()}</span>
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-400 font-medium">No profitable trade in selected timeframe.</p>
          )}
        </div>

        {/* Top Loser Card */}
        <div 
          onClick={() => topLoserLog && onSelectTrade && onSelectTrade(topLoserLog)}
          className={`p-5 rounded-3xl bg-rose-50/40 border border-rose-200/80 transition-all ${
            topLoserLog ? 'hover:shadow-md cursor-pointer hover:border-rose-300' : 'opacity-60'
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-xl bg-rose-100 flex items-center justify-center text-rose-800 border border-rose-200">
                <AlertTriangle size={16} />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider text-rose-900">Largest Drawdown Single Fill ({timeframe})</span>
            </div>
            {topLoserLog && (
              <span className="text-xs font-mono font-bold text-rose-700 bg-rose-100/60 px-2 py-0.5 rounded-full border border-rose-300">
                {formatCompactPnL(topLoserLog.pnl)} ({(topLoserLog.pnlPct ?? 0).toFixed(1)}%)
              </span>
            )}
          </div>

          {topLoserLog ? (
            <div className="space-y-2">
              <div className="text-sm font-bold text-slate-900 leading-snug truncate" title={topLoserLog.marketQuestion}>
                {topLoserLog.marketQuestion}
              </div>
              <div className="flex items-center gap-3 text-xs font-mono text-slate-600">
                <span>Filled @ ${(topLoserLog.fillPrice ?? 0.5).toFixed(3)}</span>
                <span>•</span>
                <span>Live MTM @ ${(topLoserLog.currentPrice ?? 0.5).toFixed(3)}</span>
                <span>•</span>
                <span>Size ${topLoserLog.size?.toLocaleString()}</span>
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
