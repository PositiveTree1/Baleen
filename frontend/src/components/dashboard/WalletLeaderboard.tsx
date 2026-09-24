'use client';
import { useEffect, useState, useMemo } from 'react';
import { reEvaluateWallets, fetchDiscoveryProgress, fetchCopiedWhalesStats, CopiedWhaleStat, DiscoveryProgress } from '@/lib/api-client';
import { Wallet, ExecutionLog } from '@/types';
import { RotateCw, Search, ChevronRight } from 'lucide-react';

interface WalletLeaderboardProps {
  userId?: string;
  wallets: Wallet[];
  logs: ExecutionLog[];
  onRefresh?: () => void;
  onSelectWallet: (address: string) => void;
  targetSleeveCount?: number;
}

interface LeaderboardDisplayItem {
  address: string;
  name?: string | null;
  pseudonym?: string | null;
  profileImage?: string | null;
  mirroredPnl?: number | null;
  pnl?: number | null;
  winRate?: number | null;
  tier?: string | null;
  fillsCount?: number;
  wins?: number;
  losses?: number;
  copyRatePct?: number;
  score?: number | null;
  roi?: number | null;
  tradesCopied?: number | null;
  profitFactor?: number | null;
  avgHoldHours?: number | null;
  status?: string | null;
  isCopied?: boolean;
  dormant?: boolean;
  isHft?: boolean;
  tradesPerDay?: number | null;
  unvaluedTradesCount?: number;
  knownPnlUsd?: number | null;
}

