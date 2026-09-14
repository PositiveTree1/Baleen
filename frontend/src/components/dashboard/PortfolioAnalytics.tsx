'use client';
import { useMemo, useState, useEffect, useCallback } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { ExecutionLog, Wallet, MarketAttributionItem } from '@/types';
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
import { clearAllCache, fetchPortfolioSnapshots, fetchWallets, getCachedWallets } from '@/lib/api-client';
import { Modal } from '../ui/Modal';
import { ResetSandboxModal } from './ResetSandboxModal';

export function formatAllocPct(notional: number, total: number): string {
  if (notional <= 0 || total <= 0) return '0%';
  const pct = (notional / total) * 100;
  if (pct < 0.01) return '<0.01%';
  if (pct < 1) return `${pct.toFixed(2)}%`;
  return `${pct.toFixed(1)}%`;
}

export interface OhlcCandle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  isBullish: boolean;
  pnl: number;
}

export interface TimelineSnapshotPoint {
  displayTime: string;
  time: string;
  date: string;
  balance: number;
  pnl: number;
  rawTimestamp: number;
}

interface PortfolioAnalyticsProps {
  logs: ExecutionLog[];
  snapshots?: TimelineSnapshotPoint[];
  wallets?: Wallet[];
  userId?: string;
  startingBalance?: number;
  currentBalance?: number;
  totalFilledTrades?: number;
  topAlphaMarkets?: MarketAttributionItem[];
  topDrawdownMarkets?: MarketAttributionItem[];
  allTimeWinRate?: number;
  allTimeWins?: number;
  allTimeLosses?: number;
  onSelectTrade?: (trade: ExecutionLog) => void;
  onResetComplete?: () => void;
}

