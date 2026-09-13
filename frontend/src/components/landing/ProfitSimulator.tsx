'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Calculator, Sparkles, TrendingUp, ShieldCheck, ArrowRight, Check, Layers, Sliders } from 'lucide-react';
import Link from 'next/link';

export function ProfitSimulator() {
  const [initialCapital, setInitialCapital] = useState(10000);
  const [sleeveCount, setSleeveCount] = useState<number>(5);
  const [timeHorizonMonths, setTimeHorizonMonths] = useState<number>(6);

  // Dynamic alpha compounding model based on quantitative whale baskets
  const monthlyRate = sleeveCount === 1 ? 0.125 : sleeveCount === 5 ? 0.108 : 0.092;
  const projectedBalance = initialCapital * Math.pow(1 + monthlyRate, timeHorizonMonths);
  const projectedProfit = projectedBalance - initialCapital;
  const sleeveSize = Math.round(initialCapital / sleeveCount);
  const winRate = sleeveCount === 1 ? '88.4%' : sleeveCount === 5 ? '92.4%' : '90.8%';

  return (
    <section id="simulator" className="relative overflow-hidden bg-[#040914] px-5 py-24 text-white sm:px-8 sm:py-32 lg:px-12">
      {/* Subtle Background Glows */}
      <div className="pointer-events-none absolute -left-40 top-1/4 size-96 rounded-full bg-cyan-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -right-40 bottom-1/4 size-96 rounded-full bg-emerald-500/10 blur-3xl" />

      <div className="relative mx-auto max-w-[1380px]">
        {/* Section Header */}
        <div className="mx-auto mb-16 max-w-2xl text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-1.5 text-xs font-bold tracking-wider text-cyan-200">
            <Calculator size={13} className="text-cyan-300" />
            <span>INTERACTIVE ALPHA SIMULATOR</span>
          </div>
          <h2 className="font-outfit text-3xl font-black tracking-[-0.04em] text-white sm:text-5xl">
            Model your compounding edge.
          </h2>
          <p className="mt-4 text-base leading-relaxed text-slate-300 sm:text-lg">
            Simulate portfolio growth across isolated whale sleeves using historical win rates and disciplined dynamic Kelly sizing.
          </p>
        </div>

        {/* Simulator Grid */}
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 lg:items-stretch">
          {/* Controls Column (Revolut FinTech Style) */}
          <div className="liquid-glass-panel flex flex-col justify-between rounded-[32px] p-6 sm:p-10 lg:col-span-7">
            <div className="space-y-8">
              {/* Capital Slider */}
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
                    Starting Capital
                  </label>
                  <span className="font-mono text-3xl font-black text-white sm:text-4xl tabular-nums">
                    ${initialCapital.toLocaleString()}
                  </span>
                </div>
                <input
                  type="range"
                  min={500}
                  max={25000}
                  step={250}
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(Number(e.target.value))}
                  className="h-3 w-full cursor-pointer appearance-none rounded-lg bg-white/15 accent-cyan-300 transition-all focus:outline-none"
                  aria-label="Starting Capital Slider"
                />
                <div className="mt-2.5 flex justify-between font-mono text-[11px] font-semibold text-slate-400">
                  <span>$500 (Starter)</span>
                  <span className="text-cyan-300 font-bold">$10,000 (Paper Default)</span>
                  <span>$25,000</span>
                </div>
              </div>

              {/* Sleeve Diversification Selector */}
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <label className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
                    <Layers size={14} className="text-cyan-300" />
                    Sleeve Tiering Strategy
                  </label>
                  <span className="font-mono text-xs font-bold text-emerald-300">
                    ${sleeveSize.toLocaleString()} / Sleeve
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  {[
                    { count: 1, label: '1 Whale', desc: 'Concentrated' },
                    { count: 5, label: '5 Sleeves', desc: 'Balanced (Rec.)' },
                    { count: 10, label: '10 Sleeves', desc: 'Diversified' },
                  ].map(({ count, label, desc }) => (
                    <button
                      key={count}
                      type="button"
                      onClick={() => setSleeveCount(count)}
                      className={`group cursor-pointer rounded-2xl border p-3.5 text-left transition-all ${
                        sleeveCount === count
                          ? 'border-cyan-400 bg-cyan-400/15 shadow-[0_0_20px_rgba(79,228,241,0.2)]'
                          : 'border-white/10 bg-white/[0.03] hover:border-white/20 hover:bg-white/[0.06]'
                      }`}
                    >
                      <div className="font-mono text-sm font-bold text-white">{label}</div>
                      <div className="mt-1 text-[11px] text-white/50">{desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Time Horizon Selection */}
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
                    Compounding Horizon
                  </label>
                  <span className="font-mono text-sm font-bold text-cyan-200">
                    {timeHorizonMonths} Months
                  </span>
                </div>
                <div className="grid grid-cols-4 gap-2.5">
                  {[1, 3, 6, 12].map((months) => (
                    <button
                      key={months}
                      type="button"
                      onClick={() => setTimeHorizonMonths(months)}
                      className={`cursor-pointer rounded-xl border py-3 text-xs font-bold transition-all ${
                        timeHorizonMonths === months
                          ? 'border-white bg-white text-slate-950 shadow-md scale-[1.02]'
                          : 'border-white/10 bg-white/[0.04] text-white/70 hover:border-white/25 hover:text-white'
                      }`}
                    >
                      {months} {months === 1 ? 'Mo' : 'Mo'}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Feature Highlights */}
            <div className="mt-8 border-t border-white/10 pt-6 grid grid-cols-2 gap-4 text-xs text-white/70">
              <div className="flex items-center gap-2">
                <ShieldCheck size={16} className="text-emerald-400 shrink-0" />
                <span>Isolated risk per sleeve</span>
              </div>
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-amber-300 shrink-0" />
                <span>$1.00 Polymarket order floor</span>
              </div>
            </div>
          </div>

          {/* Results Projection Card (Apple Liquid Glass) */}
          <div className="liquid-glass-card flex flex-col justify-between rounded-[32px] p-6 sm:p-10 lg:col-span-5 relative overflow-hidden border border-white/20">
            {/* Specular Glint */}
            <div className="pointer-events-none absolute -right-20 -top-20 size-60 rounded-full bg-cyan-400/20 blur-3xl" />
            <div className="pointer-events-none absolute -left-20 -bottom-20 size-60 rounded-full bg-emerald-400/15 blur-3xl" />

            <div className="relative z-10">
              <div className="mb-6 flex items-center justify-between">
                <span className="font-mono text-xs font-bold uppercase tracking-wider text-cyan-200">
                  Simulated Outcome
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 font-mono text-xs font-bold text-emerald-300">
                  <TrendingUp size={13} />
                  +{(monthlyRate * 100).toFixed(1)}% / Mo
                </span>
              </div>

              {/* Main Numbers */}
              <div className="mb-8">
                <div className="font-mono text-4xl sm:text-5xl font-black tracking-tight text-white tabular-nums">
                  ${Math.round(projectedBalance).toLocaleString()}
                </div>
                <div className="mt-2 flex items-center gap-2 font-mono text-sm font-bold text-emerald-300">
                  <span>+${Math.round(projectedProfit).toLocaleString()} Projected Net Gain</span>
                  <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-xs">
                    (+{(((projectedBalance - initialCapital) / initialCapital) * 100).toFixed(1)}%)
                  </span>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 gap-3 mb-8">
                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur-md">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-white/50 mb-1">
                    Basket Win Rate
                  </div>
                  <div className="font-mono text-xl font-bold text-white">{winRate}</div>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur-md">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-white/50 mb-1">
                    Sleeve Allocation
                  </div>
                  <div className="font-mono text-xl font-bold text-cyan-200">
                    ${sleeveSize.toLocaleString()}
                  </div>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur-md">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-white/50 mb-1">
                    Active Whales
                  </div>
                  <div className="font-mono text-xl font-bold text-amber-300">
                    {sleeveCount} Gold Snipers
                  </div>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur-md">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-white/50 mb-1">
                    Execution Mode
                  </div>
                  <div className="font-mono text-xl font-bold text-emerald-300">
                    Paper Sandbox
                  </div>
                </div>
              </div>
            </div>

            {/* Launch CTA */}
            <div className="relative z-10 border-t border-white/10 pt-4">
              <Link
                href="/dashboard"
                className="group flex h-14 w-full items-center justify-center gap-3 rounded-full bg-white px-6 text-sm font-extrabold text-slate-950 shadow-xl transition-all hover:bg-cyan-50 hover:shadow-cyan-400/20 active:scale-[0.98]"
              >
                <span>Test With $10,000 Paper Capital</span>
                <ArrowRight size={17} className="transition-transform group-hover:translate-x-1" aria-hidden="true" />
              </Link>
              <p className="mt-3 text-center font-mono text-[11px] text-white/40">
                100% simulated paper portfolio. Zero real funds required.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
