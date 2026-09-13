'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, ShieldCheck, Zap, Layers, Sparkles } from 'lucide-react';
import { LiquidGlassHeroCanvas } from './LiquidGlassHeroCanvas';

export function Hero() {
  return (
    <section className="relative min-h-[840px] flex flex-col items-center justify-center overflow-hidden pt-24 sm:pt-36 pb-20 px-3 sm:px-6 lg:px-8">
      {/* Subtle Volumetric Light Cone */}
      <div className="absolute top-0 inset-x-0 h-[500px] bg-radial-[at_50%_0%] from-[#00D09C]/10 via-cyan-500/5 to-transparent pointer-events-none" />

      {/* Centered Liquid Glass Hero Stage */}
      <div className="relative z-10 mx-auto max-w-4xl text-center flex flex-col items-center w-full">
        {/* Optical Liquid Glass Pill Badge (visionOS Control Center style) */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="liquid-glass-lens liquid-chromatic-rim mb-5 sm:mb-8 inline-flex items-center gap-2 px-3.5 sm:px-5 py-1.5 sm:py-2 text-[10px] sm:text-xs font-bold tracking-wider text-white shadow-xl max-w-full"
        >
          <span className="relative flex size-2 shrink-0">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-[#00D09C] opacity-75" />
            <span className="relative inline-flex size-2 rounded-full bg-[#00D09C]" />
          </span>
          <span className="font-mono uppercase tracking-widest text-white/90">
            BALEEN ENGINE
          </span>
          <span className="text-white/20">·</span>
          <span className="font-mono text-[#00D09C] font-black">
            ISOLATED SLEEVES
          </span>
        </motion.div>

        {/* Apple-Caliber High-Contrast Headline (Responsive clamp) */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.08 }}
          className="font-outfit text-3xl sm:text-5xl lg:text-7xl font-black leading-[1.06] tracking-[-0.03em] text-white px-2"
        >
          Filter the noise.
          <span className="block mt-1 sm:mt-2 text-transparent bg-clip-text bg-gradient-to-r from-white via-white/95 to-zinc-400">
            Mirror verified conviction.
          </span>
        </motion.h1>

        {/* Concept Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.16 }}
          className="mt-4 sm:mt-6 max-w-2xl text-xs sm:text-base md:text-lg font-normal leading-relaxed text-zinc-300 px-2"
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
          {/* Primary CTA: Luminous Liquid Glass Pill */}
          <Link
            href="/dashboard"
            className="w-full sm:w-auto inline-flex h-12 sm:h-14 items-center justify-center gap-2.5 rounded-full bg-white text-black px-7 sm:px-8 text-xs sm:text-sm font-mono font-black shadow-2xl transition-all hover:bg-zinc-100 hover:scale-[1.02] active:scale-[0.98] border border-white/40"
          >
            <span>Launch $10,000 Sandbox</span>
            <ArrowRight size={14} className="transition-transform group-hover:translate-x-1 text-[#00D09C]" aria-hidden="true" />
          </Link>

          {/* Secondary CTA: Translucent Obsidian Glass Pill */}
          <Link
            href="#simulator"
            className="liquid-pill-btn w-full sm:w-auto inline-flex h-12 sm:h-14 items-center justify-center gap-2 px-6 sm:px-7 text-xs sm:text-sm font-mono font-bold text-white transition-all hover:text-white/90 border border-white/20"
          >
            <Sparkles size={14} className="text-[#00D09C]" />
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
          className="liquid-glass-lens mt-8 sm:mt-12 inline-flex flex-wrap items-center justify-center gap-x-6 gap-y-2.5 px-5 sm:px-8 py-2.5 sm:py-3 text-xs font-mono font-semibold text-zinc-300 shadow-xl max-w-[95vw]"
        >
          <span className="inline-flex items-center gap-2">
            <ShieldCheck size={14} className="text-[#00D09C]" aria-hidden="true" />
            <span>100% Risk-Free Sandbox</span>
          </span>
          <span className="text-white/20 hidden sm:inline">·</span>
          <span className="inline-flex items-center gap-2">
            <Zap size={14} className="text-cyan-400" aria-hidden="true" />
            <span>Sub-120ms Envio Pipeline</span>
          </span>
          <span className="text-white/20 hidden sm:inline">·</span>
          <span className="inline-flex items-center gap-2">
            <Layers size={14} className="text-purple-400" aria-hidden="true" />
            <span>Dynamic Bankroll Sleeves</span>
          </span>
        </motion.div>
      </div>

      {/* Subtle Bottom Separator */}
      <div className="absolute bottom-0 inset-x-0 h-px bg-white/10" />
    </section>
  );
}
