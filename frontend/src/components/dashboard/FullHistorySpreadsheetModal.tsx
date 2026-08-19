'use client';
import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ExecutionLog } from '@/types';
import { 
  X, 
  Download, 
  Search, 
  ArrowUpDown, 
  ExternalLink, 
  FileSpreadsheet, 
  CheckCircle2, 
  Filter, 
  TrendingUp, 
  TrendingDown, 
  ChevronLeft, 
  ChevronRight,
  Layers,
  Users
} from 'lucide-react';
import { formatCompactPnL, formatExactPnL } from '@/lib/formatters';

interface FullHistorySpreadsheetModalProps {
  isOpen: boolean;
  onClose: () => void;
  logs: ExecutionLog[];
  onSelectTrade?: (trade: ExecutionLog) => void;
}

type SortField = 'timestamp' | 'whale' | 'market' | 'outcome' | 'fillPrice' | 'currentPrice' | 'size' | 'fee' | 'pnl';
type SortDirection = 'asc' | 'desc';

export function FullHistorySpreadsheetModal({
  isOpen,
  onClose,
  logs,
  onSelectTrade
}: FullHistorySpreadsheetModalProps) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'HOLDING' | 'CLOSED'>('ALL');
  const [sortField, setSortField] = useState<SortField>('timestamp');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [page, setPage] = useState(1);
  const pageSize = 25;

  // Filter & Sort
  const filteredLogs = useMemo(() => {
    let list = [...logs];

    if (statusFilter === 'HOLDING') {
      list = list.filter(l => l.side === 'BUY' && l.status === 'FILLED' && !l.marketQuestion?.toLowerCase().includes('resolved'));
    } else if (statusFilter === 'CLOSED') {
      list = list.filter(l => l.side === 'SELL' || l.status === 'RESOLVED' || l.status === 'CLOSED');
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(l => 
        l.marketQuestion?.toLowerCase().includes(q) ||
        l.walletAddress?.toLowerCase().includes(q) ||
        l.whaleName?.toLowerCase().includes(q) ||
        l.whalePseudonym?.toLowerCase().includes(q) ||
        l.outcome?.toLowerCase().includes(q) ||
        l.marketConditionId?.toLowerCase().includes(q)
      );
    }

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
    let losses = 0;

    for (const log of filteredLogs) {
      totalVol += (log.size ?? 0);
      totalFees += (log.feeUsd ?? 0);
      const p = log.pnl ?? 0;
      totalPnl += p;
      if (p > 0) wins++;
      else if (p < 0) losses++;
    }

    const totalResolved = wins + losses;
    const winRate = totalResolved > 0 ? (wins / totalResolved) * 100 : 0;

    return {
      count: filteredLogs.length,
      totalVol,
      totalFees,
      totalPnl,
      winRate
    };
  }, [filteredLogs]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(filteredLogs.length / pageSize));
  const paginatedLogs = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredLogs.slice(start, start + pageSize);
  }, [filteredLogs, page, pageSize]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Export to authentic CSV format
  const exportToCSV = () => {
    if (filteredLogs.length === 0) return;

    const headers = [
      'Trade ID',
      'Execution Timestamp (UTC)',
      'Source Whale Address',
      'Whale Name',
      'Market Condition ID',
      'Market Question',
      'Side',
      'Traded Outcome',
      'Shares / Contracts',
      'Entry Fill Price ($)',
      'Live Market Price ($)',
      'Notional Size ($)',
      'Polymarket Taker Fee ($)',
      'Fee Category',
      'Net PnL ($)',
      'PnL Pct (%)',
      'Status',
      'Polymarket URL'
    ];

    const rows = filteredLogs.map(l => {
      const fillP = l.fillPrice ?? l.entryPrice ?? 0.5;
      const curP = l.currentPrice ?? fillP;
      const fee = l.feeUsd ?? 0;
      const pnl = l.pnl ?? 0;
      const shares = fillP > 0 ? (l.size / fillP) : 0;

      return [
        `"${l.id}"`,
        `"${l.timestamp || ''}"`,
        `"${l.walletAddress || ''}"`,
        `"${(l.whaleName || l.whalePseudonym || '').replace(/"/g, '""')}"`,
        `"${l.marketConditionId || ''}"`,
        `"${(l.marketQuestion || '').replace(/"/g, '""')}"`,
        `"${l.side}"`,
        `"${l.outcome || 'Yes'}"`,
        shares.toFixed(2),
        fillP.toFixed(4),
        curP.toFixed(4),
        (l.size ?? 0).toFixed(2),
        fee.toFixed(4),
        `"${l.marketCategory || 'General'}"`,
        pnl.toFixed(2),
        (l.pnlPct ?? 0).toFixed(1),
        `"${l.status || 'FILLED'}"`,
        `"${l.polymarketUrl || ''}"`
      ].join(',');
    });

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `baleen_trade_executions_${new Date().toISOString().slice(0, 10)}.csv`);
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
          className="fixed inset-0 bg-slate-950/40 backdrop-blur-md"
        />

        {/* Spreadsheet Modal Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 12 }}
          transition={{ type: 'spring', damping: 28, stiffness: 300 }}
          className="relative w-full max-w-7xl h-[90vh] bg-white rounded-3xl border border-black/[0.08] shadow-[0_25px_60px_-15px_rgba(0,0,0,0.3)] flex flex-col overflow-hidden z-10"
        >
          {/* Modal Header */}
          <div className="p-5 px-6 border-b border-black/[0.06] bg-slate-50/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-2xs">
                <FileSpreadsheet size={20} />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
                  Complete Execution Spreadsheet
                  <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-200/80 text-slate-700 font-semibold">
                    {filteredLogs.length} records
                  </span>
                </h3>
                <p className="text-xs text-slate-500 font-medium">
                  Full institutional audit logs, order books fills, fee breakdowns, and mark-to-market positions
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2.5 flex-wrap">
              <button
                onClick={exportToCSV}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-sm transition-all cursor-pointer"
              >
                <Download size={14} />
                <span>Export CSV / Excel</span>
              </button>
              <button
                onClick={onClose}
                className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-xl transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Aggregate KPI Summary Banner */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 px-6 bg-slate-100/50 border-b border-black/[0.06] text-xs">
            <div className="p-2.5 px-3 bg-white rounded-xl border border-black/[0.04] shadow-2xs">
              <div className="text-[10px] uppercase font-bold text-slate-400">Total Volume Traded</div>
              <div className="text-sm font-bold font-mono text-slate-900 mt-0.5">
                ${stats.totalVol.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>
            <div className="p-2.5 px-3 bg-white rounded-xl border border-black/[0.04] shadow-2xs">
              <div className="text-[10px] uppercase font-bold text-slate-400">Total Polymarket Fees</div>
              <div className="text-sm font-bold font-mono text-slate-600 mt-0.5">
                -${stats.totalFees.toFixed(2)}
              </div>
            </div>
            <div className="p-2.5 px-3 bg-white rounded-xl border border-black/[0.04] shadow-2xs">
              <div className="text-[10px] uppercase font-bold text-slate-400">Win Rate</div>
              <div className="text-sm font-bold font-mono text-indigo-600 mt-0.5">
                {stats.winRate.toFixed(1)}%
              </div>
            </div>
            <div className="p-2.5 px-3 bg-white rounded-xl border border-black/[0.04] shadow-2xs">
              <div className="text-[10px] uppercase font-bold text-slate-400">Net Portfolio P&L</div>
              <div className={`text-sm font-bold font-mono mt-0.5 ${stats.totalPnl >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                {stats.totalPnl >= 0 ? '+' : '-'}${Math.abs(stats.totalPnl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          {/* Search, Filter Tabs & Sort Controls */}
          <div className="p-3.5 px-6 border-b border-black/[0.06] bg-white flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="relative w-full sm:w-80">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search market, whale, outcome, or 0x..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-black/[0.08] rounded-xl focus:outline-none focus:border-slate-400 font-mono"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-end">
              {/* Position Filter Pills */}
              <div className="flex rounded-xl bg-slate-100 p-0.5 border border-black/[0.06] text-[11px] font-semibold">
                <button
                  onClick={() => { setStatusFilter('ALL'); setPage(1); }}
                  className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                    statusFilter === 'ALL' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  All Trades ({logs.length})
                </button>
                <button
                  onClick={() => { setStatusFilter('HOLDING'); setPage(1); }}
                  className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                    statusFilter === 'HOLDING' ? 'bg-emerald-600 text-white shadow-2xs' : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  Currently Holding
                </button>
                <button
                  onClick={() => { setStatusFilter('CLOSED'); setPage(1); }}
                  className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                    statusFilter === 'CLOSED' ? 'bg-slate-900 text-white shadow-2xs' : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  Sold / Resolved
                </button>
              </div>
            </div>
          </div>

          {/* Spreadsheet Table Container */}
          <div className="flex-1 overflow-auto bg-slate-50/30 font-mono text-xs">
            <table className="w-full text-left border-collapse table-auto">
              <thead className="sticky top-0 bg-slate-100/95 backdrop-blur-md z-10 border-b border-black/[0.08] text-[10px] uppercase font-bold text-slate-600 select-none">
                <tr>
                  <th onClick={() => handleSort('timestamp')} className="p-3.5 px-4 cursor-pointer hover:bg-slate-200/60 transition-colors">
                    <div className="flex items-center gap-1">
                      <span>Timestamp</span>
                      <ArrowUpDown size={11} className={sortField === 'timestamp' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('whale')} className="p-3.5 cursor-pointer hover:bg-slate-200/60 transition-colors">
                    <div className="flex items-center gap-1">
                      <span>Whale</span>
                      <ArrowUpDown size={11} className={sortField === 'whale' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('market')} className="p-3.5 cursor-pointer hover:bg-slate-200/60 transition-colors max-w-[280px]">
                    <div className="flex items-center gap-1">
                      <span>Prediction Market</span>
                      <ArrowUpDown size={11} className={sortField === 'market' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('outcome')} className="p-3.5 cursor-pointer hover:bg-slate-200/60 transition-colors">
                    <div className="flex items-center gap-1">
                      <span>Outcome</span>
                      <ArrowUpDown size={11} className={sortField === 'outcome' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('fillPrice')} className="p-3.5 text-right cursor-pointer hover:bg-slate-200/60 transition-colors">
                    <div className="flex items-center justify-end gap-1">
                      <span>Fill Price</span>
                      <ArrowUpDown size={11} className={sortField === 'fillPrice' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('currentPrice')} className="p-3.5 text-right cursor-pointer hover:bg-slate-200/60 transition-colors">
                    <div className="flex items-center justify-end gap-1">
                      <span>Live Price</span>
                      <ArrowUpDown size={11} className={sortField === 'currentPrice' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('size')} className="p-3.5 text-right cursor-pointer hover:bg-slate-200/60 transition-colors">
                    <div className="flex items-center justify-end gap-1">
                      <span>Notional ($)</span>
                      <ArrowUpDown size={11} className={sortField === 'size' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('fee')} className="p-3.5 text-right cursor-pointer hover:bg-slate-200/60 transition-colors">
                    <div className="flex items-center justify-end gap-1">
                      <span>PM Fee</span>
                      <ArrowUpDown size={11} className={sortField === 'fee' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th onClick={() => handleSort('pnl')} className="p-3.5 px-4 text-right cursor-pointer hover:bg-slate-200/60 transition-colors">
                    <div className="flex items-center justify-end gap-1">
                      <span>Net P&L</span>
                      <ArrowUpDown size={11} className={sortField === 'pnl' ? 'text-indigo-600' : 'text-slate-400'} />
                    </div>
                  </th>
                  <th className="p-3.5 text-center">Status</th>
                  <th className="p-3.5 px-4 text-center">Link</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-black/[0.04] bg-white">
                {paginatedLogs.length > 0 ? (
                  paginatedLogs.map((log) => {
                    const fillP = log.fillPrice ?? log.entryPrice ?? 0.5;
                    const curP = log.currentPrice ?? fillP;
                    const fee = log.feeUsd ?? 0.0;
                    const pnl = log.pnl ?? 0.0;
                    const isProfit = pnl >= 0;
                    const outc = log.outcome || 'Yes';
                    const isYes = outc.toLowerCase() === 'yes' || outc.toLowerCase() === 'true';
                    const shares = fillP > 0 ? (log.size / fillP) : 0;

                    return (
                      <tr
                        key={log.id}
                        onClick={() => onSelectTrade && onSelectTrade(log)}
                        className="hover:bg-indigo-50/50 transition-colors cursor-pointer group"
                      >
                        <td className="p-3.5 px-4 text-slate-500 whitespace-nowrap text-[11px]">
                          {log.timestamp ? new Date(log.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' }) : '--'}
                        </td>
                        <td className="p-3.5 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            {log.whaleAvatar ? (
                              <img src={log.whaleAvatar} alt="" className="w-5 h-5 rounded-full object-cover shrink-0 border border-black/10 shadow-2xs" />
                            ) : (
                              <div className="w-5 h-5 rounded-full bg-slate-100 border border-black/10 flex items-center justify-center text-[9px] font-bold text-slate-600 shrink-0">
                                {log.walletAddress ? log.walletAddress.slice(2, 4).toUpperCase() : '0x'}
                              </div>
                            )}
                            <span className="font-bold text-slate-900 truncate max-w-[100px]">
                              {log.whaleName || log.whalePseudonym || (log.walletAddress ? `${log.walletAddress.slice(0, 6)}...` : '0x...')}
                            </span>
                          </div>
                        </td>
                        <td className="p-3.5 font-sans font-medium text-slate-900 max-w-[260px] truncate" title={log.marketQuestion}>
                          <div className="flex items-center gap-2">
                            {log.icon && <img src={log.icon} alt="" className="w-4 h-4 rounded object-cover shrink-0" />}
                            <span className="truncate">{log.marketQuestion || 'Polymarket Condition'}</span>
                          </div>
                        </td>
                        <td className="p-3.5 whitespace-nowrap">
                          <div className="flex items-center gap-1">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              log.side === 'BUY' ? 'text-emerald-800 bg-emerald-50 border border-emerald-200' : 'text-rose-800 bg-rose-50 border border-rose-200'
                            }`}>
                              {log.side}
                            </span>
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              isYes ? 'text-emerald-700 bg-emerald-100/60 border border-emerald-300' : 'text-rose-700 bg-rose-100/60 border border-rose-300'
                            }`}>
                              {outc}
                            </span>
                            {log.consensus && log.consensus.is_consensus && (
                              <span title="Consensus Boosted" className="text-indigo-600 bg-indigo-50 p-0.5 rounded">
                                <Users size={11} />
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="p-3.5 text-right font-bold text-slate-800">
                          ${fillP.toFixed(4)}
                        </td>
                        <td className="p-3.5 text-right font-bold text-indigo-600">
                          ${curP.toFixed(4)}
                        </td>
                        <td className="p-3.5 text-right text-slate-700 font-semibold">
                          ${(log.size ?? 0).toFixed(2)}
                          <div className="text-[10px] text-slate-400 font-normal">{shares.toFixed(1)} shs</div>
                        </td>
                        <td className="p-3.5 text-right text-slate-500 text-[11px]">
                          {fee > 0 ? `-$${fee.toFixed(3)}` : '$0.00'}
                        </td>
                        <td 
                          className="p-3.5 px-4 text-right font-bold truncate tabular-nums"
                          title={formatExactPnL(pnl)}
                        >
                          <span className={isProfit ? 'text-emerald-600' : 'text-rose-600'}>
                            {formatExactPnL(pnl)}
                          </span>
                          <div className={`text-[10px] font-normal ${isProfit ? 'text-emerald-500' : 'text-rose-500'}`}>
                            {isProfit ? '+' : ''}{(log.pnlPct ?? 0).toFixed(1)}%
                          </div>
                        </td>
                        <td className="p-3.5 text-center whitespace-nowrap">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                            log.status === 'FILLED' 
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                              : 'bg-slate-100 text-slate-700 border-black/10'
                          }`}>
                            {log.status || 'FILLED'}
                          </span>
                        </td>
                        <td className="p-3.5 px-4 text-center">
                          {log.polymarketUrl && (
                            <a
                              href={log.polymarketUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="p-1.5 inline-flex text-slate-400 hover:text-indigo-600 rounded-lg hover:bg-slate-100 transition-colors"
                              title="Open on Polymarket"
                            >
                              <ExternalLink size={13} />
                            </a>
                          )}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={11} className="p-12 text-center text-slate-400 text-xs font-sans">
                      No trades match the active filter criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="p-3.5 px-6 border-t border-black/[0.06] bg-slate-50/80 flex items-center justify-between text-xs">
            <div className="text-slate-500 font-medium font-sans">
              Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, filteredLogs.length)} of {filteredLogs.length} trades
            </div>

            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 px-3 rounded-xl bg-white border border-black/[0.08] text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed font-semibold transition-all shadow-2xs flex items-center gap-1 cursor-pointer"
              >
                <ChevronLeft size={14} /> Prev
              </button>
              <span className="px-3 font-mono font-bold text-slate-800">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-1.5 px-3 rounded-xl bg-white border border-black/[0.08] text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed font-semibold transition-all shadow-2xs flex items-center gap-1 cursor-pointer"
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
