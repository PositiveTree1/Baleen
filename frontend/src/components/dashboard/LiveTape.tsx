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
    const interval = setInterval(load, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="glass-card rounded-xl overflow-hidden h-[400px] flex flex-col">
      <div className="p-4 border-b border-white/5 flex items-center justify-between bg-white/5">
        <h3 className="font-semibold text-baleen-white flex items-center gap-2">
          <Activity size={16} className="text-baleen-cyan" /> Live Tape
        </h3>
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-baleen-cyan opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-baleen-cyan"></span>
        </span>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2 scroll-smooth">
        {loading ? (
          <div className="p-4 text-center text-sm text-baleen-muted">Connecting...</div>
        ) : logs.length > 0 ? (
          <div className="space-y-1">
            <AnimatePresence initial={false}>
              {logs.map((log) => (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ duration: 0.2 }}
                  className="flex items-center justify-between p-2 rounded hover:bg-white/5 text-sm font-mono"
                >
                  <div className="flex items-center gap-3 w-1/3">
                    <span className="text-baleen-muted">{new Date(log.timestamp).toLocaleTimeString([], { hour12: false })}</span>
                    <span className="text-baleen-white truncate">{log.walletAddress.slice(0,6)}...</span>
                  </div>
                  <div className="w-1/3 truncate px-2 text-baleen-muted" title={log.marketQuestion}>
                    {log.marketQuestion}
                  </div>
                  <div className="w-1/3 flex justify-end gap-3">
                    <span className={`font-semibold ${log.side === 'BUY' ? 'text-baleen-green' : 'text-baleen-red'}`}>
                      {log.side}
                    </span>
                    <span className="text-baleen-white w-16 text-right">${log.fillPrice.toFixed(3)}</span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-baleen-muted text-sm italic">
            Waiting for signals...
          </div>
        )}
      </div>
    </div>
  );
}
