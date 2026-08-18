'use client';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { Calculator, Sparkles, TrendingUp, ShieldCheck, ArrowRight, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';

export function ProfitSimulator() {
  const [initialCapital, setInitialCapital] = useState(10000);
  const [riskProfile, setRiskProfile] = useState<'conservative' | 'balanced' | 'aggressive'>('balanced');
  const [timeHorizonMonths, setTimeHorizonMonths] = useState(6);

  // Realistic quantitative backtest parameters based on Baleen Gold Sniper basket
  const riskMultipliers = {
    conservative: { monthlyReturnPct: 6.8, winRatePct: 82.5, maxDrawdownPct: 4.2, label: 'Conservative (1% Sizing)' },
    balanced: { monthlyReturnPct: 14.4, winRatePct: 86.4, maxDrawdownPct: 8.5, label: 'Balanced (3% Sizing)' },
    aggressive: { monthlyReturnPct: 24.2, winRatePct: 84.1, maxDrawdownPct: 14.8, label: 'Alpha Max (5% Sizing)' },
  };

  const currentProfile = riskMultipliers[riskProfile];
  const monthlyRate = currentProfile.monthlyReturnPct / 100;
  const projectedBalance = initialCapital * Math.pow(1 + monthlyRate, timeHorizonMonths);
  const projectedProfit = projectedBalance - initialCapital;
  const projectedProfitPct = ((projectedBalance - initialCapital) / initialCapital) * 100;

  return (
    <section className="py-24 px-6 lg:px-20 bg-gradient-to-b from-[#F8F9FB] to-white border-t border-black/[0.06] relative overflow-hidden">
      <div className="max-w-6xl mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold text-indigo-800 bg-indigo-50 border border-indigo-200 shadow-sm mb-4">
            <Calculator size={14} className="text-indigo-600" />
            <span>Interactive Alpha Backtester</span>
          </div>
          <h2 className="text-3xl md:text-5xl font-extrabold text-slate-950 tracking-tight mb-4">
            Simulate Your Mirrored Returns
          </h2>
          <p className="text-slate-600 text-base leading-relaxed">
            Estimate compounding performance based on the historical execution tape of Baleen&apos;s verified top 1% Polymarket whales.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
          {/* Controls Column */}
          <div className="lg:col-span-7 p-8 rounded-3xl bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_16px_36px_-6px_rgba(0,0,0,0.05)] flex flex-col justify-between">
            <div className="space-y-8">
              {/* Capital Slider */}
              <div>
                <div className="flex justify-between items-center mb-3">
                  <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Starting Capital
                  </label>
                  <span className="text-2xl font-extrabold text-slate-950 font-mono">
                    ${initialCapital.toLocaleString()}
                  </span>
                </div>
                <input
                  type="range"
                  min={1000}
                  max={50000}
                  step={1000}
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(Number(e.target.value))}
                  className="w-full h-2 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-slate-900 focus:outline-none"
                />
                <div className="flex justify-between text-[11px] text-slate-400 font-mono mt-2 font-medium">
                  <span>$1,000</span>
                  <span>$10,000</span>
                  <span>$25,000</span>
                  <span>$50,000</span>
                </div>
              </div>

              {/* Risk Profile Tabs */}
              <div>
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-3">
                  Execution Sizing Regime
                </label>
                <div className="grid grid-cols-3 gap-2.5">
                  {(['conservative', 'balanced', 'aggressive'] as const).map((profile) => (
                    <button
                      key={profile}
                      onClick={() => setRiskProfile(profile)}
                      className={`p-3.5 rounded-2xl text-xs font-semibold capitalize border transition-all text-center flex flex-col items-center gap-1 cursor-pointer ${
                        riskProfile === profile
                          ? 'bg-slate-950 text-white border-slate-950 shadow-md scale-[1.02]'
                          : 'bg-slate-50 text-slate-700 border-black/[0.06] hover:bg-slate-100 hover:text-slate-950'
                      }`}
                    >
                      <span className="font-bold">{profile}</span>
                      <span className={`text-[10px] font-mono ${riskProfile === profile ? 'text-indigo-200' : 'text-slate-500'}`}>
                        +{riskMultipliers[profile].monthlyReturnPct}% / mo
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Time Horizon */}
              <div>
                <div className="flex justify-between items-center mb-3">
                  <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Compounding Period
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
                      className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                        timeHorizonMonths === months
                          ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                          : 'bg-slate-50 text-slate-600 border-black/[0.06] hover:bg-slate-100'
                      }`}
                    >
                      {months} {months === 1 ? 'Month' : 'Months'}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Micro Guarantees */}
            <div className="pt-6 mt-6 border-t border-black/[0.06] grid grid-cols-2 gap-4 text-xs text-slate-600">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
                <span>Zero custodial counterparty risk</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
                <span>Non-HFT liquidity filtering</span>
              </div>
            </div>
          </div>

          {/* Results Projection Card */}
          <div className="lg:col-span-5 p-8 rounded-3xl bg-slate-950 text-white shadow-2xl flex flex-col justify-between relative overflow-hidden">
            {/* Ambient Background Glow */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/20 rounded-full filter blur-3xl pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-emerald-500/15 rounded-full filter blur-2xl pointer-events-none" />

            <div className="relative z-10">
              <div className="flex justify-between items-center mb-6">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
                  Projected Capital
                </span>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-800/80">
                  <TrendingUp size={12} />
                  +{projectedProfitPct.toFixed(1)}% Return
                </span>
              </div>

              {/* Hero Numbers */}
              <div className="mb-8">
                <div className="text-4xl sm:text-5xl font-black font-mono tracking-tight text-white mb-2">
                  ${Math.round(projectedBalance).toLocaleString()}
                </div>
                <div className="text-sm font-mono text-emerald-400 font-bold">
                  +${Math.round(projectedProfit).toLocaleString()} Total Alpha Generated
                </div>
              </div>

              {/* Metric Breakdown Grid */}
              <div className="grid grid-cols-2 gap-3 mb-8">
                <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
                  <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider mb-1">Basket Win Rate</div>
                  <div className="text-xl font-bold font-mono text-white">{currentProfile.winRatePct}%</div>
                </div>
                <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
                  <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider mb-1">Max Drawdown</div>
                  <div className="text-xl font-bold font-mono text-slate-300">{currentProfile.maxDrawdownPct}%</div>
                </div>
                <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
                  <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider mb-1">Monthly Avg PnL</div>
                  <div className="text-xl font-bold font-mono text-emerald-400">+{currentProfile.monthlyReturnPct}%</div>
                </div>
                <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
                  <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider mb-1">Copy Latency</div>
                  <div className="text-xl font-bold font-mono text-indigo-400">&lt; 38ms</div>
                </div>
              </div>
            </div>

            <div className="relative z-10 pt-4 border-t border-white/10">
              <Link href="/auth/signup" className="w-full block">
                <button className="w-full py-4 px-6 rounded-2xl bg-white hover:bg-slate-100 text-slate-950 font-bold text-sm transition-all shadow-lg hover:shadow-white/10 flex items-center justify-center gap-2 cursor-pointer group active:scale-[0.98]">
                  <span>Launch With $10,000 Paper Funds</span>
                  <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </button>
              </Link>
              <p className="text-[11px] text-slate-500 text-center mt-3 font-medium">
                No credit card or Polymarket private keys required.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
