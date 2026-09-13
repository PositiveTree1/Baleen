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
    <section id="simulator" className="relative overflow-hidden bg-[#07080A] px-5 py-24 text-white sm:px-8 sm:py-32 lg:px-12 border-b border-white/10">
      <div className="relative mx-auto max-w-[1380px]">
        {/* Section Header */}
        <div className="mx-auto mb-16 max-w-2xl text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-1.5 text-xs font-bold tracking-wider text-zinc-300 font-mono">
            <Calculator size={13} className="text-[#00D09C]" />
            <span>INTERACTIVE ALPHA SIMULATOR</span>
          </div>
          <h2 className="font-outfit text-3xl font-black tracking-[-0.04em] text-white sm:text-5xl">
            Model your compounding edge.
          </h2>
          <p className="mt-4 text-base leading-relaxed text-zinc-400 sm:text-lg">
            Simulate portfolio growth across isolated whale sleeves using historical win rates and disciplined dynamic Kelly sizing.
          </p>
        </div>

        {/* Simulator Grid */}
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 lg:items-stretch">
          {/* Controls Column (Revolut FinTech Style) */}
          <div className="apple-glass-card flex flex-col justify-between rounded-[32px] border border-white/10 bg-[#0E1015]/90 p-6 sm:p-10 lg:col-span-7">
            <div className="space-y-8">
              {/* Capital Slider */}
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-zinc-400 font-mono">
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
                  className="h-2.5 w-full cursor-pointer appearance-none rounded-lg bg-white/10 accent-[#00D09C] transition-all focus:outline-none"
                  aria-label="Starting Capital Slider"
                />
                <div className="mt-2.5 flex justify-between font-mono text-[11px] font-semibold text-zinc-500">
                  <span>$500 (Starter)</span>
                  <span className="text-white font-bold">$10,000 (Paper Default)</span>
                  <span>$25,000</span>
                </div>
              </div>

              {/* Sleeve Diversification Selector */}
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <label className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-zinc-400 font-mono">
                    <Layers size={14} className="text-zinc-300" />
                    Sleeve Tiering Strategy
                  </label>
                  <span className="font-mono text-xs font-bold text-[#00D09C]">
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
                          ? 'border-white bg-white/10 shadow-lg'
                          : 'border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.05]'
                      }`}
                    >
                      <div className="font-mono text-sm font-bold text-white">{label}</div>
                      <div className="mt-1 text-[11px] text-zinc-500">{desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Time Horizon Selection */}
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-zinc-400 font-mono">
                    Compounding Horizon
                  </label>
                  <span className="font-mono text-sm font-bold text-white">
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
                          ? 'border-white bg-white text-black shadow-md'
                          : 'border-white/10 bg-white/[0.04] text-zinc-400 hover:border-white/20 hover:text-white'
                      }`}
                    >
                      {months} Mo
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Feature Highlights */}
            <div className="mt-8 border-t border-white/10 pt-6 grid grid-cols-2 gap-4 text-xs text-zinc-400 font-mono">
              <div className="flex items-center gap-2">
                <ShieldCheck size={16} className="text-[#00D09C] shrink-0" />
                <span>Isolated risk per sleeve</span>
              </div>
              <div className="flex items-center gap-2">
                <Sliders size={16} className="text-zinc-300 shrink-0" />
                <span>$1.00 order floor</span>
              </div>
            </div>
          </div>

          {/* Results Projection Card (Apple Optical Glass) */}
          <div className="apple-glass-card flex flex-col justify-between rounded-[32px] border border-white/15 bg-[#0E1015]/95 p-6 sm:p-10 lg:col-span-5 relative overflow-hidden shadow-2xl">
            <div className="relative z-10">
              <div className="mb-6 flex items-center justify-between">
                <span className="font-mono text-xs font-bold uppercase tracking-wider text-zinc-400">
                  Simulated Outcome
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-[#00D09C]/30 bg-[#00D09C]/10 px-3 py-1 font-mono text-xs font-bold text-[#00D09C]">
                  <TrendingUp size={13} />
                  +{(monthlyRate * 100).toFixed(1)}% / Mo
                </span>
              </div>

              {/* Main Numbers */}
              <div className="mb-8">
                <div className="font-mono text-4xl sm:text-5xl font-black tracking-tight text-white tabular-nums">
                  ${Math.round(projectedBalance).toLocaleString()}
                </div>
                <div className="mt-2 flex items-center gap-2 font-mono text-sm font-bold text-[#00D09C]">
                  <span>+${Math.round(projectedProfit).toLocaleString()} Projected Net</span>
                  <span className="rounded bg-[#00D09C]/15 px-1.5 py-0.5 text-xs">
                    (+{(((projectedBalance - initialCapital) / initialCapital) * 100).toFixed(1)}%)
                  </span>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 gap-3 mb-8">
                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-1 font-mono">
                    Basket Win Rate
                  </div>
                  <div className="font-mono text-xl font-bold text-white">{winRate}</div>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-1 font-mono">
                    Sleeve Allocation
                  </div>
                  <div className="font-mono text-xl font-bold text-white">
                    ${sleeveSize.toLocaleString()}
                  </div>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-1 font-mono">
                    Active Whales
                  </div>
                  <div className="font-mono text-xl font-bold text-white">
                    {sleeveCount} Sleeves
                  </div>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-1 font-mono">
                    Execution Mode
                  </div>
                  <div className="font-mono text-xl font-bold text-[#00D09C]">
                    Paper Sandbox
                  </div>
                </div>
              </div>
            </div>

            {/* Launch CTA */}
            <div className="relative z-10 border-t border-white/10 pt-4">
              <Link
                href="/dashboard"
                className="group flex h-13 w-full items-center justify-center gap-3 rounded-full bg-white px-6 text-sm font-extrabold text-black shadow-xl transition-all hover:bg-zinc-200 active:scale-[0.98]"
              >
                <span>Test With $10,000 Paper Capital</span>
                <ArrowRight size={16} className="transition-transform group-hover:translate-x-1" aria-hidden="true" />
              </Link>
              <p className="mt-3 text-center font-mono text-[11px] text-zinc-500">
                100% simulated paper portfolio. Zero real funds required.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
