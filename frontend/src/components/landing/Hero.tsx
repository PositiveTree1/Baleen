'use client';
import { useState, useEffect } from 'react';
import { motion, useMotionValue, useTransform, useSpring } from 'framer-motion';
import { Button } from '../ui/Button';
import Link from 'next/link';
import Image from 'next/image';
import { fetchPlatformStats } from '@/lib/api-client';
import { PlatformStats } from '@/types';
import { ArrowRight, ShieldCheck, Zap, Activity, TrendingUp, CheckCircle2 } from 'lucide-react';

export function Hero() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  
  // High-precision smooth motion values
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  
  const springConfig = { damping: 20, stiffness: 150, mass: 0.5 };
  const smoothX = useSpring(mouseX, springConfig);
  const smoothY = useSpring(mouseY, springConfig);

  // 3D rotations
  const rotateX = useTransform(smoothY, [-180, 180], [14, -14]);
  const rotateY = useTransform(smoothX, [-180, 180], [-14, 14]);
  
  // Dynamic specular glare sheen position
  const glareX = useTransform(smoothX, [-180, 180], [0, 100]);
  const glareY = useTransform(smoothY, [-180, 180], [0, 100]);

  // Parallax floating satellite tags
  const chipX = useTransform(smoothX, [-180, 180], [-18, 18]);
  const chipY = useTransform(smoothY, [-180, 180], [-18, 18]);

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
      {/* 4K Nordic Icescape Background with seamless light edge blending */}
      <div className="absolute inset-y-0 right-0 w-full lg:w-2/3 pointer-events-none opacity-40 mix-blend-multiply overflow-hidden z-0">
        <div className="absolute inset-0 bg-gradient-to-r from-[#F8F9FB] via-[#F8F9FB]/60 to-transparent z-10" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#F8F9FB] via-transparent to-[#F8F9FB]/70 z-10" />
        <Image 
          src="/images/hero-icescape.jpg" 
          alt="Nordic Glacial Landscape" 
          fill
          priority
          className="object-cover object-center scale-105 filter saturate-[0.85] contrast-[1.05]"
        />
      </div>

      {/* Left Column: Typography & CTAs */}
      <div className="w-full lg:w-1/2 flex flex-col items-start gap-8 z-10">
        {/* Apple Tactile Pill Badge */}
        <div className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full text-xs font-semibold text-slate-800 bg-white/90 border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_4px_rgba(0,0,0,0.03)] backdrop-blur-md">
          <Image src="/logo.png" alt="Baleen" width={16} height={16} className="w-4 h-4 object-contain" />
          <span>Automated Polymarket Whale Index</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse ml-1" />
        </div>

        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-slate-950 leading-[1.05]">
          Mirror the top 1% <br />
          <span className="text-slate-500 font-semibold">on autopilot.</span>
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
            <span>Envio HyperSync Engine</span>
          </div>
        </div>
      </div>

      {/* Right Column: True 3D Interactive Skeuomorphic Card */}
      <div 
        className="w-full lg:w-1/2 flex justify-center items-center py-6 perspective-[1200px] z-10 select-none" 
        onMouseMove={handleMouseMove} 
        onMouseLeave={handleMouseLeave}
      >
        <div className="relative w-full max-w-md">
          {/* Parallax Floating Profit Tag (Top Right) */}
          <motion.div
            style={{ x: chipX, y: chipY }}
            className="absolute -top-4 -right-4 z-30 hidden sm:flex items-center gap-2 bg-white/95 backdrop-blur-xl border border-black/[0.08] px-3.5 py-2 rounded-2xl shadow-[inset_0_1px_0_rgba(255,255,255,1),0_4px_16px_rgba(0,0,0,0.08)] transform translate-z-[60px]"
          >
            <div className="w-6 h-6 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-200">
              <TrendingUp size={14} />
            </div>
            <div>
              <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Top Whale ROI</div>
              <div className="text-xs font-mono font-bold text-emerald-600">+142.8% (30d)</div>
            </div>
          </motion.div>

          {/* Parallax Floating Signal Pill (Bottom Left) */}
          <motion.div
            style={{ x: chipX, y: chipY }}
            className="absolute -bottom-4 -left-4 z-30 hidden sm:flex items-center gap-2.5 bg-white/95 backdrop-blur-xl border border-black/[0.08] px-3.5 py-2 rounded-2xl shadow-[inset_0_1px_0_rgba(255,255,255,1),0_4px_16px_rgba(0,0,0,0.08)]"
          >
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
            <div className="text-[11px] font-mono font-bold text-slate-800">
              Polygon Event Stream: <span className="text-emerald-600">LIVE</span>
            </div>
          </motion.div>

          {/* Main 3D Card */}
          <motion.div
            style={{ 
              rotateX, 
              rotateY,
              transformStyle: 'preserve-3d',
            }}
            className="w-full p-8 rounded-3xl bg-white/90 backdrop-blur-2xl border border-black/[0.09] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_4px_16px_rgba(0,0,0,0.04),0_24px_54px_-12px_rgba(0,0,0,0.12)] relative overflow-hidden transition-shadow duration-300"
          >
            {/* Dynamic Specular Reflection / Glare Layer */}
            <motion.div 
              style={{
                background: useTransform(
                  [glareX, glareY],
                  ([x, y]) => `radial-gradient(circle at ${x}% ${y}%, rgba(255,255,255,0.7) 0%, rgba(255,255,255,0) 60%)`
                )
              }}
              className="absolute inset-0 pointer-events-none z-20 mix-blend-overlay"
            />

            {/* Header: Logo & Online Badge (translateZ 45px) */}
            <div className="flex justify-between items-center mb-6" style={{ transform: 'translateZ(45px)' }}>
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-2xl bg-slate-900 text-white flex items-center justify-center shadow-md p-1.5">
                  <Image src="/logo.png" alt="Baleen" width={22} height={22} className="w-5 h-5 object-contain filter invert" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Baleen Engine</h3>
                  <div className="text-[10px] text-slate-400 font-mono font-medium">HyperSync v2.1</div>
                </div>
              </div>
              <span className="flex items-center gap-1.5 text-xs text-emerald-800 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)] font-mono font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                {stats?.indexerStatus || 'ONLINE'}
              </span>
            </div>
            
            {/* Body Metric Containers (translateZ 35px) */}
            <div className="space-y-4" style={{ transform: 'translateZ(35px)' }}>
              {/* Active Basket Hero Box */}
              <div className="p-5 rounded-2xl bg-slate-50 border border-black/[0.06] shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
                <div className="text-xs text-slate-500 font-semibold mb-1 flex items-center justify-between">
                  <span>Active Whale Index Basket</span>
                  <span className="text-[10px] font-mono text-slate-400">Scored Daily</span>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-3xl font-extrabold text-slate-950 font-mono tracking-tight">
                    {stats?.activeBasketWhales ?? 0} Whales
                  </span>
                  <span className="text-xs text-emerald-800 bg-emerald-100/80 px-2.5 py-0.5 rounded-full font-mono font-bold border border-emerald-200">
                    Gold Tier Only
                  </span>
                </div>
              </div>
              
              {/* 2-Column Stats */}
              <div className="grid grid-cols-2 gap-3" style={{ transform: 'translateZ(25px)' }}>
                <div className="p-4 rounded-2xl bg-slate-50 border border-black/[0.06] shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
                  <div className="text-[11px] text-slate-500 font-semibold mb-1">Total Mirrored</div>
                  <div className="text-xl font-extrabold text-slate-950 font-mono tracking-tight">
                    ${(stats?.totalVolumeMirrored ?? 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                  </div>
                </div>
                <div className="p-4 rounded-2xl bg-slate-50 border border-black/[0.06] shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
                  <div className="text-[11px] text-slate-500 font-semibold mb-1">Dynamic Sizing</div>
                  <div className="text-xl font-extrabold text-emerald-600 font-mono tracking-tight flex items-center gap-1">
                    <CheckCircle2 size={16} /> 100% Live
                  </div>
                </div>
              </div>

              {/* Bottom Inset Balance */}
              <div className="p-3.5 rounded-2xl bg-slate-100/80 border border-black/[0.05] flex items-center justify-between text-xs text-slate-600 font-medium" style={{ transform: 'translateZ(20px)' }}>
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
