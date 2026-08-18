'use client';
import { useEffect, useState } from 'react';
import { fetchPlatformStats, fetchExecutionLogs } from '@/lib/api-client';
import { PlatformStats, ExecutionLog } from '@/types';
import { Activity, ShieldCheck, Zap, TrendingUp, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

export function LiveTicker() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [trades, setTrades] = useState<ExecutionLog[]>([]);

  useEffect(() => {
    async function load() {
      const [statsData, tradesData] = await Promise.all([
        fetchPlatformStats(),
        fetchExecutionLogs(undefined, { limit: '10' })
      ]);
      if (statsData) setStats(statsData);
      if (tradesData && tradesData.length > 0) setTrades(tradesData);
    }
    load();
    const interval = setInterval(load, 12000);
    return () => clearInterval(interval);
  }, []);

  // Format trades into clean ticker items, with fallback if empty
  const tickerItems = trades.length > 0 ? trades : [
    { id: '1', marketQuestion: 'Fed Interest Rate Decision', side: 'BUY', userFillPrice: 0.88, notionalUsd: 250, walletAddress: '0x5f659b' },
    { id: '2', marketQuestion: 'Bitcoin $120k Target', side: 'BUY', userFillPrice: 0.64, notionalUsd: 580, walletAddress: '0x4956f6' },
    { id: '3', marketQuestion: 'Cincinnati Open: Rublev vs Borges', side: 'BUY', userFillPrice: 0.41, notionalUsd: 120, walletAddress: '0xf377b9' },
    { id: '4', marketQuestion: 'SpaceX Starship Orbital Refuel', side: 'BUY', userFillPrice: 0.79, notionalUsd: 310, walletAddress: '0x698204' },
    { id: '5', marketQuestion: 'Roehampton Tennis Championship', side: 'SELL', userFillPrice: 0.48, notionalUsd: 250, walletAddress: '0xca97f5' },
  ];

  // Duplicate the array for a seamless infinite marquee
  const marqueeList = [...tickerItems, ...tickerItems, ...tickerItems];

  return (
    <div className="w-full border-y border-black/[0.06] bg-white/90 backdrop-blur-xl overflow-hidden flex flex-col relative z-20 shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
      {/* Top Static Bar */}
      <div className="max-w-7xl mx-auto w-full px-6 py-2 flex flex-wrap items-center justify-between gap-4 text-xs border-b border-black/[0.04]">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="font-mono font-bold text-slate-800 text-[11px] uppercase tracking-wider">
              Polymarket Live Stream
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-2">
            <span className="text-slate-400 font-medium">Active Basket Whales:</span>
            <span className="font-mono text-indigo-600 font-extrabold bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-200/60">
              {stats?.activeBasketWhales ?? 17} Gold Whales
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4 text-[11px]">
          <span className="text-slate-500 font-medium">
            Execution Speed: <strong className="text-emerald-600 font-mono font-bold">&lt; 38ms (Polygon CTF)</strong>
          </span>
        </div>
      </div>

      {/* Smooth Automatic Infinite Scrolling Marquee */}
      <div className="py-2.5 overflow-hidden whitespace-nowrap flex items-center relative">
        {/* Left & Right gradient fades */}
        <div className="absolute left-0 inset-y-0 w-12 bg-gradient-to-r from-white to-transparent z-10 pointer-events-none" />
        <div className="absolute right-0 inset-y-0 w-12 bg-gradient-to-l from-white to-transparent z-10 pointer-events-none" />

        <motion.div
          animate={{ x: ['0%', '-33.333%'] }}
          transition={{
            ease: 'linear',
            duration: 35,
            repeat: Infinity,
          }}
          className="flex items-center gap-4 will-change-transform"
        >
          {marqueeList.map((item: any, idx) => (
            <div
              key={`${item.id || idx}-${idx}`}
              className="inline-flex items-center gap-3 bg-slate-50/90 border border-black/[0.06] px-3.5 py-1.5 rounded-2xl text-xs font-mono shrink-0 shadow-xs"
            >
              <span className="text-slate-400 font-bold">
                {(item.walletAddress || item.source_wallet_address || '0x0000').slice(0, 6)}...
              </span>
              <span className="font-sans font-medium text-slate-800 max-w-[200px] truncate">
                {item.marketQuestion || item.market_question || 'Prediction Market'}
              </span>
              <span className={`px-2 py-0.2 rounded-full text-[10px] font-bold border ${
                item.side === 'BUY' ? 'text-emerald-800 bg-emerald-50 border-emerald-200' : 'text-rose-800 bg-rose-50 border-rose-200'
              }`}>
                {item.side}
              </span>
              <span className="font-bold text-slate-900">
                ${(item.userFillPrice ?? item.fillPrice ?? item.whale_entry_price ?? 0.5).toFixed(2)}
              </span>
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
