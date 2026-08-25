'use client';
import { useMemo, useState, useEffect, useCallback, useRef } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { ExecutionLog } from '@/types';
import { 
  TrendingUp, 
  TrendingDown, 
  Sparkles, 
  Layers, 
  Compass, 
  ArrowUpRight, 
  ArrowDownRight, 
  CheckCircle2, 
  RefreshCw,
  HelpCircle,
  Zap,
  Code2,
  Database,
  Copy,
  Check,
  X,
  Loader2
} from 'lucide-react';
import { formatCompactPnL, formatFrenchTime, formatFrenchDate } from '@/lib/formatters';
import { resetSandboxLedger, clearAllCache, fetchPortfolioSnapshots } from '@/lib/api-client';

interface PortfolioAnalyticsProps {
  logs: ExecutionLog[];
  snapshots?: any[];
  userId?: string;
  startingBalance?: number;
  currentBalance?: number;
  totalFilledTrades?: number;
  topAlphaMarkets?: any[];
  topDrawdownMarkets?: any[];
  allTimeWinRate?: number;
  allTimeWins?: number;
  allTimeLosses?: number;
  onSelectTrade?: (trade: ExecutionLog) => void;
  onResetComplete?: () => void;
}

export function PortfolioAnalytics({
  logs,
  snapshots = [],
  userId,
  startingBalance = 10000.0,
  currentBalance = 10000.0,
  totalFilledTrades = 5049,
  topAlphaMarkets,
  topDrawdownMarkets,
  allTimeWinRate,
  allTimeWins,
  allTimeLosses,
  onSelectTrade,
  onResetComplete
}: PortfolioAnalyticsProps) {
  const [timeframe, setTimeframe] = useState<'1H' | '6H' | '1D' | '1W' | '1M' | 'YTD' | 'ALL'>('ALL');
  const [scorecardScope, setScorecardScope] = useState<'stream' | 'allTime'>('allTime');
  const [attributionTab, setAttributionTab] = useState<'both' | 'alpha' | 'drawdown'>('both');
  const [showResetModal, setShowResetModal] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [showRawDataModal, setShowRawDataModal] = useState(false);
  const [copied, setCopied] = useState(false);

  // 1. Filter Logs by Timeframe
  const filteredLogs = useMemo(() => {
    if (!logs || logs.length === 0) return [];
    if (timeframe === 'ALL') return logs;

    const now = new Date().getTime();
    let cutoff = 0;

    if (timeframe === '1H') cutoff = now - 60 * 60 * 1000;
    else if (timeframe === '6H') cutoff = now - 6 * 60 * 60 * 1000;
    else if (timeframe === '1D') cutoff = now - 24 * 60 * 60 * 1000;
    else if (timeframe === '1W') cutoff = now - 7 * 24 * 60 * 60 * 1000;
    else if (timeframe === '1M') cutoff = now - 30 * 24 * 60 * 60 * 1000;
    else if (timeframe === 'YTD') cutoff = new Date(new Date().getFullYear(), 0, 1).getTime();

    return logs.filter((l) => {
      if (!l.timestamp) return true;
      const t = new Date(l.timestamp).getTime();
      return t >= cutoff;
    });
  }, [logs, timeframe]);

  // Gracefully fallback to all logs if the specific timeframe window has 0 executions
  const isTimeframeEmpty = filteredLogs.length === 0 && logs.length > 0;
  const targetLogs = isTimeframeEmpty ? logs : filteredLogs;

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

  // Aggregate Market Attribution & Performance Stats
  const {
    alphaDrivers,
    drawdownCulprits,
    topWinnerLog,
    topLoserLog,
    winCount,
    lossCount,
    winRate,
  } = useMemo(() => {
    let wins = 0;
    let losses = 0;
    let bestWinLog: ExecutionLog | null = null;
    let worstLossLog: ExecutionLog | null = null;

    const marketMap = new Map<string, MarketSummary>();

    for (const log of targetLogs) {
      const pnl = log.pnl ?? 0;
      const fillP = log.fillPrice ?? log.entryPrice ?? 0.5;
      const curP = log.currentPrice ?? fillP;
      const notional = log.size ?? 0;

      // Classify true winners and losers
      if (pnl >= 0) {
        wins++;
        if (!bestWinLog || pnl > (bestWinLog.pnl ?? 0)) bestWinLog = log;
      } else {
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

    const totalTrades = wins + losses;
    const wr = totalTrades > 0 ? (wins / totalTrades) * 100 : 0.0;

    return {
      alphaDrivers,
      drawdownCulprits,
      topWinnerLog: bestWinLog,
      topLoserLog: worstLossLog,
      winCount: wins,
      lossCount: losses,
      winRate: wr,
    };
  }, [targetLogs]);

  // ---- Snapshot-based Chart Timeline (fetched from backend, not computed from trades) ----
  const [snapshotTimeline, setSnapshotTimeline] = useState<{
    displayTime: string;
    balance: number;
    pnl: number;
    date: string;
    rawTimestamp: number;
  }[]>([]);
  const [chartLoading, setChartLoading] = useState(false);
  const prevTimelineRef = useRef(snapshotTimeline);

  const loadSnapshots = useCallback(async () => {
    setChartLoading(true);
    try {
      const tfMap: Record<string, string> = {
        '1H': '1h', '6H': '6h', '1D': '1d', '1W': '1w', '1M': '1m', 'YTD': 'ytd', 'ALL': 'all'
      };
      const data = await fetchPortfolioSnapshots(userId, tfMap[timeframe] || 'all');
      const isMultiDay = timeframe === 'ALL' || timeframe === '1W' || timeframe === '1M' || timeframe === 'YTD' || timeframe === '1D';

      if (Array.isArray(data) && data.length > 0) {
        const timeline = data.map((s: any) => {
          const ts = s.timestamp ? new Date(s.timestamp) : new Date();
          const timeStr = s.time || formatFrenchTime(ts);
          const dateStr = s.date || formatFrenchDate(ts);
          return {
            displayTime: isMultiDay && dateStr ? `${dateStr} ${timeStr}` : timeStr,
            time: timeStr,
            date: dateStr,
            balance: Math.round((s.balance ?? 10000) * 100) / 100,
            pnl: Math.round((s.pnl ?? 0) * 100) / 100,
            rawTimestamp: ts.getTime(),
          };
        });

        // Anchor the last point only if currentBalance is consistent with the snapshot timeline
        if (timeline.length > 0) {
          const lastPoint = timeline[timeline.length - 1];
          if (currentBalance > 0 && Math.abs(currentBalance - lastPoint.balance) < 300) {
            lastPoint.balance = Math.round(currentBalance * 100) / 100;
            lastPoint.pnl = Math.round((currentBalance - startingBalance) * 100) / 100;
          }
        }

        prevTimelineRef.current = timeline;
        setSnapshotTimeline(timeline);
      } else if (prevTimelineRef.current.length === 0) {
        // No snapshots at all — show a single point at current balance
        const nowMs = Date.now();
        const fallback = [{
          displayTime: formatFrenchTime(new Date()),
          balance: Math.round(currentBalance * 100) / 100,
          pnl: Math.round((currentBalance - startingBalance) * 100) / 100,
          date: 'Now',
          rawTimestamp: nowMs,
        }];
        setSnapshotTimeline(fallback);
      }
    } catch (e) {
      console.debug("Snapshot fetch note:", e);
    } finally {
      setChartLoading(false);
    }
  }, [userId, timeframe, currentBalance, startingBalance]);

  useEffect(() => {
    loadSnapshots();
    const interval = setInterval(loadSnapshots, 15000); // Refresh chart every 15s
    return () => clearInterval(interval);
  }, [loadSnapshots]);

  // Use previous timeline while loading to prevent flicker
  const pnlTimeline = chartLoading && prevTimelineRef.current.length > 0 
    ? prevTimelineRef.current 
    : snapshotTimeline;

  // Period P&L from chart endpoints
  const periodPnL = useMemo(() => {
    if (pnlTimeline.length < 2) return Math.round((currentBalance - startingBalance) * 100) / 100;
    const startBal = pnlTimeline[0].balance;
    const endBal = pnlTimeline[pnlTimeline.length - 1].balance;
    return Math.round((endBal - startBal) * 100) / 100;
  }, [pnlTimeline, currentBalance, startingBalance]);

  const periodPnLPct = useMemo(() => {
    if (pnlTimeline.length < 2) {
      return startingBalance > 0 ? Math.round(((currentBalance - startingBalance) / startingBalance) * 10000) / 100 : 0;
    }
    const startBal = pnlTimeline[0].balance;
    return startBal > 0 ? Math.round(((pnlTimeline[pnlTimeline.length - 1].balance - startBal) / startBal) * 10000) / 100 : 0;
  }, [pnlTimeline, currentBalance, startingBalance]);

  // Handle Sandbox Reset
  const handleResetSandbox = async () => {
    setIsResetting(true);
    try {
      await resetSandboxLedger(userId);
      clearAllCache();
      setShowResetModal(false);
      if (onResetComplete) onResetComplete();
      window.location.reload();
    } catch (e) {
      console.error("Reset error:", e);
    } finally {
      setIsResetting(false);
    }
  };

  // Calculate active distinct positions count
  const activePositionsCount = useMemo(() => {
    const activeConditions = new Set<string>();
    for (const log of filteredLogs) {
      if (log.side === 'BUY' && log.status === 'FILLED' && !log.marketQuestion?.toLowerCase().includes('resolved')) {
        activeConditions.add(log.marketConditionId || log.id);
      }
    }
    return activeConditions.size;
  }, [filteredLogs]);

  return (
    <div className="space-y-6">
      {/* Top Banner: Capital Curve + Scorecard */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Net Worth Performance Area Chart */}
        <div className="lg:col-span-2 p-6 rounded-3xl bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_16px_36px_-6px_rgba(0,0,0,0.05)] space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Sandbox Capital Curve</span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                  <Zap size={10} /> Real-Time MTM
                </span>
              </div>
              <div className="flex items-baseline gap-2.5 sm:gap-3 mt-1 flex-wrap sm:flex-nowrap">
                <span className="text-2xl sm:text-3xl font-extrabold font-mono text-slate-950 tabular-nums whitespace-nowrap">
                  ${currentBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className={`inline-flex items-baseline gap-1 text-xs sm:text-sm font-mono font-bold whitespace-nowrap ${periodPnL >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                  <span>{periodPnL >= 0 ? '+' : ''}${periodPnL.toFixed(2)} ({periodPnL >= 0 ? '+' : ''}{periodPnLPct.toFixed(2)}%)</span>
                  <span className="text-[10px] text-slate-400 font-sans font-normal whitespace-nowrap ml-0.5">in {timeframe}</span>
                </span>
              </div>
            </div>

            {/* Timeframe selector & Reset */}
            <div className="flex items-center gap-1.5 sm:gap-2 shrink-0 overflow-x-auto">
              <div className={`flex items-center rounded-xl bg-slate-100 p-0.5 border border-black/[0.06] text-xs font-mono font-semibold transition-opacity ${chartLoading ? 'opacity-85' : ''}`}>
                {(['1H', '6H', '1D', '1W', '1M', 'YTD', 'ALL'] as const).map((tf) => {
                  const isActive = timeframe === tf;
                  return (
                    <button
                      key={tf}
                      disabled={chartLoading}
                      onClick={() => {
                        if (!chartLoading && tf !== timeframe) {
                          setTimeframe(tf);
                        }
                      }}
                      className={`px-2 py-1 rounded-lg transition-all flex items-center gap-1 ${
                        chartLoading ? 'cursor-not-allowed' : 'cursor-pointer'
                      } ${
                        isActive 
                          ? 'bg-white text-slate-950 font-bold shadow-xs' 
                          : 'text-slate-500 hover:text-slate-900'
                      }`}
                      title={chartLoading ? `Loading ${timeframe} snapshots...` : `Switch to ${tf} timeframe`}
                    >
                      {isActive && chartLoading && (
                        <Loader2 size={10} className="animate-spin text-indigo-600 shrink-0" />
                      )}
                      <span>{tf}</span>
                    </button>
                  );
                })}
              </div>
              <button
                onClick={() => setShowResetModal(true)}
                className="p-1.5 rounded-xl bg-slate-100 hover:bg-rose-50 text-slate-400 hover:text-rose-600 border border-black/[0.04] transition-all cursor-pointer"
                title="Reset Sandbox to $10,000 baseline"
              >
                <RefreshCw size={13} />
              </button>
              <button
                onClick={() => setShowRawDataModal(true)}
                className="p-1.5 px-2 rounded-xl bg-slate-100 hover:bg-indigo-50 text-slate-500 hover:text-indigo-600 border border-black/[0.04] transition-all cursor-pointer flex items-center gap-1 text-[11px] font-mono font-semibold"
                title="View raw chart snapshot data received from server"
              >
                <Code2 size={13} />
                <span className="hidden sm:inline">Raw Data</span>
              </button>
            </div>
          </div>

          {/* Area Chart: Clean Smooth Curve with crosshair value tracking at cursor */}
          <div className="h-56 w-full pt-2 outline-none focus:outline-none ring-0 focus:ring-0 [&_*]:outline-none [&_*]:focus:outline-none select-none">
            <ResponsiveContainer width="100%" height="100%" className="outline-none">
              <AreaChart data={pnlTimeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }} className="outline-none">
                <defs>
                  <linearGradient id="balanceGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={periodPnL >= 0 ? '#10B981' : '#F43F5E'} stopOpacity={0.25} />
                    <stop offset="95%" stopColor={periodPnL >= 0 ? '#10B981' : '#F43F5E'} stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis 
                  dataKey="displayTime" 
                  tick={{ fontSize: 9, fill: '#94A3B8' }} 
                  axisLine={false} 
                  tickLine={false}
                  minTickGap={30}
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
                            <span>{d.date} • {d.time || d.displayTime}</span>
                            <span className="font-bold text-slate-300">Sandbox Balance</span>
                          </div>
                          <div className="text-base font-bold text-white">${d.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                          <div className={`text-[11px] font-bold ${d.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {d.pnl >= 0 ? '+' : ''}${d.pnl.toFixed(2)} Total P&amp;L
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
                  stroke={periodPnL >= 0 ? '#10B981' : '#F43F5E'} 
                  strokeWidth={2.5}
                  fillOpacity={1} 
                  fill="url(#balanceGradient)"
                  dot={false}
                  activeDot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right: Execution Scorecard */}
        <div className="p-6 rounded-3xl bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_16px_36px_-6px_rgba(0,0,0,0.05)] flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Execution Scorecard</span>
              <div className="flex rounded-lg bg-slate-100 p-0.5 border border-black/[0.04] text-[10px] font-mono font-semibold">
                <button
                  onClick={() => setScorecardScope('allTime')}
                  className={`px-2 py-0.5 rounded-md transition-all cursor-pointer ${
                    scorecardScope === 'allTime'
                      ? 'bg-white text-slate-900 font-bold shadow-2xs'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                  title="Show cumulative platform statistics across all recorded trades"
                >
                  All-Time ({totalFilledTrades.toLocaleString()})
                </button>
                <button
                  onClick={() => setScorecardScope('stream')}
                  className={`px-2 py-0.5 rounded-md transition-all cursor-pointer ${
                    scorecardScope === 'stream'
                      ? 'bg-white text-slate-900 font-bold shadow-2xs'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                  title={`Show statistics for the current ${timeframe} window (${filteredLogs.length} fills)`}
                >
                  {timeframe} Stream ({filteredLogs.length})
                </button>
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold font-mono text-slate-900">
                {(scorecardScope === 'allTime' && allTimeWinRate !== undefined ? allTimeWinRate : winRate).toFixed(1)}%
              </span>
              <span className="text-xs font-mono font-semibold text-slate-500">
                Win Rate ({scorecardScope === 'allTime' && allTimeWins !== undefined ? allTimeWins.toLocaleString() : winCount}W / {scorecardScope === 'allTime' && allTimeLosses !== undefined ? allTimeLosses.toLocaleString() : lossCount}L)
              </span>
            </div>
          </div>

          {/* Win/Loss Bar */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs font-bold font-mono">
              <span className="text-emerald-700">
                {scorecardScope === 'allTime' && allTimeWins !== undefined ? allTimeWins.toLocaleString() : winCount} Won
              </span>
              <span className="text-rose-700">
                {scorecardScope === 'allTime' && allTimeLosses !== undefined ? allTimeLosses.toLocaleString() : lossCount} Lost
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden flex">
              <div 
                className="bg-emerald-500 transition-all duration-500" 
                style={{ width: `${scorecardScope === 'allTime' && allTimeWinRate !== undefined ? allTimeWinRate : winRate}%` }} 
              />
              <div 
                className="bg-rose-500 transition-all duration-500" 
                style={{ width: `${100 - (scorecardScope === 'allTime' && allTimeWinRate !== undefined ? allTimeWinRate : winRate)}%` }} 
              />
            </div>
            <div className="flex justify-between text-[10px] font-mono font-semibold text-slate-400">
              <span className="text-emerald-700">
                {scorecardScope === 'allTime' && allTimeWins !== undefined ? allTimeWins.toLocaleString() : winCount} Profitable Fills
              </span>
              <span className="text-rose-700">
                {scorecardScope === 'allTime' && allTimeLosses !== undefined ? allTimeLosses.toLocaleString() : lossCount} Unprofitable Fills
              </span>
            </div>
          </div>

          {/* Sizing, Active Positions vs Total Platform Order Fills */}
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
                Total Executions
                <span title="Total cumulative trade executions recorded in the Baleen database across all 4 days." className="cursor-help text-slate-400 hover:text-slate-600">
                  <HelpCircle size={10} />
                </span>
              </div>
              <div className="text-sm font-mono font-bold text-slate-900">
                {scorecardScope === 'allTime' ? totalFilledTrades.toLocaleString() : filteredLogs.length} Fills
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Unique Market Attribution Card (Grouped by Prediction Event) */}
      {(() => {
        const effectiveAlpha = (topAlphaMarkets && topAlphaMarkets.length > 0) ? topAlphaMarkets : alphaDrivers;
        const effectiveDrawdown = (topDrawdownMarkets && topDrawdownMarkets.length > 0) ? topDrawdownMarkets : drawdownCulprits;

        if (effectiveAlpha.length === 0 && effectiveDrawdown.length === 0) return null;

        return (
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
                  <span className="text-[11px] text-slate-500 font-mono">Cumulative Platform Gains &amp; Losses per Market ({totalFilledTrades.toLocaleString()} Executions)</span>
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
              {(attributionTab === 'both' || attributionTab === 'alpha') && effectiveAlpha.length > 0 && (
                <div className="space-y-2.5">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-800">
                    <ArrowUpRight size={14} className="text-emerald-600" />
                    <span>Top Alpha Markets (Aggregated Gains)</span>
                  </div>
                  <div className="space-y-2">
                    {effectiveAlpha.map((m: any) => (
                      <div 
                        key={m.key || m.conditionId || m.question} 
                        onClick={() => m.sampleTrade && onSelectTrade && onSelectTrade(m.sampleTrade)}
                        className="p-3.5 rounded-2xl bg-emerald-50/40 hover:bg-emerald-50/80 border border-emerald-200/80 transition-all cursor-pointer space-y-1.5 shadow-2xs"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-slate-900 truncate max-w-[210px] sm:max-w-xs" title={m.question}>
                            {m.question}
                          </span>
                          <span className="font-mono font-bold text-emerald-700">+{formatCompactPnL(m.totalPnl, false)}</span>
                        </div>
                        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                          <span>Outcome: <strong className="text-slate-700">{m.outcome || 'Yes'}</strong> • Avg Fill: ${(m.avgFillPrice || 0.5).toFixed(3)}</span>
                          <span className="text-slate-700 font-bold">{m.fillsCount || 1} fill{(m.fillsCount || 1) > 1 ? 's' : ''} • {m.whaleName || 'Whale'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Top Drawdown Markets (Losses) */}
              {(attributionTab === 'both' || attributionTab === 'drawdown') && effectiveDrawdown.length > 0 && (
                <div className="space-y-2.5">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-rose-800">
                    <ArrowDownRight size={14} className="text-rose-600" />
                    <span>Top Drawdown Markets (Aggregated Losses)</span>
                  </div>
                  <div className="space-y-2">
                    {effectiveDrawdown.map((m: any) => (
                      <div 
                        key={m.key || m.conditionId || m.question} 
                        onClick={() => m.sampleTrade && onSelectTrade && onSelectTrade(m.sampleTrade)}
                        className="p-3.5 rounded-2xl bg-rose-50/40 hover:bg-rose-50/80 border border-rose-200/80 transition-all cursor-pointer space-y-1.5 shadow-2xs"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-slate-900 truncate max-w-[210px] sm:max-w-xs" title={m.question}>
                            {m.question}
                          </span>
                          <span className="font-mono font-bold text-rose-700">{formatCompactPnL(m.totalPnl, false)}</span>
                        </div>
                        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                          <span>Outcome: <strong className="text-slate-700">{m.outcome || 'Yes'}</strong> • Avg Fill: ${(m.avgFillPrice || 0.5).toFixed(3)}</span>
                          <span className="text-slate-700 font-bold">{m.fillsCount || 1} fill{(m.fillsCount || 1) > 1 ? 's' : ''} • {m.whaleName || 'Whale'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })()}

      {/* Confirmation Reset Modal */}
      {showResetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white rounded-3xl p-6 shadow-2xl border border-black/[0.08] space-y-4">
            <h3 className="text-base font-bold text-slate-900">Reset Sandbox Simulation?</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              This will reset your paper trading balance back to <strong>$10,000.00</strong>, clear all execution logs and simulation charts.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowResetModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
              >
                Cancel
              </button>
              <button
                disabled={isResetting}
                onClick={handleResetSandbox}
                className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 transition-colors shadow-sm"
              >
                {isResetting ? 'Resetting...' : 'Confirm Reset'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Raw Snapshot Data Modal */}
      {showRawDataModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm">
          <div className="w-full max-w-3xl max-h-[85vh] bg-white rounded-3xl p-6 shadow-2xl border border-black/[0.08] flex flex-col space-y-4">
            <div className="flex items-center justify-between border-b border-black/[0.06] pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-200">
                  <Database size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Received Chart Snapshot Data</h3>
                  <p className="text-[11px] text-slate-500 font-mono">
                    Timeframe: <span className="font-bold text-slate-800">{timeframe}</span> • {pnlTimeline.length} points received from server
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(JSON.stringify(pnlTimeline, null, 2));
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700 transition-colors cursor-pointer"
                >
                  {copied ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}
                  <span>{copied ? 'Copied!' : 'Copy JSON'}</span>
                </button>
                <button
                  onClick={() => setShowRawDataModal(false)}
                  className="p-1.5 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Code / JSON Viewer */}
            <div className="flex-1 overflow-auto bg-slate-950 text-emerald-400 p-4 rounded-2xl font-mono text-xs leading-relaxed border border-white/10 shadow-inner max-h-[60vh]">
              <pre>{JSON.stringify(pnlTimeline, null, 2)}</pre>
            </div>

            <div className="flex justify-between items-center text-[11px] text-slate-400 pt-1">
              <span>Endpoint: <code className="text-slate-600 font-mono">/api/executions/snapshots?timeframe={timeframe.toLowerCase()}</code></span>
              <span>Latest Balance: <strong className="text-slate-800">${(pnlTimeline[pnlTimeline.length - 1]?.balance ?? currentBalance).toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong></span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
