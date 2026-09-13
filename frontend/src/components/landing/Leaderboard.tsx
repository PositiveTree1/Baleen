'use client';

import { useEffect, useState } from 'react';
import { fetchWallets } from '@/lib/api-client';
import { Wallet } from '@/types';
import { Badge } from '../ui/Badge';
import { Skeleton } from '../ui/Skeleton';
import { WalletDrawer } from '../dashboard/WalletDrawer';
import { Search, Trophy, ArrowUpDown, Copy, Check, ExternalLink } from 'lucide-react';

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
      try {
        const data = await fetchWallets({ limit: '50' });
        setWallets(data || []);
      } catch (err) {
        console.warn('Leaderboard fetch caught:', err);
      } finally {
        setLoading(false);
      }
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
      if (filterTier === 'high_wr') return w.winRate != null && w.winRate >= (w.winRate > 1 ? 80 : 0.8);
      if (filterTier === 'high_pnl') return w.pnl != null && w.pnl >= 100000;
      return true;
    })
    .sort((a, b) => {
      const valA = (a[sortField] ?? -Infinity) as number;
      const valB = (b[sortField] ?? -Infinity) as number;
      return sortAsc ? valA - valB : valB - valA;
    });

  return (
    <section id="leaderboard" className="relative overflow-hidden bg-[#07080A] px-5 py-24 text-white sm:px-8 sm:py-32 lg:px-12 border-b border-white/10">
      <div className="relative mx-auto max-w-[1380px]">
        {/* Header and Controls */}
        <div className="mb-12 flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-1 text-xs font-bold tracking-wider text-zinc-300 font-mono">
              <Trophy size={13} className="text-[#00D09C]" />
              <span>LIVE DISCOVERY BASKET</span>
            </div>
            <h2 className="font-outfit text-3xl font-black tracking-[-0.04em] text-white sm:text-5xl">
              Alpha Discovery Basket
            </h2>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-zinc-400 sm:text-base">
              Verified high-conviction Polymarket whales. Click any address to inspect their full historical equity curve, risk tier, and executed positions.
            </p>
          </div>

          {/* Search Bar */}
          <div className="w-full md:w-72">
            <div className="relative">
              <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input
                type="text"
                placeholder="Search 0x address..."
                aria-label="Search 0x address"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-[#0E1015] py-2.5 pl-9 pr-3.5 font-mono text-xs text-white placeholder:text-zinc-600 focus:border-white/30 focus:outline-none focus:ring-1 focus:ring-white/20"
              />
            </div>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="mb-6 flex flex-wrap items-center gap-2">
          {([
            { id: 'all', label: 'All Whales' },
            { id: 'gold', label: '⭐ Gold Snipers (85%+ WR)' },
            { id: 'high_wr', label: '🎯 High Win Rate' },
            { id: 'high_pnl', label: '💰 $100k+ Net Profit' },
          ] as const).map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setFilterTier(tab.id)}
              className={`cursor-pointer rounded-xl border px-4 py-2 text-xs font-bold transition-all ${
                filterTier === tab.id
                  ? 'border-white bg-white/10 text-white shadow-md'
                  : 'border-white/10 bg-white/[0.02] text-zinc-400 hover:border-white/20 hover:bg-white/[0.05] hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Table Container (Apple Optical Glass Card) */}
        <div className="apple-glass-card overflow-hidden rounded-[28px] border border-white/10 bg-[#0E1015]/90 shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-white/10 bg-white/[0.02] font-mono text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                  <th className="p-4 sm:px-6">Whale Address</th>
                  <th className="p-4">Tier &amp; Style</th>
                  <th
                    onClick={() => handleSort('score')}
                    className="cursor-pointer p-4 text-right transition-colors hover:text-white"
                  >
                    <span className="inline-flex items-center gap-1">
                      Score <ArrowUpDown size={11} />
                    </span>
                  </th>
                  <th
                    onClick={() => handleSort('winRate')}
                    className="cursor-pointer p-4 text-right transition-colors hover:text-white"
                  >
                    <span className="inline-flex items-center gap-1">
                      Win Rate <ArrowUpDown size={11} />
                    </span>
                  </th>
                  <th
                    onClick={() => handleSort('pnl')}
                    className="cursor-pointer p-4 text-right transition-colors hover:text-white"
                  >
                    <span className="inline-flex items-center gap-1">
                      Realized P&amp;L <ArrowUpDown size={11} />
                    </span>
                  </th>
                  <th
                    onClick={() => handleSort('tradesPerDay')}
                    className="cursor-pointer p-4 sm:px-6 text-right transition-colors hover:text-white"
                  >
                    <span className="inline-flex items-center gap-1">
                      Trades / Day <ArrowUpDown size={11} />
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.06]">
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      <td className="p-4 sm:px-6"><Skeleton className="h-4 w-28 bg-white/10" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-20 bg-white/10" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-12 ml-auto bg-white/10" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-16 ml-auto bg-white/10" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-20 ml-auto bg-white/10" /></td>
                      <td className="p-4 sm:px-6"><Skeleton className="h-4 w-8 ml-auto bg-white/10" /></td>
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
                        className={`group cursor-pointer text-xs transition-colors ${
                          isGold ? 'hover:bg-amber-400/[0.04]' : 'hover:bg-white/[0.03]'
                        }`}
                      >
                        <td className="p-4 sm:px-6 font-mono font-bold text-white flex items-center gap-2">
                          <span className="group-hover:text-[#00D09C] transition-colors">
                            {wallet.address.slice(0, 6)}...{wallet.address.slice(-4)}
                          </span>
                          <button
                            type="button"
                            onClick={(e) => handleCopy(wallet.address, e)}
                            className="rounded p-1 text-zinc-500 hover:text-white transition-colors"
                            title="Copy full address"
                          >
                            {isCopied ? <Check size={13} className="text-[#00D09C]" /> : <Copy size={13} />}
                          </button>
                        </td>
                        <td className="p-4">
                          <div className="flex items-center gap-2">
                            <Badge tier={wallet.tier} />
                            {wallet.aiStyleTag && (
                              <span className="hidden sm:inline-block rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] font-semibold text-zinc-400 font-mono">
                                {wallet.aiStyleTag}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="p-4 text-right font-mono font-bold text-white">
                          {wallet.score == null ? '—' : wallet.score.toFixed(0)}
                        </td>
                        <td className="p-4 text-right font-mono font-semibold text-white">
                          {wallet.winRate == null ? '—' : formatWinRate(wallet.winRate)}
                        </td>
                        <td className={`p-4 text-right font-mono font-extrabold ${wallet.pnl == null ? 'text-zinc-500' : wallet.pnl >= 0 ? 'text-[#00D09C]' : 'text-[#FF453A]'}`}>
                          {wallet.pnl == null ? '—' : `${wallet.pnl >= 0 ? '+' : '-'}$${Math.abs(wallet.pnl).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`}
                        </td>
                        <td className="p-4 sm:px-6 text-right font-mono font-medium text-zinc-500">
                          {wallet.tradesPerDay == null ? '—' : `${wallet.tradesPerDay.toFixed(1)}/d`}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={6} className="p-16 text-center text-sm font-medium text-zinc-500">
                      No candidate whales found in this filter tier.
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
