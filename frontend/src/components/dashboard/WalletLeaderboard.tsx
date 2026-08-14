'use client';
import { useEffect, useState } from 'react';
import { fetchWallets, reEvaluateWallets, fetchDiscoveryProgress } from '@/lib/api-client';
import { Wallet } from '@/types';
import { Badge } from '../ui/Badge';
import { Skeleton } from '../ui/Skeleton';
import { RotateCw, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface WalletLeaderboardProps {
  onSelectWallet: (address: string) => void;
}

export function WalletLeaderboard({ onSelectWallet }: WalletLeaderboardProps) {
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [progress, setProgress] = useState<any>(null);

  const load = async () => {
    const data = await fetchWallets();
    setWallets(data);
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const handleReevaluate = async () => {
    setEvaluating(true);
    try {
      reEvaluateWallets();
      
      // Poll progress every 800ms
      const interval = setInterval(async () => {
        const prog = await fetchDiscoveryProgress();
        if (prog) {
          setProgress(prog);
          if (prog.status === 'completed' || prog.status === 'error') {
            clearInterval(interval);
            setTimeout(() => {
              setEvaluating(false);
              setProgress(null);
              load();
            }, 1000);
          }
        }
      }, 800);
    } catch {
      setEvaluating(false);
    }
  };

  const formatWinRate = (wr: number) => {
    const val = wr > 1 ? wr : wr * 100;
    return `${val.toFixed(0)}%`;
  };

  return (
    <div className="rounded-3xl overflow-hidden h-[420px] flex flex-col border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_12px_28px_-4px_rgba(0,0,0,0.05)] bg-white">
      <div className="p-4 px-6 border-b border-black/[0.06] bg-slate-50/50 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <h3 className="text-sm font-bold text-slate-900 tracking-tight">Active Index Basket</h3>
          <span className="text-[11px] text-slate-500 font-mono font-semibold">({wallets.length} tracked)</span>
        </div>
        <button
          onClick={handleReevaluate}
          disabled={evaluating}
          className="flex items-center gap-1.5 px-3 py-1 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 border border-black/[0.08] rounded-xl text-xs font-semibold shadow-sm transition-all cursor-pointer disabled:opacity-50"
          title="Re-evaluate all wallets from live Polymarket API"
        >
          <RotateCw size={12} className={evaluating ? "animate-spin text-indigo-600" : ""} />
          <span>{evaluating ? "Evaluating..." : "Re-evaluate All"}</span>
        </button>
      </div>

      {/* Live Animated Progress Bar */}
      <AnimatePresence>
        {evaluating && progress && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-indigo-50/80 border-b border-indigo-100 p-3 px-5 text-xs text-indigo-900"
          >
            <div className="flex justify-between items-center mb-1.5 font-medium">
              <span className="truncate max-w-[280px]">{progress.step_description || 'Scanning Polymarket...'}</span>
              <span className="font-mono font-bold">{progress.progress_pct || 0}%</span>
            </div>
            <div className="w-full h-1.5 bg-indigo-200/60 rounded-full overflow-hidden">
              <div 
                className="h-full bg-indigo-600 rounded-full transition-all duration-300"
                style={{ width: `${progress.progress_pct || 5}%` }}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-black/[0.06] text-[10px] uppercase tracking-wider text-slate-500 bg-slate-50/90 sticky top-0 backdrop-blur-md z-10 font-semibold">
              <th className="p-3.5 px-4 font-semibold">Wallet</th>
              <th className="p-3.5 font-semibold">Tier</th>
              <th className="p-3.5 font-semibold text-right">Win Rate</th>
              <th className="p-3.5 px-4 font-semibold text-right">PnL</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-black/[0.04]">
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
              wallets.map((wallet) => {
                const isGold = wallet.tier === 'gold_sniper';
                return (
                  <tr 
                    key={wallet.address} 
                    onClick={() => onSelectWallet(wallet.address)}
                    className={`transition-colors cursor-pointer group text-xs ${
                      isGold 
                        ? 'bg-amber-500/[0.03] hover:bg-amber-500/[0.08]' 
                        : 'hover:bg-slate-50/80'
                    }`}
                  >
                    <td className="p-3.5 px-4 font-mono text-slate-800 font-bold group-hover:text-black transition-colors">
                      {wallet.address.slice(0, 5)}...{wallet.address.slice(-4)}
                    </td>
                    <td className="p-3.5"><Badge tier={wallet.tier} /></td>
                    <td className="p-3.5 text-right text-slate-800 font-mono font-semibold">{formatWinRate(wallet.winRate || 0)}</td>
                    <td className={`p-3.5 px-4 text-right font-mono font-bold ${(wallet.pnl || 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {(wallet.pnl || 0) >= 0 ? '+' : '-'}${Math.abs(wallet.pnl || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={4} className="p-12 text-center text-slate-400 text-xs font-medium">
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
