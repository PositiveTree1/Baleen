'use client';
import { useEffect, useState } from 'react';
import { fetchWallets } from '@/lib/api-client';
import { Wallet } from '@/types';
import { Badge } from '../ui/Badge';
import { Skeleton } from '../ui/Skeleton';

export function Leaderboard() {
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const data = await fetchWallets({ limit: '10' });
      setWallets(data);
      setLoading(false);
    }
    load();
  }, []);

  const formatWinRate = (wr: number) => {
    const val = wr > 1 ? wr : wr * 100;
    return `${val.toFixed(1)}%`;
  };

  return (
    <section id="leaderboard" className="py-24 px-6 lg:px-20 border-t border-black/[0.06] bg-[#F8F9FB]">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 mb-10">
          <div>
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 tracking-tight mb-2">Alpha Discovery Engine</h2>
            <p className="text-slate-600 text-sm">Top-performing Polymarket wallets continuously filtered and scored.</p>
          </div>
          <span className="text-xs text-slate-400 font-mono">Auto-refreshes every 24h</span>
        </div>

        <div className="rounded-3xl overflow-hidden border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_16px_36px_-6px_rgba(0,0,0,0.05)] bg-white">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-black/[0.06] text-[11px] uppercase tracking-wider text-slate-500 bg-slate-50/70 font-semibold">
                  <th className="p-4 sm:px-6 font-semibold">Wallet Address</th>
                  <th className="p-4 font-semibold">Tier</th>
                  <th className="p-4 font-semibold text-right">Win Rate</th>
                  <th className="p-4 font-semibold text-right">Realized P&L</th>
                  <th className="p-4 sm:px-6 font-semibold text-right">Trades / Day</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-black/[0.04]">
                {loading ? (
                  Array.from({ length: 4 }).map((_, i) => (
                    <tr key={i}>
                      <td className="p-4 sm:px-6"><Skeleton className="h-4 w-28" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-20" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-12 ml-auto" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-16 ml-auto" /></td>
                      <td className="p-4 sm:px-6"><Skeleton className="h-4 w-8 ml-auto" /></td>
                    </tr>
                  ))
                ) : wallets.length > 0 ? (
                  wallets.map((wallet) => (
                    <tr key={wallet.address} className="hover:bg-slate-50/80 transition-colors group">
                      <td className="p-4 sm:px-6 font-mono text-xs text-slate-800 font-semibold group-hover:text-black transition-colors">
                        {wallet.address.slice(0, 8)}...{wallet.address.slice(-6)}
                      </td>
                      <td className="p-4"><Badge tier={wallet.tier} /></td>
                      <td className="p-4 text-right text-slate-900 font-mono text-sm font-semibold">{formatWinRate(wallet.winRate || 0)}</td>
                      <td className={`p-4 text-right font-mono text-sm font-bold ${(wallet.pnl || 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {(wallet.pnl || 0) >= 0 ? '+' : '-'}${Math.abs(wallet.pnl || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="p-4 sm:px-6 text-right font-mono text-sm text-slate-600 font-medium">{(wallet.tradesPerDay || 0).toFixed(1)}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="p-16 text-center text-slate-400 text-sm">
                      Discovery scan active. Top wallets will appear once analysis is computed.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}
