'use client';
import { useEffect, useState, useMemo } from 'react';
import { fetchExecutionLogs, getCachedExecutionLogs } from '@/lib/api-client';
import { ExecutionLog } from '@/types';
import { FileSpreadsheet, Coins, Landmark, Trophy } from 'lucide-react';
import { FullHistorySpreadsheetModal } from './FullHistorySpreadsheetModal';

interface TradeLogProps {
  userId?: string;
  logs?: ExecutionLog[];
  totalHoldingCount?: number;
  totalClosedCount?: number;
  totalFillsCount?: number;
  onSelectTrade?: (trade: ExecutionLog) => void;
}

const MAX_DISPLAY_TRADES = 35;

export function TradeLog({ 
  userId, 
  logs: propLogs,
  totalHoldingCount, 
  totalClosedCount, 
  totalFillsCount, 
  onSelectTrade 
}: TradeLogProps) {
  const [internalLogs, setInternalLogs] = useState<ExecutionLog[]>(() => propLogs || getCachedExecutionLogs(userId) || []);
  const [loading, setLoading] = useState(() => !propLogs && (getCachedExecutionLogs(userId)?.length || 0) === 0);
  const [tab, setTab] = useState<'holding' | 'closed' | 'all'>('holding');
  const [isSpreadsheetOpen, setIsSpreadsheetOpen] = useState(false);

  useEffect(() => {
    if (propLogs) return;
    async function load() {
      if (typeof document !== 'undefined' && document.hidden) return;
      if (!userId) return;
      const data = await fetchExecutionLogs(userId, { limit: '100' });
      if (Array.isArray(data)) {
        setInternalLogs(data);
      }
      setLoading(false);
    }
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [userId, propLogs]);

  const logs = propLogs || internalLogs;
  const isDisplayLoading = propLogs ? false : (loading && internalLogs.length === 0);

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
      <div className="glass-card rounded-[28px] p-5 sm:p-7 space-y-5">
        {/* Header & Tabs */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-sky-100/80 dark:border-white/10 pb-4">
          <div>
            <h3 className="text-base font-bold text-[#0F172A] dark:text-white tracking-tight">
              Execution Audit &amp; Transactions Feed
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Paper positions, simulated fills &amp; paper PnL tracking
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Arctic Glass Segmented Pill Filter */}
            <div className="flex rounded-full bg-slate-100/90 p-1 border border-slate-200/80 text-xs font-bold">
              <button
                onClick={() => setTab('holding')}
                className={`px-3.5 py-1.5 rounded-full transition-all cursor-pointer ${
                  tab === 'holding'
                    ? 'bg-white text-slate-900 font-bold shadow-xs border border-slate-200/70'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Holding ({totalHoldingCount ?? holdingLogs.length})
              </button>
              <button
                onClick={() => setTab('closed')}
                className={`px-3.5 py-1.5 rounded-full transition-all cursor-pointer ${
                  tab === 'closed'
                    ? 'bg-white text-slate-900 font-bold shadow-xs border border-slate-200/70'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Closed ({totalClosedCount ?? closedLogs.length})
              </button>
            </div>

            <button
              onClick={() => setIsSpreadsheetOpen(true)}
              aria-label="Open full execution history modal"
              className="glass-button flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-white text-xs font-semibold border border-white/15 transition-all cursor-pointer shadow-xs active:scale-95"
              title="Open full execution history modal"
            >
              <FileSpreadsheet size={13} className="text-[#38BDF8]" />
              <span className="hidden sm:inline">Export Audit</span>
            </button>
          </div>
        </div>

        {/* Transactions Feed */}
        <div className="divide-y divide-sky-100/60 dark:divide-white/5 space-y-1">
          {isDisplayLoading ? (
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
              const pnl = trade.pnl;
              const fillPrice = trade.fillPrice ?? trade.entryPrice;
              const isProfit = pnl !== null && pnl !== undefined && pnl >= 0;
              const isClosed = trade.status === 'CLOSED' || trade.status === 'RESOLVED' || trade.side === 'SELL';
              const whaleDisplay = trade.whaleName || trade.whalePseudonym || (trade.walletAddress ? `${trade.walletAddress.slice(0, 6)}...${trade.walletAddress.slice(-4)}` : 'Whale');

              // Derive authentic exit settlement price for closed/resolved binary prediction markets if currentPrice is null
              let displayPrice = trade.currentPrice;
              if (isClosed && (displayPrice === null || displayPrice === undefined)) {
                if (pnl !== null && pnl !== undefined && fillPrice && notional > 0) {
                  const fee = trade.feeUsd ?? 0.0;
                  const shares = notional / fillPrice;
                  const payout = Math.max(0, notional + pnl + fee);
                  displayPrice = shares > 0 ? Math.max(0, Math.min(1, payout / shares)) : null;
                }
              }

              return (
                <div
                  key={trade.id}
                  onClick={() => onSelectTrade && onSelectTrade(trade)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onSelectTrade && onSelectTrade(trade);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  aria-label={`View trade details for ${trade.marketQuestion || 'contract'}`}
                  className="py-2.5 px-3 rounded-2xl hover:bg-sky-500/[0.05] dark:hover:bg-white/[0.04] transition-all cursor-pointer flex items-center justify-between gap-2.5 group min-w-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0284C7]"
                >
                  {/* Left: Outcome / Market Icon & Title */}
                  <div className="flex items-center gap-2.5 min-w-0 flex-1">
                    {getMarketIcon(trade)}

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <p className="text-xs font-bold text-[#0F172A] dark:text-white truncate group-hover:text-[#0284C7] dark:group-hover:text-[#38BDF8] transition-colors">
                          {trade.marketQuestion || 'Prediction Market Contract'}
                        </p>
                        {trade.consensus?.is_consensus && (
                          <span className="text-[9px] font-bold bg-sky-50 dark:bg-sky-500/10 text-[#0284C7] dark:text-[#38BDF8] border border-sky-200/60 dark:border-sky-500/20 px-1.5 py-0.2 rounded-full shrink-0">
                            Consensus
                          </span>
                        )}
                      </div>
                      
                      {/* Responsive Metadata Subtitle (Never overlaps) */}
                      <div className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[10px] sm:text-[11px] text-slate-500 dark:text-slate-400 font-mono mt-0.5 min-w-0">
                        <span className="truncate max-w-[85px] sm:max-w-[130px] font-semibold text-[#1E293B] dark:text-slate-300">
                          {whaleDisplay}
                        </span>
                        <span className="opacity-40">•</span>
                        <span className="shrink-0">Fill {fillPrice === null ? 'Unavailable' : `$${fillPrice.toFixed(3)}`}</span>
                        <span className="opacity-40">•</span>
                        <span className="shrink-0 font-bold text-[#0F172A] dark:text-white">
                          {isClosed ? 'Exit' : 'Mark'} {displayPrice !== null && displayPrice !== undefined ? `$${displayPrice.toFixed(3)}` : isClosed ? 'Settled' : 'Unavailable'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Notional Size & Net PnL */}
                  <div className="text-right shrink-0 pl-1.5">
                    <div className="text-xs font-bold font-mono text-[#0F172A] dark:text-white">
                      ${notional.toFixed(2)}
                    </div>
                    <div className={`text-[11px] font-bold font-mono ${pnl === null || pnl === undefined ? 'text-slate-400' : isProfit ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                      {pnl === null || pnl === undefined ? '—' : `${isProfit ? '+' : ''}$${pnl.toFixed(2)}`}
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
