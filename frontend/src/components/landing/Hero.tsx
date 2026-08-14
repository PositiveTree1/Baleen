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
  const rotateX = useTransform(y, [-100, 100], [5, -5]);
  const rotateY = useTransform(x, [-100, 100], [-5, 5]);

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
    <section className="min-h-[85vh] flex flex-col lg:flex-row items-center justify-between px-6 lg:px-20 py-24 gap-16 relative overflow-hidden bg-[#F8F9FB]">
      {/* Subtle light ambient glow */}
      <div className="absolute top-1/4 left-1/3 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-blue-100/40 rounded-full blur-[140px] pointer-events-none" />

      <div className="w-full lg:w-1/2 flex flex-col items-start gap-7 z-10">
        {/* Apple-style light pill */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold text-slate-700 bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_1px_2px_rgba(0,0,0,0.04)]">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Automated Polymarket Whale Index</span>
        </div>

        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight text-slate-900 leading-[1.08]">
          Mirror the top 1% <br />
          <span className="text-slate-500 font-semibold">on autopilot.</span>
        </h1>

        <p className="text-lg text-slate-600 max-w-xl leading-relaxed font-normal">
          Baleen is a non-custodial copy-trading engine for Polymarket. Discover top-performing prediction whales, size positions automatically, and mirror verified trades instantly.
        </p>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <Link href="/auth/signup">
            <Button variant="primary" className="px-6 py-3 text-sm font-semibold">
              Start Mirroring Free <ArrowRight size={16} />
            </Button>
          </Link>
          <Link href="#leaderboard">
            <Button variant="secondary" className="px-6 py-3 text-sm font-medium">
              Explore Live Basket
            </Button>
          </Link>
        </div>

        {/* Feature badges */}
        <div className="flex items-center gap-8 pt-6 text-xs text-slate-500 font-medium border-t border-black/[0.06] w-full">
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} className="text-emerald-600" />
            <span>Non-Custodial Sandbox</span>
          </div>
          <div className="flex items-center gap-2">
            <Zap size={16} className="text-blue-600" />
            <span>Real-time Polygon Sync</span>
          </div>
        </div>
      </div>

      {/* 3D Skeuomorphic Card */}
      <div className="w-full lg:w-1/2 flex justify-center perspective-[1000px] z-10" onMouseMove={handleMouse} onMouseLeave={handleMouseLeave}>
        <motion.div
          style={{ rotateX, rotateY }}
          className="w-full max-w-md p-8 rounded-3xl bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_4px_12px_rgba(0,0,0,0.04),0_20px_48px_-12px_rgba(0,0,0,0.08)] relative overflow-hidden"
        >
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center gap-2.5">
              <Activity size={18} className="text-slate-900" />
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Engine Status</h3>
            </div>
            <span className="flex items-center gap-1.5 text-xs text-emerald-800 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)] font-mono font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              {stats?.indexerStatus || 'ONLINE'}
            </span>
          </div>
          
          <div className="space-y-4">
            <div className="p-5 rounded-2xl bg-slate-50/80 border border-black/[0.06] shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
              <div className="text-xs text-slate-500 font-medium mb-1">Active Index Basket</div>
              <div className="flex items-baseline justify-between">
                <span className="text-3xl font-bold text-slate-900 font-mono tracking-tight">
                  {stats?.activeBasketWhales ?? 0} Whales
                </span>
                <span className="text-xs text-emerald-700 bg-emerald-100/60 px-2 py-0.5 rounded font-mono font-semibold">Gold Tier</span>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div className="p-4 rounded-2xl bg-slate-50/80 border border-black/[0.06] shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
                <div className="text-xs text-slate-500 font-medium mb-1">Total Mirrored</div>
                <div className="text-xl font-bold text-slate-900 font-mono tracking-tight">
                  ${(stats?.totalVolumeMirrored ?? 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </div>
              </div>
              <div className="p-4 rounded-2xl bg-slate-50/80 border border-black/[0.06] shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
                <div className="text-xs text-slate-500 font-medium mb-1">Dynamic Sizing</div>
                <div className="text-xl font-bold text-emerald-600 font-mono tracking-tight">
                  100% Live
                </div>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-black/[0.04] flex items-center justify-between text-xs text-slate-600 font-medium">
              <span>Sandbox Starting Capital</span>
              <span className="font-mono text-slate-900 font-bold">$10,000.00</span>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
