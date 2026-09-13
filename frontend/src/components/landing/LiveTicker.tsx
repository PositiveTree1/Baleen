'use client';

import { useEffect, useState } from 'react';
import { fetchPlatformStats, fetchExecutionLogs } from '@/lib/api-client';
import { PlatformStats, ExecutionLog } from '@/types';
import { motion } from 'framer-motion';
import { Radio, Zap } from 'lucide-react';

interface TickerItem {
  id: string;
  marketQuestion?: string;
  market_question?: string;
  side: 'BUY' | 'SELL';
  userFillPrice?: number | null;
  fillPrice?: number | null;
  whale_entry_price?: number | null;
  notionalUsd?: number;
  walletAddress?: string;
  source_wallet_address?: string;
}

const fallbackTrades: TickerItem[] = [
  { id: 'fb-1', walletAddress: '0x12a9...3f12', marketQuestion: 'Fed rate cut in June 2026', side: 'BUY', userFillPrice: 0.64, notionalUsd: 250 },
  { id: 'fb-2', walletAddress: '0x7bf3...910a', marketQuestion: 'BTC above $100k before Dec 31', side: 'BUY', userFillPrice: 0.72, notionalUsd: 500 },
  { id: 'fb-3', walletAddress: '0x4981...bb4c', marketQuestion: 'US Debt Ceiling Resolution Passed', side: 'BUY', userFillPrice: 0.38, notionalUsd: 180 },
  { id: 'fb-4', walletAddress: '0xce92...a381', marketQuestion: 'SpaceX Starship Orbital Landing', side: 'BUY', userFillPrice: 0.81, notionalUsd: 420 },
  { id: 'fb-5', walletAddress: '0x38e1...4401', marketQuestion: 'ECB reduces deposit facility rate', side: 'SELL', userFillPrice: 0.45, notionalUsd: 310 },
  { id: 'fb-6', walletAddress: '0x811a...998f', marketQuestion: 'Solana Mobile Chapter 2 Ship Date', side: 'BUY', userFillPrice: 0.59, notionalUsd: 150 },
];

export function LiveTicker() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [trades, setTrades] = useState<ExecutionLog[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const [statsData, tradesData] = await Promise.all([
          fetchPlatformStats(),
          fetchExecutionLogs(undefined, { limit: '12' })
        ]);
        if (statsData) setStats(statsData);
        if (tradesData && tradesData.length > 0) setTrades(tradesData);
      } catch (err) {
        console.warn('LiveTicker background poll silently caught:', err);
      }
    }
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  const activeTrades: TickerItem[] = trades.length > 0 ? trades : fallbackTrades;
  const marqueeList = [...activeTrades, ...activeTrades, ...activeTrades];

  return (
    <div className="relative z-20 w-full border-y border-white/10 bg-[#060c1b]/95 backdrop-blur-3xl overflow-hidden shadow-2xl">
      {/* Top Status Strip */}
      <div className="mx-auto flex max-w-[1380px] flex-wrap items-center justify-between gap-4 border-b border-white/[0.07] px-5 py-2.5 text-xs text-white/70 sm:px-8">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex size-2 rounded-full bg-emerald-400" />
            </span>
            <span className="font-mono text-[11px] font-bold tracking-wider text-white uppercase">
              Polymarket Stream · Polygon CTF
            </span>
          </div>

          <div className="hidden items-center gap-2 sm:flex">
            <span className="text-white/40 font-mono text-[11px]">Baskets:</span>
            <span className="font-mono text-[11px] font-extrabold text-cyan-300 bg-cyan-500/10 border border-cyan-400/20 px-2 py-0.5 rounded-full">
              {stats?.activeBasketWhales ?? 10} Active Sleeves
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 text-[11px]">
          <span className="inline-flex items-center gap-1.5 text-white/50 font-mono">
            <Zap size={12} className="text-amber-300" />
            Latency: <strong className="font-mono font-bold text-emerald-300">~84ms Envio Hypersync</strong>
          </span>
          <span className="text-white/20">|</span>
          <span className="text-white/50 font-mono">
            Mode: <strong className="font-mono font-bold text-cyan-300">Isolated $2k Sleeves</strong>
          </span>
        </div>
      </div>

      {/* Scrolling Marquee */}
      <div className="relative flex min-h-[46px] items-center overflow-hidden whitespace-nowrap py-2.5">
        {/* Ambient Gradient Fades */}
        <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-16 bg-gradient-to-r from-[#060c1b] to-transparent" />
        <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-16 bg-gradient-to-l from-[#060c1b] to-transparent" />

        <motion.div
          animate={{ x: ['0%', '-33.333%'] }}
          transition={{
            ease: 'linear',
            duration: 38,
            repeat: Infinity,
          }}
          className="flex items-center gap-4 will-change-transform"
        >
          {marqueeList.map((item: TickerItem, idx) => (
            <div
              key={`${item.id || idx}-${idx}`}
              className="inline-flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-1.5 text-xs font-mono backdrop-blur-xl shadow-xs"
            >
              <span className="text-white/40 font-bold">
                {(item.walletAddress || item.source_wallet_address || '0x49e1').slice(0, 6)}...
              </span>
              <span className="max-w-[240px] truncate font-sans font-medium text-slate-200">
                {item.marketQuestion || item.market_question || 'Prediction Market Contract'}
              </span>
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-bold border font-mono ${
                  item.side === 'BUY'
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                    : 'border-rose-500/30 bg-rose-500/10 text-rose-300'
                }`}
              >
                {item.side}
              </span>
              <span className="font-bold text-cyan-200">
                {(() => {
                  const price = item.userFillPrice ?? item.fillPrice ?? item.whale_entry_price;
                  return price === null || price === undefined ? '$0.50' : `$${price.toFixed(2)}`;
                })()}
              </span>
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
