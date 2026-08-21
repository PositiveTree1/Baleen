'use client';
import { useEffect, useState } from 'react';
import { fetchExecutionLogs, getCachedExecutionLogs } from '@/lib/api-client';
import { formatFrenchTime, formatFrenchTimeWithSeconds } from '@/lib/formatters';
import { ExecutionLog } from '@/types';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Flame, Filter, Search, Zap } from 'lucide-react';

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

  return (
    <div className="rounded-3xl overflow-hidden h-[460px] flex flex-col border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_12px_28px_-4px_rgba(0,0,0,0.05)] bg-white">
      <div className="p-4 px-6 border-b border-black/[0.06] flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50">
        <div className="flex items-center gap-2.5">
          <Activity size={16} className="text-slate-900" />
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">Live Execution Tape</h3>
          <div className="flex items-center gap-1.5 ml-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[10px] font-mono text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              Polygon CTF
            </span>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2">
          <div className="flex rounded-xl bg-slate-200/60 p-0.5 border border-black/[0.04] text-[11px]">
            {(['ALL', 'BUY', 'SELL', 'CONSENSUS'] as const).map((side) => (
              <button
                key={side}
                onClick={() => setSideFilter(side)}
                className={`px-2.5 py-0.5 rounded-lg font-semibold transition-all cursor-pointer ${
                  sideFilter === side 
                    ? 'bg-white text-slate-950 shadow-sm border border-black/[0.04]' 
                    : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                {side === 'CONSENSUS' ? '🔥 Consensus' : side}
              </button>
            ))}
          </div>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-3.5 scroll-smooth">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-400 font-medium">Connecting to signal stream...</div>
        ) : filteredLogs.length > 0 ? (
          <div className="space-y-1.5">
            <AnimatePresence initial={false}>
              {filteredLogs.map((log) => (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.96 }}
                  transition={{ duration: 0.18 }}
                  onClick={() => onSelectTrade && onSelectTrade(log)}
                  className="flex items-center justify-between p-2.5 px-3.5 rounded-2xl bg-slate-50/80 hover:bg-indigo-50/70 hover:border-indigo-200 border border-black/[0.04] text-xs font-mono transition-all shadow-[0_1px_2px_rgba(0,0,0,0.02)] cursor-pointer group"
                >
                  <div className="flex items-center gap-2.5 w-1/3">
                    <span className="text-slate-500 text-[11px]">
                      {formatFrenchTimeWithSeconds(log.timestamp)}
                    </span>
                    <div className="flex items-center gap-1.5 truncate">
                      {log.whaleAvatar ? (
                        <img src={log.whaleAvatar} alt="" className="w-4 h-4 rounded-full object-cover shrink-0 border border-black/10 shadow-2xs" />
                      ) : null}
                      <span className="text-slate-800 font-bold truncate group-hover:text-indigo-600 transition-colors">
                        {log.whaleName || log.whalePseudonym || (log.walletAddress ? `${log.walletAddress.slice(0, 6)}...` : '0x...')}
                      </span>
                    </div>
                  </div>
                  <div className="w-1/3 truncate px-2 flex items-center gap-1.5 text-slate-600 font-sans text-xs font-medium" title={log.marketQuestion}>
                    {log.icon ? (
                      <img src={log.icon} alt="" className="w-4 h-4 rounded-md object-cover shrink-0 border border-black/10 shadow-2xs" />
                    ) : null}
                    <span className="truncate">{log.marketQuestion || 'Market Order'}</span>
                  </div>
                  <div className="w-1/3 flex justify-end items-center gap-2">
                    {log.consensus?.is_consensus && (
                      <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-200">
                        <Flame size={10} className="text-indigo-600" />
                        {log.consensus.whale_count} Whales
                      </span>
                    )}
                    <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border shadow-[inset_0_1px_0_rgba(255,255,255,0.8)] ${
                      log.side === 'BUY' ? 'text-emerald-800 bg-emerald-50 border-emerald-200' : 'text-rose-800 bg-rose-50 border-rose-200'
                    }`}>
                      {log.side} {log.outcome ? log.outcome.slice(0, 3).toUpperCase() : 'YES'}
                    </span>
                    <span className="text-slate-900 font-bold w-14 text-right font-mono">
                      ${(log.fillPrice ?? log.entryPrice ?? 0).toFixed(3)}
                    </span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 text-xs gap-2">
            <Activity size={24} className="opacity-30 text-slate-400" />
            <span className="font-medium">Listening for Polymarket contract fills...</span>
          </div>
        )}
      </div>
    </div>
  );
}
