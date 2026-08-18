'use client';
import { useEffect, useState } from 'react';
import { fetchPlatformStats } from '@/lib/api-client';
import { PlatformStats } from '@/types';
import { Activity, Flame, TrendingUp, Sparkles, ChevronRight } from 'lucide-react';
import Link from 'next/link';

interface MarketTickerItem {
  id: string;
  question: string;
  category: 'Politics' | 'Crypto' | 'Macro' | 'Tech';
  yesProb: number;
  change24h: number;
  whaleSize: string;
  whaleSide: 'YES' | 'NO';
}

const SAMPLE_MARKETS: MarketTickerItem[] = [
  { id: '1', question: 'Fed cuts interest rate by ≥25bps in September', category: 'Macro', yesProb: 88, change24h: +4.2, whaleSize: '$240,000', whaleSide: 'YES' },
  { id: '2', question: 'Bitcoin hits $120k before end of Q4', category: 'Crypto', yesProb: 64, change24h: +7.8, whaleSize: '$580,000', whaleSide: 'YES' },
  { id: '3', question: 'US Election Polling Margin >3.5%', category: 'Politics', yesProb: 42, change24h: -2.1, whaleSize: '$195,000', whaleSide: 'NO' },
  { id: '4', question: 'SpaceX Starship orbital refuel success in 2026', category: 'Tech', yesProb: 79, change24h: +3.0, whaleSize: '$310,000', whaleSide: 'YES' },
  { id: '5', question: 'Ethereum ETF Staking Approval within 90 days', category: 'Crypto', yesProb: 53, change24h: +1.5, whaleSize: '$145,000', whaleSide: 'YES' },
];

export function LiveTicker() {
  const [stats, setStats] = useState<PlatformStats | null>(null);

  useEffect(() => {
    async function loadStats() {
      const data = await fetchPlatformStats();
      if (data) setStats(data);
    }
    loadStats();
    const interval = setInterval(loadStats, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full border-y border-black/[0.06] bg-white/90 backdrop-blur-xl overflow-hidden flex flex-col relative z-20 shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
      {/* Top Bar: Live Status & Volume Metric */}
      <div className="max-w-7xl mx-auto w-full px-6 py-2.5 flex flex-wrap items-center justify-between gap-4 text-xs border-b border-black/[0.04]">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="font-mono font-bold text-slate-800 text-[11px] uppercase tracking-wider">
              Polymarket Live Feed
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-2">
            <span className="text-slate-400 font-medium">Indexed Volume:</span>
            <span className="font-mono text-slate-950 font-extrabold">
              ${(stats?.totalVolumeMirrored ?? 8459200).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
            </span>
          </div>

          <div className="hidden md:flex items-center gap-2">
            <span className="text-slate-400 font-medium">Active Whales:</span>
            <span className="font-mono text-indigo-600 font-extrabold bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-200/60">
              {stats?.activeBasketWhales ?? 12} Audited Whales
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4 text-[11px]">
          <span className="hidden lg:inline text-slate-400 font-medium">
            HyperSync Indexer: <strong className="text-emerald-700 font-mono font-bold">&lt; 38ms</strong>
          </span>
          <Link href="#leaderboard" className="inline-flex items-center gap-1 font-semibold text-indigo-600 hover:text-indigo-800 transition-colors">
            <span>View Active Basket</span>
            <ChevronRight size={13} />
          </Link>
        </div>
      </div>

      {/* Interactive Horizontal Market Cards Ticker */}
      <div className="py-2.5 px-6 max-w-7xl mx-auto w-full overflow-x-auto scrollbar-none flex items-center gap-3">
        {SAMPLE_MARKETS.map((market) => (
          <div
            key={market.id}
            className="shrink-0 flex items-center gap-3 bg-slate-50/90 hover:bg-white border border-black/[0.06] hover:border-indigo-200 px-3.5 py-2 rounded-2xl transition-all shadow-[0_1px_2px_rgba(0,0,0,0.02)] text-xs group cursor-default"
          >
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-white border border-black/[0.06] text-slate-600">
              {market.category}
            </span>
            <span className="font-medium text-slate-800 max-w-[220px] truncate" title={market.question}>
              {market.question}
            </span>
            <div className="flex items-center gap-1.5 font-mono">
              <span className="font-bold text-slate-950">{market.yesProb}% YES</span>
              <span className={`text-[10px] font-bold ${market.change24h >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                {market.change24h >= 0 ? '+' : ''}{market.change24h}%
              </span>
            </div>
            <div className="hidden sm:flex items-center gap-1 pl-1 border-l border-black/[0.08] text-[10px] text-slate-500 font-mono">
              <span>Whale:</span>
              <span className={`font-bold px-1.5 py-0.2 rounded ${market.whaleSide === 'YES' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
                {market.whaleSide} {market.whaleSize}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
