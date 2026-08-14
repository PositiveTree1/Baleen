'use client';
import { useEffect, useState } from 'react';
import { fetchPlatformStats } from '@/lib/api-client';
import { PlatformStats } from '@/types';
import { Activity } from 'lucide-react';

export function LiveTicker() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      const data = await fetchPlatformStats();
      setStats(data);
      setLoading(false);
    }
    loadStats();
    const interval = setInterval(loadStats, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full border-y border-white/[0.06] bg-zinc-950/60 backdrop-blur-xl overflow-hidden flex items-center h-12 relative z-20">
      <div className="max-w-7xl mx-auto w-full px-6 flex items-center justify-between text-xs text-zinc-400">
        <div className="flex items-center gap-8">
          <span className="flex items-center gap-2">
            <span className="text-zinc-500 font-medium">Total Volume Mirrored:</span>
            <span className="font-mono text-white font-semibold">
              ${(stats?.totalVolumeMirrored ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </span>
          <span className="hidden sm:flex items-center gap-2">
            <span className="text-zinc-500 font-medium">Active Whales:</span>
            <span className="font-mono text-white font-semibold">{(stats?.activeBasketWhales ?? 0)}</span>
          </span>
          <span className="hidden md:flex items-center gap-2">
            <span className="text-zinc-500 font-medium">Execution Latency:</span>
            <span className="font-mono text-white font-semibold">&lt; 800ms</span>
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-zinc-500 font-medium">Indexer:</span>
          <span className={`inline-flex items-center gap-1.5 font-mono px-2 py-0.5 rounded-full text-[11px] ${
            (stats?.indexerStatus ?? 'ONLINE') === 'ONLINE' 
              ? 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20' 
              : 'text-amber-400 bg-amber-500/10 border border-amber-500/20'
          }`}>
            <span className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse" />
            {stats?.indexerStatus ?? 'ONLINE'} (Polygon)
          </span>
        </div>
      </div>
    </div>
  );
}
