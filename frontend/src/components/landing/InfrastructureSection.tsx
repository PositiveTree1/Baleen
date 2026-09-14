'use client';

import Link from 'next/link';
import { ArrowRight, Activity, CheckCircle, Cpu } from 'lucide-react';
import { LiquidGlassCard } from './LiquidGlassCard';

export function InfrastructureSection() {
  return (
    <>
      {/* Deep Quantitative Infrastructure Showcase */}
      <section id="infrastructure" className="relative overflow-hidden px-4 sm:px-6 lg:px-8 py-24 sm:py-32 border-b border-white/10">
        <div className="mx-auto max-w-[1240px]">
          <div className="glass-card glass-chromatic-bezel rounded-[36px] p-6 sm:p-12 lg:p-14 shadow-xl border border-white/20">
            <div className="grid gap-12 lg:grid-cols-[1.1fr_.9fr] items-center">
              {/* Left Column: Quantitative System Specs */}
              <div>
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.06] px-3.5 py-1 text-xs font-mono font-bold tracking-wider text-sky-400 shadow-xs">
                  <Activity size={13} />
                  <span>DEEP INFRASTRUCTURE</span>
                </div>
                <h2 className="font-outfit text-3xl sm:text-5xl font-black leading-[1.02] tracking-tight text-white">
                  Speed without compromise.
                  <span className="block text-slate-400 font-extrabold">Precision without noise.</span>
                </h2>
                <p className="mt-4 text-sm sm:text-base text-slate-300 leading-relaxed max-w-xl">
                  Every prediction trade on Polymarket is an on-chain event. Baleen captures, validates, and simulates copy execution across isolated sleeves before retail orderbooks shift.
                </p>

                {/* Technical Specs List */}
                <div className="mt-8 grid gap-3 sm:grid-cols-2 font-mono">
                  {[
                    { title: 'Envio Hypersync RPC', desc: 'Direct Polygon chain indexing at sub-120ms latency' },
                    { title: 'Dynamic Kelly Fraction', desc: 'Continuous sizing optimization per market conviction' },
                    { title: 'Algorithmic Pruning', desc: 'Automated sleeve isolation when variance shifts' },
                    { title: 'Non-Custodial Sandbox', desc: 'Risk-free simulated executions with live orderbook math' },
                  ].map((spec) => (
                    <div
                      key={spec.title}
                      className="rounded-2xl border border-white/10 bg-[#020b18]/60 p-4 shadow-xs"
                    >
                      <div className="flex items-center gap-2 text-xs sm:text-sm font-bold text-white">
                        <CheckCircle size={14} className="text-emerald-400 shrink-0" />
                        <span>{spec.title}</span>
                      </div>
                      <p className="mt-1 text-xs text-slate-300 leading-relaxed font-sans">{spec.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right Column: Apple Optical Liquid Glass Live Telemetry Card */}
              <div className="relative mx-auto w-full max-w-[460px]">
                <LiquidGlassCard className="p-6 sm:p-7">
                  {/* Telemetry Visualizer */}
                  <div className="rounded-2xl border border-white/15 bg-[#020b18]/80 p-5 space-y-4 shadow-inner">
                    <div className="flex items-center justify-between border-b border-white/10 pb-3 font-mono text-xs">
                      <span className="flex items-center gap-2 text-slate-300">
                        <Cpu size={14} className="text-sky-400" />
                        <span>HYPERSYNC PIPELINE</span>
                      </span>
                      <span className="text-emerald-400 font-bold">ONLINE</span>
                    </div>

                    <div className="space-y-2.5 font-mono text-xs">
                      <div className="flex justify-between text-slate-400">
                        <span>Mempool Ingestion:</span>
                        <span className="text-white font-bold">sub-35ms</span>
                      </div>
                      <div className="flex justify-between text-slate-400">
                        <span>CLOB Book Matching:</span>
                        <span className="text-white font-bold">sub-50ms</span>
                      </div>
                      <div className="flex justify-between text-slate-400">
                        <span>Isolated Sleeve Guard:</span>
                        <span className="text-emerald-400 font-bold">Active ($2k Cap)</span>
                      </div>
                      <div className="flex justify-between text-slate-400">
                        <span>Sizing Engine:</span>
                        <span className="text-white font-bold">Kelly Fractional</span>
                      </div>
                    </div>

                    <div className="pt-2.5 border-t border-white/10 flex items-center justify-between text-[11px] font-mono text-slate-400">
                      <span>Polygon Block #68,291,048</span>
                      <span className="text-emerald-400 font-semibold">0.00% Slippage</span>
                    </div>
                  </div>

                  {/* Highlights */}
                  <div className="mt-6 flex items-center justify-between border-t border-white/10 pt-4 font-mono">
                    <div>
                      <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        Sandbox Capital Ready
                      </div>
                      <div className="text-2xl font-black text-white tabular-nums">$10,000.00</div>
                    </div>
                    <span className="rounded-full border border-emerald-400/30 bg-emerald-950/40 px-3 py-1 text-xs font-bold text-emerald-400">
                      Guest Instant Access
                    </span>
                  </div>
                </LiquidGlassCard>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* High-Impact Closing CTA Banner (Spacious Liquid Glass Capsule) */}
      <section className="relative overflow-hidden px-4 sm:px-6 lg:px-8 py-24 sm:py-32">
        <div className="relative mx-auto max-w-[1240px]">
          <div className="glass-card glass-chromatic-bezel relative overflow-hidden rounded-[36px] p-8 sm:p-14 lg:p-16 shadow-xl border border-white/20">
            {/* Ambient Lighting */}
            <div className="absolute top-0 right-1/4 w-96 h-96 bg-sky-500/10 blur-[100px] pointer-events-none" />
            <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-cyan-500/10 blur-[100px] pointer-events-none" />

            <div className="relative z-10 flex flex-col justify-between gap-8 lg:flex-row lg:items-end">
              <div className="max-w-2xl">
                <span className="font-mono text-xs font-extrabold uppercase tracking-widest text-sky-400">
                  READY TO TEST ALPHA?
                </span>
                <h2 className="mt-3 font-outfit text-3xl sm:text-5xl lg:text-6xl font-black leading-[1.0] tracking-tight text-white">
                  The whales have moved.
                  <span className="block text-slate-400 font-extrabold">Are you tracking them?</span>
                </h2>
                <p className="mt-4 text-sm sm:text-base text-slate-300 leading-relaxed">
                  Join quantitative prediction researchers shadowing top Polymarket snipers with isolated risk, instant paper allocations, and sub-120ms execution.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center gap-3 shrink-0">
                <Link
                  href="/dashboard"
                  className="inline-flex h-13 sm:h-14 items-center justify-center gap-2.5 rounded-full bg-gradient-to-r from-sky-500 to-cyan-500 px-8 text-xs sm:text-sm font-mono font-black text-white shadow-lg shadow-sky-500/25 transition-all hover:from-sky-400 hover:to-cyan-400 hover:scale-105 active:scale-95 border border-white/40"
                >
                  <span>Launch $10,000 Sandbox</span>
                  <ArrowRight size={15} className="text-white" />
                </Link>

                <Link
                  href="/auth/signup"
                  className="glass-button inline-flex h-13 sm:h-14 items-center justify-center px-8 text-xs sm:text-sm font-mono font-bold text-white transition-all rounded-full shadow-sm"
                >
                  Create Free Account
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
