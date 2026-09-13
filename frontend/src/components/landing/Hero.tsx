'use client';

import Image from 'next/image';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, ShieldCheck, Zap, TrendingUp, Radio, ChevronRight, Layers } from 'lucide-react';

const mockSignals = [
  { market: 'Fed Rate Cut in June', side: 'YES', price: '$0.64', pnl: '+$412.50', whale: 'RevengeRange' },
  { market: 'BTC Crosses $100k EOY', side: 'YES', price: '$0.71', pnl: '+$680.00', whale: 'THEHIGHLIFE' },
  { market: 'US Debt Ceiling Passes', side: 'NO', price: '$0.38', pnl: '+$295.20', whale: 'Jackenand' },
];

export function Hero() {
  return (
    <section className="relative min-h-[860px] overflow-hidden bg-[#07080A] text-white sm:min-h-[920px] lg:min-h-[980px]">
      {/* Matte Black Obsidian Silk Texture Backdrop */}
      <div className="absolute inset-0 z-0 select-none overflow-hidden">
        <Image
          src="/images/cta_obsidian_silk.jpg"
          alt="Matte black brushed obsidian metallic texture"
          fill
          priority
          sizes="100vw"
          className="object-cover opacity-25 mix-blend-screen"
        />
        {/* Subtle Dark Vignette & Atmospheric Depth */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#07080A] via-[#07080A]/80 to-transparent sm:w-3/4" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#07080A] via-[#07080A]/60 to-transparent" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(0,208,156,0.06),transparent_65%)]" />
      </div>

      <div className="relative z-10 mx-auto grid min-h-[860px] max-w-[1380px] items-center gap-12 px-5 pb-24 pt-32 sm:min-h-[920px] sm:px-8 sm:pb-28 sm:pt-36 lg:min-h-[980px] lg:grid-cols-[1.12fr_.88fr] lg:px-12">
        {/* Left Column: Revolut FinTech High-Contrast Typography */}
        <div className="max-w-[720px]">
          {/* Institutional Status Badge */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="mb-6 inline-flex items-center gap-2.5 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-xs font-bold tracking-wider text-zinc-300 backdrop-blur-2xl shadow-xl"
          >
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-[#00D09C] opacity-75" />
              <span className="relative inline-flex size-2 rounded-full bg-[#00D09C]" />
            </span>
            <span className="font-mono text-[11px] text-zinc-200 uppercase">BALEEN PROTOCOL</span>
            <span className="text-white/20">|</span>
            <span className="font-mono text-[#00D09C]">5-WALLET ISOLATED SLEEVES</span>
          </motion.div>

          {/* Clean Main Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.08 }}
            className="font-outfit text-[clamp(3.2rem,6.5vw,5.8rem)] font-black leading-[0.94] tracking-[-0.05em] text-white"
          >
            Follow the signal.
            <span className="block text-zinc-400 font-extrabold tracking-[-0.05em]">
              Not the crowd.
            </span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.16 }}
            className="mt-6 max-w-xl text-base font-normal leading-relaxed text-zinc-400 sm:text-lg"
          >
            Baleen shadows verified high-conviction Polymarket alpha in sub-120ms isolated sleeves. Evaluated across $10,000 risk-free allocations before live execution.
          </motion.p>

          {/* Action CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.24 }}
            className="mt-8 flex flex-col gap-3.5 sm:flex-row sm:items-center"
          >
            <Link
              href="/dashboard"
              className="group inline-flex h-13 items-center justify-center gap-3 rounded-full bg-white px-8 text-sm font-extrabold text-black shadow-xl transition-all hover:bg-zinc-200 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            >
              <span>Launch $10,000 Sandbox</span>
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" aria-hidden="true" />
            </Link>

            <Link
              href="#simulator"
              className="inline-flex h-13 items-center justify-center gap-2 rounded-full border border-white/15 bg-white/[0.04] px-7 text-sm font-bold text-white backdrop-blur-2xl transition-all hover:bg-white/[0.08] hover:border-white/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
            >
              <span>Explore Compounding</span>
              <ChevronRight size={16} className="text-zinc-400" />
            </Link>
          </motion.div>

          {/* Clean Trust Indicators */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.36 }}
            className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-3 text-xs font-semibold text-zinc-400 font-mono"
          >
            <span className="inline-flex items-center gap-2">
              <ShieldCheck size={15} className="text-[#00D09C]" aria-hidden="true" />
              <span>No Wallet Connection Needed</span>
            </span>
            <span className="inline-flex items-center gap-2">
              <Zap size={15} className="text-white" aria-hidden="true" />
              <span>Sub-120ms Envio Pipeline</span>
            </span>
            <span className="inline-flex items-center gap-2">
              <Layers size={15} className="text-zinc-300" aria-hidden="true" />
              <span>Isolated $2k Sleeves</span>
            </span>
          </motion.div>
        </div>

        {/* Right Column: Apple Optical Liquid Glass Card */}
        <motion.div
          initial={{ opacity: 0, x: 30, scale: 0.96 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          transition={{ duration: 0.85, delay: 0.22, ease: [0.16, 1, 0.3, 1] }}
          className="justify-self-center w-full max-w-[460px] lg:justify-self-end"
        >
          <div className="apple-glass-card apple-lens-refraction relative overflow-hidden rounded-[32px] p-6 shadow-2xl border border-white/15 bg-[#0E1015]/90 backdrop-blur-3xl">
            {/* Top Bar of Card */}
            <div className="relative z-10 flex items-start justify-between">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 font-mono">
                  Sandbox Portfolio Allocation
                </span>
                <div className="mt-1 flex items-baseline gap-2.5">
                  <span className="font-mono text-3xl sm:text-4xl font-black tracking-tight text-white tabular-nums">
                    $14,752.18
                  </span>
                </div>
              </div>

              <div className="flex flex-col items-end gap-1">
                <span className="inline-flex items-center gap-1 rounded-full bg-[#00D09C]/10 border border-[#00D09C]/25 px-2.5 py-1 text-xs font-mono font-bold text-[#00D09C]">
                  <TrendingUp size={12} />
                  +47.52%
                </span>
                <span className="text-[10px] text-zinc-400 font-mono">+$4,752.18 Net</span>
              </div>
            </div>

            {/* Revolut Glowing Curve SVG */}
            <div className="relative z-10 mt-6 h-32 overflow-hidden rounded-2xl bg-black/40 border border-white/10 p-2">
              <svg viewBox="0 0 420 120" className="size-full" preserveAspectRatio="none" aria-hidden="true">
                <defs>
                  <linearGradient id="heroCurveArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00D09C" stopOpacity="0.30" />
                    <stop offset="100%" stopColor="#00D09C" stopOpacity="0.0" />
                  </linearGradient>
                  <filter id="revolutCurveGlow" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="2" stdDeviation="5" floodColor="#00D09C" floodOpacity="0.5" />
                  </filter>
                </defs>
                <path
                  d="M0 100 C 40 95, 70 82, 110 88 C 150 94, 180 62, 220 54 C 260 46, 290 60, 330 32 C 370 12, 395 18, 420 8 L 420 120 L 0 120 Z"
                  fill="url(#heroCurveArea)"
                />
                <path
                  d="M0 100 C 40 95, 70 82, 110 88 C 150 94, 180 62, 220 54 C 260 46, 290 60, 330 32 C 370 12, 395 18, 420 8"
                  fill="none"
                  stroke="#00D09C"
                  strokeWidth="3"
                  strokeLinecap="round"
                  filter="url(#revolutCurveGlow)"
                  className="revolut-glow-line"
                />
                <circle cx="420" cy="8" r="4" fill="#00D09C" />
              </svg>
            </div>

            {/* 5-Sleeve Basket Overview */}
            <div className="relative z-10 mt-5">
              <div className="flex items-center justify-between pb-2 border-b border-white/10 text-[11px] font-bold uppercase tracking-wider text-zinc-400 font-mono">
                <span>Active 5-Sleeve Tier</span>
                <span className="text-white">$2,000 / Sleeve</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {[
                  { name: 'RevengeRange', wr: '94.2%' },
                  { name: 'THEHIGHLIFE', wr: '88.5%' },
                  { name: 'Jackenand', wr: '91.0%' },
                  { name: 'Flipadelphia', wr: '84.6%' },
                ].map((whale) => (
                  <span
                    key={whale.name}
                    className="inline-flex items-center gap-1.5 rounded-full bg-white/[0.05] border border-white/10 px-3 py-1 text-xs font-medium text-zinc-200"
                  >
                    <span className="size-1.5 rounded-full bg-[#00D09C]" />
                    <span className="font-mono text-xs">{whale.name}</span>
                    <span className="text-[10px] text-[#00D09C] font-mono font-bold">({whale.wr})</span>
                  </span>
                ))}
              </div>
            </div>

            {/* Recent Execution Tape */}
            <div className="relative z-10 mt-5 space-y-2 border-t border-white/10 pt-4">
              <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-zinc-400 font-mono">
                <span>Live Shadow Tape</span>
                <span className="flex items-center gap-1 text-[#00D09C]">
                  <Radio size={11} className="animate-pulse" /> Sub-120ms
                </span>
              </div>
              <div className="divide-y divide-white/[0.06]">
                {mockSignals.map((item) => (
                  <div key={item.market} className="flex items-center justify-between py-2 text-xs">
                    <div className="min-w-0 pr-2">
                      <p className="font-semibold text-white truncate text-xs">{item.market}</p>
                      <p className="text-[10px] text-zinc-400 font-mono">via {item.whale}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="rounded-md bg-white/10 px-2 py-0.5 text-[10px] font-bold font-mono text-zinc-200">
                        {item.side} {item.price}
                      </span>
                      <span className="font-mono text-xs font-bold text-[#00D09C]">{item.pnl}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Subtle Bottom Separator */}
      <div className="absolute bottom-0 inset-x-0 h-px bg-white/10" />
    </section>
  );
}

