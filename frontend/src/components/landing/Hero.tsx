'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, ShieldCheck, Zap, Layers, Sparkles } from 'lucide-react';

export function Hero() {
  return (
    <section className="relative min-h-[780px] sm:min-h-[840px] flex items-center justify-center overflow-hidden pt-28 pb-20 px-5 sm:px-8">
      {/* Centered Liquid Glass Hero Stage */}
      <div className="relative z-10 mx-auto max-w-4xl text-center flex flex-col items-center">
        {/* Optical Liquid Glass Pill Badge */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="liquid-glass-lens liquid-chromatic-rim mb-8 inline-flex items-center gap-3 px-5 py-2 text-xs font-bold tracking-wider text-white"
        >
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-[#00D09C] opacity-75" />
            <span className="relative inline-flex size-2 rounded-full bg-[#00D09C]" />
          </span>
          <span className="font-mono text-[11px] uppercase tracking-widest text-white/90">BALEEN FILTER ENGINE</span>
          <span className="text-white/25">|</span>
          <span className="font-mono text-[#00D09C]">ISOLATED SLEEVE AUTOPILOT</span>
        </motion.div>

        {/* Cinematic Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.08 }}
          className="font-outfit text-[clamp(2.8rem,7vw,5.5rem)] font-black leading-[0.96] tracking-[-0.04em] text-white"
        >
          Filter the noise.
          <span className="block mt-2 text-transparent bg-clip-text bg-gradient-to-r from-white via-white/80 to-white/40">
            Mirror verified conviction.
          </span>
        </motion.h1>

        {/* Concept Subtitle: Baleen Whale Filtering Analogy */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.16 }}
          className="mt-6 max-w-2xl text-base sm:text-lg font-normal leading-relaxed text-zinc-400"
        >
          Just as the baleen filters vast oceans to extract pure sustenance, Baleen processes millions of Polymarket trades to isolate verified, non-bot alpha. Shadow qualified whale convictions in real-time.
        </motion.p>

        {/* Action Controls: Tactile Liquid Glass Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.24 }}
          className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 w-full max-w-md"
        >
          <Link
            href="/dashboard"
            className="group w-full sm:w-auto inline-flex h-14 items-center justify-center gap-3 rounded-full bg-white px-9 text-sm font-extrabold text-black shadow-2xl transition-all hover:bg-zinc-100 hover:scale-[1.03] active:scale-[0.98]"
          >
            <span>Launch $10,000 Sandbox</span>
            <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" aria-hidden="true" />
          </Link>

          <Link
            href="#advantages"
            className="liquid-pill-btn w-full sm:w-auto inline-flex h-14 items-center justify-center gap-2 px-8 text-sm font-bold text-white transition-all hover:text-white/90"
          >
            <Sparkles size={15} className="text-[#00D09C]" />
            <span>Architecture</span>
          </Link>
        </motion.div>

        {/* Liquid Glass Feature Strip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.36 }}
          className="liquid-glass-lens mt-14 inline-flex flex-wrap items-center justify-center gap-x-8 gap-y-3 px-6 py-3 text-xs font-semibold text-zinc-300 font-mono"
        >
          <span className="inline-flex items-center gap-2">
            <ShieldCheck size={15} className="text-[#00D09C]" aria-hidden="true" />
            <span>Risk-Free Paper Sandbox</span>
          </span>
          <span className="inline-flex items-center gap-2">
            <Zap size={15} className="text-cyan-400" aria-hidden="true" />
            <span>Sub-120ms Envio Hypersync</span>
          </span>
          <span className="inline-flex items-center gap-2">
            <Layers size={15} className="text-purple-400" aria-hidden="true" />
            <span>Dynamic Bankroll Sleeves</span>
          </span>
        </motion.div>
      </div>

      {/* Subtle Bottom Separator */}
      <div className="absolute bottom-0 inset-x-0 h-px bg-white/10" />
    </section>
  );
}
