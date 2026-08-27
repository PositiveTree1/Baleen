'use client';
import { useEffect, useState, useMemo } from 'react';
import { fetchExecutionLogs, getCachedExecutionLogs } from '@/lib/api-client';
import { ExecutionLog } from '@/types';
import { FileSpreadsheet } from 'lucide-react';
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
    return logs.filter(l => l.side === 'SELL' || l.status === 'RESOLVED' || l.status === 'CLOSED');
  }, [logs]);

  const filteredLogs = useMemo(() => {
    if (tab === 'holding') return holdingLogs;
    if (tab === 'closed') return closedLogs;
    return logs;
  }, [logs, tab, holdingLogs, closedLogs]);

  const displayedLogs = useMemo(() => {
    return filteredLogs.slice(0, MAX_DISPLAY_TRADES);
  }, [filteredLogs]);

  return (
    <>
      <div className="revolut-card bg-[#16171B] border border-white/[0.08] rounded-[26px] p-5 sm:p-7 space-y-5">
        {/* Header & Tabs */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-4">
          <div>
            <h3 className="text-base font-bold text-white tracking-tight">
              Execution Audit &amp; Transactions Feed
            </h3>
            <p className="text-xs text-[#8E8F99]">
              Live Polymarket CLOB positions, fill audits &amp; PnL tracking
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Revolut Segmented Pill Filter */}
            <div className="flex rounded-full bg-[#1C1D22] p-0.5 border border-white/5 text-xs font-bold">
              <button
                onClick={() => setTab('holding')}
                className={`px-3.5 py-1.5 rounded-full transition-all cursor-pointer ${
                  tab === 'holding' ? 'bg-[#2C2D35] text-white shadow-sm' : 'text-[#8E8F99] hover:text-white'
                }`}
              >
                Holding ({totalHoldingCount ?? holdingLogs.length})
              </button>
              <button
                onClick={() => setTab('closed')}
                className={`px-3.5 py-1.5 rounded-full transition-all cursor-pointer ${
                  tab === 'closed' ? 'bg-[#2C2D35] text-white shadow-sm' : 'text-[#8E8F99] hover:text-white'
                }`}
              >
                Closed ({totalClosedCount ?? closedLogs.length})
              </button>
            </div>

            <button
              onClick={() => setIsSpreadsheetOpen(true)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-[#1C1D22] hover:bg-[#2C2D35] text-white text-xs font-semibold border border-white/10 transition-all cursor-pointer"
              title="Open full execution history modal"
            >
              <FileSpreadsheet size={13} className="text-[#00D09C]" />
              <span className="hidden sm:inline">Export Audit</span>
            </button>
          </div>
        </div>

        {/* Transactions Feed (Revolut transaction list style) */}
        <div className="divide-y divide-white/5 space-y-1">
          {loading ? (
            <div className="py-12 text-center text-xs text-[#8E8F99]">
              Loading authoritative execution logs...
            </div>
          ) : displayedLogs.length === 0 ? (
            <div className="py-12 text-center text-xs text-[#8E8F99]">
              No transactions recorded for this view
            </div>
          ) : (
            displayedLogs.map((trade) => {
              const notional = trade.size ?? 10.0;
              const pnl = trade.pnl ?? 0.0;
              const fillPrice = trade.fillPrice || trade.entryPrice || 0.5;
              const livePrice = trade.currentPrice || fillPrice;
              const isProfit = pnl >= 0;
              const isYes = (trade.outcome || 'Yes').toLowerCase() === 'yes';
              const whaleDisplay = trade.whaleName || trade.whalePseudonym || (trade.walletAddress ? `${trade.walletAddress.slice(0, 6)}...${trade.walletAddress.slice(-4)}` : 'Whale');

              return (
                <div
                  key={trade.id}
                  onClick={() => onSelectTrade && onSelectTrade(trade)}
                  className="pt-2.5 pb-2.5 px-2 rounded-2xl hover:bg-[#1C1D22] transition-colors cursor-pointer flex items-center justify-between gap-3 group"
                >
                  {/* Left: Outcome Badge & Title */}
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs shrink-0 ${
                      isYes 
                        ? 'bg-[#00D09C]/10 text-[#00D09C] border border-[#00D09C]/20' 
                        : 'bg-[#FF453A]/10 text-[#FF453A] border border-[#FF453A]/20'
                    }`}>
                      {trade.outcome || 'Yes'}
                    </div>

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-xs font-bold text-white truncate max-w-xs sm:max-w-md">
                          {trade.marketQuestion || 'Prediction Market Contract'}
                        </p>
                        {trade.consensus?.is_consensus && (
                          <span className="text-[9px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-1.5 py-0.2 rounded-full">
                            Consensus
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-[11px] text-[#8E8F99] font-mono mt-0.5">
                        <span>{whaleDisplay}</span>
                        <span>•</span>
                        <span>Fill: ${fillPrice.toFixed(3)}</span>
                        <span>•</span>
                        <span className="text-white font-bold">Live: ${livePrice.toFixed(3)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Right: Notional Size & Net PnL */}
                  <div className="text-right shrink-0">
                    <div className="text-xs font-bold font-mono text-white">
                      ${notional.toFixed(2)}
                    </div>
                    <div className={`text-[11px] font-bold font-mono ${isProfit ? 'text-[#00D09C]' : 'text-[#FF453A]'}`}>
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
