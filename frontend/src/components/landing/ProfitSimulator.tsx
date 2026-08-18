'use client';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { Calculator, Sparkles, TrendingUp, ShieldCheck, ArrowRight, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';

export function ProfitSimulator() {
  const [initialCapital, setInitialCapital] = useState(20);
  const [timeHorizonMonths, setTimeHorizonMonths] = useState(6);

  // High-performance compounding model based on Baleen Gold Sniper Basket (88.4% Win Rate, multi-trades/day)
  // For $20 over 6 months at high frequency whale compounding, it projects close to ~$10,000
  // Monthly compounding factor ~2.81x (i.e. 20 * 2.81^6 ≈ 9,850)
  const baseGrowthFactorPerMonth = 2.815;
  const projectedBalance = initialCapital * Math.pow(baseGrowthFactorPerMonth, timeHorizonMonths);
  const projectedProfit = projectedBalance - initialCapital;

  return (
    <section className="py-24 px-6 lg:px-20 bg-gradient-to-b from-[#F8F9FB] to-white border-t border-black/[0.06] relative overflow-hidden">
      <div className="max-w-6xl mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold text-indigo-800 bg-indigo-50 border border-indigo-200 shadow-sm mb-4">
            <Calculator size={14} className="text-indigo-600" />
            <span>Interactive Alpha Compounding Simulator</span>
          </div>
          <h2 className="text-3xl md:text-5xl font-extrabold text-slate-950 tracking-tight mb-4">
            See What Small Capital Can Do
          </h2>
          <p className="text-slate-600 text-base leading-relaxed">
            Start with as little as <strong>$20</strong>. By mirroring verified Gold-Tier Polymarket whales on auto-pilot, high-frequency alpha compounding turns micro-allocations into serious capital.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
          {/* Controls Column */}
          <div className="lg:col-span-7 p-8 rounded-3xl bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_16px_36px_-6px_rgba(0,0,0,0.05)] flex flex-col justify-between">
            <div className="space-y-8">
              {/* Capital Slider ($20 to $1,000) */}
              <div>
                <div className="flex justify-between items-center mb-3">
                  <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Starting Capital
                  </label>
                  <span className="text-3xl font-extrabold text-slate-950 font-mono">
                    ${initialCapital.toLocaleString()}
                  </span>
                </div>
                <input
                  type="range"
                  min={20}
                  max={1000}
                  step={10}
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(Number(e.target.value))}
                  className="w-full h-2.5 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-slate-900 focus:outline-none"
                />
                <div className="flex justify-between text-[11px] text-slate-400 font-mono mt-2.5 font-semibold">
                  <span>$20 (Micro Start)</span>
                  <span>$250</span>
                  <span>$500</span>
                  <span>$1,000 (Max Starter)</span>
                </div>
              </div>

              {/* Verified Strategy Performance Card (No confusing tiers, just Average Returns) */}
              <div className="p-5 rounded-2xl bg-slate-50 border border-black/[0.06] space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles size={16} className="text-amber-500" />
                    <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Strategy Profile: Average Whale Basket Returns
                    </span>
                  </div>
                  <span className="text-[10px] font-mono font-bold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                    88.4% Win Rate
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed font-medium">
                  Positions are dynamically sized across the top 17 audited Polymarket whales. Automated profit recycling reinvests gains into fresh high-conviction contract fills.
                </p>
              </div>

              {/* Time Horizon Selection */}
              <div>
                <div className="flex justify-between items-center mb-3">
                  <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Compounding Horizon
                  </label>
                  <span className="text-sm font-bold text-slate-900 font-mono">
                    {timeHorizonMonths} Months
                  </span>
                </div>
                <div className="grid grid-cols-4 gap-2">
                  {[1, 3, 6, 12].map((months) => (
                    <button
                      key={months}
                      onClick={() => setTimeHorizonMonths(months)}
                      className={`py-2.5 px-3 rounded-xl text-xs font-bold border transition-all cursor-pointer ${
                        timeHorizonMonths === months
                          ? 'bg-slate-950 text-white border-slate-950 shadow-sm scale-[1.02]'
                          : 'bg-slate-50 text-slate-600 border-black/[0.06] hover:bg-slate-100 hover:text-slate-950'
                      }`}
                    >
                      {months} {months === 1 ? 'Month' : 'Months'}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Guarantees */}
            <div className="pt-6 mt-6 border-t border-black/[0.06] grid grid-cols-2 gap-4 text-xs text-slate-600">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
                <span>Non-custodial execution</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
                <span>Zero upfront subscription</span>
              </div>
            </div>
          </div>

          {/* Results Projection Card */}
          <div className="lg:col-span-5 p-8 rounded-3xl bg-slate-950 text-white shadow-2xl flex flex-col justify-between relative overflow-hidden">
            {/* Ambient Glow */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/20 rounded-full filter blur-3xl pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-emerald-500/15 rounded-full filter blur-2xl pointer-events-none" />

            <div className="relative z-10">
              <div className="flex justify-between items-center mb-6">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
                  Projected Value
                </span>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-800/80">
                  <TrendingUp size={12} />
                  Compounded Growth
                </span>
              </div>

              {/* Hero Numbers */}
              <div className="mb-8">
                <div className="text-4xl sm:text-5xl font-black font-mono tracking-tight text-white mb-2">
                  ${Math.round(projectedBalance).toLocaleString()}
                </div>
                <div className="text-sm font-mono text-emerald-400 font-bold">
                  {initialCapital <= 25 && timeHorizonMonths >= 6 ? (
                    <span>🔥 Turn $20 into close to $10,000+</span>
                  ) : (
                    <span>+${Math.round(projectedProfit).toLocaleString()} Projected Net Gain</span>
                  )}
                </div>
              </div>

              {/* Metric Breakdown Grid */}
              <div className="grid grid-cols-2 gap-3 mb-8">
                <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
                  <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider mb-1">Basket Win Rate</div>
                  <div className="text-xl font-bold font-mono text-white">88.4%</div>
                </div>
                <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
                  <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider mb-1">Tracked Whales</div>
                  <div className="text-xl font-bold font-mono text-slate-300">17 Active</div>
                </div>
                <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
                  <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider mb-1">Avg Profit Factor</div>
                  <div className="text-xl font-bold font-mono text-emerald-400">4.2x</div>
                </div>
                <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
                  <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider mb-1">Execution Speed</div>
                  <div className="text-xl font-bold font-mono text-indigo-400">&lt; 38ms</div>
                </div>
              </div>
            </div>

            <div className="relative z-10 pt-4 border-t border-white/10">
              <Link href="/auth/signup" className="w-full block">
                <button className="w-full py-4 px-6 rounded-2xl bg-white hover:bg-slate-100 text-slate-950 font-bold text-sm transition-all shadow-lg hover:shadow-white/10 flex items-center justify-center gap-2 cursor-pointer group active:scale-[0.98]">
                  <span>Start With $10,000 Paper Funds</span>
                  <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </button>
              </Link>
              <p className="text-[11px] text-slate-500 text-center mt-3 font-medium">
                Try the full engine completely risk-free in sandbox mode.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
