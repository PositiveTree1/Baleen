'use client';
import { useState, useEffect } from 'react';
import { motion, useMotionValue, useTransform, useSpring } from 'framer-motion';
import { Button } from '../ui/Button';
import { BrandLogo } from '../ui/BrandLogo';
import Link from 'next/link';
import Image from 'next/image';
import { fetchPlatformStats } from '@/lib/api-client';
import { PlatformStats } from '@/types';
import { ArrowRight, ShieldCheck, Zap, TrendingUp, CheckCircle2, Sparkles } from 'lucide-react';

export function Hero() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  
  // High-precision smooth motion values with refined dampening
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  
  const springConfig = { damping: 25, stiffness: 180, mass: 0.4 };
  const smoothX = useSpring(mouseX, springConfig);
  const smoothY = useSpring(mouseY, springConfig);

  // Smooth, subtle 3D rotations (keeps text razor-sharp)
  const rotateX = useTransform(smoothY, [-180, 180], [7, -7]);
  const rotateY = useTransform(smoothX, [-180, 180], [-7, 7]);
  
  // Dynamic specular glare sheen position
  const glareX = useTransform(smoothX, [-180, 180], [0, 100]);
  const glareY = useTransform(smoothY, [-180, 180], [0, 100]);

  // Parallax floating satellite tags
  const chipX = useTransform(smoothX, [-180, 180], [-12, 12]);
  const chipY = useTransform(smoothY, [-180, 180], [-12, 12]);

  useEffect(() => {
    fetchPlatformStats().then(setStats);
  }, []);

  function handleMouseMove(event: React.MouseEvent<HTMLDivElement, MouseEvent>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left - rect.width / 2;
    const y = event.clientY - rect.top - rect.height / 2;
    mouseX.set(x);
    mouseY.set(y);
  }

  function handleMouseLeave() {
    mouseX.set(0);
    mouseY.set(0);
  }

  return (
    <section className="min-h-[92vh] flex flex-col lg:flex-row items-center justify-between px-6 lg:px-20 py-20 gap-12 relative overflow-hidden bg-[#F8F9FB]">
      {/* 4K Nordic Icescape Background with luminous cold ice presence */}
      <div className="absolute inset-y-0 right-0 w-full lg:w-3/5 pointer-events-none opacity-80 lg:opacity-90 overflow-hidden z-0">
        <div className="absolute inset-0 bg-gradient-to-r from-[#F8F9FB] via-[#F8F9FB]/40 to-transparent z-10" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#F8F9FB] via-transparent to-[#F8F9FB]/40 z-10" />
        <Image 
          src="/images/hero-icescape.jpeg" 
          alt="Nordic Glacial Landscape" 
          fill
          priority
          className="object-cover object-right-top scale-105 filter saturate-[0.95] contrast-[1.05]"
        />
      </div>

      {/* Left Column: Typography & CTAs */}
      <div className="w-full lg:w-1/2 flex flex-col items-start gap-8 z-10">
        {/* Futuristic Brand Badge */}
        <Link href="/" className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full text-xs font-semibold text-slate-800 bg-white/90 border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_4px_rgba(0,0,0,0.03)] backdrop-blur-md hover:bg-white transition-colors">
          <Image src="/logo.png" alt="Baleen" width={16} height={16} className="w-4 h-4 object-contain" />
          <span className="font-brand-futuristic text-[11px] font-bold tracking-[0.14em] text-slate-900">BALEEN PROTOCOL</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse ml-1" />
        </Link>

        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-slate-950 leading-[1.05]">
          Mirror the top 1% <br />
          <span className="text-slate-500 font-semibold font-brand-cinematic">on autopilot.</span>
        </h1>

        <p className="text-lg text-slate-600 max-w-xl leading-relaxed font-normal">
          Baleen is an automated, non-custodial copy-trading engine for Polymarket. Discover top prediction whales, size positions dynamically, and mirror verified contract fills with sub-second execution.
        </p>

        <div className="flex flex-wrap items-center gap-3.5 pt-2">
          <Link href="/auth/signup">
            <Button variant="primary" className="px-7 py-3.5 text-sm font-semibold shadow-[inset_0_1px_0_rgba(255,255,255,0.2),0_2px_8px_rgba(0,0,0,0.12),0_12px_24px_-6px_rgba(0,0,0,0.1)]">
              Start Mirroring Free <ArrowRight size={16} />
            </Button>
          </Link>
          <Link href="#leaderboard">
            <Button variant="secondary" className="px-7 py-3.5 text-sm font-semibold shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_6px_rgba(0,0,0,0.04)]">
              Explore Live Basket
            </Button>
          </Link>
        </div>

        {/* Feature badges */}
        <div className="flex items-center gap-8 pt-6 text-xs text-slate-600 font-semibold border-t border-black/[0.08] w-full max-w-lg">
          <div className="flex items-center gap-2">
            <div className="p-1 rounded-md bg-emerald-50 text-emerald-600 border border-emerald-200">
              <ShieldCheck size={14} />
            </div>
            <span>Non-Custodial Sandbox</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="p-1 rounded-md bg-blue-50 text-blue-600 border border-blue-200">
              <Zap size={14} />
            </div>
            <span>Envio HyperSync (38ms)</span>
          </div>
        </div>
      </div>

      {/* Right Column: True 3D Interactive Skeuomorphic Card */}
      <div 
        className="w-full lg:w-1/2 flex justify-center items-center py-6 perspective-[1600px] z-10 select-none crisp-3d" 
        onMouseMove={handleMouseMove} 
        onMouseLeave={handleMouseLeave}
      >
        <div className="relative w-full max-w-md">
          {/* Parallax Floating Profit Tag (Top Right) */}
          <motion.div
            style={{ x: chipX, y: chipY }}
            className="absolute -top-5 -right-4 z-30 hidden sm:flex items-center gap-2.5 bg-white/95 backdrop-blur-2xl border border-black/[0.08] px-4 py-2.5 rounded-2xl shadow-[inset_0_1px_0_rgba(255,255,255,1),0_8px_20px_rgba(0,0,0,0.08)] crisp-3d"
          >
            <div className="w-7 h-7 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center border border-amber-200 shadow-sm">
              <Sparkles size={14} className="animate-spin-slow" />
            </div>
            <div className="crisp-3d">
              <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Top Gold Whale</div>
              <div className="text-xs font-mono font-bold text-emerald-600">+$287,153 PnL (88.8% WR)</div>
            </div>
          </motion.div>

          {/* Parallax Floating Signal Pill (Bottom Left) */}
          <motion.div
            style={{ x: chipX, y: chipY }}
            className="absolute -bottom-5 -left-4 z-30 hidden sm:flex items-center gap-2.5 bg-white/95 backdrop-blur-2xl border border-black/[0.08] px-4 py-2 rounded-2xl shadow-[inset_0_1px_0_rgba(255,255,255,1),0_8px_20px_rgba(0,0,0,0.08)] crisp-3d"
          >
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping" />
            <div className="text-[11px] font-mono font-bold text-slate-800 crisp-3d">
              Polygon Event Stream: <span className="text-emerald-600 font-extrabold">LIVE</span>
            </div>
          </motion.div>

          {/* Main 3D Card */}
          <motion.div
            style={{ 
              rotateX, 
              rotateY,
              transformStyle: 'preserve-3d',
            }}
            className="w-full p-8 rounded-3xl bg-white/85 backdrop-blur-3xl border border-white/90 shadow-[inset_0_1px_1px_rgba(255,255,255,1),0_4px_20px_rgba(0,0,0,0.04),0_28px_64px_-12px_rgba(15,23,42,0.12)] relative overflow-hidden transition-shadow duration-300 crisp-3d"
          >
            {/* Dynamic Specular Reflection / Glare Layer */}
            <motion.div 
              style={{
                background: useTransform(
                  [glareX, glareY],
                  ([x, y]) => `radial-gradient(circle at ${x}% ${y}%, rgba(255,255,255,0.75) 0%, rgba(255,255,255,0) 65%)`
                )
              }}
              className="absolute inset-0 pointer-events-none z-20 mix-blend-overlay"
            />

            {/* Header: Logo & Online Badge */}
            <div className="flex justify-between items-center mb-6 crisp-3d">
              <BrandLogo size="sm" subtitle="HyperSync v2.1 • 38ms" />
              <span className="flex items-center gap-1.5 text-xs text-emerald-800 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)] font-mono font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                {stats?.indexerStatus || 'ONLINE'}
              </span>
            </div>
            
            {/* Body Metric Containers */}
            <div className="space-y-4 crisp-3d">
              {/* Active Basket Hero Box */}
              <div className="p-5 rounded-2xl bg-slate-50/95 border border-black/[0.06] shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)] crisp-3d">
                <div className="text-xs text-slate-500 font-semibold mb-1 flex items-center justify-between">
                  <span>Active Whale Index Basket</span>
                  <span className="text-[10px] font-mono text-slate-400">Scored Daily</span>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-3xl font-extrabold text-slate-950 font-mono tracking-tight">
                    {stats?.activeBasketWhales ?? 0} Whales
                  </span>
                  <span className="text-xs text-amber-900 bg-gradient-to-r from-amber-100 to-amber-50 px-3 py-1 rounded-full font-mono font-bold border border-amber-300 shadow-sm flex items-center gap-1">
                    <Sparkles size={11} className="text-amber-600" /> Gold Tier Active
                  </span>
                </div>
              </div>
              
              {/* 2-Column Stats */}
              <div className="grid grid-cols-2 gap-3 crisp-3d">
                <div className="p-4 rounded-2xl bg-slate-50/95 border border-black/[0.06] shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)] crisp-3d">
                  <div className="text-[11px] text-slate-500 font-semibold mb-1">Total Mirrored</div>
                  <div className="text-xl font-extrabold text-slate-950 font-mono tracking-tight">
                    ${(stats?.totalVolumeMirrored ?? 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                  </div>
                </div>
                <div className="p-4 rounded-2xl bg-slate-50/95 border border-black/[0.06] shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)] crisp-3d">
                  <div className="text-[11px] text-slate-500 font-semibold mb-1">Dynamic Sizing</div>
                  <div className="text-xl font-extrabold text-emerald-600 font-mono tracking-tight flex items-center gap-1">
                    <CheckCircle2 size={16} /> 100% Live
                  </div>
                </div>
              </div>

              {/* Bottom Inset Balance */}
              <div className="p-3.5 rounded-2xl bg-slate-100/90 border border-black/[0.05] flex items-center justify-between text-xs text-slate-600 font-medium crisp-3d">
                <span>Sandbox Starting Capital</span>
                <span className="font-mono text-slate-900 font-bold">$10,000.00 Paper</span>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
