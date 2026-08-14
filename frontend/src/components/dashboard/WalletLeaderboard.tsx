'use client';
import { useEffect, useState } from 'react';
import { fetchWallets } from '@/lib/api-client';
import { Wallet } from '@/types';
import { Badge } from '../ui/Badge';
import { Skeleton } from '../ui/Skeleton';

interface WalletLeaderboardProps {
  onSelectWallet: (address: string) => void;
}

export function WalletLeaderboard({ onSelectWallet }: WalletLeaderboardProps) {
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const data = await fetchWallets();
      setWallets(data);
      setLoading(false);
    }
    load();
  }, []);

  const formatWinRate = (wr: number) => {
    const val = wr > 1 ? wr : wr * 100;
    return `${val.toFixed(0)}%`;
  };

  return (
    <div className="glass-card rounded-3xl overflow-hidden h-[420px] flex flex-col border border-white/[0.08] shadow-apple bg-zinc-900/40 backdrop-blur-xl">
      <div className="p-4 px-6 border-b border-white/[0.06] bg-white/[0.02] flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white tracking-tight">Active Index Basket</h3>
        <span className="text-[11px] text-zinc-500 font-mono">{wallets.length} tracked</span>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/[0.06] text-[10px] uppercase tracking-wider text-zinc-400 bg-zinc-950/80 sticky top-0 backdrop-blur-md z-10">
              <th className="p-3.5 px-4 font-medium">Wallet</th>
              <th className="p-3.5 font-medium">Tier</th>
              <th className="p-3.5 font-medium text-right">Win Rate</th>
              <th className="p-3.5 px-4 font-medium text-right">PnL</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.03]">
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  <td className="p-3.5 px-4"><Skeleton className="h-3.5 w-16" /></td>
                  <td className="p-3.5"><Skeleton className="h-3.5 w-14" /></td>
                  <td className="p-3.5"><Skeleton className="h-3.5 w-8 ml-auto" /></td>
                  <td className="p-3.5 px-4"><Skeleton className="h-3.5 w-12 ml-auto" /></td>
                </tr>
              ))
            ) : wallets.length > 0 ? (
              wallets.map((wallet) => (
                <tr 
                  key={wallet.address} 
                  onClick={() => onSelectWallet(wallet.address)}
                  className="hover:bg-white/[0.04] transition-colors cursor-pointer group text-xs"
                >
                  <td className="p-3.5 px-4 font-mono text-zinc-300 group-hover:text-white transition-colors">
                    {wallet.address.slice(0, 5)}...{wallet.address.slice(-4)}
                  </td>
                  <td className="p-3.5"><Badge tier={wallet.tier} /></td>
                  <td className="p-3.5 text-right text-zinc-300 font-mono">{formatWinRate(wallet.winRate || 0)}</td>
                  <td className={`p-3.5 px-4 text-right font-mono font-medium ${(wallet.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {(wallet.pnl || 0) >= 0 ? '+' : '-'}${Math.abs(wallet.pnl || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="p-12 text-center text-zinc-500 text-xs">
                  Discovery scan running...
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
