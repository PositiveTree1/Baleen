'use client';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Button } from '../ui/Button';
import { BrandLogo } from '../ui/BrandLogo';
import Link from 'next/link';
import Image from 'next/image';
import dynamic from 'next/dynamic';
import { fetchPlatformStats } from '@/lib/api-client';
import { PlatformStats } from '@/types';
import { ArrowRight, ShieldCheck, Zap, TrendingUp, CheckCircle2, Sparkles, Activity, Layers, Compass } from 'lucide-react';

// Dynamic import with ssr: false for WebGL ShaderGradient Canvas
const ShaderGradientBackground = dynamic(
  () => import('./ShaderGradientBackground').then((mod) => mod.ShaderGradientBackground),
  { ssr: false }
);

export function Hero() {
  const [stats, setStats] = useState<PlatformStats | null>(null);

  useEffect(() => {
    fetchPlatformStats().then(setStats);
  }, []);

  return (
    <section className="min-h-[92vh] flex flex-col lg:flex-row items-center justify-between px-6 lg:px-20 py-20 gap-12 relative overflow-hidden bg-[#F8F9FB]">
      {/* 3D Animated WebGL Fluid ShaderGradient Canvas */}
      <ShaderGradientBackground />

      {/* Left Column: Typography & CTAs */}
      <div className="w-full lg:w-1/2 flex flex-col items-start gap-8 z-10">
        {/* Futuristic Brand Badge */}
        <Link 
          href="/" 
          className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full text-xs font-semibold text-slate-800 bg-white/90 border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.04)] backdrop-blur-xl hover:bg-white hover:shadow-md transition-all"
        >
          <Image src="/logo.png" alt="Baleen" width={18} height={18} className="w-4.5 h-4.5 object-contain" />
          <span className="font-brand-futuristic text-[11px] font-bold tracking-[0.15em] text-slate-950">BALEEN PROTOCOL</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse ml-1" />
        </Link>

        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-slate-950 leading-[1.05]">
          Mirror the top 1% <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-blue-600 to-indigo-800 font-brand-cinematic">
            on autopilot.
          </span>
        </h1>

        <p className="text-lg text-slate-600 max-w-xl leading-relaxed font-normal">
          Baleen is an institutional copy-trading engine for Polymarket. Discover verified prediction whales, size positions dynamically, and mirror smart money fills with sub-second latency.
        </p>

        <div className="flex flex-wrap items-center gap-3.5 pt-2">
          <Link href="/auth/signup">
            <Button variant="primary" className="px-7 py-3.5 text-sm font-semibold shadow-[inset_0_1px_0_rgba(255,255,255,0.2),0_2px_8px_rgba(0,0,0,0.12),0_12px_24px_-6px_rgba(99,102,241,0.3)] hover:scale-105 transition-all">
              Start Mirroring Free <ArrowRight size={16} />
            </Button>
          </Link>
          <Link href="#leaderboard">
            <Button variant="secondary" className="px-7 py-3.5 text-sm font-semibold shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_6px_rgba(0,0,0,0.04)] bg-white/90 backdrop-blur-lg hover:bg-white transition-all">
              Explore Live Basket
            </Button>
          </Link>
        </div>

        {/* Feature badges */}
        <div className="flex items-center gap-6 pt-6 text-xs text-slate-600 font-semibold border-t border-black/[0.08] w-full max-w-lg">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600 border border-emerald-200 shadow-2xs">
              <ShieldCheck size={14} />
            </div>
            <span>Non-Custodial Sandbox</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-blue-50 text-blue-600 border border-blue-200 shadow-2xs">
              <Zap size={14} />
            </div>
            <span>38ms HyperSync Engine</span>
          </div>
        </div>
      </div>

      {/* Right Column: Luminous Apple/Stripe Glassmorphism Control Center */}
      <div className="w-full lg:w-1/2 flex justify-center items-center py-6 z-10">
        <div className="relative w-full max-w-md">
          {/* Floating Live Signal Pill (Top Right) */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="absolute -top-5 -right-3 z-30 hidden sm:flex items-center gap-2.5 bg-white/95 backdrop-blur-2xl border border-black/[0.08] px-4 py-2 rounded-2xl shadow-[inset_0_1px_0_rgba(255,255,255,1),0_8px_24px_rgba(0,0,0,0.06)]"
          >
            <div className="w-7 h-7 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center border border-amber-200 shadow-2xs">
              <Sparkles size={14} className="animate-spin-slow" />
            </div>
            <div>
              <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Top Gold Whale</div>
              <div className="text-xs font-mono font-bold text-emerald-600">+$287,153 PnL (88.8% WR)</div>
            </div>
          </motion.div>

          {/* Floating Polygon Telemetry Pill (Bottom Left) */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="absolute -bottom-5 -left-3 z-30 hidden sm:flex items-center gap-2 bg-white/95 backdrop-blur-2xl border border-black/[0.08] px-4 py-2 rounded-2xl shadow-[inset_0_1px_0_rgba(255,255,255,1),0_8px_24px_rgba(0,0,0,0.06)]"
          >
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping" />
            <div className="text-[11px] font-mono font-bold text-slate-800">
              Polygon Event Stream: <span className="text-emerald-600 font-extrabold">LIVE</span>
            </div>
          </motion.div>

          {/* Main Glassmorphism Card */}
          <div className="w-full p-8 rounded-3xl bg-white/90 backdrop-blur-3xl border border-white/95 shadow-[inset_0_1px_1px_rgba(255,255,255,1),0_4px_24px_rgba(0,0,0,0.04),0_24px_60px_-12px_rgba(15,23,42,0.08)] relative overflow-hidden transition-all duration-300">
            {/* Header: Logo & Online Badge */}
            <div className="flex justify-between items-center mb-6">
              <BrandLogo size="sm" subtitle="HyperSync v2.1 • 38ms" />
              <span className="flex items-center gap-1.5 text-xs text-emerald-800 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200 shadow-2xs font-mono font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                {stats?.indexerStatus || 'ONLINE'}
              </span>
            </div>
            
            {/* Body Metric Containers */}
            <div className="space-y-4">
              {/* Active Basket Hero Box */}
              <div className="p-5 rounded-2xl bg-slate-50/95 border border-black/[0.06] shadow-2xs">
                <div className="text-xs text-slate-500 font-semibold mb-1 flex items-center justify-between">
                  <span>Active Whale Index Basket</span>
                  <span className="text-[10px] font-mono text-slate-400">Scored Daily</span>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-3xl font-extrabold text-slate-950 font-mono tracking-tight">
                    {stats?.activeBasketWhales ?? 0} Whales
                  </span>
                  <span className="text-xs text-amber-900 bg-gradient-to-r from-amber-100 to-amber-50 px-3 py-1 rounded-full font-mono font-bold border border-amber-300 shadow-2xs flex items-center gap-1">
                    <Sparkles size={11} className="text-amber-600" /> Gold Tier Active
                  </span>
                </div>
              </div>
              
              {/* 2-Column Stats */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-4 rounded-2xl bg-slate-50/95 border border-black/[0.06] shadow-2xs">
                  <div className="text-[11px] text-slate-500 font-semibold mb-1">Total Mirrored</div>
                  <div className="text-xl font-extrabold text-slate-950 font-mono tracking-tight">
                    ${(stats?.totalVolumeMirrored ?? 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                  </div>
                </div>
                <div className="p-4 rounded-2xl bg-slate-50/95 border border-black/[0.06] shadow-2xs">
                  <div className="text-[11px] text-slate-500 font-semibold mb-1">Dynamic Sizing</div>
                  <div className="text-xl font-extrabold text-emerald-600 font-mono tracking-tight flex items-center gap-1">
                    <CheckCircle2 size={16} /> 100% Live
                  </div>
                </div>
              </div>

              {/* Bottom Inset Balance */}
              <div className="p-3.5 rounded-2xl bg-slate-100/90 border border-black/[0.05] flex items-center justify-between text-xs text-slate-600 font-medium">
                <span>Sandbox Starting Capital</span>
                <span className="font-mono text-slate-900 font-bold">$10,000.00 Paper</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
