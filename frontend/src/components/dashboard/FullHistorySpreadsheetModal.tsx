'use client';
import { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ExecutionLog } from '@/types';
import { fetchExecutionLogs } from '@/lib/api-client';
import { 
  X, 
  Download, 
  Search, 
  ArrowUpDown, 
  ExternalLink, 
  FileSpreadsheet, 
  TrendingUp, 
  TrendingDown, 
  ChevronLeft, 
  ChevronRight,
  Loader2
} from 'lucide-react';
import { formatCompactPnL, formatExactPnL, formatFrenchDateTime } from '@/lib/formatters';

interface FullHistorySpreadsheetModalProps {
  isOpen: boolean;
  onClose: () => void;
  logs: ExecutionLog[];
  onSelectTrade?: (trade: ExecutionLog) => void;
}

const PAGE_SIZE = 25;

export function FullHistorySpreadsheetModal({
  isOpen,
  onClose,
  logs,
  onSelectTrade
}: FullHistorySpreadsheetModalProps) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'HOLDING' | 'CLOSED'>('ALL');
  const [sortField, setSortField] = useState<string>('timestamp');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);
  const [isExportingAll, setIsExportingAll] = useState(false);

  // Filtered and Sorted Logs
  const filteredLogs = useMemo(() => {
    let list = [...logs];

    // Status filtering
    if (statusFilter === 'HOLDING') {
      list = list.filter(l => l.side === 'BUY' && l.status === 'FILLED' && !l.marketQuestion?.toLowerCase().includes('resolved'));
    } else if (statusFilter === 'CLOSED') {
      list = list.filter(l => l.side === 'SELL' || l.status === 'RESOLVED' || l.status === 'CLOSED');
    }

    // Search filtering
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(l => 
        l.marketQuestion?.toLowerCase().includes(q) ||
        l.walletAddress?.toLowerCase().includes(q) ||
        l.whaleName?.toLowerCase().includes(q) ||
        l.whalePseudonym?.toLowerCase().includes(q) ||
        l.outcome?.toLowerCase().includes(q) ||
        l.marketCategory?.toLowerCase().includes(q) ||
        l.id?.toLowerCase().includes(q)
      );
    }

    // Sorting
    list.sort((a, b) => {
      let valA: any = 0;
      let valB: any = 0;

      switch (sortField) {
        case 'timestamp':
          valA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
          valB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
          break;
        case 'whale':
          valA = (a.whaleName || a.whalePseudonym || a.walletAddress || '').toLowerCase();
          valB = (b.whaleName || b.whalePseudonym || b.walletAddress || '').toLowerCase();
          break;
        case 'market':
          valA = (a.marketQuestion || '').toLowerCase();
          valB = (b.marketQuestion || '').toLowerCase();
          break;
        case 'outcome':
          valA = (a.outcome || '').toLowerCase();
          valB = (b.outcome || '').toLowerCase();
          break;
        case 'fillPrice':
          valA = a.fillPrice ?? a.entryPrice ?? 0;
          valB = b.fillPrice ?? b.entryPrice ?? 0;
          break;
        case 'currentPrice':
          valA = a.currentPrice ?? 0;
          valB = b.currentPrice ?? 0;
          break;
        case 'size':
          valA = a.size ?? 0;
          valB = b.size ?? 0;
          break;
        case 'fee':
          valA = a.feeUsd ?? 0;
          valB = b.feeUsd ?? 0;
          break;
        case 'pnl':
          valA = a.pnl ?? 0;
          valB = b.pnl ?? 0;
          break;
      }

      if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
      if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return list;
  }, [logs, search, statusFilter, sortField, sortDirection]);

  // Aggregate Stats
  const stats = useMemo(() => {
    let totalVol = 0;
    let totalFees = 0;
    let totalPnl = 0;
    let wins = 0;
    let totalEvaluated = 0;

    filteredLogs.forEach(l => {
      totalVol += (l.size ?? 0);
      totalFees += (l.feeUsd ?? 0);
      const p = l.pnl ?? 0;
      totalPnl += p;
      if (l.side === 'SELL' || l.status === 'RESOLVED' || l.status === 'CLOSED') {
        totalEvaluated++;
        if (p > 0) wins++;
      }
    });

    const winRate = totalEvaluated > 0 ? (wins / totalEvaluated) * 100 : 0;
    return { totalVol, totalFees, totalPnl, winRate, count: filteredLogs.length };
  }, [filteredLogs]);

  // Pagination Slice
  const totalPages = Math.max(1, Math.ceil(filteredLogs.length / PAGE_SIZE));
  const paginatedLogs = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filteredLogs.slice(start, start + PAGE_SIZE);
  }, [filteredLogs, page]);

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const exportToCSV = (customLogs?: ExecutionLog[]) => {
    const listToExport = customLogs || (filteredLogs.length > 0 ? filteredLogs : logs);
    if (listToExport.length === 0) return;

    const headers = [
      'Trade ID',
      'Execution Timestamp (UTC)',
      'Source Whale Address',
      'Whale Name',
      'Market Condition ID',
      'Market Question',
      'Side',
      'Traded Outcome',
      'Fill Price ($)',
      'Live Price ($)',
      'Notional Size ($)',
      'Fee ($)',
      'Net PnL ($)',
      'Status'
    ];

    const rows = listToExport.map(l => {
      const fillP = l.fillPrice ?? l.entryPrice ?? 0.0;
      const curP = l.currentPrice ?? fillP;
      const fee = l.feeUsd ?? 0;
      const pnl = l.pnl ?? 0;

      return [
        `"${l.id}"`,
        `"${l.timestamp || ''}"`,
        `"${l.walletAddress || ''}"`,
        `"${(l.whaleName || l.whalePseudonym || '').replace(/"/g, '""')}"`,
        `"${l.marketConditionId || ''}"`,
        `"${(l.marketQuestion || '').replace(/"/g, '""')}"`,
        `"${l.side}"`,
        `"${l.outcome || 'Yes'}"`,
        fillP.toFixed(4),
        curP.toFixed(4),
        (l.size ?? 0).toFixed(2),
        fee.toFixed(4),
        pnl.toFixed(2),
        `"${l.status || 'FILLED'}"`
      ].join(',');
    });

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `baleen_execution_audit_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-hidden">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/60 dark:bg-black/80 backdrop-blur-md"
        />

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="relative w-full max-w-7xl max-h-[92vh] bg-white dark:bg-[#16171B] text-slate-900 dark:text-white rounded-3xl border border-black/[0.08] dark:border-white/10 shadow-2xl flex flex-col overflow-hidden z-10"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-black/[0.06] dark:border-white/10 bg-slate-50/80 dark:bg-[#1C1D22]">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/20 shadow-2xs">
                <FileSpreadsheet size={20} />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-950 dark:text-white tracking-tight">
                  Master Execution Spreadsheet &amp; Trade Archive
                </h3>
                <p className="text-xs text-slate-500 dark:text-[#8E8F99] font-medium">
                  Full institutional audit logs, order books fills, fee breakdowns, and mark-to-market positions
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2.5 flex-wrap">
              <button
                onClick={() => exportToCSV()}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-sm transition-all cursor-pointer"
              >
                <Download size={14} />
                <span>Export CSV</span>
              </button>
              <button
                onClick={onClose}
                className="p-2 text-slate-400 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/60 dark:hover:bg-[#2C2D35] rounded-xl transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Aggregate KPI Summary Banner */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 px-6 bg-slate-100/50 dark:bg-[#121316] border-b border-black/[0.06] dark:border-white/10 text-xs">
            <div className="p-2.5 px-3 bg-white dark:bg-[#1C1D22] rounded-xl border border-black/[0.04] dark:border-white/5 shadow-2xs">
              <div className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">Total Volume Traded</div>
              <div className="text-sm font-bold font-mono text-slate-900 dark:text-white mt-0.5">
                ${stats.totalVol.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>
            <div className="p-2.5 px-3 bg-white dark:bg-[#1C1D22] rounded-xl border border-black/[0.04] dark:border-white/5 shadow-2xs">
              <div className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">Total Polymarket Fees</div>
              <div className="text-sm font-bold font-mono text-slate-600 dark:text-[#8E8F99] mt-0.5">
                -${stats.totalFees.toFixed(2)}
              </div>
            </div>
            <div className="p-2.5 px-3 bg-white dark:bg-[#1C1D22] rounded-xl border border-black/[0.04] dark:border-white/5 shadow-2xs">
              <div className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">Win Rate</div>
              <div className="text-sm font-bold font-mono text-indigo-600 dark:text-indigo-400 mt-0.5">
                {stats.winRate.toFixed(1)}%
              </div>
            </div>
            <div className="p-2.5 px-3 bg-white dark:bg-[#1C1D22] rounded-xl border border-black/[0.04] dark:border-white/5 shadow-2xs">
              <div className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">Net Portfolio P&L</div>
              <div className={`text-sm font-bold font-mono mt-0.5 ${stats.totalPnl >= 0 ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                {stats.totalPnl >= 0 ? '+' : '-'}${Math.abs(stats.totalPnl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          {/* Search, Filter Tabs & Sort Controls */}
          <div className="p-3.5 px-6 border-b border-black/[0.06] dark:border-white/10 bg-white dark:bg-[#16171B] flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="relative w-full sm:w-80">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-[#8E8F99]" />
              <input
                type="text"
                placeholder="Search market, whale, outcome..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 dark:bg-[#1C1D22] text-slate-900 dark:text-white border border-black/[0.08] dark:border-white/10 rounded-xl focus:outline-none focus:border-slate-400 font-mono"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-end">
              <div className="flex rounded-full bg-slate-100 dark:bg-[#1C1D22] p-0.5 border border-black/[0.06] dark:border-white/5 text-[11px] font-semibold">
                <button
                  onClick={() => { setStatusFilter('ALL'); setPage(1); }}
                  className={`px-3 py-1 rounded-full transition-all cursor-pointer ${
                    statusFilter === 'ALL' ? 'bg-white dark:bg-[#2C2D35] text-slate-900 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99]'
                  }`}
                >
                  All Trades ({logs.length})
                </button>
                <button
                  onClick={() => { setStatusFilter('HOLDING'); setPage(1); }}
                  className={`px-3 py-1 rounded-full transition-all cursor-pointer ${
                    statusFilter === 'HOLDING' ? 'bg-white dark:bg-[#2C2D35] text-emerald-600 dark:text-[#00D09C] shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99]'
                  }`}
                >
                  Currently Holding
                </button>
                <button
                  onClick={() => { setStatusFilter('CLOSED'); setPage(1); }}
                  className={`px-3 py-1 rounded-full transition-all cursor-pointer ${
                    statusFilter === 'CLOSED' ? 'bg-white dark:bg-[#2C2D35] text-slate-900 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99]'
                  }`}
                >
                  Sold / Resolved
                </button>
              </div>
            </div>
          </div>

          {/* Spreadsheet Table Container */}
          <div className="flex-1 overflow-auto bg-slate-50/30 dark:bg-[#0B0C0E]/50 font-mono text-xs">
            <table className="w-full text-left border-collapse table-auto">
              <thead className="sticky top-0 bg-slate-100/95 dark:bg-[#1C1D22]/95 backdrop-blur-md z-10 border-b border-black/[0.08] dark:border-white/10 text-[10px] uppercase font-bold text-slate-600 dark:text-[#8E8F99] select-none">
                <tr>
                  <th onClick={() => handleSort('timestamp')} className="p-3.5 px-4 cursor-pointer hover:bg-slate-200/60 dark:hover:bg-[#2C2D35] transition-colors">
                    <div className="flex items-center gap-1">
                      <span>Timestamp</span>
                      <ArrowUpDown size={11} className={sortField === 'timestamp' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('whale')} className="p-3.5 cursor-pointer hover:bg-slate-200/60 dark:hover:bg-[#2C2D35] transition-colors">
                    <div className="flex items-center gap-1">
                      <span>Whale</span>
                      <ArrowUpDown size={11} className={sortField === 'whale' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('market')} className="p-3.5 cursor-pointer hover:bg-slate-200/60 dark:hover:bg-[#2C2D35] transition-colors max-w-[280px]">
                    <div className="flex items-center gap-1">
                      <span>Prediction Market</span>
                      <ArrowUpDown size={11} className={sortField === 'market' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('outcome')} className="p-3.5 cursor-pointer hover:bg-slate-200/60 dark:hover:bg-[#2C2D35] transition-colors">
                    <div className="flex items-center gap-1">
                      <span>Outcome</span>
                      <ArrowUpDown size={11} className={sortField === 'outcome' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('fillPrice')} className="p-3.5 text-right cursor-pointer hover:bg-slate-200/60 dark:hover:bg-[#2C2D35] transition-colors">
                    <div className="flex items-center justify-end gap-1">
                      <span>Fill Price</span>
                      <ArrowUpDown size={11} className={sortField === 'fillPrice' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('currentPrice')} className="p-3.5 text-right cursor-pointer hover:bg-slate-200/60 dark:hover:bg-[#2C2D35] transition-colors">
                    <div className="flex items-center justify-end gap-1">
                      <span>Live Price</span>
                      <ArrowUpDown size={11} className={sortField === 'currentPrice' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('size')} className="p-3.5 text-right cursor-pointer hover:bg-slate-200/60 dark:hover:bg-[#2C2D35] transition-colors">
                    <div className="flex items-center justify-end gap-1">
                      <span>Size ($)</span>
                      <ArrowUpDown size={11} className={sortField === 'size' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('pnl')} className="p-3.5 text-right cursor-pointer hover:bg-slate-200/60 dark:hover:bg-[#2C2D35] transition-colors">
                    <div className="flex items-center justify-end gap-1">
                      <span>PnL ($)</span>
                      <ArrowUpDown size={11} className={sortField === 'pnl' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-black/[0.04] dark:divide-white/5 text-slate-800 dark:text-white">
                {paginatedLogs.map((trade) => {
                  const fillP = trade.fillPrice ?? trade.entryPrice ?? 0.5;
                  const curP = trade.currentPrice ?? fillP;
                  const pnl = trade.pnl ?? 0;
                  const isProfit = pnl >= 0;

                  return (
                    <tr 
                      key={trade.id} 
                      onClick={() => onSelectTrade && onSelectTrade(trade)}
                      className="hover:bg-slate-100/70 dark:hover:bg-[#1C1D22] transition-colors cursor-pointer"
                    >
                      <td className="p-3.5 px-4 text-[11px] text-slate-500 dark:text-[#8E8F99] whitespace-nowrap">
                        {trade.timestamp ? formatFrenchDateTime(trade.timestamp, true) : 'Live'}
                      </td>
                      <td className="p-3.5 text-xs font-semibold text-slate-900 dark:text-white whitespace-nowrap">
                        {trade.whaleName || trade.whalePseudonym || (trade.walletAddress ? `${trade.walletAddress.slice(0, 6)}...${trade.walletAddress.slice(-4)}` : 'Whale')}
                      </td>
                      <td className="p-3.5 text-xs font-semibold text-slate-900 dark:text-white max-w-[280px] truncate">
                        {trade.marketQuestion || 'Polymarket Event'}
                      </td>
                      <td className="p-3.5">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          (trade.outcome || 'Yes').toLowerCase() === 'yes'
                            ? 'bg-emerald-50 dark:bg-[#00D09C]/10 text-emerald-700 dark:text-[#00D09C]'
                            : 'bg-rose-50 dark:bg-[#FF453A]/10 text-rose-700 dark:text-[#FF453A]'
                        }`}>
                          {trade.outcome || 'Yes'}
                        </span>
                      </td>
                      <td className="p-3.5 text-right font-mono text-xs">
                        ${fillP.toFixed(3)}
                      </td>
                      <td className="p-3.5 text-right font-mono text-xs font-bold text-slate-900 dark:text-white">
                        ${curP.toFixed(3)}
                      </td>
                      <td className="p-3.5 text-right font-mono text-xs font-bold">
                        ${(trade.size ?? 0).toFixed(2)}
                      </td>
                      <td className={`p-3.5 text-right font-mono text-xs font-bold ${isProfit ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                        {isProfit ? '+' : ''}${pnl.toFixed(2)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="p-4 px-6 border-t border-black/[0.06] dark:border-white/10 bg-slate-50/80 dark:bg-[#1C1D22] flex items-center justify-between text-xs">
            <span className="text-slate-500 dark:text-[#8E8F99]">
              Showing {Math.min(filteredLogs.length, (page - 1) * PAGE_SIZE + 1)}–{Math.min(filteredLogs.length, page * PAGE_SIZE)} of {filteredLogs.length} entries
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 rounded-lg border border-black/[0.08] dark:border-white/10 bg-white dark:bg-[#16171B] disabled:opacity-40"
              >
                <ChevronLeft size={14} />
              </button>
              <span className="text-slate-700 dark:text-white font-mono">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-1.5 rounded-lg border border-black/[0.08] dark:border-white/10 bg-white dark:bg-[#16171B] disabled:opacity-40"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
