'use client';
import { useEffect, useState } from 'react';
import { fetchExecutionLogs } from '@/lib/api-client';
import { ExecutionLog } from '@/types';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity } from 'lucide-react';

export function LiveTape() {
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
    <div className="glass-card rounded-3xl overflow-hidden h-[420px] flex flex-col border border-white/[0.08] shadow-apple bg-zinc-900/40 backdrop-blur-xl">
      <div className="p-4 px-6 border-b border-white/[0.06] flex items-center justify-between bg-white/[0.02]">
        <div className="flex items-center gap-2.5">
          <Activity size={15} className="text-emerald-400" />
          <h3 className="text-sm font-semibold text-white tracking-tight">Live Execution Tape</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-zinc-500">Polygon CTF</span>
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
          </span>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-3 scroll-smooth">
        {loading ? (
          <div className="p-8 text-center text-xs text-zinc-500">Connecting to signal stream...</div>
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
                  className="flex items-center justify-between p-2.5 px-3 rounded-2xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/[0.03] text-xs font-mono transition-colors"
                >
                  <div className="flex items-center gap-2.5 w-1/3">
                    <span className="text-zinc-500 text-[11px]">
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString([], { hour12: false }) : '--:--'}
                    </span>
                    <span className="text-zinc-300 font-medium truncate">
                      {(log.walletAddress || '0x0000').slice(0, 6)}...
                    </span>
                  </div>
                  <div className="w-1/3 truncate px-2 text-zinc-400 font-sans text-xs" title={log.marketQuestion}>
                    {log.marketQuestion || 'Market Order'}
                  </div>
                  <div className="w-1/3 flex justify-end items-center gap-3">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      log.side === 'BUY' ? 'text-emerald-400 bg-emerald-500/10' : 'text-rose-400 bg-rose-500/10'
                    }`}>
                      {log.side}
                    </span>
                    <span className="text-white font-medium w-16 text-right font-mono">
                      ${(log.fillPrice ?? 0).toFixed(3)}
                    </span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-zinc-500 text-xs gap-2">
            <Activity size={24} className="opacity-30" />
            <span>Listening for Polymarket contract fills...</span>
          </div>
        )}
      </div>
    </div>
  );
}