export function PortfolioAnalytics({
  logs,
  snapshots = [],
  wallets: propWallets,
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
  const [loadedWallets, setLoadedWallets] = useState<Wallet[]>(() => getCachedWallets() || []);

  useEffect(() => {
    fetchWallets({ limit: '150' }).then((data) => {
      if (Array.isArray(data) && data.length > 0) setLoadedWallets(data);
    }).catch(() => {});
  }, []);

  const effectiveWallets = (propWallets && propWallets.length > 0) ? propWallets : loadedWallets;

  const topCandidateRoster = useMemo(() => {
    return [...effectiveWallets]
      .filter((w) => (!w.status || w.status === 'active') && w.tier !== 'dormant' && !w.dormant && !w.isHft && w.tradesPerDay != null && w.tradesPerDay <= 50)
      .sort((a, b) => (b.score ?? -Infinity) - (a.score ?? -Infinity));
  }, [effectiveWallets]);

  const top10Addresses = useMemo(() => {
    return new Set(topCandidateRoster.slice(0, 10).map((w) => (w.address || '').toLowerCase()));
  }, [topCandidateRoster]);

  const top10Roster = useMemo(() => {
    return topCandidateRoster.slice(0, 10);
  }, [topCandidateRoster]);

  const [timeframe, setTimeframe] = useState<string>('ALL');
  const [chartType, setChartType] = useState<'area' | 'candles'>('area');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [showDeepAnalytics, setShowDeepAnalytics] = useState(false);
  const [showStrategyModal, setShowStrategyModal] = useState(false);
  const [showSpreadsheet, setShowSpreadsheet] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);
  const [showRawDataModal, setShowRawDataModal] = useState(false);
  const [copied, setCopied] = useState(false);

  // 1. Timeframe Filter on Execution Logs
  const targetLogs = useMemo(() => {
    if (timeframe === 'ALL') return logs;
    const latestTimestamp = logs.reduce((max, l) => {
      const t = l.timestamp ? new Date(l.timestamp).getTime() : 0;
      return t > max ? t : max;
    }, 0);
    const map: Record<string, number> = {
      '1H': 60 * 60 * 1000,
      '6H': 6 * 60 * 60 * 1000,
      '1D': 24 * 60 * 60 * 1000,
      '1W': 7 * 24 * 60 * 60 * 1000,
      '1M': 30 * 24 * 60 * 60 * 1000,
    };
    const span = map[timeframe] || 0;
    if (!span || latestTimestamp === 0) return logs;
    return logs.filter((l) => {
      const t = new Date(l.timestamp).getTime();
      return latestTimestamp - t <= span;
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
    sampleTrade?: ExecutionLog;
  }

  // 2. Aggregate Market Attribution (Top Alpha & Top Drawdown)
  const { topAlpha, topDrawdown } = useMemo(() => {
    // When viewing all-time, prefer the full database attribution computed by the backend summary
    if (timeframe === 'ALL' && topAlphaMarkets && topAlphaMarkets.length > 0) {
      const alpha = topAlphaMarkets.filter(m => m.totalPnl !== undefined && m.totalPnl !== null).map((m: MarketAttributionItem) => ({
        key: m.key || m.conditionId || m.question || 'unknown',
        question: m.question || 'Prediction Market',
        conditionId: m.conditionId || '',
        outcome: m.outcome || 'Yes',
        totalPnl: m.totalPnl as number,
        totalNotional: m.totalNotional ?? 0.0,
        fillsCount: m.fillsCount ?? 0,
        avgFillPrice: m.avgFillPrice ?? 0.0,
        whaleName: m.whaleName || 'Whale',
        sampleTrade: (m as { sampleTrade?: ExecutionLog }).sampleTrade || logs.find(l => (l.marketQuestion === m.question || l.marketConditionId === m.conditionId))
      })).slice(0, 4);

      const drawdown = (topDrawdownMarkets || []).filter(m => m.totalPnl !== undefined && m.totalPnl !== null).map((m: MarketAttributionItem) => ({
        key: m.key || m.conditionId || m.question || 'unknown',
        question: m.question || 'Prediction Market',
        conditionId: m.conditionId || '',
        outcome: m.outcome || 'Yes',
        totalPnl: m.totalPnl as number,
        totalNotional: m.totalNotional ?? 0.0,
        fillsCount: m.fillsCount ?? 0,
        avgFillPrice: m.avgFillPrice ?? 0.0,
        whaleName: m.whaleName || 'Whale',
        sampleTrade: (m as { sampleTrade?: ExecutionLog }).sampleTrade || logs.find(l => (l.marketQuestion === m.question || l.marketConditionId === m.conditionId))
      })).slice(0, 4);

      return { topAlpha: alpha, topDrawdown: drawdown };
    }

    // Otherwise compute from filtered timeframe logs
    const marketMap = new Map<string, MarketSummary>();

    targetLogs.forEach((l) => {
      const effPrice = l.fillPrice ?? l.entryPrice ?? null;
      const effPnl = l.pnl !== null && l.pnl !== undefined ? l.pnl : (l.feeUsd !== null && l.feeUsd !== undefined ? -l.feeUsd : 0.0);
      if (effPrice === null) return;

      const key = l.marketConditionId || l.marketQuestion || 'unknown';
      if (!marketMap.has(key)) {
        marketMap.set(key, {
          key,
          question: l.marketQuestion || 'Prediction Market',
          conditionId: l.marketConditionId || '',
          outcome: l.outcome || 'Yes',
          totalPnl: 0,
          totalNotional: 0,
          fillsCount: 0,
          avgFillPrice: effPrice,
          whaleName: l.whaleName || l.whalePseudonym || 'Whale',
          sampleTrade: l,
        });
      }

      const item = marketMap.get(key)!;
      const notional = l.size ? l.size * effPrice : 0.0;
      item.totalPnl += effPnl;
      item.totalNotional += notional;
      item.fillsCount += 1;
      if (!item.sampleTrade) item.sampleTrade = l;
    });

    const all = Array.from(marketMap.values());
    let alpha = all.filter((m) => m.totalPnl > 0).sort((a, b) => b.totalPnl - a.totalPnl).slice(0, 4);
    let drawdown = all.filter((m) => m.totalPnl < 0).sort((a, b) => a.totalPnl - b.totalPnl).slice(0, 4);

    if (alpha.length === 0 && topAlphaMarkets && topAlphaMarkets.length > 0) {
      alpha = topAlphaMarkets.filter(m => m.totalPnl !== undefined && m.totalPnl !== null).map((m: MarketAttributionItem) => ({
        key: m.key || m.conditionId || m.question || 'unknown',
        question: m.question || 'Prediction Market',
        conditionId: m.conditionId || '',
        outcome: m.outcome || 'Yes',
        totalPnl: m.totalPnl as number,
        totalNotional: m.totalNotional ?? 0.0,
        fillsCount: m.fillsCount ?? 0,
        avgFillPrice: m.avgFillPrice ?? 0.0,
        whaleName: m.whaleName || 'Whale',
        sampleTrade: (m as { sampleTrade?: ExecutionLog }).sampleTrade || logs.find(l => (l.marketQuestion === m.question || l.marketConditionId === m.conditionId))
      })).slice(0, 4);
    }

    if (drawdown.length === 0 && topDrawdownMarkets && topDrawdownMarkets.length > 0) {
      drawdown = topDrawdownMarkets.filter(m => m.totalPnl !== undefined && m.totalPnl !== null).map((m: MarketAttributionItem) => ({
        key: m.key || m.conditionId || m.question || 'unknown',
        question: m.question || 'Prediction Market',
        conditionId: m.conditionId || '',
        outcome: m.outcome || 'Yes',
        totalPnl: m.totalPnl as number,
        totalNotional: m.totalNotional ?? 0.0,
        fillsCount: m.fillsCount ?? 0,
        avgFillPrice: m.avgFillPrice ?? 0.0,
        whaleName: m.whaleName || 'Whale',
        sampleTrade: (m as { sampleTrade?: ExecutionLog }).sampleTrade || logs.find(l => (l.marketQuestion === m.question || l.marketConditionId === m.conditionId))
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

    targetLogs.filter((l) => l.pnl !== null && l.pnl !== undefined).forEach((l) => {
      const pnl = l.pnl as number;
      const notional = l.size ?? 0.0;
      const fee = l.feeUsd ?? 0.0;
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

  // 4. Authentic Active Capital Allocation (Sleeve Breakdown & Total Bankroll %)
  const activeHoldingLogs = useMemo(() => {
    return logs.filter((l) => l.status === 'FILLED' && l.side === 'BUY');
  }, [logs]);

  const activeAllocationStats = useMemo(() => {
    const bankroll = currentBalance > 0 ? currentBalance : 10000;
    const targetSleeveCount = bankroll < 250 ? 1 : bankroll < 1000 ? 2 : bankroll < 3000 ? 4 : bankroll < 15000 ? 5 : 10;
    const sleeveBudget = bankroll / targetSleeveCount;

    // 1. Group all filled BUY logs by wallet address
    const whaleMap = new Map<string, { address: string; notional: number; name: string; fillCount: number }>();
    let totalTargetNotional = 0;
    let totalTargetCount = 0;

    activeHoldingLogs.forEach((l) => {
      const addr = (l.walletAddress || '').toLowerCase();
      if (!addr) return;
      const size = l.size ?? 0.0;
      const name = l.whaleName || l.whalePseudonym || `${addr.slice(0, 6)}...${addr.slice(-4)}`;

      if (!whaleMap.has(addr)) {
        whaleMap.set(addr, { address: addr, notional: 0, name, fillCount: 0 });
      }
      const item = whaleMap.get(addr)!;
      item.notional += size;
      item.fillCount += 1;
      totalTargetNotional += size;
      totalTargetCount += 1;
    });

    const colors = ['#00D09C', '#FF7A00', '#FF2D78', '#00A3FF', '#A855F7', '#EC4899', '#EAB308', '#06B6D4', '#6366F1', '#14B8A6'];

    // 2. Actively deployed whales with positive holdings, sorted highest notional first
    const deployedWhales = Array.from(whaleMap.values())
      .filter((w) => w.notional > 0)
      .sort((a, b) => b.notional - a.notional)
      .map((w, idx) => {
        const bankrollPct = Math.round((w.notional / bankroll) * 1000) / 10;
        const sleevePct = Math.round((w.notional / sleeveBudget) * 100);
        return {
          name: w.name,
          address: w.address,
          notional: w.notional,
          fillCount: w.fillCount,
          bankrollPct,
          sleevePct,
          color: colors[idx % colors.length]
        };
      });

    // 3. Construct fixed sleeves:
    // Priority: Deployed whales with active holdings FIRST, then remaining slots filled with topCandidateRoster
    const sleeves: Array<{
      index: number;
      name: string;
      address: string;
      color: string;
      deployedNotional: number;
      sleevePct: number;
      bankrollPct: number;
      isDeployed: boolean;
    }> = [];

    const assignedAddrs = new Set<string>();

    // A. Add all actively deployed whales into the first sleeves
    deployedWhales.forEach((w) => {
      if (sleeves.length < targetSleeveCount) {
        assignedAddrs.add(w.address);
        const idx = sleeves.length;
        sleeves.push({
          index: idx + 1,
          name: w.name,
          address: w.address,
          color: w.color,
          deployedNotional: w.notional,
          sleevePct: w.sleevePct,
          bankrollPct: w.bankrollPct,
          isDeployed: true
        });
      }
    });

    // B. Fill remaining sleeves from topCandidateRoster (un-deployed cash slots)
    topCandidateRoster.forEach((c) => {
      const addr = (c.address || '').toLowerCase();
      if (sleeves.length < targetSleeveCount && addr && !assignedAddrs.has(addr)) {
        assignedAddrs.add(addr);
        const idx = sleeves.length;
        const name = c.pseudonym || c.name || `${addr.slice(0, 6)}...${addr.slice(-4)}`;
        sleeves.push({
          index: idx + 1,
          name,
          address: addr,
          color: colors[idx % colors.length],
          deployedNotional: 0,
          sleevePct: 0,
          bankrollPct: 0,
          isDeployed: false
        });
      }
    });

    // C. Fill any remaining with Cash reserve slots
    while (sleeves.length < targetSleeveCount) {
      const idx = sleeves.length;
      sleeves.push({
        index: idx + 1,
        name: `Sleeve #${idx + 1}`,
        address: '',
        color: colors[idx % colors.length],
        deployedNotional: 0,
        sleevePct: 0,
        bankrollPct: 0,
        isDeployed: false
      });
    }

    const totalInvestedBankrollPct = Math.round((totalTargetNotional / bankroll) * 1000) / 10;
    const freeCash = Math.max(0, bankroll - totalTargetNotional);
    const freeCashPct = Math.max(0, Math.round((100 - totalInvestedBankrollPct) * 10) / 10);

    const segments = deployedWhales.map((item) => ({
      name: item.name,
      pct: item.bankrollPct,
      sleevePct: item.sleevePct,
      notional: item.notional,
      color: item.color
    }));

    if (freeCashPct > 0) {
      segments.push({
        name: 'Free Cash',
        pct: freeCashPct,
        sleevePct: 100,
        notional: freeCash,
        color: '#475569'
      });
    }

    if (segments.length === 0) {
      segments.push({ name: '100% Cash Balance', pct: 100, sleevePct: 100, notional: bankroll, color: '#00D09C' });
    }

    return {
      targetSleeveCount,
      sleeves,
      top10Sleeves: sleeves, // backward compatibility
      segments,
      activeWhales: deployedWhales,
      totalNotional: totalTargetNotional,
      freeCash,
      allocatedPct: totalInvestedBankrollPct,
      sleeveBudget,
      count: totalTargetCount,
      legacyCount: 0,
      legacyNotional: 0,
      totalAllNotional: totalTargetNotional
    };
  }, [activeHoldingLogs, currentBalance, topCandidateRoster]);

  // 5. Portfolio Snapshots Timeline
  const [serverSnapshots, setServerSnapshots] = useState<TimelineSnapshotPoint[]>(snapshots);
  const [chartLoading, setChartLoading] = useState(false);
  const [hoveredCandle, setHoveredCandle] = useState<OhlcCandle | null>(null);
  const [snapshotRefreshKey, setSnapshotRefreshKey] = useState(0);

  useEffect(() => {
    let isMounted = true;
    const fetchTimeline = async () => {
      try {
        const data = await fetchPortfolioSnapshots(userId, timeframe);
        if (!isMounted) return;
        const isMultiDay = timeframe === 'ALL' || timeframe === '1M' || timeframe === 'YTD' || timeframe === '1W';

        if (Array.isArray(data) && data.length > 0) {
          const timeline: TimelineSnapshotPoint[] = data.flatMap((s) => {
            if (!s.timestamp || !Number.isFinite(s.balance) || !Number.isFinite(s.pnl)) return [];
            const ts = new Date(s.timestamp);
            if (!Number.isFinite(ts.getTime())) return [];
            const timeStr = formatFrenchTime(ts);
            const dateStr = formatFrenchDate(ts);
            return [{
              displayTime: isMultiDay && dateStr ? `${dateStr} ${timeStr}` : timeStr,
              time: timeStr,
              date: dateStr,
              balance: Math.round(s.balance * 100) / 100,
              pnl: Math.round(s.pnl * 100) / 100,
              rawTimestamp: ts.getTime(),
            }];
          });
          setServerSnapshots(timeline);
        }
      } catch (e) {
        console.debug("Snapshot fetch note:", e);
      } finally {
        if (isMounted) setChartLoading(false);
      }
    };

    void fetchTimeline();
    return () => {
      isMounted = false;
    };
  }, [userId, timeframe, currentBalance, startingBalance, snapshotRefreshKey]);

  const pnlTimeline = useMemo(() => {
    const isMultiDay = timeframe === 'ALL' || timeframe === '1M' || timeframe === 'YTD' || timeframe === '1W';

    // 1. If real server snapshots exist (>2 points)
    if (serverSnapshots && serverSnapshots.length > 2) {
      if (timeframe === 'ALL') return serverSnapshots;
      const latest = serverSnapshots[serverSnapshots.length - 1].rawTimestamp;
      const map: Record<string, number> = {
        '1H': 60 * 60 * 1000,
        '6H': 6 * 60 * 60 * 1000,
        '1D': 24 * 60 * 60 * 1000,
        '1W': 7 * 24 * 60 * 60 * 1000,
        '1M': 30 * 24 * 60 * 60 * 1000,
        'YTD': 365 * 24 * 60 * 60 * 1000,
      };
      const span = map[timeframe];
      if (span && latest) {
        const filtered = serverSnapshots.filter((s) => latest - s.rawTimestamp <= span);
        if (filtered.length >= 2) return filtered;
      }
      return serverSnapshots;
    }

    // 2. Synthesize dynamic trajectory directly from the user's trades (targetLogs)
    if (targetLogs && targetLogs.length > 0) {
      const chronological = [...targetLogs]
        .filter((l) => l.timestamp)
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

      if (chronological.length > 0) {
        let runningBal = startingBalance;
        const pts: TimelineSnapshotPoint[] = [];

        // Start anchor point
        const t0 = new Date(chronological[0].timestamp);
        const startTime = new Date(t0.getTime() - 20 * 60 * 1000);
        pts.push({
          displayTime: isMultiDay ? `${formatFrenchDate(startTime)} ${formatFrenchTime(startTime)}` : formatFrenchTime(startTime),
          time: formatFrenchTime(startTime),
          date: formatFrenchDate(startTime),
          balance: startingBalance,
          pnl: 0,
          rawTimestamp: startTime.getTime(),
        });

        chronological.forEach((l) => {
          const t = new Date(l.timestamp);
          const tradePnl = Number.isFinite(l.pnl) ? (l.pnl ?? 0) : 0;
          runningBal += tradePnl;
          pts.push({
            displayTime: isMultiDay ? `${formatFrenchDate(t)} ${formatFrenchTime(t)}` : formatFrenchTime(t),
            time: formatFrenchTime(t),
            date: formatFrenchDate(t),
            balance: Math.round(runningBal * 100) / 100,
            pnl: Math.round((runningBal - startingBalance) * 100) / 100,
            rawTimestamp: t.getTime(),
          });
        });

        // Current anchor point
        const now = new Date();
        pts.push({
          displayTime: isMultiDay ? `${formatFrenchDate(now)} ${formatFrenchTime(now)}` : formatFrenchTime(now),
          time: formatFrenchTime(now),
          date: formatFrenchDate(now),
          balance: Math.round(currentBalance * 100) / 100,
          pnl: Math.round((currentBalance - startingBalance) * 100) / 100,
          rawTimestamp: now.getTime(),
        });

        return pts;
      }
    }

    // 3. Dynamic timeframe-bounded synthetic trajectory when no trades exist
    const now = new Date();
    const mapDur: Record<string, number> = {
      '1H': 60 * 60 * 1000,
      '6H': 6 * 60 * 60 * 1000,
      '1D': 24 * 60 * 60 * 1000,
      '1W': 7 * 24 * 60 * 60 * 1000,
      '1M': 30 * 24 * 60 * 60 * 1000,
      'YTD': 90 * 24 * 60 * 60 * 1000,
      'ALL': 180 * 24 * 60 * 60 * 1000,
    };
    const dur = mapDur[timeframe] || 24 * 60 * 60 * 1000;
    const startT = new Date(now.getTime() - dur);
    return [
      {
        displayTime: isMultiDay ? `${formatFrenchDate(startT)} ${formatFrenchTime(startT)}` : formatFrenchTime(startT),
        time: formatFrenchTime(startT),
        date: formatFrenchDate(startT),
        balance: startingBalance,
        pnl: 0,
        rawTimestamp: startT.getTime(),
      },
      {
        displayTime: isMultiDay ? `${formatFrenchDate(now)} ${formatFrenchTime(now)}` : formatFrenchTime(now),
        time: formatFrenchTime(now),
        date: formatFrenchDate(now),
        balance: currentBalance,
        pnl: Math.round((currentBalance - startingBalance) * 100) / 100,
        rawTimestamp: now.getTime(),
      },
    ];
  }, [serverSnapshots, targetLogs, timeframe, startingBalance, currentBalance]);

  // Build OHLC Candles from timeline snapshots
  const ohlcCandles = useMemo(() => {
    if (!pnlTimeline || pnlTimeline.length < 2) return [];
    
    const numBuckets = Math.min(30, Math.max(6, Math.floor(pnlTimeline.length / 4)));
    const bucketSize = Math.max(1, Math.floor(pnlTimeline.length / numBuckets));
    const candles: OhlcCandle[] = [];

    for (let i = 0; i < pnlTimeline.length; i += bucketSize) {
      const chunk = pnlTimeline.slice(i, i + bucketSize);
      if (chunk.length === 0) continue;
      const prices = chunk.map((s: TimelineSnapshotPoint) => s.balance);
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
        pnl: Math.round((close - startingBalance) * 100) / 100
      });
    }

    return candles;
  }, [pnlTimeline, startingBalance]);

  // Derive Period Statistics
  const firstBal = pnlTimeline.length > 0 ? pnlTimeline[0].balance : startingBalance;
  const lastBal = pnlTimeline.length > 0 ? pnlTimeline[pnlTimeline.length - 1].balance : currentBalance;
  const periodPnL = lastBal - firstBal;
  const periodPnLPct = firstBal > 0 ? (periodPnL / firstBal) * 100 : 0;

  const isPositive = periodPnL >= 0;
  const omittedMarketEvidenceCount = targetLogs.filter((l) => {
    const effPrice = l.fillPrice ?? l.entryPrice ?? null;
    return effPrice === null && (l.pnl === null || l.pnl === undefined);
  }).length;

  const handleOpenMarketTrade = useCallback((m: MarketSummary) => {
    if (!onSelectTrade) return;
    const match = logs.find((l) => (m.conditionId && l.marketConditionId === m.conditionId) || (m.question && l.marketQuestion === m.question));
    if (match) {
      onSelectTrade(match);
    }
  }, [logs, onSelectTrade]);

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* ========================================================= */}
      {/* 1. ARCTIC GLASS LINE / CANDLESTICK CHART CARD */}
      {/* ========================================================= */}
      <div className="glass-card p-4 sm:p-8 space-y-4 sm:space-y-6 rounded-[28px] border border-sky-100/80 dark:border-white/10 shadow-sm">
        {/* Asset Header & Price */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <span className="text-[11px] sm:text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Polymarket Copy Portfolio · Balance
            </span>
            <div className="flex flex-wrap items-baseline gap-2 sm:gap-3">
              <span className="text-2xl sm:text-4xl lg:text-5xl font-bold font-outfit text-[#0F172A] dark:text-white tracking-tight">
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

          {/* Controls: Chart Type Toggle & Arctic Timeframe Pills */}
          <div className="flex flex-wrap sm:flex-nowrap items-center justify-between sm:justify-end gap-2 w-full sm:w-auto">
            {/* Area vs Candle Toggle */}
            <div className="flex items-center bg-white/5 p-1 rounded-full border border-white/10">
              <button
                onClick={() => setChartType('area')}
                className={`p-1.5 rounded-full text-xs font-bold transition-all cursor-pointer active:scale-95 ${
                  chartType === 'area' ? 'glass-button text-white shadow-xs' : 'text-slate-400 hover:text-white'
                }`}
                title="Line / Area View"
              >
                <Activity size={13} />
              </button>
              <button
                onClick={() => setChartType('candles')}
                className={`p-1.5 rounded-full text-xs font-bold transition-all cursor-pointer active:scale-95 ${
                  chartType === 'candles' ? 'glass-button text-white shadow-xs' : 'text-slate-400 hover:text-white'
                }`}
                title="Candlestick (OHLC) Trader View"
              >
                <CandlestickChart size={13} />
              </button>
            </div>

            {/* Arctic Timeframe Pills */}
            <div className="flex items-center gap-0.5 sm:gap-1 bg-white/5 p-1 rounded-full border border-white/10 overflow-x-auto max-w-full no-scrollbar">
              {(['1H', '6H', '1D', '1W', '1M', 'YTD', 'ALL'] as const).map((tf) => {
                const isActive = timeframe === tf;
                return (
                  <button
                    key={tf}
                    onClick={() => setTimeframe(tf)}
                    className={`px-2.5 sm:px-3 py-1 rounded-full text-[11px] sm:text-xs font-bold transition-all cursor-pointer whitespace-nowrap active:scale-95 ${
                      isActive ? 'glass-button text-white shadow-xs' : 'text-slate-400 hover:text-white'
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
            Experimental paper valuations use available price observations and simulated fills. Price freshness and accounting remain under validation.
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowResetModal(true)}
              className="text-xs text-slate-500 dark:text-[#8E8F99] hover:text-slate-950 dark:hover:text-white transition-colors cursor-pointer flex items-center gap-1 font-semibold"
            >
              <RefreshCw size={12} />
              Start New Paper Run
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
      {/* ========================================================= */}
      {/* 2. ARCTIC GLACIER ANALYTICS & CARD WIDGETS SECTION */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        
        {/* Card 1: Sleeve Capital Allocation (Isolated Sleeves) */}
        <div className="glass-card p-5 space-y-4 rounded-[28px]">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 dark:text-[#8E8F99]">
                {activeAllocationStats.targetSleeveCount}-Wallet Sleeve Capital
              </span>
              <span className="text-[10px] font-mono font-bold text-emerald-600 dark:text-[#00D09C] bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                {activeAllocationStats.activeWhales.length} Deployed · {Math.max(0, activeAllocationStats.targetSleeveCount - activeAllocationStats.activeWhales.length)} in Cash ({activeAllocationStats.count} Lots)
              </span>
            </div>
            <div className="flex items-baseline justify-between">
              <div className="text-2xl font-bold text-slate-950 dark:text-white font-outfit">
                ${activeAllocationStats.totalNotional.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <span className="text-[11px] font-mono font-medium text-slate-500 dark:text-[#8E8F99]">
                {formatAllocPct(activeAllocationStats.totalNotional, currentBalance || 10000)} of ${Math.round(currentBalance || 10000).toLocaleString()} Bankroll
              </span>
            </div>
          </div>

          {/* Isolated Sleeves Visual Slot Grid */}
          <div className={`grid gap-1.5 w-full pt-1 ${
            activeAllocationStats.targetSleeveCount === 5 ? 'grid-cols-5' :
            activeAllocationStats.targetSleeveCount === 4 ? 'grid-cols-4' :
            activeAllocationStats.targetSleeveCount === 2 ? 'grid-cols-2' :
            activeAllocationStats.targetSleeveCount === 1 ? 'grid-cols-1' :
            'grid-cols-10'
          }`}>
            {activeAllocationStats.top10Sleeves.map((sleeve) => (
              <div
                key={sleeve.index}
                className="h-2.5 rounded-full relative overflow-hidden bg-slate-100 dark:bg-white/[0.06] border border-sky-100/60 dark:border-white/10 flex items-center justify-start transition-colors"
                title={
                  sleeve.isDeployed
                    ? `Sleeve #${sleeve.index} (${sleeve.name}): $${sleeve.deployedNotional.toFixed(2)} deployed (${formatAllocPct(sleeve.deployedNotional, activeAllocationStats.sleeveBudget)} of $${Math.round(activeAllocationStats.sleeveBudget).toLocaleString()} sleeve) • $${(activeAllocationStats.sleeveBudget - sleeve.deployedNotional).toFixed(2)} liquid cash`
                    : `Sleeve #${sleeve.index} (${sleeve.name}): 100% Cash Ready ($${Math.round(activeAllocationStats.sleeveBudget).toLocaleString()} liquid reserve)`
                }
              >
                {sleeve.isDeployed && (
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.max(4, Math.min(100, (sleeve.deployedNotional / activeAllocationStats.sleeveBudget) * 100))}%`,
                      backgroundColor: sleeve.color
                    }}
                  />
                )}
              </div>
            ))}
          </div>

          {/* Dynamic Sleeve Allocation Legend */}
          <div className="space-y-1.5 text-[11px] font-semibold text-slate-600 dark:text-[#8E8F99]">
            {activeAllocationStats.activeWhales.length > 0 ? (
              <>
                {activeAllocationStats.activeWhales.slice(0, 3).map((w) => (
                  <div key={w.name} className="flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-1.5 truncate">
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: w.color }} />
                      <span className="text-slate-900 dark:text-white font-bold truncate">{w.name}</span>
                    </div>
                    <div className="font-mono text-slate-700 dark:text-slate-300 shrink-0">
                      ${w.notional.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}{' '}
                      <span className="text-slate-400 text-[10px]">
                        ({formatAllocPct(w.notional, activeAllocationStats.sleeveBudget)} of ${Math.round(activeAllocationStats.sleeveBudget).toLocaleString()} Sleeve • {formatAllocPct(w.notional, currentBalance || 10000)} Portfolio)
                      </span>
                    </div>
                  </div>
                ))}
                {activeAllocationStats.activeWhales.length > 3 && (
                  <div className="text-[10px] text-slate-400 dark:text-[#8E8F99] text-right font-mono">
                    + {activeAllocationStats.activeWhales.length - 3} more active sleeve{activeAllocationStats.activeWhales.length - 3 === 1 ? '' : 's'}
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center justify-between text-[11px] text-slate-500">
                <span>{activeAllocationStats.targetSleeveCount} Isolated ${Math.round(activeAllocationStats.sleeveBudget).toLocaleString()} Sleeves Ready</span>
                <span className="font-mono text-emerald-500 font-bold">${Math.round(currentBalance || 10000).toLocaleString()} Free Cash</span>
              </div>
            )}
            {/* Explicit Cash Buffer Row */}
            <div className="flex items-center justify-between text-[11px] pt-1 border-t border-black/[0.04] dark:border-white/5 font-mono">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="w-2 h-2 rounded-full shrink-0 bg-slate-400 dark:bg-slate-500" />
                <span className="text-slate-700 dark:text-slate-300 font-medium whitespace-nowrap">
                  Liquid Reserves ({Math.max(0, activeAllocationStats.targetSleeveCount - activeAllocationStats.activeWhales.length)} sleeves idle):
                </span>
              </div>
              <span className="text-slate-900 dark:text-slate-200 font-bold shrink-0 ml-2">
                ${activeAllocationStats.freeCash.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ({Math.round(100 - activeAllocationStats.allocatedPct)}%)
              </span>
            </div>
            {activeAllocationStats.legacyCount > 0 && (
              <div className="flex items-center justify-between text-[10px] text-amber-600 dark:text-amber-400 pt-0.5 font-mono">
                <span>Legacy Holdings (Exiting):</span>
                <span>${activeAllocationStats.legacyNotional.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ({activeAllocationStats.legacyCount} lots)</span>
              </div>
            )}
          </div>
        </div>

        {/* Card 2: Execution Win Rate & Micro Dual-Bars */}
        <div className="glass-card p-5 space-y-4 rounded-[28px]">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-slate-500 dark:text-[#8E8F99]">Execution Win Rate</span>
            <div className="text-2xl font-bold text-slate-950 dark:text-white font-outfit">
              {winRate.toFixed(1)}% <span className="text-xs text-slate-500 dark:text-[#8E8F99] font-normal">({totalWins}W / {totalLosses}L)</span>
            </div>
          </div>

          {/* Dual Progress Bars */}
          <div className="space-y-2">
            <div className="h-2 w-full rounded-full bg-sky-100/60 dark:bg-white/[0.06] overflow-hidden">
              <div 
                className="h-full bg-[#00D09C] rounded-full transition-all" 
                style={{ width: `${Math.min(100, Math.max(5, winRate))}%` }} 
              />
            </div>
            <div className="h-2 w-full rounded-full bg-sky-100/60 dark:bg-white/[0.06] overflow-hidden">
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
        <div className="glass-card p-5 space-y-4 rounded-[28px]">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-slate-500 dark:text-[#8E8F99]">Recorded Fees / Notional</span>
            <div className="text-2xl font-bold text-slate-950 dark:text-white font-outfit">
              {feeRatePct.toFixed(2)}% <span className="text-xs text-slate-500 dark:text-[#8E8F99] font-semibold">Paper estimate</span>
            </div>
          </div>

          {/* Micro Vertical Indicator Bars */}
          <div className="flex items-end gap-1.5 h-6">
            <div className="w-2.5 h-3 bg-slate-200 dark:bg-white/10 rounded-full" />
            <div className="w-2.5 h-5 bg-slate-200 dark:bg-white/10 rounded-full" />
            <div className="w-2.5 h-6 bg-[#00D09C] rounded-full" />
            <div className="w-2.5 h-4 bg-slate-200 dark:bg-white/10 rounded-full" />
            <div className="w-2.5 h-5 bg-[#00D09C] rounded-full" />
          </div>

          <div className="flex justify-between text-[11px] text-slate-500 dark:text-[#8E8F99]">
            <span>Fee model</span>
            <span className="text-slate-950 dark:text-white font-mono font-bold">Under validation</span>
          </div>
        </div>

      </div>

      {/* ========================================================= */}
      {/* ========================================================= */}
      {/* 3. ARCTIC GLACIER ALPHA & DRAWDOWN ATTRIBUTION LIST (CLICKABLE) */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {omittedMarketEvidenceCount > 0 && (
          <div className="md:col-span-2 rounded-2xl border border-amber-200/80 bg-amber-50/80 dark:border-amber-500/20 dark:bg-amber-500/10 px-4 py-3 text-xs text-amber-900 dark:text-amber-200">
            Market attribution shows known records only; {omittedMarketEvidenceCount} trade{omittedMarketEvidenceCount === 1 ? '' : 's'} omitted because price or PnL evidence is unavailable.
          </div>
        )}
        
        {/* Top Alpha Generators */}
        <div className="glass-card p-5 sm:p-6 space-y-4 rounded-[28px]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-[#00D09C]">
                <ArrowUpRight size={15} />
              </div>
              <h4 className="text-sm font-bold text-slate-950 dark:text-white">Top Alpha Generators</h4>
            </div>
            <span className="text-[11px] font-mono text-slate-400 dark:text-[#8E8F99]">Click to inspect</span>
          </div>

          <div className="space-y-2">
            {topAlpha.length === 0 ? (
              <div className="p-4 rounded-2xl bg-white/40 dark:bg-white/[0.02] border border-sky-100/60 dark:border-white/5 text-center py-6">
                <span className="text-xs text-slate-400 dark:text-[#8E8F99] font-medium">No positive alpha markets in this view</span>
              </div>
            ) : (
              topAlpha.map((m) => (
                <div
                  key={m.key}
                  onClick={() => handleOpenMarketTrade(m)}
                  className="p-3.5 rounded-2xl bg-white/60 dark:bg-white/[0.03] hover:bg-white/90 dark:hover:bg-white/[0.07] border border-sky-100/60 dark:border-white/5 transition-all cursor-pointer flex items-center justify-between group shadow-sm"
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
        <div className="glass-card p-5 sm:p-6 space-y-4 rounded-[28px]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-600 dark:text-[#FF453A]">
                <ArrowDownRight size={15} />
              </div>
              <h4 className="text-sm font-bold text-slate-950 dark:text-white">Top Drawdowns</h4>
            </div>
            <span className="text-[11px] font-mono text-slate-400 dark:text-[#8E8F99]">Click to inspect</span>
          </div>

          <div className="space-y-2">
            {topDrawdown.length === 0 ? (
              <div className="p-4 rounded-2xl bg-white/40 dark:bg-white/[0.02] border border-sky-100/60 dark:border-white/5 text-center py-6">
                <span className="text-xs text-slate-400 dark:text-[#8E8F99] font-medium">No drawdown markets in this view</span>
              </div>
            ) : (
              topDrawdown.map((m) => (
                <div
                  key={m.key}
                  onClick={() => handleOpenMarketTrade(m)}
                  className="p-3.5 rounded-2xl bg-white/60 dark:bg-white/[0.03] hover:bg-white/90 dark:hover:bg-white/[0.07] border border-sky-100/60 dark:border-white/5 transition-all cursor-pointer flex items-center justify-between group shadow-sm"
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
      <ResetSandboxModal
        isOpen={showResetModal}
        onClose={() => setShowResetModal(false)}
        userId={userId}
        currentBalance={currentBalance}
        onResetComplete={() => {
          if (onResetComplete) onResetComplete();
          setChartLoading(true);
          setSnapshotRefreshKey((prev) => prev + 1);
        }}
      />

      {/* ========================================================= */}
      {/* RAW DATA CODE MODAL */}
      {/* ========================================================= */}
      <Modal
        isOpen={showRawDataModal}
        onClose={() => setShowRawDataModal(false)}
        title="Raw Snapshot Data Payload"
        maxWidth="max-w-xl"
      >
        <div className="space-y-4">
          <pre className="bg-slate-950 p-4 rounded-2xl text-[11px] font-mono text-[#00D09C] overflow-x-auto max-h-80 border border-white/5">
            {JSON.stringify(pnlTimeline, null, 2)}
          </pre>
          <button
            onClick={() => {
              navigator.clipboard.writeText(JSON.stringify(pnlTimeline, null, 2));
              setCopied(true);
              setTimeout(() => setCopied(false), 2000);
            }}
            className="glass-button w-full py-3 rounded-xl text-white text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer"
          >
            {copied ? <Check size={14} className="text-[#00D09C]" /> : <Copy size={14} />}
            {copied ? 'Copied to Clipboard' : 'Copy JSON'}
          </button>
        </div>
      </Modal>
    </div>
  );
}
