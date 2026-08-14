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
    <div className="w-full border-y border-black/[0.06] bg-white/80 backdrop-blur-xl overflow-hidden flex items-center h-12 relative z-20 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
      <div className="max-w-7xl mx-auto w-full px-6 flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-8">
          <span className="flex items-center gap-2">
            <span className="text-slate-400 font-medium">Total Volume Mirrored:</span>
            <span className="font-mono text-slate-900 font-bold">
              ${(stats?.totalVolumeMirrored ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </span>
          <span className="hidden sm:flex items-center gap-2">
            <span className="text-slate-400 font-medium">Active Whales:</span>
            <span className="font-mono text-slate-900 font-bold">{(stats?.activeBasketWhales ?? 0)}</span>
          </span>
          <span className="hidden md:flex items-center gap-2">
            <span className="text-slate-400 font-medium">Execution Latency:</span>
            <span className="font-mono text-slate-900 font-bold">&lt; 800ms</span>
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-slate-400 font-medium">Indexer:</span>
          <span className={`inline-flex items-center gap-1.5 font-mono px-2.5 py-0.5 rounded-full text-[11px] font-semibold border shadow-[inset_0_1px_0_rgba(255,255,255,0.8)] ${
            (stats?.indexerStatus ?? 'ONLINE') === 'ONLINE' 
              ? 'text-emerald-800 bg-emerald-50 border-emerald-200' 
              : 'text-amber-800 bg-amber-50 border-amber-200'
          }`}>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            {stats?.indexerStatus ?? 'ONLINE'} (Polygon)
          </span>
        </div>
      </div>
    </div>
  );
}
