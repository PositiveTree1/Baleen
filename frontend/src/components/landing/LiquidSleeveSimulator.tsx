'use client';

import { useState, useId } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Sliders, ArrowRight, CheckCircle2, Droplets, Zap } from 'lucide-react';
import Link from 'next/link';

export function LiquidSleeveSimulator() {
  const [bankroll, setBankroll] = useState<number>(5000);
  const sliderId = useId();

  // Dynamic sleeve allocation math
  const sleeveCount = bankroll < 500 ? 1 : bankroll < 2000 ? 2 : bankroll < 5000 ? 3 : bankroll < 10000 ? 4 : 5;
  const sleeveCap = Math.min(2000, Math.round(bankroll / sleeveCount));
  const fillPercentage = Math.min(100, Math.max(18, (sleeveCap / 2000) * 100));
  const estimatedMonthlyAlpha = Math.round(bankroll * 0.284);

  return (
    <section id="simulator" className="relative overflow-hidden px-4 sm:px-6 lg:px-8 py-20 sm:py-32 border-b border-white/10">
      <div className="mx-auto max-w-[1240px]">
        {/* Section Header */}
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.04] px-3.5 py-1 text-xs font-mono font-bold tracking-wider text-[#00D09C] backdrop-blur-xl">
            <Sliders size={13} />
            <span>INTERACTIVE CAPITAL ENGINE</span>
          </div>
          <h2 className="mt-4 font-outfit text-3xl sm:text-5xl font-black tracking-tight text-white leading-[1.05]">
            Dynamic Isolated Sleeves.
            <span className="block text-zinc-400 font-extrabold">Never risk portfolio contagion.</span>
          </h2>
          <p className="mt-4 text-sm sm:text-base text-zinc-400 leading-relaxed">
            Drag the capital slider to watch Baleen automatically partition your bankroll into independent liquid glass risk sleeves. If one whale suffers variance, your other sleeves remain completely untouched.
          </p>
        </div>

        {/* Interactive Simulator Console */}
        <div className="mt-10 sm:mt-12 rounded-[36px] border border-white/15 bg-gradient-to-b from-white/[0.07] via-white/[0.02] to-black/70 p-5 sm:p-10 backdrop-blur-3xl shadow-2xl">
          {/* Target Portfolio Bankroll & Slider Header */}
          <div className="rounded-3xl border border-white/10 bg-black/40 p-5 sm:p-7 backdrop-blur-2xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <label htmlFor={sliderId} className="text-xs font-mono font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                  <Droplets size={14} className="text-[#00D09C]" />
                  <span>Target Portfolio Bankroll</span>
                </label>
                <div className="text-xs font-mono text-zinc-500 mt-0.5">
                  Allocates capital across 1–5 mathematically isolated risk boundaries
                </div>
              </div>
              <div className="font-mono text-3xl sm:text-4xl font-black text-white tabular-nums tracking-tight">
                ${bankroll.toLocaleString()}
              </div>
            </div>

            {/* Custom Tactile Liquid Slider */}
            <div className="mt-5 relative">
              <input
                id={sliderId}
                type="range"
                min="200"
                max="20000"
                step="200"
                value={bankroll}
                aria-label="Target portfolio bankroll"
                onChange={(e) => setBankroll(Number(e.target.value))}
                className="w-full h-2.5 rounded-full appearance-none cursor-pointer bg-white/15 accent-[#00D09C] transition-all"
              />
              <div className="flex justify-between text-[10px] sm:text-xs font-mono text-zinc-400 mt-2.5">
                <span>$200 (1 Sleeve)</span>
                <span className="hidden sm:inline">$2,000 (2 Sleeves)</span>
                <span>$5,000 (3 Sleeves)</span>
                <span className="hidden sm:inline">$10,000 (4 Sleeves)</span>
                <span>$20,000 (5 Sleeves)</span>
              </div>
            </div>
          </div>

          {/* 3D Liquid Glass Vials Visualizer (Prominently Placed for Both Desktop & Mobile) */}
          <div className="mt-6 sm:mt-8 p-5 sm:p-8 rounded-3xl border border-white/15 bg-black/50 backdrop-blur-3xl shadow-inner">
            <div className="flex items-center justify-between mb-6 font-mono text-xs text-zinc-400">
              <div className="flex items-center gap-2">
                <Shield size={14} className="text-[#00D09C]" />
                <span className="font-bold text-white uppercase tracking-wider text-[11px] sm:text-xs">
                  Liquid Risk Isolation Vials
                </span>
              </div>
              <span className="text-[#00D09C] font-bold text-[10px] sm:text-xs">
                {sleeveCount} of 5 Sleeves Active
              </span>
            </div>

            {/* 5 Vertical Liquid Glass Vials (Clean Responsive Grid) */}
            <div className="grid grid-cols-5 gap-2 sm:gap-6 h-56 sm:h-64 w-full items-end justify-items-center">
              {Array.from({ length: 5 }).map((_, idx) => {
                const isActive = idx < sleeveCount;
                const label = ['A', 'B', 'C', 'D', 'E'][idx];
                const whaleAddr = ['0x12a9', '0x7bf3', '0x4981', '0xce92', '0x38e1'][idx];

                return (
                  <div
                    key={label}
                    className="relative flex flex-col items-center h-full w-full max-w-[72px]"
                  >
                    {/* Outer 3D Liquid Glass Vial Tube */}
                    <div
                      className={`relative w-full h-full rounded-[24px] sm:rounded-[30px] overflow-hidden transition-all duration-500 flex flex-col justify-end p-1 sm:p-1.5 ${
                        isActive
                          ? 'border-1.5 border-white/40 shadow-[0_10px_35px_rgba(0,208,156,0.3)]'
                          : 'border border-white/10 opacity-35'
                      }`}
                      style={{
                        background:
                          'radial-gradient(120% 100% at 50% 10%, rgba(255,255,255,0.25) 0%, rgba(255,255,255,0.04) 60%, rgba(0,0,0,0.6) 100%)',
                        backdropFilter: 'blur(24px) saturate(200%)',
                        boxShadow: isActive
                          ? 'inset 0 2.5px 2px 0 rgba(255,255,255,0.9), inset 0 -2.5px 2px 0 rgba(0,0,0,0.6)'
                          : undefined,
                      }}
                    >
                      {/* Top Specular Arc Highlight */}
                      <div className="absolute top-1.5 inset-x-2 h-3 rounded-full bg-gradient-to-b from-white/95 to-transparent pointer-events-none z-20" />

                      {/* Animated Fluid Liquid Level */}
                      <AnimatePresence>
                        {isActive && (
                          <motion.div
                            initial={{ height: 0 }}
                            animate={{ height: `${fillPercentage}%` }}
                            exit={{ height: 0 }}
                            transition={{ type: 'spring', stiffness: 220, damping: 22 }}
                            className="relative w-full rounded-[18px] sm:rounded-[24px] overflow-hidden"
                            style={{
                              background:
                                'linear-gradient(180deg, rgba(56, 189, 248, 0.85) 0%, rgba(0, 208, 156, 0.9) 60%, rgba(0, 160, 120, 0.95) 100%)',
                              boxShadow:
                                'inset 0 2px 4px rgba(255,255,255,0.95), 0 0 24px rgba(0,208,156,0.65)',
                            }}
                          >
                            {/* Fluid Meniscus Curve on top of liquid */}
                            <div className="absolute top-0 inset-x-0 h-2 sm:h-2.5 bg-white/80 rounded-full blur-[0.5px]" />
                            {/* Liquid Wave Ripple Shimmer */}
                            <div className="absolute inset-0 bg-radial-[at_50%_0%] from-white/30 via-transparent to-transparent pointer-events-none" />
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {/* Glass Tube Bevel Edges */}
                      <div className="absolute inset-0 rounded-[24px] sm:rounded-[30px] border border-white/15 pointer-events-none" />
                      {/* Bottom Specular Reflection */}
                      <div className="absolute bottom-1 inset-x-2.5 h-1 rounded-full bg-gradient-to-r from-cyan-400/40 via-white/60 to-purple-400/40 pointer-events-none" />
                    </div>

                    {/* Vial Label & Capital Metric */}
                    <div className="mt-2 text-center font-mono">
                      <div className="text-[10px] sm:text-xs font-black text-white">Sleeve {label}</div>
                      <div className="text-[9px] sm:text-[10px] font-bold text-zinc-400 truncate">
                        {isActive ? `$${sleeveCap}` : 'Guarded'}
                      </div>
                      <div className="text-[8px] text-zinc-500 hidden sm:block">
                        {isActive ? whaleAddr : 'Isolated'}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Visualizer Status Footer */}
            <div className="mt-6 flex flex-wrap items-center justify-between gap-2 pt-4 border-t border-white/10 text-[10px] sm:text-xs font-mono text-zinc-400">
              <span className="flex items-center gap-1.5">
                <span className="size-1.5 rounded-full bg-[#00D09C] animate-ping" />
                <span>Zero Cross-Sleeve Contagion</span>
              </span>
              <span className="text-[#00D09C] font-bold">100% Mathematical Boundary Enforced</span>
            </div>
          </div>

          {/* Dynamic Stats Grid & Safeguards */}
          <div className="mt-6 sm:mt-8 grid gap-4 sm:grid-cols-3 font-mono">
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 backdrop-blur-xl">
              <div className="text-[10px] text-zinc-400 uppercase tracking-wider">Active Sleeves</div>
              <div className="text-xl sm:text-2xl font-black text-white mt-1 tabular-nums">
                {sleeveCount} / 5
              </div>
              <div className="text-[10px] text-[#00D09C] font-semibold mt-0.5">Isolated Risk Compartments</div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 backdrop-blur-xl">
              <div className="text-[10px] text-zinc-400 uppercase tracking-wider">Per-Sleeve Cap</div>
              <div className="text-xl sm:text-2xl font-black text-white mt-1 tabular-nums">
                ${sleeveCap.toLocaleString()}
              </div>
              <div className="text-[10px] text-cyan-400 font-semibold mt-0.5">Kelly Fractional Limit</div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 backdrop-blur-xl">
              <div className="text-[10px] text-zinc-400 uppercase tracking-wider">Est. Monthly Alpha</div>
              <div className="text-xl sm:text-2xl font-black text-[#00D09C] mt-1 tabular-nums">
                +${estimatedMonthlyAlpha.toLocaleString()}
              </div>
              <div className="text-[10px] text-zinc-400 font-semibold mt-0.5">Observed 91.4% Win Model</div>
            </div>
          </div>

          {/* Bottom Safeguards & Launch CTA */}
          <div className="mt-6 sm:mt-8 flex flex-col lg:flex-row lg:items-center justify-between gap-5 pt-6 border-t border-white/10">
            <div className="space-y-2 text-xs font-mono text-zinc-300">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-[#00D09C] shrink-0" />
                <span>Strict $1.00 Polymarket order floor enforcement</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-[#00D09C] shrink-0" />
                <span>Zero margin leakage between independent whale copies</span>
              </div>
            </div>

            <Link
              href="/dashboard"
              className="liquid-pill-btn inline-flex h-12 sm:h-14 items-center justify-center gap-2.5 px-7 text-xs sm:text-sm font-mono font-bold text-white shadow-xl hover:scale-105 active:scale-95 transition-all self-start lg:self-auto border border-white/20"
            >
              <span>Launch Simulated Portfolio with ${bankroll.toLocaleString()}</span>
              <ArrowRight size={14} className="text-[#00D09C]" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
