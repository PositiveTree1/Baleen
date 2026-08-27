'use client';
import { useEffect, useState } from 'react';
import { fetchWallets, getCachedWallets, reEvaluateWallets, fetchDiscoveryProgress, fetchCopiedWalletStats } from '@/lib/api-client';
import { Wallet } from '@/types';
import { RotateCw, Search, ChevronRight } from 'lucide-react';

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
  const [tab, setTab] = useState<'copied' | 'all' | 'gold'>('copied');

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
    if (search && !w.address.toLowerCase().includes(search.toLowerCase()) && !(w.name || '').toLowerCase().includes(search.toLowerCase())) return false;
    if (tab === 'gold') return w.tier === 'gold_sniper';
    return true;
  });

  const filteredCopied = copiedStats.filter((c) => {
    if (search && !c.address.toLowerCase().includes(search.toLowerCase()) && !(c.name || '').toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const displayList = tab === 'copied' ? (filteredCopied.length > 0 ? filteredCopied : filteredWallets) : filteredWallets;

  return (
    <div className="revolut-card rounded-[26px] p-5 sm:p-6 flex flex-col h-[480px] space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-slate-950 dark:text-white tracking-tight">Active Index Whales</h3>
          <p className="text-xs text-slate-500 dark:text-[#8E8F99]">Mirrored Polymarket accounts</p>
        </div>
        <button
          onClick={handleReevaluate}
          disabled={evaluating}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] text-slate-800 dark:text-white text-xs font-semibold rounded-full border border-black/[0.04] dark:border-white/10 transition-all cursor-pointer disabled:opacity-50"
        >
          <RotateCw size={12} className={evaluating ? "animate-spin text-[#00D09C]" : ""} />
          <span>{evaluating ? "Evaluating..." : "Scan Whales"}</span>
        </button>
      </div>

      {/* Search & Tabs */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-[#8E8F99]" />
          <input
            type="text"
            placeholder="Search address or pseudonym..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-[#F1F3F5] dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 rounded-full text-xs text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-[#8E8F99] focus:outline-none focus:border-black/20 dark:focus:border-white/20"
          />
        </div>
        <div className="flex rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] p-0.5 border border-black/[0.04] dark:border-white/5 text-[11px] font-bold">
          <button
            onClick={() => setTab('copied')}
            className={`px-3 py-1 rounded-full transition-all ${tab === 'copied' ? 'bg-white dark:bg-[#2C2D35] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99]'}`}
          >
            Copied
          </button>
          <button
            onClick={() => setTab('gold')}
            className={`px-3 py-1 rounded-full transition-all ${tab === 'gold' ? 'bg-white dark:bg-[#2C2D35] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99]'}`}
          >
            Gold
          </button>
          <button
            onClick={() => setTab('all')}
            className={`px-3 py-1 rounded-full transition-all ${tab === 'all' ? 'bg-white dark:bg-[#2C2D35] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99]'}`}
          >
            All
          </button>
        </div>
      </div>

      {/* Whales List (Revolut Contact/Sheet style) */}
      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 divide-y divide-black/[0.04] dark:divide-white/5">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-48 text-slate-400 dark:text-[#8E8F99] text-xs">
            <RotateCw size={20} className="animate-spin mb-2 text-[#00D09C]" />
            <span>Synchronizing Whale Basket...</span>
          </div>
        ) : displayList.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-slate-400 dark:text-[#8E8F99] text-xs">
            <span>No whales found</span>
          </div>
        ) : (
          displayList.map((w: any) => {
            const name = w.name || w.pseudonym || `${w.address.slice(0, 6)}...${w.address.slice(-4)}`;
            const pnl = w.allTimePnl ?? w.all_time_pnl_usd ?? w.totalPnl ?? 0.0;
            const winRate = w.winRatePct ?? w.win_rate_pct ?? w.winRate ?? 70.0;
            const isGold = (w.tier === 'gold_sniper');
            const positions = w.activePositionsCount ?? w.positions_count ?? 12;

            return (
              <div
                key={w.address}
                onClick={() => onSelectWallet(w.address)}
                className="pt-2 flex items-center justify-between p-2 rounded-2xl hover:bg-slate-50 dark:hover:bg-[#1C1D22] transition-colors cursor-pointer group"
              >
                {/* Left: Circular Avatar & Name */}
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-full bg-slate-200 dark:bg-[#2C2D35] border border-black/[0.04] dark:border-white/10 flex items-center justify-center font-bold text-sm text-slate-800 dark:text-white shrink-0 uppercase relative">
                    {name.slice(0, 2)}
                    {isGold && (
                      <span className="absolute -top-0.5 -right-0.5 w-3 h-3 rounded-full bg-amber-400 border-2 border-white dark:border-[#16171B]" />
                    )}
                  </div>

                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-slate-900 dark:text-white truncate">{name}</span>
                      {isGold && (
                        <span className="text-[9px] bg-amber-50 dark:bg-amber-400/10 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-400/20 px-1.5 py-0.2 rounded-full font-bold">
                          Gold
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-slate-500 dark:text-[#8E8F99] font-mono block truncate">
                      {formatWinRate(winRate)} Win Rate • {positions} Open
                    </span>
                  </div>
                </div>

                {/* Right: Net PnL & Arrow */}
                <div className="flex items-center gap-2 shrink-0">
                  <div className="text-right">
                    <div className={`text-xs font-bold font-mono ${pnl >= 0 ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                      {pnl >= 0 ? '+' : ''}${Math.abs(pnl).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </div>
                    <span className="text-[10px] text-slate-400 dark:text-[#8E8F99]">Mirrored</span>
                  </div>
                  <ChevronRight size={14} className="text-slate-400 dark:text-[#8E8F99] group-hover:text-slate-900 dark:group-hover:text-white transition-colors" />
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
