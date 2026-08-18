'use client';
import { motion } from 'framer-motion';
import { Flame, Users, TrendingUp, ShieldAlert, Sparkles, Compass } from 'lucide-react';
import Link from 'next/link';

interface ConsensusMarket {
  id: string;
  question: string;
  category: string;
  whaleCount: number;
  totalNotional: number;
  dominantSide: 'YES' | 'NO';
  avgEntryPrice: number;
  currentPrice: number;
  unrealizedPnlPct: number;
}

const TOP_CONSENSUS_CLUSTERS: ConsensusMarket[] = [
  {
    id: 'fed-rates-sep',
    question: 'Fed cuts interest rate by ≥25bps at Sept FOMC',
    category: 'Macro',
    whaleCount: 8,
    totalNotional: 485000,
    dominantSide: 'YES',
    avgEntryPrice: 0.72,
    currentPrice: 0.88,
    unrealizedPnlPct: +22.2,
  },
  {
    id: 'btc-120k-q4',
    question: 'Bitcoin hits $120,000 before December 31, 2026',
    category: 'Crypto',
    whaleCount: 6,
    totalNotional: 340000,
    dominantSide: 'YES',
    avgEntryPrice: 0.44,
    currentPrice: 0.64,
    unrealizedPnlPct: +45.5,
  },
  {
    id: 'spacex-starship',
    question: 'SpaceX Starship orbital payload delivery successful',
    category: 'Tech',
    whaleCount: 4,
    totalNotional: 195000,
    dominantSide: 'YES',
    avgEntryPrice: 0.61,
    currentPrice: 0.79,
    unrealizedPnlPct: +29.5,
  },
];

export function ConsensusRadar() {
  return (
    <div className="rounded-3xl p-6 bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_12px_28px_-4px_rgba(0,0,0,0.05)]">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6 pb-4 border-b border-black/[0.06]">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1 rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-200">
              <Flame size={15} />
            </span>
            <h3 className="text-sm font-bold text-slate-950 tracking-tight">Smart Money Consensus Radar</h3>
          </div>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            Markets where multiple top-tier basket whales are concurrently positioned.
          </p>
        </div>
        <span className="text-[11px] font-mono font-bold text-indigo-700 bg-indigo-50 px-3 py-1 rounded-full border border-indigo-200/80 shrink-0 self-start sm:self-auto">
          High Conviction Filter
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {TOP_CONSENSUS_CLUSTERS.map((market) => (
          <div
            key={market.id}
            className="p-4 rounded-2xl bg-slate-50/90 hover:bg-indigo-50/50 border border-black/[0.06] hover:border-indigo-200 transition-all flex flex-col justify-between group shadow-sm"
          >
            <div className="space-y-2 mb-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-white border border-black/[0.06] text-slate-600">
                  {market.category}
                </span>
                <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-indigo-700 bg-white px-2 py-0.5 rounded-md border border-indigo-100 shadow-xs">
                  <Users size={11} /> {market.whaleCount} Whales In
                </span>
              </div>
              <h4 className="text-xs font-bold text-slate-900 line-clamp-2 leading-snug group-hover:text-indigo-950">
                {market.question}
              </h4>
            </div>

            <div className="pt-3 border-t border-black/[0.04] space-y-2">
              <div className="flex justify-between items-center text-[11px] font-mono">
                <span className="text-slate-500">Aggregate Size:</span>
                <span className="font-bold text-slate-900">${market.totalNotional.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center text-[11px] font-mono">
                <span className="text-slate-500">Conviction Side:</span>
                <span className="font-extrabold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px]">
                  {market.dominantSide} @ ${(market.avgEntryPrice).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between items-center text-[11px] font-mono">
                <span className="text-slate-500">Unrealized Delta:</span>
                <span className="font-bold text-emerald-600">
                  +{market.unrealizedPnlPct.toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