export function WalletLeaderboard({ userId, wallets, logs, onRefresh, onSelectWallet, targetSleeveCount = 5 }: WalletLeaderboardProps) {
  const [copiedStats, setCopiedStats] = useState<CopiedWhaleStat[]>([]);
  const [loading, setLoading] = useState(wallets.length === 0);
  const [evaluating, setEvaluating] = useState(false);
  const [, setProgress] = useState<DiscoveryProgress | null>(null);
  const [search, setSearch] = useState('');
  const [tab, setTab] = useState<'copied' | 'topActive' | 'all'>('copied');

  const topActiveAddresses = useMemo(() => {
    const sorted = [...wallets]
      .filter((w) => w.tier !== 'dormant' && !w.dormant)
      .sort((a, b) => (b.score ?? -Infinity) - (a.score ?? -Infinity));
    return new Set(sorted.slice(0, targetSleeveCount).map((w) => (w.address || '').toLowerCase()));
  }, [wallets, targetSleeveCount]);

  const load = async () => {
    if (typeof document !== 'undefined' && document.hidden) return;
    const copiedData = await fetchCopiedWhalesStats(userId);
    if (Array.isArray(copiedData) && copiedData.length > 0) setCopiedStats(copiedData);
    setLoading(false);
    onRefresh?.();
  };

  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      if (typeof document !== 'undefined' && document.hidden) return;
      const copiedData = await fetchCopiedWhalesStats(userId);
      if (!isMounted) return;
      if (Array.isArray(copiedData) && copiedData.length > 0) setCopiedStats(copiedData);
      setLoading(false);
    };

    void fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [userId]);

  useEffect(() => {
    if (wallets.length > 0) setLoading(false);
  }, [wallets.length]);

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

  // Compute mirrored PnL per whale (prioritize all-time database aggregation)
  const copiedWhalesWithPnL = useMemo(() => {
    if (copiedStats && copiedStats.length > 0) {
      return copiedStats.map((c) => ({
        address: c.address,
        name: c.name || c.pseudonym || `${c.address.slice(0, 6)}...${c.address.slice(-4)}`,
        pseudonym: c.pseudonym,
        profileImage: c.profileImage,
        mirroredPnl: c.mirroredPnl ?? c.netPnl ?? null,
        fillsCount: c.fillsCount ?? c.tradesCopied ?? 0,
        wins: c.wins,
        losses: c.losses,
        unvaluedTradesCount: c.unvaluedTradesCount ?? 0,
        knownPnlUsd: c.knownPnlUsd ?? null,
        tier: c.tier || 'standard',
        copyRatePct: c.copyRatePct ?? 100,
      })).sort((a, b) => (b.mirroredPnl ?? -Infinity) - (a.mirroredPnl ?? -Infinity));
    }

    const map = new Map<string, {
      address: string;
      name: string;
      mirroredPnl: number | null;
      fillsCount: number;
      wins: number;
      losses: number;
      tier: string;
      unvaluedTradesCount: number;
    }>();

    logs.forEach((l) => {
      const addr = (l.walletAddress || '').toLowerCase();
      if (!addr) return;
      if (!map.has(addr)) {
        map.set(addr, {
          address: l.walletAddress,
          name: l.whaleName || l.whalePseudonym || `${l.walletAddress.slice(0, 6)}...${l.walletAddress.slice(-4)}`,
          mirroredPnl: null,
          fillsCount: 0,
          wins: 0,
          losses: 0,
          tier: l.whaleTier || 'standard',
          unvaluedTradesCount: 0,
        });
      }
      const item = map.get(addr)!;
      item.fillsCount += 1;
      if (l.pnl == null) {
        item.unvaluedTradesCount += 1;
      } else {
        item.mirroredPnl = (item.mirroredPnl ?? 0) + l.pnl;
        if (l.pnl > 0) item.wins += 1;
        else if (l.pnl < 0) item.losses += 1;
      }
    });

    return Array.from(map.values()).sort((a, b) => (b.mirroredPnl ?? -Infinity) - (a.mirroredPnl ?? -Infinity));
  }, [copiedStats, logs]);

  const filteredWallets = wallets.filter((w) => {
    if (search && !w.address.toLowerCase().includes(search.toLowerCase()) && !(w.name || '').toLowerCase().includes(search.toLowerCase())) return false;
    if (tab === 'topActive') return topActiveAddresses.has((w.address || '').toLowerCase());
    return true;
  });

  const filteredCopied = copiedWhalesWithPnL.filter((c) => {
    if (search && !c.address.toLowerCase().includes(search.toLowerCase()) && !(c.name || '').toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const displayList: LeaderboardDisplayItem[] = tab === 'copied' ? filteredCopied : filteredWallets;

  return (
    <div className="glass-card rounded-[28px] p-5 sm:p-6 flex flex-col h-[480px] space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-slate-950 dark:text-white tracking-tight">Verified Wallets</h3>
          <p className="text-xs text-slate-500 dark:text-[#8E8F99]">The same evidence-qualified candidates used by automatic paper copying</p>
        </div>
        <button
          onClick={handleReevaluate}
          disabled={evaluating}
          aria-label={evaluating ? "Evaluating whales..." : "Scan whales"}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#f0f7fd] hover:bg-[#e2f0fb] border border-[#d4e5f5] text-slate-700 hover:text-sky-600 text-xs font-semibold transition-all cursor-pointer disabled:opacity-50"
        >
          <RotateCw size={12} className={evaluating ? "animate-spin text-sky-500" : ""} />
          <span>{evaluating ? "Evaluating..." : "Scan Whales"}</span>
        </button>
      </div>

      {/* Search & Tabs */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search address or pseudonym..."
            aria-label="Search address or pseudonym"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-slate-50/80 border border-slate-200 rounded-full text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-400"
          />
        </div>
        <div className="flex rounded-full bg-slate-100/90 p-1 border border-slate-200/80 text-[11px] font-bold justify-between sm:justify-start shrink-0">
          <button
            onClick={() => setTab('copied')}
            className={`flex-1 sm:flex-initial px-3 py-1.5 rounded-full transition-all text-center ${tab === 'copied' ? 'bg-white text-slate-900 shadow-xs border border-sky-100 font-bold' : 'text-slate-500 hover:text-slate-800'}`}
          >
            Copied
          </button>
          <button
            onClick={() => setTab('topActive')}
            className={`flex-1 sm:flex-initial px-3 py-1.5 rounded-full transition-all text-center ${tab === 'topActive' ? 'bg-white text-slate-900 shadow-xs border border-sky-100 font-bold' : 'text-slate-500 hover:text-slate-800'}`}
          >
            Top {Math.min(targetSleeveCount, wallets.length)} Active
          </button>
          <button
            onClick={() => setTab('all')}
            className={`flex-1 sm:flex-initial px-3 py-1.5 rounded-full transition-all text-center ${tab === 'all' ? 'bg-white text-slate-900 shadow-xs border border-sky-100 font-bold' : 'text-slate-500 hover:text-slate-800'}`}
          >
            All Qualified
          </button>
        </div>
      </div>

      {/* Whales List (Revolut Contact/Sheet style) */}
      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 divide-y divide-black/[0.04] dark:divide-white/5">
        {loading ? (
          <div className="space-y-3 pt-1">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="flex items-center justify-between p-2">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full animate-shimmer shrink-0" />
                  <div className="space-y-1.5">
                    <div className="w-32 h-3.5 rounded-md animate-shimmer" />
                    <div className="w-24 h-2.5 rounded-md animate-shimmer" />
                  </div>
                </div>
                <div className="space-y-1.5 text-right flex flex-col items-end">
                  <div className="w-16 h-3.5 rounded-md animate-shimmer" />
                  <div className="w-12 h-2.5 rounded-md animate-shimmer" />
                </div>
              </div>
            ))}
          </div>
        ) : displayList.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-slate-400 dark:text-[#8E8F99] text-xs">
            <span>No whales found</span>
          </div>
        ) : (
          displayList.map((w: LeaderboardDisplayItem) => {
            const name = w.name || w.pseudonym || `${w.address.slice(0, 6)}...${w.address.slice(-4)}`;
            const isCopiedTab = (tab === 'copied');
            const pnl = isCopiedTab ? w.mirroredPnl : w.pnl;
            const winRate = w.winRate;
            const isGold = (w.tier === 'gold_sniper');
            const fillsCount = w.fillsCount ?? 0;
            const isTopActive = topActiveAddresses.has((w.address || '').toLowerCase());

            return (
              <div
                key={w.address}
                role="button"
                tabIndex={0}
                aria-label={`View wallet details for ${name}`}
                onClick={() => onSelectWallet(w.address)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectWallet(w.address);
                  }
                }}
                className={`flex items-center justify-between p-2.5 rounded-2xl hover:bg-white/60 dark:hover:bg-white/[0.04] border border-transparent hover:border-sky-100/60 dark:hover:border-white/5 transition-all cursor-pointer group focus:outline-none focus:ring-1 focus:ring-indigo-500/40 ${
                  !isCopiedTab && !isTopActive ? 'opacity-40 hover:opacity-90 grayscale-[35%]' : 'opacity-100'
                }`}
              >
                {/* Left: Circular Avatar & Name */}
                <div className="flex items-center gap-3 min-w-0">
                  <div className="relative shrink-0">
                    <img 
                      src={w.profileImage || `https://api.dicebear.com/7.x/identicon/svg?seed=${w.address || name}`} 
                      alt="" 
                      className="w-10 h-10 rounded-full object-cover border border-black/10 dark:border-white/10 bg-slate-100 dark:bg-[#1C1D22]" 
                    />
                    {isGold && (
                      <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 rounded-full bg-amber-400 border-2 border-white dark:border-[#16171B] shadow-2xs" />
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
                      {!isCopiedTab && (
                        isTopActive ? (
                          <span className="text-[9px] bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20 px-1.5 py-0.2 rounded-full font-bold">
                            Top {targetSleeveCount} Active
                          </span>
                        ) : (
                          <span className="text-[9px] bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-[#8E8F99] border border-black/5 dark:border-white/5 px-1.5 py-0.2 rounded-full font-semibold">
                            Bench
                          </span>
                        )
                      )}
                    </div>
                    <span className="text-[11px] text-slate-500 dark:text-[#8E8F99] font-mono block truncate">
                      {isCopiedTab
                        ? `${fillsCount} Fills • Active Basket${(w.unvaluedTradesCount ?? 0) > 0 ? ` • ${w.unvaluedTradesCount} Unavailable` : ''}`
                        : `${winRate == null ? 'Unavailable' : `${formatWinRate(winRate)} Win Rate`}${fillsCount > 0 ? ` • ${fillsCount} Fills` : ''}`}
                    </span>
                  </div>
                </div>

                {/* Right: Net PnL & Arrow */}
                <div className="flex items-center gap-2 shrink-0">
                  <div className="text-right">
                    <div className={`text-xs font-bold font-mono ${pnl == null ? 'text-slate-400 dark:text-[#8E8F99]' : pnl >= 0 ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                      {pnl == null ? 'Unavailable' : `${pnl >= 0 ? '+' : '-'}$${Math.abs(pnl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                    </div>
                    <span className="text-[10px] text-slate-400 dark:text-[#8E8F99]">
                      {isCopiedTab ? 'Copied Paper PnL' : 'Source Wallet PnL'}
                    </span>
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
