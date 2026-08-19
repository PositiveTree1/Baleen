'use client';
import { useEffect, useState, useMemo } from 'react';
import { ExecutionLog } from '@/types';
import { fetchPortfolioSnapshots } from '@/lib/api-client';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';
import { TrendingUp, TrendingDown, Award, AlertTriangle, Zap, HelpCircle, Flame, Compass, ArrowUpRight, ArrowDownRight, Sparkles, Filter } from 'lucide-react';
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

  // Active net positions held
  const activePositionsCount = useMemo(() => {
    const activeCids = new Set<string>();
    for (const l of logs) {
      if (l.side === 'BUY' && l.status === 'FILLED') {
        activeCids.add(l.marketConditionId || l.id);
      }
    }
    return activeCids.size;
  }, [logs]);

  // Calculate Winners, Losers, Top 50 significant trades, and aligned timeline
  const { 
    topWinner, 
    topLoser, 
    winCount, 
    lossCount, 
    winRate, 
    totalResolved, 
    pnlTimeline, 
    periodNetPnL, 
    drawdownCulprits,
    alphaDrivers,
    topSignificantTrades 
  } = useMemo(() => {
    let bestWin: ExecutionLog | null = null;
    let worstLoss: ExecutionLog | null = null;
    let wins = 0;
    let losses = 0;
    let pnlSum = 0;

    const winLogs: ExecutionLog[] = [];
    const lossLogs: ExecutionLog[] = [];

    for (const log of filteredLogs) {
      const pnl = log.pnl ?? 0;
      pnlSum += pnl;
      if (pnl > 0) {
        wins++;
        winLogs.push(log);
        if (!bestWin || pnl > (bestWin.pnl ?? 0)) {
          bestWin = log;
        }
      } else if (pnl < 0) {
        losses++;
        lossLogs.push(log);
        if (!worstLoss || pnl < (worstLoss.pnl ?? 0)) {
          worstLoss = log;
        }
      }
    }

    // Top 3 drawdown contributors (biggest losses)
    const drawdownCulprits = lossLogs
      .sort((a, b) => (a.pnl ?? 0) - (b.pnl ?? 0))
      .slice(0, 3);

    // Top 3 alpha contributors (biggest wins)
    const alphaDrivers = winLogs
      .sort((a, b) => (b.pnl ?? 0) - (a.pnl ?? 0))
      .slice(0, 3);

    // Top 50 most significant trades for the heatpoint markers
    const topSignificantTrades = [...filteredLogs]
      .sort((a, b) => Math.abs(b.pnl ?? 0) - Math.abs(a.pnl ?? 0))
      .slice(0, 50);

    const significantIds = new Set(topSignificantTrades.map(t => t.id));

    const totalResolved = wins + losses;
    const wr = totalResolved > 0 ? (wins / totalResolved) * 100 : 0.0;

    interface TimelinePoint {
      time: string;
      balance: number;
      pnl: number;
      date: string;
      eventTrade?: ExecutionLog;
      isSignificant?: boolean;
    }

    // Build strictly chronological timeline from trades sorted by timestamp
    const sortedLogs = [...filteredLogs].sort((a, b) => {
      const ta = a.timestamp ? new Date(a.timestamp).getTime() : 0;
      const tb = b.timestamp ? new Date(b.timestamp).getTime() : 0;
      return ta - tb;
    });

    const timeline: TimelinePoint[] = [];
    let running = startingBalance;

    timeline.push({
      time: 'Start',
      balance: Math.round(startingBalance * 100) / 100,
      pnl: 0,
      date: 'Baseline'
    });

    // Sample or bucket chronological trajectory
    const totalPoints = sortedLogs.length;
    const step = totalPoints > 80 ? Math.ceil(totalPoints / 80) : 1;

    for (let i = 0; i < totalPoints; i++) {
      const log = sortedLogs[i];
      const pnl = log.pnl ?? 0;
      running += pnl;

      const isSig = significantIds.has(log.id);
      const shouldInclude = isSig || (i % step === 0) || (i === totalPoints - 1);

      if (shouldInclude) {
        const dObj = log.timestamp ? new Date(log.timestamp) : null;
        const timeLabel = dObj 
          ? dObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
          : `T-${timeline.length}`;
        const dateLabel = dObj 
          ? dObj.toLocaleDateString([], { month: 'short', day: 'numeric' }) 
          : '';

        timeline.push({
          time: timeLabel,
          balance: Math.round(running * 100) / 100,
          pnl: Math.round((running - startingBalance) * 100) / 100,
          date: dateLabel,
          eventTrade: isSig ? log : undefined,
          isSignificant: isSig
        });
      }
    }

    // Pin final point precisely to live currentBalance
    timeline.push({
      time: 'Now',
      balance: Math.round(currentBalance * 100) / 100,
      pnl: Math.round((currentBalance - startingBalance) * 100) / 100,
      date: 'Live'
    });

    return {
      topWinner: bestWin,
      topLoser: worstLoss,
      winCount: wins,
      lossCount: losses,
      winRate: wr,
      totalResolved,
      pnlTimeline: timeline,
      periodNetPnL: pnlSum,
      drawdownCulprits,
      alphaDrivers,
      topSignificantTrades
    };
  }, [filteredLogs, startingBalance, currentBalance]);

  const netPnL = timeframe === 'ALL' ? (currentBalance - startingBalance) : periodNetPnL;
  const netPnLPct = startingBalance > 0 ? (netPnL / startingBalance) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Top Banner: Capital Curve + Scorecard */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Net Worth Performance Area Chart & TradingView Attribution */}
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

          {/* Area Chart with MonotoneX / Linear Coordinates (100% Dot Synchronization) */}
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
                      const trade = d.eventTrade as ExecutionLog | undefined;
                      return (
                        <div className="bg-slate-950 text-white px-4 py-3 rounded-2xl text-xs font-mono shadow-2xl border border-white/10 max-w-xs space-y-1.5">
                          <div className="flex items-center justify-between text-[10px] text-slate-400">
                            <span>{d.date} • {d.time}</span>
                            <span className="font-bold text-slate-300">Sandbox MTM</span>
                          </div>
                          <div className="text-base font-bold text-white">${d.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                          <div className={`text-[11px] font-bold ${d.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {d.pnl >= 0 ? '+' : ''}${d.pnl.toFixed(2)} Mark-to-Market P&amp;L
                          </div>

                          {trade && (
                            <div className="pt-2 border-t border-white/10 text-[11px] font-sans space-y-1 text-slate-300">
                              <div className="font-bold text-white truncate flex items-center gap-1.5">
                                <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold font-mono ${trade.side === 'BUY' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'}`}>
                                  {trade.side}
                                </span>
                                <span className="truncate">{trade.marketQuestion || 'Event Contract'}</span>
                              </div>
                              <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                                <span>Whale: {trade.whaleName || trade.whalePseudonym || '0x...'}</span>
                                <span className={trade.pnl && trade.pnl >= 0 ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                                  {formatCompactPnL(trade.pnl)}
                                </span>
                              </div>
                            </div>
                          )}
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
                  dot={viewMode === 'attribution' ? (props: any) => {
                    const { cx, cy, payload } = props;
                    if (!payload.isSignificant) return <></>;
                    const pnl = payload.eventTrade?.pnl ?? 0;
                    const fillCol = pnl >= 0 ? '#10B981' : '#F43F5E';
                    return (
                      <circle 
                        key={`${cx}-${cy}`}
                        cx={cx} 
                        cy={cy} 
                        r={4.5} 
                        fill={fillCol} 
                        stroke="#FFFFFF" 
                        strokeWidth={2}
                        className="cursor-pointer transition-transform hover:scale-125"
                        onClick={() => payload.eventTrade && onSelectTrade && onSelectTrade(payload.eventTrade)}
                      />
                    );
                  } : false}
                  activeDot={{ r: 6, fill: netPnL >= 0 ? '#10B981' : '#F43F5E', stroke: '#FFFFFF', strokeWidth: 2.5 }}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Quick-select Top 50 Heatpoint Markers Strip (when in attribution mode) */}
          {viewMode === 'attribution' && topSignificantTrades.length > 0 && (
            <div className="pt-2 border-t border-black/[0.06] space-y-2">
              <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500">
                <span className="flex items-center gap-1.5">
                  <Sparkles size={12} className="text-indigo-600" />
                  Top Significant Alpha &amp; Drawdown Fills ({topSignificantTrades.length})
                </span>
                <span className="text-[10px] text-slate-400 font-mono">Click to inspect trade</span>
              </div>
              <div className="flex gap-2 overflow-x-auto pb-1.5 scroll-smooth">
                {topSignificantTrades.slice(0, 16).map((t) => {
                  const pnl = t.pnl ?? 0;
                  const isWin = pnl >= 0;
                  return (
                    <button
                      key={t.id}
                      onClick={() => onSelectTrade && onSelectTrade(t)}
                      className={`px-2.5 py-1 rounded-xl text-[10px] font-mono font-bold whitespace-nowrap flex items-center gap-1.5 border transition-all cursor-pointer shadow-2xs hover:scale-105 ${
                        isWin 
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100' 
                          : 'bg-rose-50 text-rose-800 border-rose-200 hover:bg-rose-100'
                      }`}
                    >
                      <span>{t.whaleName || t.whalePseudonym || 'Whale'}</span>
                      <span>{formatCompactPnL(pnl)}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Right: Execution Scorecard with Positions vs Fills */}
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

      {/* Dual Attribution Card: White Theme with Top Alpha Drivers & Drawdown Attribution */}
      {(alphaDrivers.length > 0 || drawdownCulprits.length > 0) && (
        <div className="p-6 rounded-3xl bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_16px_36px_-6px_rgba(0,0,0,0.05)] space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-black/[0.06] pb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center border border-indigo-200">
                <Sparkles size={15} />
              </div>
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                  Valuation &amp; Performance Attribution (Why Did P&amp;L Move?)
                </h4>
                <span className="text-[11px] text-slate-500 font-mono">Live Mark-to-Market Price Shifts &amp; Alpha Breakdown</span>
              </div>
            </div>

            {/* Filter Tabs: Both, Alpha Gains, Drawdown */}
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
                  {t === 'both' ? 'All Attribution' : t === 'alpha' ? '🚀 Alpha Drivers' : '⚠️ Drawdown'}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Top Alpha Drivers (Winners) */}
            {(attributionTab === 'both' || attributionTab === 'alpha') && alphaDrivers.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-800">
                  <ArrowUpRight size={14} className="text-emerald-600" />
                  <span>Top Alpha Drivers (Best Price Appreciation)</span>
                </div>
                <div className="space-y-2">
                  {alphaDrivers.map((c) => {
                    const fillP = c.fillPrice ?? c.entryPrice ?? 0.5;
                    const curP = c.currentPrice ?? fillP;
                    return (
                      <div 
                        key={c.id} 
                        onClick={() => onSelectTrade && onSelectTrade(c)}
                        className="p-3.5 rounded-2xl bg-emerald-50/40 hover:bg-emerald-50/80 border border-emerald-200/80 transition-all cursor-pointer space-y-1.5 shadow-2xs"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-slate-900 truncate max-w-[200px]" title={c.marketQuestion}>
                            {c.marketQuestion || 'Prediction Contract'}
                          </span>
                          <span className="font-mono font-bold text-emerald-700">+{formatCompactPnL(c.pnl, false)}</span>
                        </div>
                        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                          <span>Fill: ${(fillP).toFixed(3)} → Live: ${(curP).toFixed(3)}</span>
                          <span className="text-slate-700 font-bold">{c.whaleName || c.whalePseudonym || 'Whale'}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Top Drawdown Culprits (Losses) */}
            {(attributionTab === 'both' || attributionTab === 'drawdown') && drawdownCulprits.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center gap-1.5 text-xs font-bold text-rose-800">
                  <ArrowDownRight size={14} className="text-rose-600" />
                  <span>Top Drawdown Culprits (Adverse Price Moves)</span>
                </div>
                <div className="space-y-2">
                  {drawdownCulprits.map((c) => {
                    const fillP = c.fillPrice ?? c.entryPrice ?? 0.5;
                    const curP = c.currentPrice ?? fillP;
                    return (
                      <div 
                        key={c.id} 
                        onClick={() => onSelectTrade && onSelectTrade(c)}
                        className="p-3.5 rounded-2xl bg-rose-50/40 hover:bg-rose-50/80 border border-rose-200/80 transition-all cursor-pointer space-y-1.5 shadow-2xs"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-slate-900 truncate max-w-[200px]" title={c.marketQuestion}>
                            {c.marketQuestion || 'Prediction Contract'}
                          </span>
                          <span className="font-mono font-bold text-rose-700">{formatCompactPnL(c.pnl)}</span>
                        </div>
                        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                          <span>Fill: ${(fillP).toFixed(3)} → Live: ${(curP).toFixed(3)}</span>
                          <span className="text-slate-700 font-bold">{c.whaleName || c.whalePseudonym || 'Whale'}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

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
                +{formatCompactPnL(topWinner.pnl, false)} (+{(topWinner.pnlPct ?? 0).toFixed(1)}%)
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
                {formatCompactPnL(topLoser.pnl)} ({(topLoser.pnlPct ?? 0).toFixed(1)}%)
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
