'use client';
import { useState, useEffect } from 'react';
import { motion, useMotionValue, useTransform } from 'framer-motion';
import { Button } from '../ui/Button';
import Link from 'next/link';
import { fetchPlatformStats } from '@/lib/api-client';
import { PlatformStats } from '@/types';
import { ArrowRight, ShieldCheck, Zap, Activity } from 'lucide-react';

export function Hero() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useTransform(y, [-100, 100], [6, -6]);
  const rotateY = useTransform(x, [-100, 100], [-6, 6]);

  useEffect(() => {
    fetchPlatformStats().then(setStats);
  }, []);

  function handleMouse(event: React.MouseEvent<HTMLDivElement, MouseEvent>) {
    const rect = event.currentTarget.getBoundingClientRect();
    x.set(event.clientX - rect.left - rect.width / 2);
    y.set(event.clientY - rect.top - rect.height / 2);
  }

  function handleMouseLeave() {
    x.set(0);
    y.set(0);
  }

  return (
    <section className="min-h-[85vh] flex flex-col lg:flex-row items-center justify-between px-6 lg:px-20 py-24 gap-16 relative overflow-hidden">
      {/* Subtle radial ambient light */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-white/[0.03] rounded-full blur-[140px] pointer-events-none" />

      <div className="w-full lg:w-1/2 flex flex-col items-start gap-7 z-10">
        {/* Apple-style pill */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium text-zinc-300 bg-white/[0.05] border border-white/[0.08] backdrop-blur-md">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>Automated Polymarket Whale Index</span>
        </div>

        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight text-white leading-[1.08]">
          Mirror the top 1% <br />
          <span className="text-zinc-400">on autopilot.</span>
        </h1>

        <p className="text-lg text-zinc-400 max-w-xl leading-relaxed font-normal">
          Baleen automates Polymarket whale-index copy-trading. Discover elite wallets, match verified trades instantly, and build your automated prediction portfolio.
        </p>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <Link href="/auth/signup">
            <Button variant="primary" className="px-6 py-3 text-sm font-semibold">
              Start Mirroring Free <ArrowRight size={16} />
            </Button>
          </Link>
          <Link href="#leaderboard">
            <Button variant="secondary" className="px-6 py-3 text-sm">
              Explore Live Basket
            </Button>
          </Link>
        </div>

        {/* Feature badges */}
        <div className="flex items-center gap-6 pt-4 text-xs text-zinc-500 font-medium border-t border-white/[0.06] w-full">
          <div className="flex items-center gap-1.5">
            <ShieldCheck size={14} className="text-zinc-400" />
            <span>Non-Custodial Sandbox</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Zap size={14} className="text-zinc-400" />
            <span>Real-time Polygon Sync</span>
          </div>
        </div>
      </div>

      {/* 3D Glass Interactive Card */}
      <div className="w-full lg:w-1/2 flex justify-center perspective-[1000px] z-10" onMouseMove={handleMouse} onMouseLeave={handleMouseLeave}>
        <motion.div
          style={{ rotateX, rotateY }}
          className="glass-card w-full max-w-md p-7 rounded-3xl border border-white/[0.08] shadow-apple relative overflow-hidden backdrop-blur-2xl bg-zinc-900/60"
        >
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center gap-2.5">
              <Activity size={16} className="text-emerald-400" />
              <h3 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">Baleen Engine Status</h3>
            </div>
            <span className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20 font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              {stats?.indexerStatus || 'ONLINE'}
            </span>
          </div>
          
          <div className="space-y-4">
            <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.06]">
              <div className="text-xs text-zinc-500 mb-1">Active Index Basket</div>
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-bold text-white font-mono tracking-tight">
                  {stats?.activeBasketWhales ?? 0} Whales
                </span>
                <span className="text-xs text-zinc-400 font-mono">Gold Tier</span>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.06]">
                <div className="text-xs text-zinc-500 mb-1">Total Volume Mirrored</div>
                <div className="text-lg font-bold text-white font-mono tracking-tight">
                  ${(stats?.totalVolumeMirrored ?? 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </div>
              </div>
              <div className="p-4 rounded-2xl bg-black/40 border border-white/[0.06]">
                <div className="text-xs text-zinc-500 mb-1">Dynamic Sizing</div>
                <div className="text-lg font-bold text-emerald-400 font-mono tracking-tight">
                  100% Live
                </div>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.05] flex items-center justify-between text-xs text-zinc-400">
              <span>Paper Sandbox Starting Capital</span>
              <span className="font-mono text-white font-medium">$10,000.00</span>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
