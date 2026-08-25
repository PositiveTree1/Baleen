'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight, ShieldCheck, Zap, TrendingUp, Play, User } from 'lucide-react';

export function Hero() {
  return (
    <section className="relative pt-10 pb-20 px-6 lg:px-20 overflow-hidden bg-white">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center justify-between gap-12 lg:gap-16">
        
        {/* Left Column: Typography & CTAs */}
        <div className="w-full lg:w-[48%] flex flex-col items-start gap-6 z-10">
          <span className="text-[11px] font-bold tracking-[0.2em] uppercase text-slate-400 font-mono">
            Smarter trading. Simpler.
          </span>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-950 leading-[1.08]">
            Mirror the top 1% <br />
            on Polymarket.
          </h1>

          <p className="text-base sm:text-lg text-slate-600 max-w-lg leading-relaxed font-normal">
            Baleen is an institutional copy-trading engine for Polymarket. Discover verified prediction whales, size positions dynamically, and mirror smart money fills with sub-second latency.
          </p>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-3.5 pt-2">
            <Link href="/auth/signup">
              <button className="flex items-center gap-2 px-6 py-3.5 rounded-full bg-slate-950 text-white hover:bg-slate-800 text-sm font-semibold transition-all shadow-sm hover:shadow active:scale-[0.98] cursor-pointer">
                <span>Get Started Free</span>
                <ArrowRight size={15} />
              </button>
            </Link>
            <Link href="#advantage">
              <button className="flex items-center gap-2 px-6 py-3.5 rounded-full bg-slate-50 hover:bg-slate-100 border border-black/[0.08] text-slate-800 text-sm font-semibold transition-all cursor-pointer">
                <Play size={13} className="fill-slate-800 text-slate-800" />
                <span>Watch Demo</span>
              </button>
            </Link>
          </div>

          {/* 3 Feature Badges */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-10 mt-4 border-t border-black/[0.06] w-full">
            <div className="flex items-start gap-2.5">
              <div className="p-1.5 rounded-lg bg-slate-50 border border-black/[0.06] text-slate-700 mt-0.5">
                <ShieldCheck size={16} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900">Verified Wallets</h4>
                <p className="text-[11px] text-slate-500 mt-0.5">Only trusted traders</p>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <div className="p-1.5 rounded-lg bg-slate-50 border border-black/[0.06] text-slate-700 mt-0.5">
                <Zap size={16} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900">Real-Time Sync</h4>
                <p className="text-[11px] text-slate-500 mt-0.5">Sub-second latency</p>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <div className="p-1.5 rounded-lg bg-slate-50 border border-black/[0.06] text-slate-700 mt-0.5">
                <TrendingUp size={16} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900">Dynamic Sizing</h4>
                <p className="text-[11px] text-slate-500 mt-0.5">Smarter risk management</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: High-End Dual Device Showcase (Laptop + Phone) */}
        <div className="w-full lg:w-[52%] flex justify-center items-center relative py-6">
          <div className="relative w-full max-w-xl">
            
            {/* Laptop Mockup Container */}
            <div className="relative rounded-2xl bg-slate-900 p-2.5 sm:p-3.5 shadow-2xl border border-slate-800 text-white font-sans overflow-hidden">
              {/* Laptop Header Bar */}
              <div className="flex items-center justify-between px-3 py-2 border-b border-white/[0.08] text-xs">
                <div className="flex items-center gap-2">
                  <Image src="/logo.png" alt="Baleen" width={14} height={14} className="object-contain" />
                  <span className="font-bold tracking-wider text-[11px]">BALEEN</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Connected
                  </span>
                  <div className="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center text-slate-300">
                    <User size={10} />
                  </div>
                </div>
              </div>

              {/* Laptop Main Body */}
              <div className="flex gap-4 p-3 sm:p-4 text-xs">
                {/* Left Mini Sidebar */}
                <div className="hidden sm:flex flex-col gap-2.5 w-24 text-[11px] text-slate-400 shrink-0 border-r border-white/[0.06] pr-2">
                  <span className="px-2 py-1 rounded bg-white/10 text-white font-semibold flex items-center gap-1">
                    Dashboard
                  </span>
                  <span className="px-2 py-1 hover:text-slate-200">Top Traders</span>
                  <span className="px-2 py-1 hover:text-slate-200">My Trades</span>
                  <span className="px-2 py-1 hover:text-slate-200">Settings</span>
                </div>

                {/* Right Content Area */}
                <div className="flex-1 space-y-3.5 min-w-0">
                  {/* Balance Header & Chart */}
                  <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                    <div className="text-[10px] text-slate-400">Total Portfolio Value</div>
                    <div className="flex items-baseline gap-2 mt-0.5">
                      <span className="text-xl font-bold font-mono text-white">$12,483.26</span>
                      <span className="text-xs text-emerald-400 font-semibold font-mono">+12.4%</span>
                    </div>
                    {/* SVG Sparkline Curve */}
                    <div className="h-10 w-full mt-2">
                      <svg viewBox="0 0 300 60" className="w-full h-full stroke-emerald-400 fill-none" preserveAspectRatio="none">
                        <path d="M0 45 Q 40 48, 80 35 T 160 30 T 220 18 T 300 8" strokeWidth="2.5" strokeLinecap="round" />
                        <path d="M0 45 Q 40 48, 80 35 T 160 30 T 220 18 T 300 8 L 300 60 L 0 60 Z" fill="rgba(52, 211, 153, 0.08)" stroke="none" />
                      </svg>
                    </div>
                  </div>

                  {/* Top Traders Table */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[10px] font-semibold text-slate-400 px-1">
                      <span>Top Traders</span>
                      <span className="text-indigo-400 hover:underline cursor-pointer">View all →</span>
                    </div>

                    <div className="space-y-1.5">
                      {[
                        { name: 'WhaleAlpha', wr: '93%', pnl: '+297.4%', fol: '12.4k' },
                        { name: 'PolymarketPro', wr: '88%', pnl: '+156.2%', fol: '8.7k' },
                        { name: 'TheOracle', wr: '82%', pnl: '+143.7%', fol: '6.1k' },
                      ].map((t, idx) => (
                        <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/[0.04] text-[11px]">
                          <div className="flex items-center gap-2">
                            <div className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-300 font-bold flex items-center justify-center text-[9px]">
                              {t.name[0]}
                            </div>
                            <span className="font-medium text-slate-200">{t.name}</span>
                          </div>
                          <span className="text-slate-400 font-mono text-[10px] hidden sm:inline">{t.wr} WR</span>
                          <span className="text-emerald-400 font-mono font-semibold text-[10px]">{t.pnl}</span>
                          <span className="text-slate-500 text-[10px] hidden sm:inline">{t.fol}</span>
                          <button className="px-2 py-0.5 rounded bg-white/10 hover:bg-white/20 text-white font-medium text-[10px]">
                            Copy
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Floating iPhone Mockup (Bottom Right Overlap) */}
            <div className="absolute -bottom-6 -right-3 sm:-right-6 w-36 sm:w-44 rounded-2xl sm:rounded-3xl bg-slate-950 p-2 sm:p-2.5 shadow-2xl border-2 border-slate-700 text-white font-sans z-20">
              <div className="flex items-center justify-between px-1 py-1 border-b border-white/[0.08] text-[9px]">
                <span className="font-bold text-[9px]">BALEEN</span>
                <span className="text-slate-400">9:41</span>
              </div>
              <div className="py-2 px-1 space-y-2">
                <div>
                  <div className="text-[8px] text-slate-400">Total PnL</div>
                  <div className="text-xs font-bold font-mono text-emerald-400">+12.4%</div>
                  <svg viewBox="0 0 100 30" className="w-full h-5 stroke-emerald-400 fill-none mt-1">
                    <path d="M0 25 Q 30 20, 60 12 T 100 4" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                </div>

                <div className="space-y-1 pt-1 border-t border-white/[0.06]">
                  <div className="text-[8px] text-slate-400 font-semibold">Active Positions</div>
                  <div className="p-1 rounded bg-white/[0.04] text-[8px] flex justify-between">
                    <span className="truncate max-w-[50px] text-slate-300">Trump</span>
                    <span className="font-mono text-emerald-400">+$3,240</span>
                  </div>
                  <div className="p-1 rounded bg-white/[0.04] text-[8px] flex justify-between">
                    <span className="truncate max-w-[50px] text-slate-300">Bitcoin</span>
                    <span className="font-mono text-emerald-400">+$1,892</span>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>

      </div>
    </section>
  );
}
