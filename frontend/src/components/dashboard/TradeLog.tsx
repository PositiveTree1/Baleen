'use client';
import { useEffect, useState, useMemo } from 'react';
import { fetchExecutionLogs, getCachedExecutionLogs } from '@/lib/api-client';
import { ExecutionLog } from '@/types';
import { Skeleton } from '../ui/Skeleton';
import { Tag, HelpCircle, Users, FileSpreadsheet, Layers, CheckCircle2, TrendingUp, TrendingDown, ArrowRight, ExternalLink } from 'lucide-react';
import { formatCompactPnL, formatExactPnL, formatFrenchDateTime } from '@/lib/formatters';
import { FullHistorySpreadsheetModal } from './FullHistorySpreadsheetModal';

interface TradeLogProps {
  userId?: string;
  totalHoldingCount?: number;
  totalClosedCount?: number;
  totalFillsCount?: number;
  onSelectTrade?: (trade: ExecutionLog) => void;
}

const MAX_DISPLAY_TRADES = 30;

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

  // Holding vs Closed classification
  // - Holding = Open Long Positions (side === 'BUY' and status === 'FILLED' and not resolved)
  // - Closed / Sold = Exited or Sold Positions (side === 'SELL' or status in ['RESOLVED', 'CLOSED'])
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

  // Cap at 30 items for display
  const displayedLogs = useMemo(() => {
    return filteredLogs.slice(0, MAX_DISPLAY_TRADES);
  }, [filteredLogs]);

  // Aggregate stats for the active tab
  const activeStats = useMemo(() => {
    let notional = 0;
    let pnlTotal = 0;
    for (const l of filteredLogs) {
      notional += (l.size ?? 0);
      pnlTotal += (l.pnl ?? 0);
    }
    return {
      count: filteredLogs.length,
      notional,
      pnlTotal
    };
  }, [filteredLogs]);

  return (
    <>
      <div className="rounded-3xl overflow-hidden mt-6 border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_16px_36px_-6px_rgba(0,0,0,0.05)] bg-white">
        {/* Header & Tabs */}
        <div className="p-4 px-6 border-b border-black/[0.06] bg-slate-50/50 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2">
                Execution Audit &amp; Positions Center
                <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-200/80 text-slate-700 font-bold">
                  {filteredLogs.length} {tab === 'holding' ? 'holding' : tab === 'closed' ? 'closed' : 'total'}
                </span>
              </h3>
              <span className="text-[11px] text-slate-500 font-mono font-semibold">
                Real-time mark-to-market positions, order execution logs &amp; quadratic taker fee audits
              </span>
            </div>

            {/* Position Filter Tabs */}
            <div className="flex rounded-xl bg-slate-200/70 p-0.5 border border-black/[0.04] text-[11px] font-semibold">
              <button
                onClick={() => setTab('holding')}
                className={`px-3 py-1 rounded-lg transition-all cursor-pointer flex items-center gap-1.5 ${
                  tab === 'holding' 
                    ? 'bg-white text-emerald-800 shadow-sm font-bold' 
                    : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span>Currently Holding ({totalHoldingCount !== undefined ? totalHoldingCount.toLocaleString() : holdingLogs.length})</span>
              </button>
              <button
                onClick={() => setTab('closed')}
                className={`px-3 py-1 rounded-lg transition-all cursor-pointer flex items-center gap-1.5 ${
                  tab === 'closed' 
                    ? 'bg-white text-slate-900 shadow-sm font-bold' 
                    : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                <span>Sold / Resolved ({totalClosedCount !== undefined ? totalClosedCount.toLocaleString() : closedLogs.length})</span>
              </button>
              <button
                onClick={() => setTab('all')}
                className={`px-3 py-1 rounded-lg transition-all cursor-pointer flex items-center gap-1.5 ${
                  tab === 'all' 
                    ? 'bg-white text-indigo-700 shadow-sm font-bold' 
                    : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                <Layers size={12} />
                <span>All Fills ({totalFillsCount !== undefined ? totalFillsCount.toLocaleString() : logs.length})</span>
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            {/* Open Full Spreadsheet Button */}
            <button
              onClick={() => setIsSpreadsheetOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white hover:bg-slate-50 text-slate-800 border border-black/[0.08] text-xs font-semibold shadow-2xs hover:shadow-xs transition-all cursor-pointer"
              title="Open full interactive spreadsheet modal with search, column sorting, and CSV export for all 5,000+ executions"
            >
              <FileSpreadsheet size={14} className="text-emerald-700" />
              <span>Full Spreadsheet</span>
            </button>

            <div className="flex items-center gap-2 text-[10px] font-mono font-semibold text-slate-500 bg-white px-2.5 py-1 rounded-full border border-black/[0.06] shadow-2xs">
              <span>Fee Model: <strong>Quadratic Curve (0%-7%)</strong></span>
            </div>
          </div>
        </div>

        {/* Tab Quick Metric Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 px-6 bg-slate-100/40 border-b border-black/[0.04] text-xs">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-500 font-medium">
              {tab === 'holding' ? 'Active Positions:' : tab === 'closed' ? 'Closed Trades:' : 'Total Fills:'}
            </span>
            <span className="font-mono font-bold text-slate-900">{activeStats.count}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-500 font-medium">
              {tab === 'holding' ? 'Capital Deployed:' : 'Notional Volume:'}
            </span>
            <span className="font-mono font-bold text-slate-900">${activeStats.notional.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-500 font-medium">
              {tab === 'holding' ? 'Unrealized MTM P&L:' : 'Realized Net P&L:'}
            </span>
            <span className={`font-mono font-bold ${activeStats.pnlTotal >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
              {formatCompactPnL(activeStats.pnlTotal)}
            </span>
          </div>
          <div className="flex items-center justify-end">
            <span className="text-[10px] text-slate-400 font-mono">Capped at {MAX_DISPLAY_TRADES} in view</span>
          </div>
        </div>

        {/* Table View */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-black/[0.06] text-[10px] uppercase tracking-wider text-slate-500 bg-slate-50/90 font-semibold">
                <th className="p-4 sm:px-6 font-semibold">Timestamp</th>
                <th className="p-4 font-semibold">Source Whale</th>
                <th className="p-4 font-semibold">Prediction Market</th>
                <th className="p-4 font-semibold">Action &amp; Outcome</th>
                <th className="p-4 font-semibold text-right">Fill Price</th>
                <th className="p-4 font-semibold text-right">Live Price</th>
                <th className="p-4 font-semibold text-right">
                  {tab === 'holding' ? 'Contracts / Cost' : 'Notional'}
                </th>
                <th className="p-4 font-semibold text-right">PM Fee</th>
                <th className="p-4 sm:px-6 font-semibold text-right">
                  {tab === 'holding' ? 'Unrealized P&L' : 'Net P&L'}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-black/[0.04]">
              {loading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <tr key={i}>
                    <td className="p-4 sm:px-6"><Skeleton className="h-3.5 w-20" /></td>
                    <td className="p-4"><Skeleton className="h-3.5 w-28" /></td>
                    <td className="p-4"><Skeleton className="h-3.5 w-44" /></td>
                    <td className="p-4"><Skeleton className="h-3.5 w-16" /></td>
                    <td className="p-4"><Skeleton className="h-3.5 w-14 ml-auto" /></td>
                    <td className="p-4"><Skeleton className="h-3.5 w-14 ml-auto" /></td>
                    <td className="p-4"><Skeleton className="h-3.5 w-14 ml-auto" /></td>
                    <td className="p-4"><Skeleton className="h-3.5 w-12 ml-auto" /></td>
                    <td className="p-4 sm:px-6"><Skeleton className="h-3.5 w-14 ml-auto" /></td>
                  </tr>
                ))
              ) : displayedLogs.length > 0 ? (
                displayedLogs.map((log) => {
                  const fillP = log.fillPrice ?? log.entryPrice ?? 0.5;
                  const curP = log.currentPrice ?? fillP;
                  const fee = log.feeUsd ?? 0.0;
                  const pnl = log.pnl ?? (log.side === 'BUY' ? (log.size * ((curP - fillP) / fillP) - fee) : (log.size * ((fillP - curP) / fillP) - fee));
                  const isProfit = pnl >= 0;
                  const outc = log.outcome || 'Yes';
                  const isYes = outc.toLowerCase() === 'yes' || outc.toLowerCase() === 'true';
                  const shares = fillP > 0 ? (log.size / fillP) : 0;

                  return (
                    <tr 
                      key={log.id} 
                      onClick={() => onSelectTrade && onSelectTrade(log)}
                      className="hover:bg-indigo-50/60 transition-colors text-xs cursor-pointer group"
                    >
                      <td className="p-4 sm:px-6 text-slate-500 font-mono whitespace-nowrap">
                        {formatFrenchDateTime(log.timestamp)}
                      </td>
                      <td className="p-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {log.whaleAvatar ? (
                            <img src={log.whaleAvatar} alt="" className="w-5 h-5 rounded-full object-cover shrink-0 border border-black/10 shadow-2xs" />
                          ) : (
                            <div className="w-5 h-5 rounded-full bg-slate-100 border border-black/10 flex items-center justify-center text-[10px] font-bold text-slate-600 shrink-0">
                              {log.walletAddress ? log.walletAddress.slice(2, 4).toUpperCase() : '0x'}
                            </div>
                          )}
                          <div className="truncate">
                            <span className="font-bold text-slate-900 truncate max-w-[110px] block">
                              {log.whaleName || log.whalePseudonym || (log.walletAddress ? `${log.walletAddress.slice(0, 6)}...` : '0x...')}
                            </span>
                            <span className="text-[10px] font-mono text-slate-400 block">
                              ${(log.whaleStakeUsd ?? (log.size * 10)).toLocaleString(undefined, { maximumFractionDigits: 0 })} • {log.whaleBankrollPct ? `${log.whaleBankrollPct.toFixed(1)}%` : '1.8%'}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="p-4 text-slate-800 truncate max-w-[200px] font-semibold group-hover:text-indigo-600 transition-colors" title={log.marketQuestion}>
                        <div className="flex items-center gap-2">
                          {log.icon ? (
                            <img src={log.icon} alt="" className="w-5 h-5 rounded-md object-cover shrink-0 border border-black/10 shadow-2xs" />
                          ) : null}
                          <span className="truncate max-w-[200px]">{log.marketQuestion || 'Polymarket Condition'}</span>
                        </div>
                      </td>
                      <td className="p-4 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border shadow-[inset_0_1px_0_rgba(255,255,255,0.8)] ${
                            log.side === 'BUY' ? 'text-emerald-800 bg-emerald-50 border-emerald-200' : 'text-rose-800 bg-rose-50 border-rose-200'
                          }`}>
                            {log.side}
                          </span>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                            isYes ? 'text-emerald-700 bg-emerald-100/50 border-emerald-300' : 'text-rose-700 bg-rose-100/50 border-rose-300'
                          }`}>
                            {outc}
                          </span>
                          {log.consensus && log.consensus.is_consensus && (
                            <span 
                              title={`Cohort Consensus (${log.consensus.whale_count} Whales: ${log.consensus.whale_details?.map(w => w.name || w.pseudonym || w.address.slice(0,6)).join(', ') || 'Aligned Whales'})`} 
                              className="text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded-full border border-indigo-200 flex items-center gap-1 cursor-help"
                            >
                              <Users size={10} />
                              <span className="text-[9px] font-bold font-mono">{log.consensus.whale_count}W</span>
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="p-4 text-right font-mono text-slate-800 font-semibold">
                        ${fillP.toFixed(3)}
                      </td>
                      <td className="p-4 text-right font-mono text-indigo-600 font-bold">
                        ${curP.toFixed(3)}
                      </td>
                      <td className="p-4 text-right font-mono text-slate-700 font-semibold">
                        ${(log.size ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        {tab === 'holding' && (
                          <div className="text-[10px] text-slate-400 font-normal">{shares.toFixed(1)} contracts</div>
                        )}
                      </td>
                      <td className="p-4 text-right font-mono text-slate-500 text-[11px]">
                        {fee > 0 ? `-$${fee.toFixed(2)}` : '$0.00'}
                      </td>
                      <td 
                        className="p-4 sm:px-6 text-right font-mono font-bold truncate tabular-nums tracking-tight"
                        title={formatExactPnL(pnl)}
                      >
                        <span className={isProfit ? 'text-emerald-600' : 'text-rose-600'}>
                          {formatCompactPnL(pnl)}
                        </span>
                        <div className={`text-[10px] font-normal ${isProfit ? 'text-emerald-500' : 'text-rose-500'}`}>
                          {isProfit ? '+' : ''}{(log.pnlPct ?? 0).toFixed(1)}%
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={9} className="p-12 text-center text-slate-400 text-xs font-medium">
                    {tab === 'holding' 
                      ? 'No active holdings currently. Mirrored positions will appear here when signals fire.'
                      : tab === 'closed'
                      ? 'No closed positions yet.'
                      : 'No execution logs recorded yet.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Footer: View All / Open Spreadsheet Banner */}
        {filteredLogs.length > MAX_DISPLAY_TRADES && (
          <div className="p-4 px-6 border-t border-black/[0.06] bg-slate-50/80 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
            <span className="text-slate-600 font-medium">
              Displaying latest <strong>{MAX_DISPLAY_TRADES}</strong> of <strong>{filteredLogs.length}</strong> {tab === 'holding' ? 'active holdings' : tab === 'closed' ? 'resolved trades' : 'executions'}.
            </span>
            <button
              onClick={() => setIsSpreadsheetOpen(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 hover:bg-black text-white font-semibold transition-all shadow-sm cursor-pointer"
            >
              <FileSpreadsheet size={14} className="text-emerald-400" />
              <span>Open Complete Spreadsheet ({logs.length} Total Trades)</span>
              <ArrowRight size={13} />
            </button>
          </div>
        )}
      </div>

      {/* Spreadsheet Modal */}
      <FullHistorySpreadsheetModal
        isOpen={isSpreadsheetOpen}
        onClose={() => setIsSpreadsheetOpen(false)}
        logs={logs}
        onSelectTrade={onSelectTrade}
      />
    </>
  );
}
