'use client';

import Image from 'next/image';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, Sparkles, ShieldCheck, Zap, TrendingUp, Radio, ChevronRight } from 'lucide-react';

const mockSignals = [
  { market: 'Fed Rate Cut in June', side: 'YES', price: '$0.64', pnl: '+$412.50', whale: 'RevengeRange' },
  { market: 'BTC Crosses $100k EOY', side: 'YES', price: '$0.71', pnl: '+$680.00', whale: 'THEHIGHLIFE' },
  { market: 'US Debt Ceiling Passes', side: 'NO', price: '$0.38', pnl: '+$295.20', whale: 'Jackenand' },
];

export function Hero() {
  return (
    <section className="relative min-h-[860px] overflow-hidden bg-[#040914] text-white sm:min-h-[920px] lg:min-h-[980px]">
      {/* Pacific Surrealism Masterpiece Background */}
      <div className="absolute inset-0 z-0 select-none">
        <Image
          src="/images/baleen-pacific-surreal.jpg"
          alt="Pacific Coast twilight sanctuary fusing Hiroshi Nagai vibrant pool with René Magritte sheltering canopy"
          fill
          priority
          sizes="100vw"
          className="object-cover object-[center_30%] sm:object-center"
        />
        {/* Seamless Radial & Directional Vignettes */}
        <div className="absolute inset-0 bg-radial-vignette opacity-80" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#040914] via-[#040914]/85 to-transparent sm:w-3/4" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#060c1b] via-[#060c1b]/60 to-transparent" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(79,228,241,0.18),transparent_60%)]" />
        <div className="hero-grain absolute inset-0 opacity-[0.22]" aria-hidden="true" />
      </div>

      <div className="relative z-10 mx-auto grid min-h-[860px] max-w-[1380px] items-center gap-12 px-5 pb-24 pt-32 sm:min-h-[920px] sm:px-8 sm:pb-28 sm:pt-36 lg:min-h-[980px] lg:grid-cols-[1.12fr_.88fr] lg:px-12">
        {/* Left Column: Revolut-Style High Contrast Typography */}
        <div className="max-w-[720px]">
          {/* Status Badge */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="mb-6 inline-flex items-center gap-2.5 rounded-full border border-white/20 bg-black/40 px-4 py-2 text-xs font-bold tracking-wider text-cyan-200 backdrop-blur-2xl shadow-lg"
          >
            <span className="relative flex size-2.5">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex size-2.5 rounded-full bg-emerald-400" />
            </span>
            <span>LIVE POLYMARKET INTELLIGENCE</span>
            <span className="text-white/30">|</span>
            <span className="font-mono text-emerald-300">91.4% AVG WIN RATE</span>
          </motion.div>

          {/* Main Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.08 }}
            className="font-outfit text-[clamp(3.2rem,6.5vw,5.8rem)] font-black leading-[0.92] tracking-[-0.055em] text-white"
          >
            Follow the signal.
            <span className="block surreal-text-gradient drop-shadow-sm">
              Not the crowd.
            </span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.16 }}
            className="mt-6 max-w-xl text-base font-normal leading-relaxed text-slate-200/90 sm:text-lg"
          >
            Baleen shadows verified high-conviction Polymarket whales in sub-120ms isolated sleeves. Tested across $10,000 risk-free paper allocations before any live execution.
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
              className="group inline-flex h-14 items-center justify-center gap-3 rounded-full bg-white px-8 text-sm font-extrabold text-slate-950 shadow-[0_12px_35px_rgba(79,228,241,0.25)] transition-all hover:bg-cyan-50 hover:shadow-[0_16px_45px_rgba(79,228,241,0.35)] active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
            >
              <span>Launch $10,000 Sandbox</span>
              <ArrowRight size={17} className="transition-transform group-hover:translate-x-1" aria-hidden="true" />
            </Link>

            <Link
              href="#simulator"
              className="inline-flex h-14 items-center justify-center gap-2 rounded-full border border-white/20 bg-white/[0.08] px-7 text-sm font-bold text-white backdrop-blur-2xl transition-all hover:bg-white/[0.16] hover:border-white/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
            >
              <span>Explore Compounding</span>
              <ChevronRight size={16} className="text-white/60" />
            </Link>
          </motion.div>

          {/* Trust Highlights */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.36 }}
            className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-3 text-xs font-semibold text-white/70"
          >
            <span className="inline-flex items-center gap-2">
              <ShieldCheck size={16} className="text-emerald-400" aria-hidden="true" />
              <span>No Wallet Connection Needed</span>
            </span>
            <span className="inline-flex items-center gap-2">
              <Zap size={16} className="text-cyan-300" aria-hidden="true" />
              <span>Sub-120ms Envio Pipeline</span>
            </span>
            <span className="inline-flex items-center gap-2">
              <Sparkles size={16} className="text-amber-300" aria-hidden="true" />
              <span>Isolated $2k Sleeves</span>
            </span>
          </motion.div>
        </div>

        {/* Right Column: Apple Liquid Glass Card Mockup */}
        <motion.div
          initial={{ opacity: 0, x: 30, scale: 0.96 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          transition={{ duration: 0.85, delay: 0.22, ease: [0.16, 1, 0.3, 1] }}
          className="justify-self-center w-full max-w-[460px] lg:justify-self-end"
        >
          <div className="liquid-glass-card relative overflow-hidden rounded-[32px] p-6 shadow-2xl border border-white/20">
            {/* Specular Inner Rim Light */}
            <div className="absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-black/20 pointer-events-none" />

            {/* Top Bar of Glass Card */}
            <div className="relative z-10 flex items-start justify-between">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-200/80">
                  Paper Portfolio Sleeve
                </span>
                <div className="mt-1 flex items-baseline gap-2.5">
                  <span className="font-mono text-3xl sm:text-4xl font-black tracking-tight text-white tabular-nums">
                    $14,752.18
                  </span>
                </div>
              </div>

              <div className="flex flex-col items-end gap-1.5">
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-400/30 px-2.5 py-1 text-xs font-mono font-bold text-emerald-300">
                  <TrendingUp size={12} />
                  +47.52%
                </span>
                <span className="text-[10px] text-white/50 font-mono">+$4,752.18 Alpha</span>
              </div>
            </div>

            {/* Dynamic Equity Curve SVG */}
            <div className="relative z-10 mt-6 h-32 overflow-hidden rounded-2xl bg-gradient-to-b from-cyan-500/10 to-transparent border border-white/10 p-2">
              <svg viewBox="0 0 420 120" className="size-full" preserveAspectRatio="none" aria-hidden="true">
                <defs>
                  <linearGradient id="heroCurveArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4fe4f1" stopOpacity="0.45" />
                    <stop offset="100%" stopColor="#00d09c" stopOpacity="0.0" />
                  </linearGradient>
                  <linearGradient id="heroCurveStroke" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#38bdf8" />
                    <stop offset="50%" stopColor="#4fe4f1" />
                    <stop offset="100%" stopColor="#10b981" />
                  </linearGradient>
                </defs>
                <path
                  d="M0 100 C 40 95, 70 82, 110 88 C 150 94, 180 62, 220 54 C 260 46, 290 60, 330 32 C 370 12, 395 18, 420 8 L 420 120 L 0 120 Z"
                  fill="url(#heroCurveArea)"
                />
                <path
                  d="M0 100 C 40 95, 70 82, 110 88 C 150 94, 180 62, 220 54 C 260 46, 290 60, 330 32 C 370 12, 395 18, 420 8"
                  fill="none"
                  stroke="url(#heroCurveStroke)"
                  strokeWidth="3.5"
                  strokeLinecap="round"
                />
                <circle cx="420" cy="8" r="4.5" fill="#4fe4f1" className="animate-pulse" />
              </svg>
            </div>

            {/* Active Whale Sleeve Badges */}
            <div className="relative z-10 mt-5">
              <div className="flex items-center justify-between pb-2 border-b border-white/10 text-[11px] font-bold uppercase tracking-wider text-white/50">
                <span>Active 5-Sleeve Basket</span>
                <span className="text-cyan-300 font-mono">$2,000 / Sleeve</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {[
                  { name: 'RevengeRange', wr: '94.2%', tier: 'Gold' },
                  { name: 'THEHIGHLIFE', wr: '88.5%', tier: 'Gold' },
                  { name: 'Jackenand', wr: '91.0%', tier: 'Gold' },
                  { name: 'Flipadelphia', wr: '84.6%', tier: 'Active' },
                ].map((whale) => (
                  <span
                    key={whale.name}
                    className="inline-flex items-center gap-1.5 rounded-full bg-white/[0.08] border border-white/15 px-3 py-1 text-xs font-medium text-white/90"
                  >
                    <span className="size-1.5 rounded-full bg-emerald-400" />
                    <span className="font-mono text-xs">{whale.name}</span>
                    <span className="text-[10px] text-emerald-300 font-mono font-bold">({whale.wr})</span>
                  </span>
                ))}
              </div>
            </div>

            {/* Recent Executions Strip */}
            <div className="relative z-10 mt-5 space-y-2 border-t border-white/10 pt-4">
              <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-white/45">
                <span>Live Feed</span>
                <span className="flex items-center gap-1 text-emerald-300 font-mono">
                  <Radio size={11} className="animate-pulse" /> Sub-120ms Fills
                </span>
              </div>
              <div className="divide-y divide-white/[0.06]">
                {mockSignals.map((item) => (
                  <div key={item.market} className="flex items-center justify-between py-2 text-xs">
                    <div className="min-w-0 pr-2">
                      <p className="font-semibold text-white truncate text-xs">{item.market}</p>
                      <p className="text-[10px] text-white/50 font-mono">via {item.whale}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="rounded-md bg-white/10 px-2 py-0.5 text-[10px] font-bold font-mono text-cyan-200">
                        {item.side} {item.price}
                      </span>
                      <span className="font-mono text-xs font-bold text-emerald-300">{item.pnl}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Subtle Bottom Separator */}
      <div className="absolute bottom-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent" />
    </section>
  );
}
