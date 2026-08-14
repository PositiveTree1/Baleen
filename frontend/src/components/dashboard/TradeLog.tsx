'use client';
import { useEffect, useState } from 'react';
import { fetchExecutionLogs } from '@/lib/api-client';
import { ExecutionLog } from '@/types';
import { Skeleton } from '../ui/Skeleton';

export function TradeLog({ userId }: { userId?: string }) {
  const [logs, setLogs] = useState<ExecutionLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const data = await fetchExecutionLogs(userId, { limit: '50' });
      setLogs(data);
      setLoading(false);
    }
    load();
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, [userId]);

  return (
    <div className="glass-card rounded-3xl overflow-hidden mt-6 border border-white/[0.08] shadow-apple bg-zinc-900/40 backdrop-blur-xl">
      <div className="p-4 px-6 border-b border-white/[0.06] bg-white/[0.02] flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white tracking-tight">Execution Audit Log</h3>
        <span className="text-[11px] text-zinc-500 font-mono">Realized Fills</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/[0.06] text-[10px] uppercase tracking-wider text-zinc-400 bg-zinc-950/60">
              <th className="p-4 sm:px-6 font-medium">Timestamp</th>
              <th className="p-4 font-medium">Prediction Market</th>
              <th className="p-4 font-medium">Side</th>
              <th className="p-4 font-medium text-right">Fill Price</th>
              <th className="p-4 font-medium text-right">Notional ($)</th>
              <th className="p-4 sm:px-6 font-medium text-right">Realized P&L</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.03]">
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i}>
                  <td className="p-4 sm:px-6"><Skeleton className="h-3.5 w-20" /></td>
                  <td className="p-4"><Skeleton className="h-3.5 w-48" /></td>
                  <td className="p-4"><Skeleton className="h-3.5 w-10" /></td>
                  <td className="p-4"><Skeleton className="h-3.5 w-14 ml-auto" /></td>
                  <td className="p-4"><Skeleton className="h-3.5 w-14 ml-auto" /></td>
                  <td className="p-4 sm:px-6"><Skeleton className="h-3.5 w-14 ml-auto" /></td>
                </tr>
              ))
            ) : logs.length > 0 ? (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-white/[0.03] transition-colors text-xs">
                  <td className="p-4 sm:px-6 text-zinc-500 font-mono whitespace-nowrap">
                    {log.timestamp ? new Date(log.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : '--'}
                  </td>
                  <td className="p-4 text-zinc-200 truncate max-w-[240px] font-medium" title={log.marketQuestion}>
                    {log.marketQuestion || 'Polymarket Condition'}
                  </td>
                  <td className="p-4">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      log.side === 'BUY' ? 'text-emerald-400 bg-emerald-500/10' : 'text-rose-400 bg-rose-500/10'
                    }`}>
                      {log.side}
                    </span>
                  </td>
                  <td className="p-4 text-right font-mono text-white">
                    ${(log.fillPrice ?? 0).toFixed(3)}
                  </td>
                  <td className="p-4 text-right font-mono text-zinc-300">
                    ${(log.size ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="p-4 sm:px-6 text-right font-mono font-medium">
                    {log.pnl !== undefined && log.pnl !== null ? (
                      <span className={log.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                        {log.pnl >= 0 ? '+' : '-'}${Math.abs(log.pnl).toFixed(2)}
                      </span>
                    ) : (
                      <span className="text-zinc-600">-</span>
                    )}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6} className="p-12 text-center text-zinc-500 text-xs">
                  No execution logs recorded yet. Signals from basket whales will trigger auto-mirrored trades here.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
