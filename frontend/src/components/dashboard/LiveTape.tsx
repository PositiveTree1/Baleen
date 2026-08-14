'use client';
import { useEffect, useState } from 'react';
import { fetchExecutionLogs } from '@/lib/api-client';
import { ExecutionLog } from '@/types';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity } from 'lucide-react';

interface LiveTapeProps {
  onSelectTrade?: (trade: ExecutionLog) => void;
}

export function LiveTape({ onSelectTrade }: LiveTapeProps) {
  const [logs, setLogs] = useState<ExecutionLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const data = await fetchExecutionLogs(undefined, { limit: '20' });
      setLogs(data);
      setLoading(false);
    }
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="rounded-3xl overflow-hidden h-[420px] flex flex-col border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_12px_28px_-4px_rgba(0,0,0,0.05)] bg-white">
      <div className="p-4 px-6 border-b border-black/[0.06] flex items-center justify-between bg-slate-50/50">
        <div className="flex items-center gap-2.5">
          <Activity size={16} className="text-slate-900" />
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">Live Execution Tape</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-slate-500 font-semibold">Polygon CTF</span>
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-3.5 scroll-smooth">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-400 font-medium">Connecting to signal stream...</div>
        ) : logs.length > 0 ? (
          <div className="space-y-1.5">
            <AnimatePresence initial={false}>
              {logs.map((log) => (
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
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString([], { hour12: false }) : '--:--'}
                    </span>
                    <span className="text-slate-800 font-bold truncate group-hover:text-indigo-600 transition-colors">
                      {(log.walletAddress || '0x0000').slice(0, 6)}...
                    </span>
                  </div>
                  <div className="w-1/3 truncate px-2 text-slate-600 font-sans text-xs font-medium" title={log.marketQuestion}>
                    {log.marketQuestion || 'Market Order'}
                  </div>
                  <div className="w-1/3 flex justify-end items-center gap-3">
                    {log.consensus?.is_consensus && (
                      <span className="hidden sm:inline-block px-1.5 py-0.5 rounded text-[9px] font-bold bg-indigo-100 text-indigo-800">
                        {log.consensus.whale_count} Whales
                      </span>
                    )}
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border shadow-[inset_0_1px_0_rgba(255,255,255,0.8)] ${
                      log.side === 'BUY' ? 'text-emerald-800 bg-emerald-50 border-emerald-200' : 'text-rose-800 bg-rose-50 border-rose-200'
                    }`}>
                      {log.side}
                    </span>
                    <span className="text-slate-900 font-bold w-16 text-right font-mono">
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
