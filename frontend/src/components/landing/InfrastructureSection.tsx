'use client';

import Link from 'next/link';
import { ArrowRight, Activity, CheckCircle, Cpu } from 'lucide-react';
import { LiquidGlassCard } from './LiquidGlassCard';

export function InfrastructureSection() {
  return (
    <>
      {/* Deep Quantitative Infrastructure Showcase */}
      <section id="infrastructure" className="relative overflow-hidden px-4 sm:px-6 lg:px-8 py-24 sm:py-32 border-b border-sky-100/80">
        <div className="mx-auto max-w-[1240px]">
          <div className="glass-card glass-chromatic-bezel rounded-[36px] p-6 sm:p-12 lg:p-14 shadow-xl border border-white/95">
            <div className="grid gap-12 lg:grid-cols-[1.1fr_.9fr] items-center">
              {/* Left Column: Quantitative System Specs */}
              <div>
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-sky-100 bg-sky-50/80 px-3.5 py-1 text-xs font-mono font-bold tracking-wider text-sky-700 shadow-xs">
                  <Activity size={13} />
                  <span>DEEP INFRASTRUCTURE</span>
                </div>
                <h2 className="font-outfit text-3xl sm:text-5xl font-black leading-[1.02] tracking-tight text-slate-950">
                  Speed without compromise.
                  <span className="block text-slate-600 font-extrabold">Precision without noise.</span>
                </h2>
                <p className="mt-4 text-sm sm:text-base text-slate-600 leading-relaxed max-w-xl">
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
                      className="rounded-2xl border border-sky-100 bg-white/80 p-4 shadow-xs"
                    >
                      <div className="flex items-center gap-2 text-xs sm:text-sm font-bold text-slate-900">
                        <CheckCircle size={14} className="text-emerald-600 shrink-0" />
                        <span>{spec.title}</span>
                      </div>
                      <p className="mt-1 text-xs text-slate-600 leading-relaxed font-sans">{spec.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right Column: Apple Optical Liquid Glass Live Telemetry Card */}
              <div className="relative mx-auto w-full max-w-[460px]">
                <LiquidGlassCard className="p-6 sm:p-7">
                  {/* Telemetry Visualizer */}
                  <div className="rounded-2xl border border-sky-100 bg-sky-50/70 p-5 space-y-4 shadow-inner">
                    <div className="flex items-center justify-between border-b border-sky-100 pb-3 font-mono text-xs">
                      <span className="flex items-center gap-2 text-slate-600">
                        <Cpu size={14} className="text-sky-600" />
                        <span>HYPERSYNC PIPELINE</span>
                      </span>
                      <span className="text-emerald-600 font-bold">ONLINE</span>
                    </div>

                    <div className="space-y-2.5 font-mono text-xs">
                      <div className="flex justify-between text-slate-500">
                        <span>Mempool Ingestion:</span>
                        <span className="text-slate-900 font-bold">sub-35ms</span>
                      </div>
                      <div className="flex justify-between text-slate-500">
                        <span>CLOB Book Matching:</span>
                        <span className="text-slate-900 font-bold">sub-50ms</span>
                      </div>
                      <div className="flex justify-between text-slate-500">
                        <span>Isolated Sleeve Guard:</span>
                        <span className="text-emerald-700 font-bold">Active ($2k Cap)</span>
                      </div>
                      <div className="flex justify-between text-slate-500">
                        <span>Sizing Engine:</span>
                        <span className="text-slate-900 font-bold">Kelly Fractional</span>
                      </div>
                    </div>

                    <div className="pt-2.5 border-t border-sky-100 flex items-center justify-between text-[11px] font-mono text-slate-400">
                      <span>Polygon Block #68,291,048</span>
                      <span className="text-emerald-700 font-semibold">0.00% Slippage</span>
                    </div>
                  </div>

                  {/* Highlights */}
                  <div className="mt-6 flex items-center justify-between border-t border-sky-100 pt-4 font-mono">
                    <div>
                      <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                        Sandbox Capital Ready
                      </div>
                      <div className="text-2xl font-black text-slate-950 tabular-nums">$10,000.00</div>
                    </div>
                    <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
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
          <div className="glass-card glass-chromatic-bezel relative overflow-hidden rounded-[36px] p-8 sm:p-14 lg:p-16 shadow-xl border border-white/95">
            {/* Ambient Lighting */}
            <div className="absolute top-0 right-1/4 w-96 h-96 bg-sky-200/40 blur-[100px] pointer-events-none" />
            <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-cyan-200/35 blur-[100px] pointer-events-none" />

            <div className="relative z-10 flex flex-col justify-between gap-8 lg:flex-row lg:items-end">
              <div className="max-w-2xl">
                <span className="font-mono text-xs font-extrabold uppercase tracking-widest text-sky-700">
                  READY TO TEST ALPHA?
                </span>
                <h2 className="mt-3 font-outfit text-3xl sm:text-5xl lg:text-6xl font-black leading-[1.0] tracking-tight text-slate-950">
                  The whales have moved.
                  <span className="block text-slate-600 font-extrabold">Are you tracking them?</span>
                </h2>
                <p className="mt-4 text-sm sm:text-base text-slate-600 leading-relaxed">
                  Join quantitative prediction researchers shadowing top Polymarket snipers with isolated risk, instant paper allocations, and sub-120ms execution.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center gap-3 shrink-0">
                <Link
                  href="/dashboard"
                  className="inline-flex h-13 sm:h-14 items-center justify-center gap-2.5 rounded-full bg-gradient-to-r from-sky-600 to-cyan-600 px-8 text-xs sm:text-sm font-mono font-black text-white shadow-lg shadow-sky-500/25 transition-all hover:from-sky-500 hover:to-cyan-500 hover:scale-105 active:scale-95 border border-white/40"
                >
                  <span>Launch $10,000 Sandbox</span>
                  <ArrowRight size={15} className="text-white" />
                </Link>

                <Link
                  href="/auth/signup"
                  className="glass-button inline-flex h-13 sm:h-14 items-center justify-center px-8 text-xs sm:text-sm font-mono font-bold text-slate-800 transition-all hover:text-slate-950 border border-white/90 shadow-sm"
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
