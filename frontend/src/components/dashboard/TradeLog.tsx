'use client';
import { useEffect, useState } from 'react';
import { fetchExecutionLogs } from '@/lib/api-client';
import { ExecutionLog } from '@/types';
import { Skeleton } from '../ui/Skeleton';
import { Tag, HelpCircle } from 'lucide-react';

interface TradeLogProps {
  userId?: string;
  onSelectTrade?: (trade: ExecutionLog) => void;
}

export function TradeLog({ userId, onSelectTrade }: TradeLogProps) {
  const [logs, setLogs] = useState<ExecutionLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const data = await fetchExecutionLogs(userId, { limit: '500' });
      setLogs(data);
      setLoading(false);
    }
    load();
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, [userId]);

  return (
    <div className="rounded-3xl overflow-hidden mt-6 border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_16px_36px_-6px_rgba(0,0,0,0.05)] bg-white">
      <div className="p-4 px-6 border-b border-black/[0.06] bg-slate-50/50 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">Execution Audit Log</h3>
          <span className="text-[11px] text-slate-500 font-mono font-semibold">Realized & Active Fills with 2026 Dynamic Polymarket Fees</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono font-semibold text-slate-500 bg-white px-2.5 py-1 rounded-full border border-black/[0.06] shadow-2xs">
          <span>Fee Model: <strong>Quadratic Taker Curve (0%-7%)</strong></span>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-black/[0.06] text-[10px] uppercase tracking-wider text-slate-500 bg-slate-50/90 font-semibold">
              <th className="p-4 sm:px-6 font-semibold">Timestamp</th>
              <th className="p-4 font-semibold">Prediction Market</th>
              <th className="p-4 font-semibold">Category</th>
              <th className="p-4 font-semibold">Side</th>
              <th className="p-4 font-semibold text-right">Fill Price</th>
              <th className="p-4 font-semibold text-right">Live Price</th>
              <th className="p-4 font-semibold text-right">Notional</th>
              <th className="p-4 font-semibold text-right">PM Fee</th>
              <th className="p-4 sm:px-6 font-semibold text-right">Net P&L</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-black/[0.04]">
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i}>
                  <td className="p-4 sm:px-6"><Skeleton className="h-3.5 w-20" /></td>
                  <td className="p-4"><Skeleton className="h-3.5 w-44" /></td>
                  <td className="p-4"><Skeleton className="h-3.5 w-16" /></td>
                  <td className="p-4"><Skeleton className="h-3.5 w-10" /></td>
                  <td className="p-4"><Skeleton className="h-3.5 w-14 ml-auto" /></td>
                  <td className="p-4"><Skeleton className="h-3.5 w-14 ml-auto" /></td>
                  <td className="p-4"><Skeleton className="h-3.5 w-14 ml-auto" /></td>
                  <td className="p-4"><Skeleton className="h-3.5 w-12 ml-auto" /></td>
                  <td className="p-4 sm:px-6"><Skeleton className="h-3.5 w-14 ml-auto" /></td>
                </tr>
              ))
            ) : logs.length > 0 ? (
              logs.map((log) => {
                const fillP = log.fillPrice ?? log.entryPrice ?? 0.5;
                const curP = log.currentPrice ?? fillP;
                const fee = log.feeUsd ?? 0.0;
                const pnl = log.pnl ?? (log.side === 'BUY' ? (log.size * ((curP - fillP) / fillP) - fee) : (log.size * ((fillP - curP) / fillP) - fee));
                const isProfit = pnl >= 0;
                const category = log.marketCategory || 'General';

                return (
                  <tr 
                    key={log.id} 
                    onClick={() => onSelectTrade && onSelectTrade(log)}
                    className="hover:bg-indigo-50/60 transition-colors text-xs cursor-pointer group"
                  >
                    <td className="p-4 sm:px-6 text-slate-500 font-mono whitespace-nowrap">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : '--'}
                    </td>
                    <td className="p-4 text-slate-800 truncate max-w-[200px] font-semibold group-hover:text-indigo-600 transition-colors" title={log.marketQuestion}>
                      <div className="flex items-center gap-2">
                        {log.icon ? (
                          <img src={log.icon} alt="" className="w-5 h-5 rounded-full object-cover shrink-0 border border-black/10" />
                        ) : null}
                        <span className="truncate max-w-[200px]">{log.marketQuestion || 'Polymarket Condition'}</span>
                      </div>
                    </td>
                    <td className="p-4 whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold border ${
                        category === 'Crypto' ? 'bg-amber-50 text-amber-800 border-amber-200' :
                        category === 'Sports' ? 'bg-blue-50 text-blue-800 border-blue-200' :
                        category === 'Politics & Finance' ? 'bg-purple-50 text-purple-800 border-purple-200' :
                        category === 'Geopolitics' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                        'bg-slate-50 text-slate-700 border-slate-200'
                      }`}>
                        {category}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border shadow-[inset_0_1px_0_rgba(255,255,255,0.8)] ${
                        log.side === 'BUY' ? 'text-emerald-800 bg-emerald-50 border-emerald-200' : 'text-rose-800 bg-rose-50 border-rose-200'
                      }`}>
                        {log.side}
                      </span>
                    </td>
                    <td className="p-4 text-right font-mono text-slate-800 font-semibold">
                      ${fillP.toFixed(3)}
                    </td>
                    <td className="p-4 text-right font-mono text-indigo-600 font-bold">
                      ${curP.toFixed(3)}
                    </td>
                    <td className="p-4 text-right font-mono text-slate-700 font-semibold">
                      ${(log.size ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="p-4 text-right font-mono text-slate-500 text-[11px]">
                      {fee > 0 ? `-$${fee.toFixed(2)}` : '$0.00'}
                    </td>
                    <td className="p-4 sm:px-6 text-right font-mono font-bold">
                      <span className={isProfit ? 'text-emerald-600' : 'text-rose-600'}>
                        {isProfit ? '+' : '-'}${Math.abs(pnl).toFixed(2)}
                      </span>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={9} className="p-12 text-center text-slate-400 text-xs font-medium">
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
