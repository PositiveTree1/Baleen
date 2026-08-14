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
      // In a real app, you might pass userId to only fetch user's own trade log
      const data = await fetchExecutionLogs(userId, { limit: '50' });
      setLogs(data);
      setLoading(false);
    }
    load();
  }, [userId]);

  return (
    <div className="glass-card rounded-xl overflow-hidden mt-6">
      <div className="p-4 border-b border-white/5 bg-white/5">
        <h3 className="font-semibold text-baleen-white">Trade History</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/10 text-xs uppercase text-baleen-muted bg-white/5">
              <th className="p-4 font-medium">Time</th>
              <th className="p-4 font-medium">Market</th>
              <th className="p-4 font-medium">Side</th>
              <th className="p-4 font-medium text-right">Fill Price</th>
              <th className="p-4 font-medium text-right">Size</th>
              <th className="p-4 font-medium text-right">P&L</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-white/5">
                  <td className="p-4"><Skeleton className="h-4 w-24" /></td>
                  <td className="p-4"><Skeleton className="h-4 w-48" /></td>
                  <td className="p-4"><Skeleton className="h-4 w-12" /></td>
                  <td className="p-4"><Skeleton className="h-4 w-16 ml-auto" /></td>
                  <td className="p-4"><Skeleton className="h-4 w-16 ml-auto" /></td>
                  <td className="p-4"><Skeleton className="h-4 w-16 ml-auto" /></td>
                </tr>
              ))
            ) : logs.length > 0 ? (
              logs.map((log) => (
                <tr key={log.id} className="border-b border-white/5 hover:bg-white/5 transition-colors text-sm">
                  <td className="p-4 text-baleen-muted whitespace-nowrap">
                    {new Date(log.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                  </td>
                  <td className="p-4 text-baleen-white truncate max-w-[200px]" title={log.marketQuestion}>
                    {log.marketQuestion}
                  </td>
                  <td className={`p-4 font-semibold ${log.side === 'BUY' ? 'text-baleen-green' : 'text-baleen-red'}`}>
                    {log.side}
                  </td>
                  <td className="p-4 text-right font-mono text-baleen-white">
                    ${(log.fillPrice ?? 0).toFixed(3)}
                  </td>
                  <td className="p-4 text-right font-mono text-baleen-white">
                    ${(log.size ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td className="p-4 text-right font-mono">
                    {log.pnl !== undefined ? (
                      <span className={log.pnl >= 0 ? 'text-baleen-green' : 'text-baleen-red'}>
                        {log.pnl >= 0 ? '+' : '-'}${Math.abs(log.pnl).toFixed(2)}
                      </span>
                    ) : (
                      <span className="text-baleen-muted">-</span>
                    )}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6} className="p-8 text-center text-baleen-muted">
                  No trades found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
