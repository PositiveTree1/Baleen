'use client';
import { useEffect, useState } from 'react';
import { fetchExecutionLogs, getCachedExecutionLogs } from '@/lib/api-client';
import { formatFrenchTimeWithSeconds } from '@/lib/formatters';
import { ExecutionLog } from '@/types';
import { Search, Flame, Coins, Landmark, Trophy, Globe, Zap, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import Image from 'next/image';

interface LiveTapeProps {
  userId?: string;
  onSelectTrade?: (trade: ExecutionLog) => void;
}

export function LiveTape({ userId, onSelectTrade }: LiveTapeProps) {
  const [logs, setLogs] = useState<ExecutionLog[]>(() => getCachedExecutionLogs(userId) || []);
  const [loading, setLoading] = useState(() => (getCachedExecutionLogs(userId)?.length || 0) === 0);
  const [sideFilter, setSideFilter] = useState<'ALL' | 'BUY' | 'SELL' | 'CONSENSUS'>('ALL');
  const [search, setSearch] = useState('');

  useEffect(() => {
    async function load() {
      if (typeof document !== 'undefined' && document.hidden) return;
      const data = await fetchExecutionLogs(userId, { limit: '30' });
      if (Array.isArray(data)) {
        setLogs(data);
      }
      setLoading(false);
    }
    load();
    const interval = setInterval(load, 6000);
    return () => clearInterval(interval);
  }, [userId]);

  const filteredLogs = logs.filter((log) => {
    if (sideFilter === 'BUY' && log.side !== 'BUY') return false;
    if (sideFilter === 'SELL' && log.side !== 'SELL') return false;
    if (sideFilter === 'CONSENSUS' && !log.consensus?.is_consensus) return false;
    if (search && !log.marketQuestion?.toLowerCase().includes(search.toLowerCase()) && !log.walletAddress?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const getMarketIcon = (log: ExecutionLog) => {
    if (log.icon) {
      return (
        <img
          src={log.icon}
          alt="Market"
          className="w-9 h-9 rounded-full object-cover border border-black/[0.08] dark:border-white/10"
        />
      );
    }
    const q = (log.marketQuestion || '').toLowerCase();
    if (q.includes('fed') || q.includes('rate') || q.includes('cpi') || q.includes('trump') || q.includes('biden') || q.includes('election')) {
      return (
        <div className="w-9 h-9 rounded-full bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/20 flex items-center justify-center">
          <Landmark size={15} />
        </div>
      );
    }
    if (q.includes('btc') || q.includes('eth') || q.includes('crypto') || q.includes('sol')) {
      return (
        <div className="w-9 h-9 rounded-full bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20 flex items-center justify-center">
          <Coins size={15} />
        </div>
      );
    }
    if (q.includes('vs') || q.includes('cup') || q.includes('nfl') || q.includes('nba') || q.includes('win') || q.includes('points')) {
      return (
        <div className="w-9 h-9 rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-[#00D09C] border border-emerald-200 dark:border-[#00D09C]/20 flex items-center justify-center">
          <Trophy size={15} />
        </div>
      );
    }
    return (
      <div className="w-9 h-9 rounded-full bg-slate-100 dark:bg-[#2C2D35] text-slate-700 dark:text-white border border-black/[0.08] dark:border-white/10 flex items-center justify-center text-xs font-bold font-mono">
        {(log.outcome || 'Yes').slice(0, 3)}
      </div>
    );
  };

  return (
    <div className="revolut-card rounded-[26px] p-5 sm:p-6 flex flex-col h-[480px] space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-[#00D09C] animate-pulse" />
          <h3 className="text-base font-bold text-slate-950 dark:text-white tracking-tight">Live Execution Tape</h3>
          <span className="text-xs text-slate-500 dark:text-[#8E8F99] font-mono">Polymarket Fills</span>
        </div>

        {/* Filter Pills */}
        <div className="flex rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] p-0.5 border border-black/[0.04] dark:border-white/5 text-[11px] font-bold">
          {(['ALL', 'BUY', 'SELL', 'CONSENSUS'] as const).map((side) => (
            <button
              key={side}
              onClick={() => setSideFilter(side)}
              className={`px-3 py-1 rounded-full transition-all cursor-pointer ${
                sideFilter === side ? 'bg-white dark:bg-[#2C2D35] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99] hover:text-slate-950 dark:hover:text-white'
              }`}
            >
              {side === 'CONSENSUS' ? '🔥 Consensus' : side}
            </button>
          ))}
        </div>
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-[#8E8F99]" />
        <input
          type="text"
          placeholder="Filter live order executions..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Filter live order executions"
          spellCheck={false}
          className="w-full pl-9 pr-3 py-2 bg-[#F1F3F5] dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 rounded-full text-xs text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-[#8E8F99] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C]"
        />
      </div>

      {/* Execution Feed */}
      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 divide-y divide-black/[0.04] dark:divide-white/5" aria-live="polite">
        {loading ? (
          <div className="space-y-3 pt-1">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="flex items-center justify-between p-2">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full animate-shimmer shrink-0" />
                  <div className="space-y-1.5">
                    <div className="w-44 sm:w-56 h-3 rounded-md animate-shimmer" />
                    <div className="w-24 h-2.5 rounded-md animate-shimmer" />
                  </div>
                </div>
                <div className="space-y-1.5 text-right flex flex-col items-end">
                  <div className="w-12 h-3 rounded-md animate-shimmer" />
                  <div className="w-8 h-2.5 rounded-md animate-shimmer" />
                </div>
              </div>
            ))}
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-400 dark:text-[#8E8F99]">
            No live trades match filter
          </div>
        ) : (
          filteredLogs.map((log) => {
            const isBuy = (log.side || 'BUY').toUpperCase() === 'BUY';
            const notional = log.size ?? 0.0;
            const fillPrice = log.fillPrice || log.entryPrice || 0.0;
            const timeStr = log.timestamp ? formatFrenchTimeWithSeconds(new Date(log.timestamp)) : '';
            const whaleDisplay = log.whaleName || log.whalePseudonym || (log.walletAddress ? `${log.walletAddress.slice(0, 6)}...${log.walletAddress.slice(-4)}` : 'Whale');
            const outcomeText = log.outcome || 'Yes';

            return (
              <div
                key={log.id}
                onClick={() => onSelectTrade && onSelectTrade(log)}
                className="py-2 px-2 flex items-center justify-between gap-2.5 rounded-2xl hover:bg-slate-50 dark:hover:bg-[#1C1D22] transition-colors cursor-pointer group min-w-0"
              >
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  {/* Side Indicator Badge & Market Icon */}
                  <div className="relative shrink-0">
                    {getMarketIcon(log)}
                    <div className={`absolute -bottom-1 -right-1 w-4 h-4 rounded-full border border-white dark:border-[#16171B] flex items-center justify-center ${
                      isBuy ? 'bg-[#00D09C] text-black' : 'bg-[#FF453A] text-white'
                    }`}>
                      {isBuy ? <ArrowUpRight size={10} strokeWidth={3} /> : <ArrowDownRight size={10} strokeWidth={3} />}
                    </div>
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-bold text-slate-900 dark:text-white truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                      {log.marketQuestion || 'Prediction Market'}
                    </p>
                    <div className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[10px] text-slate-500 dark:text-[#8E8F99] font-mono mt-0.5 min-w-0">
                      {/* Explicit BUY / SELL badge */}
                      <span className={`font-extrabold px-1.5 py-0.2 rounded-md shrink-0 ${
                        isBuy
                          ? 'bg-emerald-100 dark:bg-[#00D09C]/20 text-emerald-800 dark:text-[#00D09C]'
                          : 'bg-rose-100 dark:bg-[#FF453A]/20 text-rose-800 dark:text-[#FF453A]'
                      }`}>
                        {isBuy ? 'BUY' : 'SELL'}
                      </span>
                      {/* Outcome Badge */}
                      <span className="font-bold px-1.5 py-0.2 rounded-md bg-slate-200 dark:bg-[#2C2D35] text-slate-700 dark:text-[#E2E3E8] shrink-0">
                        {outcomeText}
                      </span>
                      <span className="opacity-40">•</span>
                      <span className="shrink-0 font-medium">${fillPrice.toFixed(3)}</span>
                      <span className="opacity-40">•</span>
                      <span className="truncate max-w-[80px] sm:max-w-[120px]">{whaleDisplay}</span>
                    </div>
                  </div>
                </div>

                <div className="text-right shrink-0 pl-1.5">
                  <div className="text-xs font-bold font-mono tabular-nums text-slate-950 dark:text-white">
                    ${notional.toFixed(2)}
                  </div>
                  <span className="text-[10px] text-slate-400 dark:text-[#8E8F99] font-mono">{timeStr}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
