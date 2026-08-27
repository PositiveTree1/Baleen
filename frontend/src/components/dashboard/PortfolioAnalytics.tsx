'use client';
import { useMemo, useState, useEffect, useCallback } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { ExecutionLog } from '@/types';
import { 
  TrendingUp, 
  TrendingDown, 
  ArrowUpRight, 
  ArrowDownRight, 
  RefreshCw, 
  Code2, 
  Copy, 
  Check, 
  X, 
  Loader2 
} from 'lucide-react';
import { formatFrenchTime, formatFrenchDate } from '@/lib/formatters';
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
    whaleName: string;
    sampleTrade?: ExecutionLog;
  }

  // 2. Aggregate Market Attribution
  const { topAlpha, topDrawdown } = useMemo(() => {
    if (timeframe === 'ALL' && topAlphaMarkets && topAlphaMarkets.length > 0) {
      return {
        topAlpha: topAlphaMarkets as MarketSummary[],
        topDrawdown: (topDrawdownMarkets || []) as MarketSummary[]
      };
    }

    const marketMap = new Map<string, MarketSummary>();
    targetLogs.forEach((l) => {
      if (l.side === 'SELL' && l.pnl === undefined) return;
      const key = l.marketQuestion || l.marketConditionId || l.id;
      const notional = l.size ?? 10.0;
      const pnl = l.pnl ?? 0.0;
      const fillP = l.fillPrice || l.entryPrice || 0.5;
      const whaleName = l.whaleName || l.whalePseudonym || (l.walletAddress ? `${l.walletAddress.slice(0, 6)}...${l.walletAddress.slice(-4)}` : 'Whale');

      if (!marketMap.has(key)) {
        marketMap.set(key, {
          key,
          question: l.marketQuestion || 'Prediction Market',
          conditionId: l.marketConditionId || '',
          outcome: l.outcome || 'Yes',
          totalPnl: 0,
          totalNotional: 0,
          fillsCount: 0,
          avgFillPrice: fillP,
          whaleName,
          sampleTrade: l
        });
      }
      const item = marketMap.get(key)!;
      item.totalPnl += pnl;
      item.totalNotional += notional;
      item.fillsCount += 1;
      if (!item.sampleTrade) item.sampleTrade = l;
    });

    const all = Array.from(marketMap.values());
    const alpha = all.filter((m) => m.totalPnl > 0).sort((a, b) => b.totalPnl - a.totalPnl).slice(0, 4);
    const drawdown = all.filter((m) => m.totalPnl < 0).sort((a, b) => a.totalPnl - b.totalPnl).slice(0, 4);
    return { topAlpha: alpha, topDrawdown: drawdown };
  }, [targetLogs, timeframe, topAlphaMarkets, topDrawdownMarkets]);

  // 3. Execution Scorecard Metrics
  const { totalWins, totalLosses, winRate, feeRatePct, totalNotionalInvested } = useMemo(() => {
    if (allTimeWins !== undefined && allTimeLosses !== undefined) {
      const totalEval = allTimeWins + allTimeLosses;
      const wr = allTimeWinRate ?? (totalEval > 0 ? (allTimeWins / totalEval) * 100 : 0.0);
      const totalNotional = logs.reduce((acc, l) => acc + (l.size ?? 10.0), 0);
      const totalFees = logs.reduce((acc, l) => acc + (l.feeUsd || 0.0), 0);
      const feeRate = totalNotional > 0 ? (totalFees / totalNotional) * 100 : 0.0;

      return {
        totalWins: allTimeWins,
        totalLosses: allTimeLosses,
        winRate: wr,
        feeRatePct: feeRate,
        totalNotionalInvested: totalNotional
      };
    }

    let wins = 0;
    let losses = 0;
    let totalNotional = 0;
    let totalFees = 0;

    targetLogs.forEach((l) => {
      const pnl = l.pnl ?? 0.0;
      const notional = l.size ?? 10.0;
      const fee = l.feeUsd || 0.0;
      totalNotional += notional;
      totalFees += fee;
      if (pnl > 0) wins += 1;
      else if (pnl < 0) losses += 1;
    });

    const evaluated = wins + losses;
    const wr = evaluated > 0 ? (wins / evaluated) * 100 : 0.0;
    const feeRate = totalNotional > 0 ? (totalFees / totalNotional) * 100 : 0.0;

    return {
      totalWins: wins,
      totalLosses: losses,
      winRate: wr,
      feeRatePct: feeRate,
      totalNotionalInvested: totalNotional
    };
  }, [targetLogs, allTimeWins, allTimeLosses, allTimeWinRate, logs]);

  // 4. Portfolio Snapshots Timeline
  const [serverSnapshots, setServerSnapshots] = useState<any[]>(snapshots);
  const [chartLoading, setChartLoading] = useState(false);

  const loadSnapshots = useCallback(async (tf: string) => {
    setChartLoading(true);
    try {
      const data = await fetchPortfolioSnapshots(userId, tf);
      const isMultiDay = tf === 'ALL' || tf === '1M' || tf === 'YTD' || tf === '1W';

      if (Array.isArray(data) && data.length > 0) {
        const timeline = data.map((s: any) => {
          const ts = s.timestamp ? new Date(s.timestamp) : new Date();
          const timeStr = formatFrenchTime(ts);
          const dateStr = formatFrenchDate(ts);
          return {
            displayTime: isMultiDay && dateStr ? `${dateStr} ${timeStr}` : timeStr,
            time: timeStr,
            date: dateStr,
            balance: Math.round((s.balance ?? 10000) * 100) / 100,
            pnl: Math.round((s.pnl ?? 0) * 100) / 100,
            rawTimestamp: ts.getTime(),
          };
        });

        const lastSnapshotBal = timeline.length > 0 ? timeline[timeline.length - 1].balance : 10000.0;
        const isDefaultFallback = (currentBalance === 10000.0 && Math.abs(lastSnapshotBal - 10000.0) > 50.0);
        const resolvedCurrentBalance = isDefaultFallback ? lastSnapshotBal : currentBalance;

        if (resolvedCurrentBalance > 0) {
          const now = new Date();
          const nowTimeStr = formatFrenchTime(now);
          const nowDateStr = formatFrenchDate(now);
          const livePoint = {
            displayTime: isMultiDay && nowDateStr ? `${nowDateStr} ${nowTimeStr}` : nowTimeStr,
            time: nowTimeStr,
            date: nowDateStr,
            balance: Math.round(resolvedCurrentBalance * 100) / 100,
            pnl: Math.round((resolvedCurrentBalance - startingBalance) * 100) / 100,
            rawTimestamp: now.getTime(),
          };

          if (timeline.length === 0) {
            timeline.push(livePoint);
          } else {
            const lastPoint = timeline[timeline.length - 1];
            if ((now.getTime() - lastPoint.rawTimestamp) > 300000) {
              timeline.push(livePoint);
            } else {
              lastPoint.balance = Math.round(resolvedCurrentBalance * 100) / 100;
              lastPoint.pnl = Math.round((resolvedCurrentBalance - startingBalance) * 100) / 100;
            }
          }
        }

        setServerSnapshots(timeline);
      }
    } catch (e) {
      console.debug("Snapshot fetch note:", e);
    } finally {
      setChartLoading(false);
    }
  }, [userId, currentBalance, startingBalance]);

  useEffect(() => {
    loadSnapshots(timeframe);
  }, [timeframe, loadSnapshots]);

  const pnlTimeline = useMemo(() => {
    if (serverSnapshots && serverSnapshots.length > 0) return serverSnapshots;
    return [
      { displayTime: 'Genesis', time: '00:00', date: '', balance: startingBalance, pnl: 0, rawTimestamp: Date.now() },
      { displayTime: 'Now', time: 'Live', date: '', balance: currentBalance, pnl: currentBalance - startingBalance, rawTimestamp: Date.now() }
    ];
  }, [serverSnapshots, startingBalance, currentBalance]);

  const periodPnL = useMemo(() => {
    if (pnlTimeline.length < 2) return currentBalance - startingBalance;
    const first = pnlTimeline[0].balance;
    const last = pnlTimeline[pnlTimeline.length - 1].balance;
    return last - first;
  }, [pnlTimeline, currentBalance, startingBalance]);

  const periodPnLPct = useMemo(() => {
    if (pnlTimeline.length < 2) return startingBalance > 0 ? ((currentBalance - startingBalance) / startingBalance) * 100 : 0.0;
    const first = pnlTimeline[0].balance;
    const pnl = periodPnL;
    return first > 0 ? (pnl / first) * 100 : 0.0;
  }, [pnlTimeline, periodPnL, currentBalance, startingBalance]);

  const handleResetExecute = async () => {
    setIsResetting(true);
    try {
      await resetSandboxLedger(userId);
      clearAllCache();
      setShowResetModal(false);
      if (onResetComplete) onResetComplete();
      loadSnapshots(timeframe);
    } catch (e) {
      console.error("Reset failed:", e);
    } finally {
      setIsResetting(false);
    }
  };

  const isPositive = periodPnL >= 0;

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* ========================================================= */}
      {/* 1. REVOLUT LINE CHART CARD */}
      {/* ========================================================= */}
      <div className="revolut-card p-6 sm:p-8 space-y-6 rounded-[26px]">
        {/* Asset Header & Price */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-slate-500 dark:text-[#8E8F99] uppercase tracking-wider">
              Polymarket Copy Portfolio · Balance
            </span>
            <div className="flex items-baseline gap-3">
              <span className="text-3xl sm:text-4xl lg:text-5xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                ${(pnlTimeline[pnlTimeline.length - 1]?.balance ?? currentBalance).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <div className={`inline-flex items-center gap-1 text-xs font-mono font-bold ${isPositive ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                {isPositive ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                <span>
                  {isPositive ? '+' : ''}${periodPnL.toFixed(2)} ({isPositive ? '+' : ''}{periodPnLPct.toFixed(2)}%) · {timeframe}
                </span>
              </div>
            </div>
          </div>

          {/* Revolut Timeframe Pills */}
          <div className="flex items-center gap-1 bg-[#F1F3F5] dark:bg-[#1C1D22] p-1 rounded-full border border-black/[0.04] dark:border-white/5 shrink-0 overflow-x-auto">
            {(['1H', '6H', '1D', '1W', '1M', 'YTD', 'ALL'] as const).map((tf) => {
              const isActive = timeframe === tf;
              return (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-3 py-1 rounded-full text-xs font-bold transition-all cursor-pointer ${
                    isActive ? 'bg-white dark:bg-[#2C2D35] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  {tf}
                </button>
              );
            })}
          </div>
        </div>

        {/* Chart Area */}
        <div className="h-64 sm:h-72 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={pnlTimeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="revolutGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={isPositive ? '#00D09C' : '#FF453A'} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={isPositive ? '#00D09C' : '#FF453A'} stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="displayTime" stroke="#94A3B8" tick={{ fill: '#94A3B8', fontSize: 9, fontWeight: 600 }} tickLine={false} axisLine={false} minTickGap={35} />
              <YAxis domain={['auto', 'auto']} stroke="#94A3B8" tick={{ fill: '#94A3B8', fontSize: 10, fontWeight: 600 }} tickLine={false} axisLine={false} tickFormatter={(val) => `$${Math.round(val).toLocaleString()}`} />
              <Tooltip 
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload;
                    return (
                      <div className="bg-white dark:bg-[#1C1D22] text-slate-900 dark:text-white px-4 py-3 rounded-2xl text-xs font-mono shadow-xl border border-black/[0.08] dark:border-white/10 space-y-1">
                        <div className="text-[10px] text-slate-500 dark:text-[#8E8F99] font-bold">{d.date} • {d.time || d.displayTime}</div>
                        <div className="text-sm font-extrabold text-slate-950 dark:text-white">${d.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                        <div className={`font-bold ${d.pnl >= 0 ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                          {d.pnl >= 0 ? '+' : ''}${d.pnl.toFixed(2)} Mark-to-Market
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
                stroke={isPositive ? '#00D09C' : '#FF453A'} 
                strokeWidth={2.5} 
                fillOpacity={1} 
                fill="url(#revolutGrad)" 
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Revolut Informational Caption */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-black/[0.04] dark:border-white/5 text-[11px] text-slate-500 dark:text-[#8E8F99]">
          <p>
            Mark-to-market valuations reflect real-time Polymarket CLOB midpoint orderbook prices and execution fills.
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowResetModal(true)}
              className="text-xs text-slate-500 dark:text-[#8E8F99] hover:text-slate-950 dark:hover:text-white transition-colors cursor-pointer flex items-center gap-1 font-semibold"
            >
              <RefreshCw size={12} />
              Reset Ledger
            </button>
            <button
              onClick={() => setShowRawDataModal(true)}
              className="text-xs text-slate-500 dark:text-[#8E8F99] hover:text-slate-950 dark:hover:text-white transition-colors cursor-pointer flex items-center gap-1 font-semibold ml-2"
            >
              <Code2 size={12} />
              Raw Data
            </button>
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 2. REVOLUT ANALYTICS & CARD WIDGETS SECTION */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        
        {/* Card 1: Active Capital Allocation (Multi-Segment Bar) */}
        <div className="revolut-card p-5 space-y-4 rounded-[26px]">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-slate-500 dark:text-[#8E8F99]">Capital Allocation</span>
            <div className="text-2xl font-bold text-slate-950 dark:text-white font-outfit">
              ${totalNotionalInvested.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </div>
          </div>

          {/* Segmented Progress Bar */}
          <div className="h-2.5 w-full rounded-full bg-slate-100 dark:bg-[#1C1D22] overflow-hidden flex gap-1">
            <div className="h-full bg-[#00D09C] rounded-full" style={{ width: '42%' }} />
            <div className="h-full bg-[#FF7A00] rounded-full" style={{ width: '28%' }} />
            <div className="h-full bg-[#FF2D78] rounded-full" style={{ width: '18%' }} />
            <div className="h-full bg-slate-300 dark:bg-[#787985] rounded-full" style={{ width: '12%' }} />
          </div>

          {/* Legend */}
          <div className="grid grid-cols-2 gap-2 text-[11px] font-semibold text-slate-600 dark:text-[#8E8F99]">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#00D09C]" />
              <span className="text-slate-900 dark:text-white">hoodr</span> (42%)
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#FF7A00]" />
              <span className="text-slate-900 dark:text-white">Kracken</span> (28%)
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#FF2D78]" />
              <span className="text-slate-900 dark:text-white">bloodmaster</span> (18%)
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-slate-400 dark:bg-[#787985]" />
              <span>Others</span> (12%)
            </div>
          </div>
        </div>

        {/* Card 2: Execution Win Rate & Micro Dual-Bars */}
        <div className="revolut-card p-5 space-y-4 rounded-[26px]">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-slate-500 dark:text-[#8E8F99]">Execution Win Rate</span>
            <div className="text-2xl font-bold text-slate-950 dark:text-white font-outfit">
              {winRate.toFixed(1)}% <span className="text-xs text-slate-500 dark:text-[#8E8F99] font-normal">({totalWins}W / {totalLosses}L)</span>
            </div>
          </div>

          {/* Dual Progress Bars */}
          <div className="space-y-2">
            <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-[#1C1D22] overflow-hidden">
              <div 
                className="h-full bg-[#00D09C] rounded-full transition-all" 
                style={{ width: `${Math.min(100, Math.max(5, winRate))}%` }} 
              />
            </div>
            <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-[#1C1D22] overflow-hidden">
              <div 
                className="h-full bg-[#FF453A] rounded-full transition-all" 
                style={{ width: `${Math.min(100, Math.max(5, 100 - winRate))}%` }} 
              />
            </div>
          </div>

          <div className="flex justify-between text-[11px] font-semibold">
            <span className="text-emerald-600 dark:text-[#00D09C]">{totalWins} Profitable Fills</span>
            <span className="text-rose-600 dark:text-[#FF453A]">{totalLosses} Unprofitable Fills</span>
          </div>
        </div>

        {/* Card 3: Taker Fee & Cashflow Efficiency */}
        <div className="revolut-card p-5 space-y-4 rounded-[26px]">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-slate-500 dark:text-[#8E8F99]">Quadratic Fee Rate</span>
            <div className="text-2xl font-bold text-slate-950 dark:text-white font-outfit">
              {feeRatePct.toFixed(2)}% <span className="text-xs text-emerald-600 dark:text-[#00D09C] font-semibold">● On track</span>
            </div>
          </div>

          {/* Micro Vertical Indicator Bars */}
          <div className="flex items-end gap-1.5 h-6">
            <div className="w-2.5 h-3 bg-slate-200 dark:bg-[#2C2D35] rounded-full" />
            <div className="w-2.5 h-5 bg-slate-200 dark:bg-[#2C2D35] rounded-full" />
            <div className="w-2.5 h-6 bg-[#00D09C] rounded-full" />
            <div className="w-2.5 h-4 bg-slate-200 dark:bg-[#2C2D35] rounded-full" />
            <div className="w-2.5 h-5 bg-[#00D09C] rounded-full" />
          </div>

          <div className="flex justify-between text-[11px] text-slate-500 dark:text-[#8E8F99]">
            <span>Dynamic Polymarket Taker Gate</span>
            <span className="text-slate-950 dark:text-white font-mono font-bold">EV &gt; 2.5× Fee</span>
          </div>
        </div>

      </div>

      {/* ========================================================= */}
      {/* 3. REVOLUT ALPHA & DRAWDOWN ATTRIBUTION LIST */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        
        {/* Top Alpha Generators */}
        <div className="revolut-card p-5 sm:p-6 space-y-4 rounded-[26px]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-emerald-50 dark:bg-[#00D09C]/10 border border-emerald-200 dark:border-[#00D09C]/20 flex items-center justify-center text-emerald-600 dark:text-[#00D09C]">
                <ArrowUpRight size={15} />
              </div>
              <h4 className="text-sm font-bold text-slate-950 dark:text-white">Top Alpha Generators</h4>
            </div>
            <span className="text-[11px] font-mono text-slate-400 dark:text-[#8E8F99]">Closed &amp; Open</span>
          </div>

          <div className="space-y-2">
            {topAlpha.length === 0 ? (
              <p className="text-xs text-slate-400 dark:text-[#8E8F99] py-4 text-center">No profitable positions recorded yet</p>
            ) : (
              topAlpha.map((m) => (
                <div
                  key={m.key}
                  onClick={() => m.sampleTrade && onSelectTrade && onSelectTrade(m.sampleTrade)}
                  className="p-3 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] hover:bg-slate-100 dark:hover:bg-[#24262E] border border-black/[0.04] dark:border-white/5 transition-all cursor-pointer flex items-center justify-between"
                >
                  <div className="min-w-0 pr-3">
                    <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">{m.question}</p>
                    <span className="text-[10px] text-slate-500 dark:text-[#8E8F99] font-mono">{m.whaleName} • {m.outcome}</span>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-xs font-mono font-bold text-emerald-600 dark:text-[#00D09C]">
                      +${m.totalPnl.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Top Drawdowns */}
        <div className="revolut-card p-5 sm:p-6 space-y-4 rounded-[26px]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-rose-50 dark:bg-[#FF453A]/10 border border-rose-200 dark:border-[#FF453A]/20 flex items-center justify-center text-rose-600 dark:text-[#FF453A]">
                <ArrowDownRight size={15} />
              </div>
              <h4 className="text-sm font-bold text-slate-950 dark:text-white">Top Drawdowns</h4>
            </div>
            <span className="text-[11px] font-mono text-slate-400 dark:text-[#8E8F99]">Risk Audit</span>
          </div>

          <div className="space-y-2">
            {topDrawdown.length === 0 ? (
              <p className="text-xs text-slate-400 dark:text-[#8E8F99] py-4 text-center">No drawdown positions recorded</p>
            ) : (
              topDrawdown.map((m) => (
                <div
                  key={m.key}
                  onClick={() => m.sampleTrade && onSelectTrade && onSelectTrade(m.sampleTrade)}
                  className="p-3 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] hover:bg-slate-100 dark:hover:bg-[#24262E] border border-black/[0.04] dark:border-white/5 transition-all cursor-pointer flex items-center justify-between"
                >
                  <div className="min-w-0 pr-3">
                    <p className="text-xs font-semibold text-slate-900 dark:text-white truncate">{m.question}</p>
                    <span className="text-[10px] text-slate-500 dark:text-[#8E8F99] font-mono">{m.whaleName} • {m.outcome}</span>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-xs font-mono font-bold text-rose-600 dark:text-[#FF453A]">
                      -${Math.abs(m.totalPnl).toFixed(2)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>

      {/* ========================================================= */}
      {/* RESET SANDBOX MODAL */}
      {/* ========================================================= */}
      {showResetModal && (
        <div className="fixed inset-0 bg-black/60 dark:bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/10 dark:border-white/10 p-6 rounded-[28px] max-w-sm w-full space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-slate-950 dark:text-white">Reset Sandbox to $10,000?</h3>
            <p className="text-xs text-slate-500 dark:text-[#8E8F99]">
              This will clear historical simulation trade logs and reset your balance back to pristine $10,000.00 baseline.
            </p>
            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setShowResetModal(false)}
                className="flex-1 py-3 rounded-full bg-slate-100 dark:bg-[#1C1D22] hover:bg-slate-200 dark:hover:bg-[#24262E] text-slate-800 dark:text-white text-xs font-semibold border border-black/5 dark:border-white/5 transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleResetExecute}
                disabled={isResetting}
                className="flex-1 py-3 rounded-full bg-slate-950 dark:bg-white hover:bg-slate-800 dark:hover:bg-slate-200 text-white dark:text-black text-xs font-bold transition-all cursor-pointer flex items-center justify-center gap-1.5"
              >
                {isResetting && <Loader2 size={13} className="animate-spin" />}
                Confirm Reset
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* RAW DATA CODE MODAL */}
      {/* ========================================================= */}
      {showRawDataModal && (
        <div className="fixed inset-0 bg-black/60 dark:bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/10 dark:border-white/10 p-6 rounded-[28px] max-w-xl w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-black/10 dark:border-white/10 pb-3">
              <h3 className="text-sm font-bold text-slate-950 dark:text-white">Raw Snapshot Data Payload</h3>
              <button onClick={() => setShowRawDataModal(false)} className="p-1 rounded-full text-slate-400 dark:text-[#8E8F99] hover:text-slate-800 dark:hover:text-white">
                <X size={16} />
              </button>
            </div>
            <pre className="bg-slate-950 p-4 rounded-2xl text-[11px] font-mono text-[#00D09C] overflow-x-auto max-h-80 border border-white/5">
              {JSON.stringify(pnlTimeline, null, 2)}
            </pre>
            <button
              onClick={() => {
                navigator.clipboard.writeText(JSON.stringify(pnlTimeline, null, 2));
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              }}
              className="w-full py-3 rounded-full bg-slate-100 dark:bg-[#1C1D22] hover:bg-slate-200 dark:hover:bg-[#24262E] text-slate-800 dark:text-white text-xs font-bold border border-black/5 dark:border-white/5 transition-all flex items-center justify-center gap-1.5"
            >
              {copied ? <Check size={14} className="text-[#00D09C]" /> : <Copy size={14} />}
              {copied ? 'Copied to Clipboard' : 'Copy JSON'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
