'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, ShieldCheck, Zap, Layers, Sparkles } from 'lucide-react';
import { LiquidGlassHeroCanvas } from './LiquidGlassHeroCanvas';

export function Hero() {
  return (
    <section className="relative min-h-[840px] flex flex-col items-center justify-center overflow-hidden pt-24 sm:pt-36 pb-20 px-3 sm:px-6 lg:px-8">
      {/* Volumetric Arctic Illumination Cone */}
      <div className="absolute top-0 inset-x-0 h-[520px] bg-radial-[at_50%_0%] from-sky-200/50 via-cyan-100/25 to-transparent pointer-events-none" />

      {/* Centered Liquid Glass Hero Stage */}
      <div className="relative z-10 mx-auto max-w-4xl text-center flex flex-col items-center w-full">
        {/* Optical Liquid Glass Pill Badge (visionOS Control Center style) */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="glass-dock glass-chromatic-bezel mb-5 sm:mb-8 inline-flex items-center gap-2 px-3.5 sm:px-5 py-1.5 sm:py-2 text-[10px] sm:text-xs font-bold tracking-wider text-slate-200 shadow-md max-w-full border border-white/20"
        >
          <span className="relative flex size-2 shrink-0">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex size-2 rounded-full bg-emerald-400" />
          </span>
          <span className="font-mono uppercase tracking-widest text-slate-300">
            BALEEN ENGINE
          </span>
          <span className="text-slate-500">·</span>
          <span className="font-mono text-sky-400 font-black">
            ISOLATED SLEEVES
          </span>
        </motion.div>

        {/* Apple-Caliber High-Contrast Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.08 }}
          className="font-outfit text-3xl sm:text-5xl lg:text-7xl font-black leading-[1.06] tracking-[-0.03em] text-white px-2"
        >
          Filter the noise.
          <span className="block mt-1 sm:mt-2 text-transparent bg-clip-text bg-gradient-to-r from-white via-sky-200 to-cyan-400">
            Mirror verified conviction.
          </span>
        </motion.h1>

        {/* Concept Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.16 }}
          className="mt-4 sm:mt-6 max-w-2xl text-xs sm:text-base md:text-lg font-normal leading-relaxed text-slate-300 px-2"
        >
          Just as the baleen whale filters ocean waters to capture pure sustenance, Baleen indexes millions of Polymarket trades in real-time, isolating verified whale convictions across strictly segregated risk sleeves.
        </motion.p>

        {/* Action Controls: Tactile Liquid Glass Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.24 }}
          className="mt-7 sm:mt-10 flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 w-full max-w-md px-3"
        >
          {/* Primary CTA: High-Contrast Luminous Action Pill */}
          <Link
            href="/dashboard"
            className="w-full sm:w-auto inline-flex h-12 sm:h-14 items-center justify-center gap-2.5 rounded-full bg-gradient-to-r from-sky-500 to-cyan-500 text-white px-7 sm:px-8 text-xs sm:text-sm font-mono font-black shadow-lg shadow-sky-500/30 transition-all hover:from-sky-400 hover:to-cyan-400 hover:scale-[1.02] active:scale-[0.98] border border-white/40"
          >
            <span>Launch $10,000 Sandbox</span>
            <ArrowRight size={14} className="transition-transform group-hover:translate-x-1 text-white" aria-hidden="true" />
          </Link>

          {/* Secondary CTA: Translucent Liquid Glass Pill */}
          <Link
            href="#simulator"
            className="glass-button w-full sm:w-auto inline-flex h-12 sm:h-14 items-center justify-center gap-2 px-6 sm:px-7 text-xs sm:text-sm font-mono font-bold text-white transition-all shadow-sm rounded-full"
          >
            <Sparkles size={14} className="text-sky-400" />
            <span>Interactive Simulator</span>
          </Link>
        </motion.div>

        {/* Liquid Glass Interactive Centerpiece */}
        <div className="w-full mt-3 sm:mt-4">
          <LiquidGlassHeroCanvas />
        </div>

        {/* Liquid Glass Feature Strip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.35 }}
          className="glass-dock glass-chromatic-bezel mt-8 sm:mt-12 inline-flex flex-wrap items-center justify-center gap-x-6 gap-y-2.5 px-5 sm:px-8 py-2.5 sm:py-3 text-xs font-mono font-semibold text-slate-200 shadow-md max-w-[95vw] border border-white/20"
        >
          <span className="inline-flex items-center gap-2">
            <ShieldCheck size={14} className="text-emerald-400" aria-hidden="true" />
            <span>100% Risk-Free Sandbox</span>
          </span>
          <span className="text-slate-600 hidden sm:inline">·</span>
          <span className="inline-flex items-center gap-2">
            <Zap size={14} className="text-sky-400" aria-hidden="true" />
            <span>Sub-120ms Envio Pipeline</span>
          </span>
          <span className="text-slate-600 hidden sm:inline">·</span>
          <span className="inline-flex items-center gap-2">
            <Layers size={14} className="text-indigo-400" aria-hidden="true" />
            <span>Dynamic Bankroll Sleeves</span>
          </span>
        </motion.div>
      </div>

      {/* Subtle Bottom Separator */}
      <div className="absolute bottom-0 inset-x-0 h-px bg-white/10" />
    </section>
  );
}
