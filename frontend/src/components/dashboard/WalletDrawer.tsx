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

  return (
    <AnimatePresence>
      {address && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-baleen-charcoal border-l border-white/10 shadow-2xl overflow-y-auto"
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-8">
                <h2 className="text-xl font-semibold text-baleen-white">Wallet Profile</h2>
                <button onClick={onClose} className="p-2 text-baleen-muted hover:text-baleen-white hover:bg-white/10 rounded-full transition-colors">
                  <X size={20} />
                </button>
              </div>

              {loading ? (
                <div className="space-y-6">
                  <Skeleton className="h-8 w-3/4" />
                  <Skeleton className="h-4 w-1/4" />
                  <div className="grid grid-cols-2 gap-4">
                    <Skeleton className="h-20 w-full" />
                    <Skeleton className="h-20 w-full" />
                  </div>
                  <Skeleton className="h-48 w-full" />
                </div>
              ) : wallet ? (
                <div className="space-y-8">
                  {/* Header */}
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-2xl font-mono text-baleen-cyan break-all">
                        {wallet.address}
                      </h3>
                      <a href={`https://polymarket.com/profile/${wallet.address}`} target="_blank" rel="noreferrer" className="text-baleen-muted hover:text-baleen-white">
                        <ExternalLink size={16} />
                      </a>
                    </div>
                    <div className="flex gap-2 items-center mt-3">
                      <Badge tier={wallet.tier} />
                      {wallet.aiStyleTag && (
                        <span className="px-2 py-1 text-xs bg-baleen-blue/10 text-baleen-blue rounded border border-baleen-blue/20">
                          {wallet.aiStyleTag}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* AI Summary */}
                  <div className="p-4 bg-white/5 border border-white/5 rounded-xl">
                    <h4 className="text-sm font-medium text-baleen-muted mb-2 uppercase tracking-wider">AI Analysis</h4>
                    <p className="text-sm text-baleen-white leading-relaxed">
                      {wallet.aiSummary || 'Analysis pending... The AI engine processes new wallets within 24 hours of indexing.'}
                    </p>
                  </div>

                  {/* Stats Grid */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-white/5 rounded-xl">
                      <div className="text-xs text-baleen-muted mb-1">Win Rate</div>
                      <div className="text-xl font-semibold text-baleen-white">{(wallet.winRate * 100).toFixed(1)}%</div>
                    </div>
                    <div className="p-4 bg-white/5 rounded-xl">
                      <div className="text-xs text-baleen-muted mb-1">Total P&L</div>
                      <div className={`text-xl font-semibold ${wallet.pnl >= 0 ? 'text-baleen-green' : 'text-baleen-red'}`}>
                        {wallet.pnl >= 0 ? '+' : '-'}${Math.abs(wallet.pnl).toLocaleString()}
                      </div>
                    </div>
                    <div className="p-4 bg-white/5 rounded-xl">
                      <div className="text-xs text-baleen-muted mb-1">Max Drawdown</div>
                      <div className="text-xl font-semibold text-baleen-white">{(wallet.maxDrawdown * 100).toFixed(1)}%</div>
                    </div>
                    <div className="p-4 bg-white/5 rounded-xl">
                      <div className="text-xs text-baleen-muted mb-1">Trades / Day</div>
                      <div className="text-xl font-semibold text-baleen-white">{wallet.tradesPerDay.toFixed(1)}</div>
                    </div>
                  </div>

                  {/* Score Chart */}
                  <div>
                    <h4 className="text-sm font-medium text-baleen-muted mb-4 uppercase tracking-wider">Score History</h4>
                    <div className="h-48">
                      <ScoreHistoryChart data={wallet.scoreHistory} />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center text-baleen-muted py-12">Wallet data not found.</div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
