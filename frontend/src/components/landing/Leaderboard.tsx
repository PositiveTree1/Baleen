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
      const data = await fetchWallets({ limit: '5' });
      setWallets(data);
      setLoading(false);
    }
    load();
  }, []);

  return (
    <section className="py-24 px-6 lg:px-20 bg-baleen-charcoal/30 border-t border-white/5">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-end mb-8">
          <div>
            <h2 className="text-3xl font-bold text-baleen-white mb-2">Alpha Discovery Engine</h2>
            <p className="text-baleen-muted">Top performing wallets indexed in the last 24 hours.</p>
          </div>
        </div>

        <div className="glass-card rounded-xl overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/10 text-xs uppercase text-baleen-muted bg-white/5">
                <th className="p-4 font-medium">Wallet Address</th>
                <th className="p-4 font-medium">Tier</th>
                <th className="p-4 font-medium text-right">Win Rate</th>
                <th className="p-4 font-medium text-right">P&L</th>
                <th className="p-4 font-medium text-right">Trades/Day</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <tr key={i} className="border-b border-white/5">
                    <td className="p-4"><Skeleton className="h-5 w-32" /></td>
                    <td className="p-4"><Skeleton className="h-5 w-20" /></td>
                    <td className="p-4"><Skeleton className="h-5 w-12 ml-auto" /></td>
                    <td className="p-4"><Skeleton className="h-5 w-16 ml-auto" /></td>
                    <td className="p-4"><Skeleton className="h-5 w-8 ml-auto" /></td>
                  </tr>
                ))
              ) : wallets.length > 0 ? (
                wallets.map((wallet) => (
                  <tr key={wallet.address} className="border-b border-white/5 hover:bg-white/5 transition-colors group">
                    <td className="p-4 font-mono text-sm text-baleen-white group-hover:text-baleen-cyan transition-colors">
                      {wallet.address.slice(0, 6)}...{wallet.address.slice(-4)}
                    </td>
                    <td className="p-4"><Badge tier={wallet.tier} /></td>
                    <td className="p-4 text-right text-baleen-white">{(wallet.winRate * 100).toFixed(1)}%</td>
                    <td className={`p-4 text-right font-medium ${wallet.pnl >= 0 ? 'text-baleen-green' : 'text-baleen-red'}`}>
                      {wallet.pnl >= 0 ? '+' : '-'}${Math.abs(wallet.pnl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="p-4 text-right text-baleen-muted">{wallet.tradesPerDay.toFixed(1)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="p-12 text-center text-baleen-muted">
                    No wallets scored yet. The discovery engine runs every 6 hours.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
