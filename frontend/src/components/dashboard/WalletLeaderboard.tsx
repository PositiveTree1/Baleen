'use client';
import { useEffect, useState } from 'react';
import { fetchWallets, getCachedWallets, reEvaluateWallets, fetchDiscoveryProgress, fetchCopiedWalletStats } from '@/lib/api-client';
import { Wallet } from '@/types';
import { Badge } from '../ui/Badge';
import { Skeleton } from '../ui/Skeleton';
import { RotateCw, Search, DollarSign, TrendingUp, Award } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { formatCompactPnL, formatExactPnL } from '@/lib/formatters';

interface WalletLeaderboardProps {
  userId?: string;
  onSelectWallet: (address: string) => void;
}

export function WalletLeaderboard({ userId, onSelectWallet }: WalletLeaderboardProps) {
  const [wallets, setWallets] = useState<Wallet[]>(() => getCachedWallets() || []);
  const [copiedStats, setCopiedStats] = useState<any[]>([]);
  const [loading, setLoading] = useState(() => (getCachedWallets()?.length || 0) === 0);
  const [evaluating, setEvaluating] = useState(false);
  const [progress, setProgress] = useState<any>(null);
  const [search, setSearch] = useState('');
  const [tab, setTab] = useState<'all' | 'gold' | 'copied'>('copied');

  const load = async () => {
    const [walletsData, copiedData] = await Promise.all([
      fetchWallets(),
      fetchCopiedWalletStats(userId)
    ]);
    if (walletsData && walletsData.length > 0) setWallets(walletsData);
    if (copiedData && copiedData.length > 0) setCopiedStats(copiedData);
    setLoading(false);
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, [userId]);

  const handleReevaluate = async () => {
    setEvaluating(true);
    try {
      reEvaluateWallets();
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

  const filteredWallets = wallets.filter((w) => {
    if (search && !w.address.toLowerCase().includes(search.toLowerCase())) return false;
    if (tab === 'gold') return w.tier === 'gold_sniper';
    return true;
  });

  const filteredCopied = copiedStats.filter((c) => {
    if (search && !c.address.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="rounded-3xl overflow-hidden h-[460px] flex flex-col apple-glass light-refraction relative">
      <div className="p-4 px-6 border-b border-black/[0.06] bg-slate-50/50 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-slate-900 tracking-tight">Active Index Basket</h3>
            <span className="text-[11px] text-slate-500 font-mono font-semibold">
              ({tab === 'copied' ? `${filteredCopied.length} copied` : `${filteredWallets.length} active`})
            </span>
          </div>
          <button
            onClick={handleReevaluate}
            disabled={evaluating}
            className="flex items-center gap-1.5 px-3 py-1 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 border border-black/[0.08] rounded-xl text-xs font-semibold shadow-sm transition-all cursor-pointer disabled:opacity-50"
            title="Re-evaluate all wallets from live Polymarket API"
          >
            <RotateCw size={12} className={evaluating ? "animate-spin text-indigo-600" : ""} />
            <span>{evaluating ? "Evaluating..." : "Re-evaluate"}</span>
          </button>
        </div>

        {/* Search & Tabs */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Filter 0x address..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-7 pr-2.5 py-1 text-xs font-mono bg-white border border-black/[0.08] rounded-xl focus:outline-none focus:border-slate-400"
            />
          </div>
          <div className="flex rounded-xl bg-slate-200/60 p-0.5 border border-black/[0.04] text-[11px] shrink-0">
            <button
              onClick={() => setTab('copied')}
              className={`px-2.5 py-0.5 rounded-lg font-semibold transition-all ${tab === 'copied' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-900'}`}
            >
              Copied Alpha
            </button>
            <button
              onClick={() => setTab('gold')}
              className={`px-2.5 py-0.5 rounded-lg font-semibold transition-all ${tab === 'gold' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'}`}
            >
              Gold
            </button>
            <button
              onClick={() => setTab('all')}
              className={`px-2.5 py-0.5 rounded-lg font-semibold transition-all ${tab === 'all' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'}`}
            >
              All
            </button>
          </div>
        </div>
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
      
      {/* Scrollable Container without horizontal scrollbar */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden">
        {tab === 'copied' ? (
          <table className="w-full text-left border-collapse table-fixed">
            <thead>
              <tr className="border-b border-black/[0.06] text-[10px] uppercase tracking-wider text-slate-500 bg-slate-50/90 sticky top-0 backdrop-blur-md z-10 font-bold">
                <th className="p-3.5 px-4 w-[34%]">Whale Address</th>
                <th className="p-3.5 text-center w-[22%]">Fills</th>
                <th className="p-3.5 text-right w-[22%]">Win Rate</th>
                <th className="p-3.5 px-4 text-right w-[22%]">Copied P&L</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-black/[0.04]">
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td className="p-3.5 px-4"><Skeleton className="h-3.5 w-16" /></td>
                    <td className="p-3.5"><Skeleton className="h-3.5 w-8 mx-auto" /></td>
                    <td className="p-3.5"><Skeleton className="h-3.5 w-8 ml-auto" /></td>
                    <td className="p-3.5 px-4"><Skeleton className="h-3.5 w-12 ml-auto" /></td>
                  </tr>
                ))
              ) : filteredCopied.length > 0 ? (
                filteredCopied.map((item) => {
                  const isProfit = (item.netPnl || 0) >= 0;
                  const wObj = wallets.find(w => w.address.toLowerCase() === item.address.toLowerCase());
                  const displayName = wObj?.name || wObj?.pseudonym;
                  return (
                    <tr 
                      key={item.address} 
                      onClick={() => onSelectWallet(item.address)}
                      className="transition-colors cursor-pointer hover:bg-indigo-50/60 group text-xs"
                    >
                      <td className="p-3.5 px-4 font-mono text-slate-800 font-bold group-hover:text-indigo-600 transition-colors truncate">
                        <div className="flex items-center gap-2">
                          {wObj?.profileImage ? (
                            <img 
                              src={wObj.profileImage} 
                              alt="" 
                              className="w-5 h-5 rounded-full object-cover border border-black/10 shrink-0 shadow-2xs" 
                            />
                          ) : (
                            <div className="w-5 h-5 rounded-full bg-slate-100 border border-black/10 flex items-center justify-center text-[9px] font-bold text-slate-600 shrink-0">
                              {item.address.slice(2, 4).toUpperCase()}
                            </div>
                          )}
                          <div className="truncate">
                            {displayName ? (
                              <div className="font-sans font-bold text-slate-900 text-xs truncate">
                                {displayName}
                              </div>
                            ) : null}
                            <div className="text-[10px] text-slate-500 font-mono">
                              {item.address.slice(0, 6)}...{item.address.slice(-4)}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="p-3.5 text-center font-mono text-slate-600 font-semibold">
                        <span className="px-2 py-0.5 rounded-full bg-slate-100 text-[11px] font-bold">
                          {item.tradesCopied}
                        </span>
                      </td>
                      <td className="p-3.5 text-right text-slate-800 font-mono font-semibold">
                        {item.winRateCopied.toFixed(0)}%
                      </td>
                      <td 
                        className={`p-3.5 px-4 text-right font-mono font-bold truncate tabular-nums tracking-tight ${isProfit ? 'text-emerald-600' : 'text-rose-600'}`}
                        title={formatExactPnL(item.netPnl)}
                      >
                        {formatCompactPnL(item.netPnl)}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={4} className="p-10 text-center text-slate-400 text-xs font-medium">
                    No copied trades executed yet. Mirrored fills will appear here.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        ) : (
          <table className="w-full text-left border-collapse table-fixed">
            <thead>
              <tr className="border-b border-black/[0.06] text-[10px] uppercase tracking-wider text-slate-500 bg-slate-50/90 sticky top-0 backdrop-blur-md z-10 font-bold">
                <th className="p-3.5 px-4 w-[34%]">Wallet</th>
                <th className="p-3.5 w-[22%]">Tier</th>
                <th className="p-3.5 text-right w-[22%]">Win Rate</th>
                <th className="p-3.5 px-4 text-right w-[22%]">Total PnL</th>
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
              ) : filteredWallets.length > 0 ? (
                filteredWallets.map((wallet) => {
                  const isGold = wallet.tier === 'gold_sniper';
                  const displayName = wallet.name || wallet.pseudonym;
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
                      <td className="p-3.5 px-4 font-mono text-slate-800 font-bold group-hover:text-indigo-600 transition-colors truncate">
                        <div className="flex items-center gap-2">
                          {wallet.profileImage ? (
                            <img 
                              src={wallet.profileImage} 
                              alt="Avatar" 
                              className="w-5 h-5 rounded-full object-cover border border-black/10 shrink-0" 
                            />
                          ) : null}
                          <div className="truncate">
                            {displayName ? (
                              <div className="font-sans font-bold text-slate-900 text-xs truncate">
                                {displayName}
                              </div>
                            ) : null}
                            <div className="text-[10px] text-slate-500 font-mono">
                              {wallet.address.slice(0, 6)}...{wallet.address.slice(-4)}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="p-3.5"><Badge tier={wallet.tier} /></td>
                      <td className="p-3.5 text-right text-slate-800 font-mono font-semibold">{formatWinRate(wallet.winRate || 0)}</td>
                      <td 
                        className={`p-3.5 px-4 text-right font-mono font-bold truncate tabular-nums tracking-tight ${(wallet.pnl || 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}
                        title={formatExactPnL(wallet.pnl)}
                      >
                        {formatCompactPnL(wallet.pnl)}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={4} className="p-12 text-center text-slate-400 text-xs font-medium">
                    {search ? 'No matching wallets.' : 'Discovery scan running...'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
