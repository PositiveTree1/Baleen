'use client';
import { useEffect, useState, useMemo } from 'react';
import { fetchExecutionLogs, getCachedExecutionLogs } from '@/lib/api-client';
import { ExecutionLog } from '@/types';
import { FileSpreadsheet, Coins, Landmark, Trophy } from 'lucide-react';
import { FullHistorySpreadsheetModal } from './FullHistorySpreadsheetModal';

interface TradeLogProps {
  userId?: string;
  totalHoldingCount?: number;
  totalClosedCount?: number;
  totalFillsCount?: number;
  onSelectTrade?: (trade: ExecutionLog) => void;
}

const MAX_DISPLAY_TRADES = 35;

export function TradeLog({ 
  userId, 
  totalHoldingCount, 
  totalClosedCount, 
  totalFillsCount, 
  onSelectTrade 
}: TradeLogProps) {
  const [logs, setLogs] = useState<ExecutionLog[]>(() => getCachedExecutionLogs(userId) || []);
  const [loading, setLoading] = useState(() => (getCachedExecutionLogs(userId)?.length || 0) === 0);
  const [tab, setTab] = useState<'holding' | 'closed' | 'all'>('holding');
  const [isSpreadsheetOpen, setIsSpreadsheetOpen] = useState(false);

  useEffect(() => {
    async function load() {
      if (typeof document !== 'undefined' && document.hidden) return;
      const data = await fetchExecutionLogs(userId, { limit: '100' });
      if (Array.isArray(data)) {
        setLogs(data);
      }
      setLoading(false);
    }
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [userId]);

  const holdingLogs = useMemo(() => {
    return logs.filter(l => l.side === 'BUY' && l.status === 'FILLED' && !l.marketQuestion?.toLowerCase().includes('resolved'));
  }, [logs]);

  const closedLogs = useMemo(() => {
    return logs.filter(l => l.status === 'CLOSED' || l.status === 'RESOLVED' || l.side === 'SELL');
  }, [logs]);

  const filteredLogs = useMemo(() => {
    if (tab === 'holding') return holdingLogs;
    if (tab === 'closed') return closedLogs;
    return logs;
  }, [logs, tab, holdingLogs, closedLogs]);

  const displayedLogs = useMemo(() => {
    return filteredLogs.slice(0, MAX_DISPLAY_TRADES);
  }, [filteredLogs]);

  const getMarketIcon = (trade: ExecutionLog) => {
    if (trade.icon) {
      return (
        <img
          src={trade.icon}
          alt="Market"
          className="w-10 h-10 rounded-full object-cover border border-black/[0.08] dark:border-white/10 shrink-0"
        />
      );
    }
    const q = (trade.marketQuestion || '').toLowerCase();
    if (q.includes('fed') || q.includes('rate') || q.includes('cpi') || q.includes('trump') || q.includes('biden') || q.includes('election')) {
      return (
        <div className="w-10 h-10 rounded-full bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/20 flex items-center justify-center shrink-0">
          <Landmark size={16} />
        </div>
      );
    }
    if (q.includes('btc') || q.includes('eth') || q.includes('crypto') || q.includes('sol')) {
      return (
        <div className="w-10 h-10 rounded-full bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20 flex items-center justify-center shrink-0">
          <Coins size={16} />
        </div>
      );
    }
    if (q.includes('vs') || q.includes('cup') || q.includes('nfl') || q.includes('nba') || q.includes('win') || q.includes('points')) {
      return (
        <div className="w-10 h-10 rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-[#00D09C] border border-emerald-200 dark:border-[#00D09C]/20 flex items-center justify-center shrink-0">
          <Trophy size={16} />
        </div>
      );
    }
    const isYes = (trade.outcome || 'Yes').toLowerCase() === 'yes';
    return (
      <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs shrink-0 ${
        isYes 
          ? 'bg-emerald-50 dark:bg-[#00D09C]/10 text-emerald-700 dark:text-[#00D09C] border border-emerald-200 dark:border-[#00D09C]/20' 
          : 'bg-rose-50 dark:bg-[#FF453A]/10 text-rose-700 dark:text-[#FF453A] border border-rose-200 dark:border-[#FF453A]/20'
      }`}>
        {trade.outcome || 'Yes'}
      </div>
    );
  };

  return (
    <>
      <div className="revolut-card rounded-[26px] p-5 sm:p-7 space-y-5">
        {/* Header & Tabs */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-black/[0.04] dark:border-white/5 pb-4">
          <div>
            <h3 className="text-base font-bold text-slate-950 dark:text-white tracking-tight">
              Execution Audit &amp; Transactions Feed
            </h3>
            <p className="text-xs text-slate-500 dark:text-[#8E8F99]">
              Live Polymarket CLOB positions, fill audits &amp; PnL tracking
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Revolut Segmented Pill Filter */}
            <div className="flex rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] p-0.5 border border-black/[0.04] dark:border-white/5 text-xs font-bold">
              <button
                onClick={() => setTab('holding')}
                className={`px-3.5 py-1.5 rounded-full transition-all cursor-pointer ${
                  tab === 'holding' ? 'bg-white dark:bg-[#2C2D35] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                Holding ({totalHoldingCount ?? holdingLogs.length})
              </button>
              <button
                onClick={() => setTab('closed')}
                className={`px-3.5 py-1.5 rounded-full transition-all cursor-pointer ${
                  tab === 'closed' ? 'bg-white dark:bg-[#2C2D35] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                Closed ({totalClosedCount ?? closedLogs.length})
              </button>
            </div>

            <button
              onClick={() => setIsSpreadsheetOpen(true)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] text-slate-800 dark:text-white text-xs font-semibold border border-black/[0.04] dark:border-white/10 transition-all cursor-pointer shadow-2xs"
              title="Open full execution history modal"
            >
              <FileSpreadsheet size={13} className="text-[#00D09C]" />
              <span className="hidden sm:inline">Export Audit</span>
            </button>
          </div>
        </div>

        {/* Transactions Feed (Revolut transaction list style) */}
        <div className="divide-y divide-black/[0.04] dark:divide-white/5 space-y-1">
          {loading ? (
            <div className="space-y-3 pt-2">
              {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                <div key={i} className="pt-2.5 pb-2.5 px-2 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full animate-shimmer shrink-0" />
                    <div className="space-y-1.5">
                      <div className="w-56 sm:w-80 h-3.5 rounded-md animate-shimmer" />
                      <div className="w-36 h-2.5 rounded-md animate-shimmer" />
                    </div>
                  </div>
                  <div className="space-y-1.5 text-right flex flex-col items-end shrink-0">
                    <div className="w-16 h-3.5 rounded-md animate-shimmer" />
                    <div className="w-10 h-2.5 rounded-md animate-shimmer" />
                  </div>
                </div>
              ))}
            </div>
          ) : displayedLogs.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-400 dark:text-[#8E8F99]">
              No transactions recorded for this view
            </div>
          ) : (
            displayedLogs.map((trade) => {
              const notional = trade.size ?? 0.0;
              const pnl = trade.pnl ?? 0.0;
              const fillPrice = trade.fillPrice || trade.entryPrice || 0.0;
              const livePrice = trade.currentPrice || fillPrice;
              const isProfit = pnl >= 0;
              const isClosed = trade.status === 'CLOSED' || trade.status === 'RESOLVED' || trade.side === 'SELL';
              const whaleDisplay = trade.whaleName || trade.whalePseudonym || (trade.walletAddress ? `${trade.walletAddress.slice(0, 6)}...${trade.walletAddress.slice(-4)}` : 'Whale');

              return (
                <div
                  key={trade.id}
                  onClick={() => onSelectTrade && onSelectTrade(trade)}
                  className="py-2.5 px-2 rounded-2xl hover:bg-slate-50 dark:hover:bg-[#1C1D22] transition-colors cursor-pointer flex items-center justify-between gap-2.5 group min-w-0"
                >
                  {/* Left: Outcome / Market Icon & Title */}
                  <div className="flex items-center gap-2.5 min-w-0 flex-1">
                    {getMarketIcon(trade)}

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <p className="text-xs font-bold text-slate-900 dark:text-white truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                          {trade.marketQuestion || 'Prediction Market Contract'}
                        </p>
                        {trade.consensus?.is_consensus && (
                          <span className="text-[9px] font-bold bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/20 px-1.5 py-0.2 rounded-full shrink-0">
                            Consensus
                          </span>
                        )}
                      </div>
                      
                      {/* Responsive Metadata Subtitle (Never overlaps) */}
                      <div className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[10px] sm:text-[11px] text-slate-500 dark:text-[#8E8F99] font-mono mt-0.5 min-w-0">
                        <span className="truncate max-w-[85px] sm:max-w-[130px] font-medium text-slate-700 dark:text-slate-300">
                          {whaleDisplay}
                        </span>
                        <span className="opacity-40">•</span>
                        <span className="shrink-0">Fill ${fillPrice.toFixed(3)}</span>
                        <span className="opacity-40">•</span>
                        <span className="shrink-0 font-bold text-slate-900 dark:text-white">
                          {isClosed ? 'Exit' : 'Live'} ${livePrice.toFixed(3)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Notional Size & Net PnL */}
                  <div className="text-right shrink-0 pl-1.5">
                    <div className="text-xs font-bold font-mono text-slate-950 dark:text-white">
                      ${notional.toFixed(2)}
                    </div>
                    <div className={`text-[11px] font-bold font-mono ${isProfit ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                      {isProfit ? '+' : ''}${pnl.toFixed(2)}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {isSpreadsheetOpen && (
        <FullHistorySpreadsheetModal 
          isOpen={isSpreadsheetOpen}
          onClose={() => setIsSpreadsheetOpen(false)}
          logs={logs}
          onSelectTrade={onSelectTrade}
        />
      )}
    </>
  );
}
