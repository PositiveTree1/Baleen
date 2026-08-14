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
    const interval = setInterval(loadStats, 30000); // refresh every 30s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full border-y border-white/5 bg-baleen-charcoal/50 backdrop-blur-md overflow-hidden flex items-center h-12 relative z-20">
      <div className="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-baleen-obsidian to-transparent z-10"></div>
      
      <div className="flex items-center whitespace-nowrap animate-[scroll_20s_linear_infinite] gap-16 px-4">
        {loading ? (
          <span className="text-sm text-baleen-muted">Connecting to network...</span>
        ) : stats ? (
          <>
            <span className="text-sm text-baleen-white flex items-center gap-2">
              <span className="text-baleen-muted">Total Mirrored:</span>
              <span className="font-mono text-baleen-cyan">${(stats?.totalVolumeMirrored ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            </span>
            <span className="text-sm text-baleen-white flex items-center gap-2">
              <span className="text-baleen-muted">Active Whales:</span>
              <span className="font-mono">{(stats?.activeBasketWhales ?? 0)}</span>
            </span>
            <span className="text-sm text-baleen-white flex items-center gap-2">
              <span className="text-baleen-muted">Indexer Status:</span>
              <span className={`flex items-center gap-1 ${(stats?.indexerStatus ?? 'SYNCING') === 'ONLINE' ? 'text-baleen-green' : 'text-amber-500'}`}>
                <Activity size={14} /> {(stats?.indexerStatus ?? 'SYNCING')}
              </span>
            </span>
            {/* Repeat for seamless scroll effect if needed, though simple CSS scroll works too */}
          </>
        ) : (
          <span className="text-sm text-baleen-muted">Network stats currently unavailable.</span>
        )}
      </div>

      <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-baleen-obsidian to-transparent z-10"></div>
      
      <style jsx>{`
        @keyframes scroll {
          0% { transform: translateX(100vw); }
          100% { transform: translateX(-100%); }
        }
      `}</style>
    </div>
  );
}
