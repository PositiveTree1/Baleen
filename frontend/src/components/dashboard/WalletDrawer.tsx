'use client';
import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState } from 'react';
import { fetchWallet } from '@/lib/api-client';
import { WalletDetail } from '@/types';
import { X, ExternalLink } from 'lucide-react';
import { Badge } from '../ui/Badge';
import { Skeleton } from '../ui/Skeleton';
import { ScoreHistoryChart } from '../charts/ScoreHistoryChart';

interface WalletDrawerProps {
  address: string | null;
  onClose: () => void;
}

export function WalletDrawer({ address, onClose }: WalletDrawerProps) {
  const [wallet, setWallet] = useState<WalletDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!address) return;
    let mounted = true;
    setLoading(true);
    fetchWallet(address).then(data => {
      if (mounted) {
        setWallet(data);
        setLoading(false);
      }
    });
    return () => { mounted = false; };
  }, [address]);

  const formatPct = (val: number) => {
    const num = val > 1 ? val : val * 100;
    return `${num.toFixed(1)}%`;
  };

  return (
    <AnimatePresence>
      {address && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-md"
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-zinc-950/95 border-l border-white/[0.08] shadow-2xl backdrop-blur-2xl overflow-y-auto"
          >
            <div className="p-8">
              <div className="flex items-center justify-between mb-8 pb-4 border-b border-white/[0.06]">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <h2 className="text-base font-semibold text-white tracking-tight">Whale Audit Profile</h2>
                </div>
                <button 
                  onClick={onClose} 
                  className="p-1.5 text-zinc-400 hover:text-white hover:bg-white/[0.08] rounded-full transition-colors cursor-pointer"
                >
                  <X size={18} />
                </button>
              </div>

              {loading ? (
                <div className="space-y-6">
                  <Skeleton className="h-7 w-3/4" />
                  <Skeleton className="h-4 w-1/3" />
                  <div className="grid grid-cols-2 gap-4">
                    <Skeleton className="h-24 w-full rounded-2xl" />
                    <Skeleton className="h-24 w-full rounded-2xl" />
                  </div>
                  <Skeleton className="h-48 w-full rounded-2xl" />
                </div>
              ) : wallet ? (
                <div className="space-y-8">
                  {/* Address & Links */}
                  <div>
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-sm font-mono text-white break-all bg-white/[0.04] p-3 rounded-2xl border border-white/[0.06] flex-1">
                        {wallet.address}
                      </span>
                      <a 
                        href={`https://polymarket.com/profile/${wallet.address}`} 
                        target="_blank" 
                        rel="noreferrer" 
                        className="p-3 bg-white/[0.06] hover:bg-white/[0.12] rounded-2xl border border-white/[0.08] text-zinc-300 hover:text-white transition-colors"
                        title="View on Polymarket"
                      >
                        <ExternalLink size={16} />
                      </a>
                    </div>
                    <div className="flex gap-2 items-center">
                      <Badge tier={wallet.tier} />
                      {wallet.aiStyleTag && (
                        <span className="px-2.5 py-0.5 text-[11px] font-medium bg-blue-500/10 text-blue-400 rounded-full border border-blue-500/20">
                          {wallet.aiStyleTag}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* AI Plain English Summary */}
                  <div className="p-5 bg-zinc-900/40 border border-white/[0.08] rounded-3xl backdrop-blur-xl">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                      <h4 className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">AI Behavioral Analysis</h4>
                    </div>
                    <p className="text-sm text-zinc-200 leading-relaxed font-normal">
                      {wallet.aiSummary || 'Analysis generated automatically via Groq AI based on verified on-chain trading behavior.'}
                    </p>
                  </div>

                  {/* Stats Grid */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-4 bg-zinc-900/40 border border-white/[0.06] rounded-2xl">
                      <div className="text-[11px] text-zinc-500 mb-1">Win Rate</div>
                      <div className="text-2xl font-bold text-white font-mono">{formatPct(wallet.winRate || 0)}</div>
                    </div>
                    <div className="p-4 bg-zinc-900/40 border border-white/[0.06] rounded-2xl">
                      <div className="text-[11px] text-zinc-500 mb-1">Realized PnL</div>
                      <div className={`text-2xl font-bold font-mono ${(wallet.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {(wallet.pnl || 0) >= 0 ? '+' : '-'}${Math.abs(wallet.pnl || 0).toLocaleString()}
                      </div>
                    </div>
                    <div className="p-4 bg-zinc-900/40 border border-white/[0.06] rounded-2xl">
                      <div className="text-[11px] text-zinc-500 mb-1">Max Drawdown</div>
                      <div className="text-2xl font-bold text-zinc-300 font-mono">{formatPct(wallet.maxDrawdown || 0)}</div>
                    </div>
                    <div className="p-4 bg-zinc-900/40 border border-white/[0.06] rounded-2xl">
                      <div className="text-[11px] text-zinc-500 mb-1">Frequency</div>
                      <div className="text-2xl font-bold text-zinc-300 font-mono">{(wallet.tradesPerDay || 0).toFixed(1)} / day</div>
                    </div>
                  </div>

                  {/* Score History Chart */}
                  {wallet.scoreHistory && wallet.scoreHistory.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-zinc-400 mb-3 uppercase tracking-wider">Score Decay History</h4>
                      <div className="h-44 p-4 rounded-3xl bg-zinc-900/40 border border-white/[0.06]">
                        <ScoreHistoryChart data={wallet.scoreHistory} />
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-zinc-500 py-12 text-sm">Wallet details unavailable.</div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
