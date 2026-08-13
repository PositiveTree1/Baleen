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

  return (
    <div className="glass-card rounded-xl overflow-hidden h-[400px] flex flex-col">
      <div className="p-4 border-b border-white/5 bg-white/5">
        <h3 className="font-semibold text-baleen-white">Top Indexed Wallets</h3>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/10 text-xs uppercase text-baleen-muted bg-baleen-obsidian/50 sticky top-0 backdrop-blur-md z-10">
              <th className="p-3 font-medium">Wallet</th>
              <th className="p-3 font-medium">Tier</th>
              <th className="p-3 font-medium text-right">Win Rate</th>
              <th className="p-3 font-medium text-right">P&L</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-white/5">
                  <td className="p-3"><Skeleton className="h-4 w-20" /></td>
                  <td className="p-3"><Skeleton className="h-4 w-16" /></td>
                  <td className="p-3"><Skeleton className="h-4 w-10 ml-auto" /></td>
                  <td className="p-3"><Skeleton className="h-4 w-12 ml-auto" /></td>
                </tr>
              ))
            ) : wallets.length > 0 ? (
              wallets.map((wallet) => (
                <tr 
                  key={wallet.address} 
                  onClick={() => onSelectWallet(wallet.address)}
                  className="border-b border-white/5 hover:bg-white/5 transition-colors cursor-pointer group text-sm"
                >
                  <td className="p-3 font-mono text-baleen-white group-hover:text-baleen-cyan transition-colors">
                    {wallet.address.slice(0, 4)}...{wallet.address.slice(-4)}
                  </td>
                  <td className="p-3"><Badge tier={wallet.tier} /></td>
                  <td className="p-3 text-right text-baleen-white">{(wallet.winRate * 100).toFixed(1)}%</td>
                  <td className={`p-3 text-right font-medium ${wallet.pnl >= 0 ? 'text-baleen-green' : 'text-baleen-red'}`}>
                    {wallet.pnl >= 0 ? '+' : '-'}${Math.abs(wallet.pnl).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="p-8 text-center text-baleen-muted text-sm">
                  No wallets indexed yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
