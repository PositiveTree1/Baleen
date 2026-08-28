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
  Loader2,
  BarChart2,
  Activity,
  CandlestickChart
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
  totalFilledTrades = 0,
  topAlphaMarkets,
  topDrawdownMarkets,
  allTimeWinRate,
  allTimeWins,
  allTimeLosses,
  onSelectTrade,
  onResetComplete
}: PortfolioAnalyticsProps) {
  const [timeframe, setTimeframe] = useState<string>('ALL');
  const [chartType, setChartType] = useState<'area' | 'candles'>('area');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [showDeepAnalytics, setShowDeepAnalytics] = useState(false);
  const [showStrategyModal, setShowStrategyModal] = useState(false);
  const [showSpreadsheet, setShowSpreadsheet] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [showRawDataModal, setShowRawDataModal] = useState(false);
  const [copied, setCopied] = useState(false);

  // 1. Timeframe Filter on Execution Logs
  const targetLogs = useMemo(() => {
    if (timeframe === 'ALL') return logs;
    const now = Date.now();
    const map: Record<string, number> = {
      '1H': 60 * 60 * 1000,
      '6H': 6 * 60 * 60 * 1000,
      '1D': 24 * 60 * 60 * 1000,
      '1W': 7 * 24 * 60 * 60 * 1000,
      '1M': 30 * 24 * 60 * 60 * 1000,
    };
    const span = map[timeframe] || 0;
    if (!span) return logs;
    return logs.filter((l) => {
      const t = new Date(l.timestamp).getTime();
      return now - t <= span;
    });
  }, [logs, timeframe]);

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
    sampleTrade: ExecutionLog;
  }

  // 2. Aggregate Market Attribution (Top Alpha & Top Drawdown)
  const { topAlpha, topDrawdown } = useMemo(() => {
    // When viewing all-time, prefer the full database attribution computed by the backend summary
    if (timeframe === 'ALL' && topAlphaMarkets && topAlphaMarkets.length > 0) {
      const alpha = topAlphaMarkets.map((m: any) => ({
        key: m.key || m.conditionId || m.question,
        question: m.question || 'Prediction Market',
        conditionId: m.conditionId || '',
        outcome: m.outcome || 'Yes',
        totalPnl: m.totalPnl ?? 0.0,
        totalNotional: m.totalNotional ?? 0.0,
        fillsCount: m.fillsCount ?? 0,
        avgFillPrice: m.avgFillPrice ?? 0.0,
        whaleName: m.whaleName || 'Whale',
        sampleTrade: m.sampleTrade || logs.find(l => (l.marketQuestion === m.question || l.marketConditionId === m.conditionId)) || logs[0]
      })).slice(0, 4);

      const drawdown = (topDrawdownMarkets || []).map((m: any) => ({
        key: m.key || m.conditionId || m.question,
        question: m.question || 'Prediction Market',
        conditionId: m.conditionId || '',
        outcome: m.outcome || 'Yes',
        totalPnl: m.totalPnl ?? 0.0,
        totalNotional: m.totalNotional ?? 0.0,
        fillsCount: m.fillsCount ?? 0,
        avgFillPrice: m.avgFillPrice ?? 0.0,
        whaleName: m.whaleName || 'Whale',
        sampleTrade: m.sampleTrade || logs.find(l => (l.marketQuestion === m.question || l.marketConditionId === m.conditionId)) || logs[0]
      })).slice(0, 4);

      return { topAlpha: alpha, topDrawdown: drawdown };
    }

    const marketMap = new Map<string, MarketSummary>();
    targetLogs.forEach((l) => {
      const key = l.marketQuestion || l.marketConditionId || l.id;
      const notional = l.size ?? 0.0;
      const pnl = l.pnl ?? 0.0;
      const fillP = l.fillPrice || l.entryPrice || 0.0;
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
    let alpha = all.filter((m) => m.totalPnl > 0).sort((a, b) => b.totalPnl - a.totalPnl).slice(0, 4);
    let drawdown = all.filter((m) => m.totalPnl < 0).sort((a, b) => a.totalPnl - b.totalPnl).slice(0, 4);

    if (alpha.length === 0 && topAlphaMarkets && topAlphaMarkets.length > 0) {
      alpha = topAlphaMarkets.map((m: any) => ({
        key: m.key || m.conditionId || m.question,
        question: m.question || 'Prediction Market',
        conditionId: m.conditionId || '',
        outcome: m.outcome || 'Yes',
        totalPnl: m.totalPnl ?? 0.0,
        totalNotional: m.totalNotional ?? 0.0,
        fillsCount: m.fillsCount ?? 0,
        avgFillPrice: m.avgFillPrice ?? 0.0,
        whaleName: m.whaleName || 'Whale',
        sampleTrade: m.sampleTrade || logs.find(l => (l.marketQuestion === m.question || l.marketConditionId === m.conditionId)) || logs[0]
      })).slice(0, 4);
    }

    if (drawdown.length === 0 && topDrawdownMarkets && topDrawdownMarkets.length > 0) {
      drawdown = topDrawdownMarkets.map((m: any) => ({
        key: m.key || m.conditionId || m.question,
        question: m.question || 'Prediction Market',
        conditionId: m.conditionId || '',
        outcome: m.outcome || 'Yes',
        totalPnl: m.totalPnl ?? 0.0,
        totalNotional: m.totalNotional ?? 0.0,
        fillsCount: m.fillsCount ?? 0,
        avgFillPrice: m.avgFillPrice ?? 0.0,
        whaleName: m.whaleName || 'Whale',
        sampleTrade: m.sampleTrade || logs.find(l => (l.marketQuestion === m.question || l.marketConditionId === m.conditionId)) || logs[0]
      })).slice(0, 4);
    }

    return { topAlpha: alpha, topDrawdown: drawdown };
  }, [timeframe, targetLogs, topAlphaMarkets, topDrawdownMarkets, logs]);

  // 3. Execution Scorecard Metrics
  const { totalWins, totalLosses, winRate, feeRatePct, totalNotionalInvested } = useMemo(() => {
    if (allTimeWins !== undefined && allTimeLosses !== undefined) {
      const totalEval = allTimeWins + allTimeLosses;
      const wr = allTimeWinRate ?? (totalEval > 0 ? (allTimeWins / totalEval) * 100 : 0.0);
      const totalNotional = logs.reduce((acc, l) => acc + (l.size ?? 0.0), 0);
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
      const notional = l.size ?? 0.0;
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

  // 4. Authentic Active Capital Allocation (Open Positions Only)
  const activeHoldingLogs = useMemo(() => {
    return logs.filter((l) => l.status === 'FILLED' && l.side === 'BUY');
  }, [logs]);

  const activeAllocationStats = useMemo(() => {
    const whaleMap = new Map<string, number>();
    let totalNotional = 0;

    activeHoldingLogs.forEach((l) => {
      const name = l.whaleName || l.whalePseudonym || (l.walletAddress ? `${l.walletAddress.slice(0, 6)}...${l.walletAddress.slice(-4)}` : 'Whale');
      const size = l.size ?? 0.0;
      whaleMap.set(name, (whaleMap.get(name) || 0) + size);
      totalNotional += size;
    });

    const sorted = Array.from(whaleMap.entries())
      .map(([name, notional]) => ({
        name,
        notional,
        pct: totalNotional > 0 ? (notional / totalNotional) * 100 : 0
      }))
      .sort((a, b) => b.notional - a.notional);

    const top3 = sorted.slice(0, 3);
    const top3PctSum = top3.reduce((acc, x) => acc + x.pct, 0);
    const othersPct = Math.max(0, 100 - top3PctSum);

    const colors = ['#00D09C', '#FF7A00', '#FF2D78', '#787985'];

    const segments = top3.map((item, idx) => ({
      name: item.name,
      pct: Math.max(1, Math.round(item.pct)),
      color: colors[idx]
    }));

    if (sorted.length > 3 && othersPct > 0) {
      segments.push({
        name: 'Others',
        pct: Math.max(1, Math.round(othersPct)),
        color: colors[3]
      });
    }

    if (segments.length === 0) {
      segments.push({ name: '100% Cash Balance', pct: 100, color: '#00D09C' });
    }

    const effectiveInvested = currentBalance > 0 ? Math.min(totalNotional, currentBalance) : totalNotional;
    const freeCash = currentBalance > 0 ? Math.max(0, currentBalance - effectiveInvested) : 0;
    const allocatedPct = currentBalance > 0 ? Math.min(100, Math.round((effectiveInvested / currentBalance) * 100)) : 0;

    return {
      segments,
      totalNotional: effectiveInvested,
      grossNotional: totalNotional,
      freeCash,
      allocatedPct,
      count: activeHoldingLogs.length
    };
  }, [activeHoldingLogs, currentBalance]);

  // 5. Portfolio Snapshots Timeline
  const [serverSnapshots, setServerSnapshots] = useState<any[]>(snapshots);
  const [chartLoading, setChartLoading] = useState(false);
  const [hoveredCandle, setHoveredCandle] = useState<any>(null);

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
    return [];
  }, [serverSnapshots]);

  // Build OHLC Candles from timeline snapshots
  const ohlcCandles = useMemo(() => {
    if (!pnlTimeline || pnlTimeline.length < 2) return [];
    
    const numBuckets = Math.min(30, Math.max(6, Math.floor(pnlTimeline.length / 4)));
    const bucketSize = Math.max(1, Math.floor(pnlTimeline.length / numBuckets));
    const candles: {
      time: string;
      open: number;
      high: number;
      low: number;
      close: number;
      isBullish: boolean;
      pnl: number;
    }[] = [];

    for (let i = 0; i < pnlTimeline.length; i += bucketSize) {
      const chunk = pnlTimeline.slice(i, i + bucketSize);
      if (chunk.length === 0) continue;
      const prices = chunk.map((s: any) => s.balance);
      const open = chunk[0].balance;
      const close = chunk[chunk.length - 1].balance;
      const high = Math.max(...prices);
      const low = Math.min(...prices);
      const isBullish = close >= open;

      candles.push({
        time: chunk[chunk.length - 1].displayTime,
        open,
        high,
        low,
        close,
        isBullish,
        pnl: close - open,
      });
    }
    return candles;
  }, [pnlTimeline]);

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

  const handleOpenMarketTrade = (m: any) => {
    if (!onSelectTrade) return;
    const match = logs.find((l) => (m.conditionId && l.marketConditionId === m.conditionId) || (m.question && l.marketQuestion === m.question));
    if (match) {
      onSelectTrade(match);
    } else {
      const avgP = m.avgFillPrice || 0.5;
      onSelectTrade({
        id: m.conditionId || m.key || `mkt-${Date.now()}`,
        timestamp: new Date().toISOString(),
        walletAddress: m.walletAddress || '0x0000000000000000000000000000000000000000',
        marketQuestion: m.question || 'Prediction Market Contract',
        marketConditionId: m.conditionId || '',
        outcome: m.outcome || 'Yes',
        side: (m.totalPnl ?? 0) >= 0 ? 'BUY' : 'SELL',
        entryPrice: avgP,
        fillPrice: avgP,
        currentPrice: avgP,
        size: m.totalNotional || 10.0,
        pnl: m.totalPnl ?? 0.0,
        pnlPct: (m.totalNotional && m.totalNotional > 0) ? ((m.totalPnl ?? 0) / m.totalNotional) * 100 : 0.0,
        whaleName: m.whaleName || 'Whale',
        status: 'RESOLVED',
      });
    }
  };

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* ========================================================= */}
      {/* 1. REVOLUT LINE / CANDLESTICK CHART CARD */}
      {/* ========================================================= */}
      <div className="revolut-card p-4 sm:p-8 space-y-4 sm:space-y-6 rounded-[22px] sm:rounded-[26px]">
        {/* Asset Header & Price */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <span className="text-[11px] sm:text-xs font-semibold text-slate-500 dark:text-[#8E8F99] uppercase tracking-wider">
              Polymarket Copy Portfolio · Balance
            </span>
            <div className="flex flex-wrap items-baseline gap-2 sm:gap-3">
              <span className="text-2xl sm:text-4xl lg:text-5xl font-bold font-outfit text-slate-950 dark:text-white tracking-tight">
                ${currentBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <div className={`inline-flex items-center gap-1 text-[11px] sm:text-xs font-mono font-bold ${isPositive ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                {isPositive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                <span>
                  {isPositive ? '+' : ''}${periodPnL.toFixed(2)} ({isPositive ? '+' : ''}{periodPnLPct.toFixed(2)}%) · {timeframe}
                </span>
              </div>
            </div>
          </div>

          {/* Controls: Chart Type Toggle & Revolut Timeframe Pills */}
          <div className="flex flex-wrap sm:flex-nowrap items-center justify-between sm:justify-end gap-2 w-full sm:w-auto">
            {/* Area vs Candle Toggle */}
            <div className="flex items-center bg-[#F1F3F5] dark:bg-[#1C1D22] p-0.5 sm:p-1 rounded-full border border-black/[0.04] dark:border-white/5">
              <button
                onClick={() => setChartType('area')}
                className={`p-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                  chartType === 'area' ? 'bg-white dark:bg-[#2C2D35] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white'
                }`}
                title="Line / Area View"
              >
                <Activity size={13} />
              </button>
              <button
                onClick={() => setChartType('candles')}
                className={`p-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                  chartType === 'candles' ? 'bg-white dark:bg-[#2C2D35] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white'
                }`}
                title="Candlestick (OHLC) Trader View"
              >
                <CandlestickChart size={13} />
              </button>
            </div>

            {/* Revolut Timeframe Pills */}
            <div className="flex items-center gap-0.5 sm:gap-1 bg-[#F1F3F5] dark:bg-[#1C1D22] p-0.5 sm:p-1 rounded-full border border-black/[0.04] dark:border-white/5 overflow-x-auto max-w-full no-scrollbar">
              {(['1H', '6H', '1D', '1W', '1M', 'YTD', 'ALL'] as const).map((tf) => {
                const isActive = timeframe === tf;
                return (
                  <button
                    key={tf}
                    onClick={() => setTimeframe(tf)}
                    className={`px-2 sm:px-3 py-1 rounded-full text-[11px] sm:text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                      isActive ? 'bg-white dark:bg-[#2C2D35] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    {tf}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Chart Area */}
        <div className="h-64 sm:h-72 w-full pt-2">
          {chartLoading || pnlTimeline.length === 0 ? (
            <div className="w-full h-full flex flex-col items-center justify-center gap-3">
              <div className="w-full h-48 rounded-2xl animate-shimmer" />
              <span className="text-xs text-slate-400 dark:text-[#8E8F99] font-mono">Synchronizing verified Polymarket CLOB trajectory...</span>
            </div>
          ) : chartType === 'candles' && ohlcCandles.length > 0 ? (
            /* Candlestick OHLC Chart Renderer */
            <div className="w-full h-full flex flex-col justify-between relative select-none">
              {hoveredCandle && (
                <div className="absolute top-0 right-2 z-10 bg-white/90 dark:bg-[#1C1D22]/90 backdrop-blur-sm border border-black/10 dark:border-white/10 rounded-xl px-3 py-1.5 text-[11px] font-mono shadow-md flex items-center gap-3">
                  <span>{hoveredCandle.time}</span>
                  <span>O: <strong>${hoveredCandle.open.toFixed(0)}</strong></span>
                  <span>H: <strong className="text-emerald-600 dark:text-[#00D09C]">${hoveredCandle.high.toFixed(0)}</strong></span>
                  <span>L: <strong className="text-rose-600 dark:text-[#FF453A]">${hoveredCandle.low.toFixed(0)}</strong></span>
                  <span>C: <strong>${hoveredCandle.close.toFixed(0)}</strong></span>
                </div>
              )}
              {(() => {
                const allHighs = ohlcCandles.map((c) => c.high);
                const allLows = ohlcCandles.map((c) => c.low);
                const minPrice = Math.min(...allLows);
                const maxPrice = Math.max(...allHighs);
                const range = Math.max(1, maxPrice - minPrice);
                const pad = range * 0.1;
                const domainMin = minPrice - pad;
                const domainMax = maxPrice + pad;
                const domainRange = domainMax - domainMin;

                return (
                  <svg className="w-full h-56" viewBox={`0 0 ${ohlcCandles.length * 20} 220`} preserveAspectRatio="none">
                    {ohlcCandles.map((c, idx) => {
                      const x = idx * 20 + 10;
                      const wickY1 = 200 - ((c.high - domainMin) / domainRange) * 190;
                      const wickY2 = 200 - ((c.low - domainMin) / domainRange) * 190;
                      const bodyTopVal = Math.max(c.open, c.close);
                      const bodyBotVal = Math.min(c.open, c.close);
                      const bodyY = 200 - ((bodyTopVal - domainMin) / domainRange) * 190;
                      const bodyH = Math.max(3, ((bodyTopVal - bodyBotVal) / domainRange) * 190);
                      const color = c.isBullish ? '#00D09C' : '#FF453A';

                      return (
                        <g 
                          key={idx} 
                          onMouseEnter={() => setHoveredCandle(c)}
                          onMouseLeave={() => setHoveredCandle(null)}
                          className="cursor-crosshair group"
                        >
                          {/* Wick */}
                          <line x1={x} y1={wickY1} x2={x} y2={wickY2} stroke={color} strokeWidth={1.5} opacity={0.8} />
                          {/* Body */}
                          <rect 
                            x={x - 6} 
                            y={bodyY} 
                            width={12} 
                            height={bodyH} 
                            fill={color} 
                            rx={1.5}
                            className="group-hover:opacity-100 transition-opacity"
                          />
                        </g>
                      );
                    })}
                  </svg>
                );
              })()}
              <div className="flex justify-between text-[9px] font-mono text-slate-400 dark:text-[#8E8F99] pt-1 border-t border-black/[0.04] dark:border-white/5">
                <span>{ohlcCandles[0]?.time}</span>
                <span>Candlestick OHLC Trader Mode (Polymarket Mark-to-Market Snapshots)</span>
                <span>{ohlcCandles[ohlcCandles.length - 1]?.time}</span>
              </div>
            </div>
          ) : (
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
          )}
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
        
        {/* Card 1: Active Capital Invested (Live Open Positions Only) */}
        <div className="revolut-card p-5 space-y-4 rounded-[26px]">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 dark:text-[#8E8F99]">Active Capital Invested</span>
              <span className="text-[10px] font-mono font-bold text-emerald-600 dark:text-[#00D09C] bg-emerald-50 dark:bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-200/50 dark:border-emerald-500/20">
                {activeAllocationStats.count} Live Position{activeAllocationStats.count === 1 ? '' : 's'}
              </span>
            </div>
            <div className="flex items-baseline justify-between">
              <div className="text-2xl font-bold text-slate-950 dark:text-white font-outfit">
                ${activeAllocationStats.totalNotional.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <span className="text-[11px] font-mono font-medium text-slate-500 dark:text-[#8E8F99]">
                {activeAllocationStats.allocatedPct}% of Equity
              </span>
            </div>
          </div>

          {/* Dynamic Segmented Progress Bar */}
          <div className="h-2.5 w-full rounded-full bg-slate-100 dark:bg-[#1C1D22] overflow-hidden flex gap-1">
            {activeAllocationStats.segments.map((seg) => (
              <div 
                key={seg.name} 
                className="h-full rounded-full transition-all"
                style={{ width: `${seg.pct}%`, backgroundColor: seg.color }} 
              />
            ))}
          </div>

          {/* Dynamic Legend */}
          <div className="grid grid-cols-2 gap-2 text-[11px] font-semibold text-slate-600 dark:text-[#8E8F99]">
            {activeAllocationStats.segments.map((seg) => (
              <div key={seg.name} className="flex items-center gap-1.5 truncate">
                <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: seg.color }} />
                <span className="text-slate-900 dark:text-white truncate">{seg.name}</span>
                <span className="shrink-0">({seg.pct}%)</span>
              </div>
            ))}
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
      {/* 3. REVOLUT ALPHA & DRAWDOWN ATTRIBUTION LIST (CLICKABLE) */}
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
            <span className="text-[11px] font-mono text-slate-400 dark:text-[#8E8F99]">Click to inspect</span>
          </div>

          <div className="space-y-2">
            {topAlpha.length === 0 ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="p-3 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 flex items-center justify-between">
                    <div className="space-y-1.5">
                      <div className="w-48 h-3 rounded-md animate-shimmer" />
                      <div className="w-28 h-2 rounded-md animate-shimmer" />
                    </div>
                    <div className="w-12 h-3 rounded-md animate-shimmer" />
                  </div>
                ))}
              </div>
            ) : (
              topAlpha.map((m) => (
                <div
                  key={m.key}
                  onClick={() => handleOpenMarketTrade(m)}
                  className="p-3 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] hover:bg-slate-100 dark:hover:bg-[#24262E] border border-black/[0.04] dark:border-white/5 transition-all cursor-pointer flex items-center justify-between group"
                >
                  <div className="min-w-0 pr-3">
                    <p className="text-xs font-semibold text-slate-900 dark:text-white truncate group-hover:text-emerald-600 dark:group-hover:text-[#00D09C] transition-colors">{m.question}</p>
                    <span className="text-[10px] text-slate-500 dark:text-[#8E8F99] font-mono">{m.whaleName} • {m.outcome} • {m.fillsCount} fills</span>
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
            <span className="text-[11px] font-mono text-slate-400 dark:text-[#8E8F99]">Click to inspect</span>
          </div>

          <div className="space-y-2">
            {topDrawdown.length === 0 ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="p-3 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 flex items-center justify-between">
                    <div className="space-y-1.5">
                      <div className="w-48 h-3 rounded-md animate-shimmer" />
                      <div className="w-28 h-2 rounded-md animate-shimmer" />
                    </div>
                    <div className="w-12 h-3 rounded-md animate-shimmer" />
                  </div>
                ))}
              </div>
            ) : (
              topDrawdown.map((m) => (
                <div
                  key={m.key}
                  onClick={() => handleOpenMarketTrade(m)}
                  className="p-3 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] hover:bg-slate-100 dark:hover:bg-[#24262E] border border-black/[0.04] dark:border-white/5 transition-all cursor-pointer flex items-center justify-between group"
                >
                  <div className="min-w-0 pr-3">
                    <p className="text-xs font-semibold text-slate-900 dark:text-white truncate group-hover:text-rose-600 dark:group-hover:text-[#FF453A] transition-colors">{m.question}</p>
                    <span className="text-[10px] text-slate-500 dark:text-[#8E8F99] font-mono">{m.whaleName} • {m.outcome} • {m.fillsCount} fills</span>
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
