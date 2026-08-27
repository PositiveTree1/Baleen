'use client';
import { useEffect, useState } from 'react';
import { fetchExecutionLogs, getCachedExecutionLogs } from '@/lib/api-client';
import { formatFrenchTimeWithSeconds } from '@/lib/formatters';
import { ExecutionLog } from '@/types';
import { Search, Flame, Coins, Landmark, Trophy, Globe, Zap } from 'lucide-react';
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
      const data = await fetchExecutionLogs(userId, { limit: '30' });
      if (Array.isArray(data)) {
        setLogs(data);
      }
      setLoading(false);
    }
    load();
    const interval = setInterval(load, 4000);
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
          className="w-full pl-9 pr-3 py-2 bg-[#F1F3F5] dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 rounded-full text-xs text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-[#8E8F99] focus:outline-none focus:border-black/20 dark:focus:border-white/20"
        />
      </div>

      {/* Execution Feed */}
      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 divide-y divide-black/[0.04] dark:divide-white/5">
        {loading ? (
          <div className="py-12 text-center text-xs text-slate-400 dark:text-[#8E8F99]">
            Streaming live fills...
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-400 dark:text-[#8E8F99]">
            No live trades match filter
          </div>
        ) : (
          filteredLogs.map((log) => {
            const isBuy = log.side === 'BUY';
            const notional = log.size ?? 10.0;
            const fillPrice = log.fillPrice || log.entryPrice || 0.5;
            const timeStr = log.timestamp ? formatFrenchTimeWithSeconds(new Date(log.timestamp)) : '';
            const whaleDisplay = log.whaleName || log.whalePseudonym || (log.walletAddress ? `${log.walletAddress.slice(0, 6)}...${log.walletAddress.slice(-4)}` : 'Whale');

            return (
              <div
                key={log.id}
                onClick={() => onSelectTrade && onSelectTrade(log)}
                className="pt-2 flex items-center justify-between p-2 rounded-2xl hover:bg-slate-50 dark:hover:bg-[#1C1D22] transition-colors cursor-pointer group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  {/* Market Icon */}
                  <div className="shrink-0">
                    {getMarketIcon(log)}
                  </div>

                  <div className="min-w-0">
                    <p className="text-xs font-bold text-slate-900 dark:text-white truncate max-w-xs sm:max-w-sm group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                      {log.marketQuestion || 'Prediction Market'}
                    </p>
                    <div className="flex items-center gap-1.5 text-[10px] text-slate-500 dark:text-[#8E8F99] font-mono mt-0.5">
                      <span className={`font-bold px-1.5 py-0.2 rounded-md ${
                        (log.outcome || 'Yes').toLowerCase() === 'yes'
                          ? 'bg-emerald-50 dark:bg-[#00D09C]/10 text-emerald-700 dark:text-[#00D09C]'
                          : 'bg-rose-50 dark:bg-[#FF453A]/10 text-rose-700 dark:text-[#FF453A]'
                      }`}>
                        {log.outcome || 'Yes'}
                      </span>
                      <span>•</span>
                      <span>${fillPrice.toFixed(3)}</span>
                      <span>•</span>
                      <span>{whaleDisplay}</span>
                    </div>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <div className="text-xs font-bold font-mono text-slate-950 dark:text-white">
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
