'use client';
import { useEffect, useState } from 'react';
import { fetchWallets } from '@/lib/api-client';
import { Wallet } from '@/types';
import { Badge } from '../ui/Badge';
import { Skeleton } from '../ui/Skeleton';
import { WalletDrawer } from '../dashboard/WalletDrawer';
import { Search, Sparkles, Filter, TrendingUp, Trophy, ArrowUpDown, ChevronRight, Copy, Check } from 'lucide-react';

export function Leaderboard() {
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWallet, setSelectedWallet] = useState<string | null>(null);
  const [filterTier, setFilterTier] = useState<'all' | 'gold' | 'high_wr' | 'high_pnl'>('all');
  const [search, setSearch] = useState('');
  const [sortField, setSortField] = useState<'score' | 'winRate' | 'pnl' | 'tradesPerDay'>('pnl');
  const [sortAsc, setSortAsc] = useState(false);
  const [copiedAddr, setCopiedAddr] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const data = await fetchWallets({ limit: '50' });
      setWallets(data);
      setLoading(false);
    }
    load();
  }, []);

  const handleCopy = (addr: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(addr);
    setCopiedAddr(addr);
    setTimeout(() => setCopiedAddr(null), 2000);
  };

  const formatWinRate = (wr: number) => {
    const val = wr > 1 ? wr : wr * 100;
    return `${val.toFixed(1)}%`;
  };

  const handleSort = (field: 'score' | 'winRate' | 'pnl' | 'tradesPerDay') => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const filteredWallets = wallets
    .filter((w) => {
      if (search && !w.address.toLowerCase().includes(search.toLowerCase())) return false;
      if (filterTier === 'gold') return w.tier === 'gold_sniper';
      if (filterTier === 'high_wr') return (w.winRate || 0) >= (w.winRate && w.winRate > 1 ? 80 : 0.8);
      if (filterTier === 'high_pnl') return (w.pnl || 0) >= 100000;
      return true;
    })
    .sort((a, b) => {
      const valA = (a[sortField] ?? 0) as number;
      const valB = (b[sortField] ?? 0) as number;
      return sortAsc ? valA - valB : valB - valA;
    });

  return (
    <section id="leaderboard" className="py-24 px-6 lg:px-20 border-t border-black/[0.06] bg-[#F8F9FB]">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 shadow-sm mb-3">
              <Trophy size={14} className="text-emerald-600" />
              <span>Verified Polymarket On-Chain Ledger</span>
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold text-slate-950 tracking-tight mb-2">
              Alpha Discovery Basket
            </h2>
            <p className="text-slate-600 text-sm max-w-xl">
              Live quantitative leaderboard of audited whales. Click any address to inspect complete P&amp;L history, AI behavioral style tag, and win rate confidence bounds.
            </p>
          </div>

          {/* Search & Filter Controls */}
          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            <div className="relative flex-1 md:w-56">
              <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search 0x address..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3.5 py-2 text-xs font-mono bg-white border border-black/[0.08] rounded-2xl focus:outline-none focus:border-slate-400 shadow-sm"
              />
            </div>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex flex-wrap items-center gap-2 mb-6">
          {[
            { id: 'all', label: 'All Whales' },
            { id: 'gold', label: '⭐ Gold Snipers (85%+ WR)' },
            { id: 'high_wr', label: '🎯 High Win Rate' },
            { id: 'high_pnl', label: '💰 $100k+ Net Profit' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilterTier(tab.id as any)}
              className={`text-xs px-4 py-2 rounded-xl font-semibold transition-all cursor-pointer border ${
                filterTier === tab.id
                  ? 'bg-slate-900 text-white border-slate-900 shadow-sm'
                  : 'bg-white text-slate-600 border-black/[0.06] hover:bg-slate-50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Table Container */}
        <div className="rounded-3xl overflow-hidden border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_16px_36px_-6px_rgba(0,0,0,0.05)] bg-white">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-black/[0.06] text-[10px] uppercase tracking-wider text-slate-500 bg-slate-50/90 font-bold">
                  <th className="p-4 sm:px-6">Whale Address</th>
                  <th className="p-4">Tier &amp; Style</th>
                  <th 
                    onClick={() => handleSort('score')} 
                    className="p-4 text-right cursor-pointer hover:text-slate-900 transition-colors"
                  >
                    <span className="inline-flex items-center gap-1">
                      Score <ArrowUpDown size={11} />
                    </span>
                  </th>
                  <th 
                    onClick={() => handleSort('winRate')} 
                    className="p-4 text-right cursor-pointer hover:text-slate-900 transition-colors"
                  >
                    <span className="inline-flex items-center gap-1">
                      Win Rate <ArrowUpDown size={11} />
                    </span>
                  </th>
                  <th 
                    onClick={() => handleSort('pnl')} 
                    className="p-4 text-right cursor-pointer hover:text-slate-900 transition-colors"
                  >
                    <span className="inline-flex items-center gap-1">
                      Realized P&amp;L <ArrowUpDown size={11} />
                    </span>
                  </th>
                  <th 
                    onClick={() => handleSort('tradesPerDay')} 
                    className="p-4 sm:px-6 text-right cursor-pointer hover:text-slate-900 transition-colors"
                  >
                    <span className="inline-flex items-center gap-1">
                      Trades / Day <ArrowUpDown size={11} />
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-black/[0.04]">
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      <td className="p-4 sm:px-6"><Skeleton className="h-4 w-28" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-20" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-12 ml-auto" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-16 ml-auto" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-20 ml-auto" /></td>
                      <td className="p-4 sm:px-6"><Skeleton className="h-4 w-8 ml-auto" /></td>
                    </tr>
                  ))
                ) : filteredWallets.length > 0 ? (
                  filteredWallets.map((wallet) => {
                    const isGold = wallet.tier === 'gold_sniper';
                    const isCopied = copiedAddr === wallet.address;

                    return (
                      <tr 
                        key={wallet.address} 
                        onClick={() => setSelectedWallet(wallet.address)}
                        className={`transition-colors cursor-pointer group text-xs ${
                          isGold ? 'hover:bg-amber-500/[0.05]' : 'hover:bg-indigo-50/50'
                        }`}
                      >
                        <td className="p-4 sm:px-6 font-mono font-bold text-slate-900 flex items-center gap-2">
                          <span className="group-hover:text-indigo-600 transition-colors">
                            {wallet.address.slice(0, 6)}...{wallet.address.slice(-4)}
                          </span>
                          <button
                            onClick={(e) => handleCopy(wallet.address, e)}
                            className="p-1 text-slate-400 hover:text-slate-800 rounded transition-colors"
                            title="Copy full address"
                          >
                            {isCopied ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}
                          </button>
                        </td>
                        <td className="p-4">
                          <div className="flex items-center gap-2">
                            <Badge tier={wallet.tier} />
                            {wallet.aiStyleTag && (
                              <span className="hidden sm:inline-block text-[10px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full border border-black/[0.04]">
                                {wallet.aiStyleTag}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="p-4 text-right font-mono font-bold text-blue-600">
                          {(wallet.score || 0).toFixed(0)}
                        </td>
                        <td className="p-4 text-right font-mono font-semibold text-slate-900">
                          {formatWinRate(wallet.winRate || 0)}
                        </td>
                        <td className={`p-4 text-right font-mono font-extrabold ${(wallet.pnl || 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                          {(wallet.pnl || 0) >= 0 ? '+' : '-'}${Math.abs(wallet.pnl || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                        </td>
                        <td className="p-4 sm:px-6 text-right font-mono font-medium text-slate-600">
                          {(wallet.tradesPerDay || 0).toFixed(1)}/d
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={6} className="p-16 text-center text-slate-400 text-sm font-medium">
                      No wallets match this filter. Try clearing filters or run a discovery scan.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Embedded Drawer on Landing Page */}
      <WalletDrawer 
        address={selectedWallet} 
        onClose={() => setSelectedWallet(null)} 
      />
    </section>
  );
}
