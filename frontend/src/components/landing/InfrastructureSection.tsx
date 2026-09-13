'use client';

import Image from 'next/image';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, ShieldCheck, Zap, Layers, Activity, CheckCircle } from 'lucide-react';

export function InfrastructureSection() {
  return (
    <>
      {/* Deep Pacific Surrealism Architecture Showcase */}
      <section id="infrastructure" className="relative overflow-hidden bg-[#040914] px-5 py-24 text-white sm:px-8 sm:py-32 lg:px-12">
        <div className="mx-auto max-w-[1380px]">
          <div className="liquid-glass-panel relative overflow-hidden rounded-[36px] border border-white/15 p-6 sm:p-12 lg:p-16">
            <div className="grid gap-12 lg:grid-cols-[1.1fr_.9fr] lg:items-center">
              {/* Left Column: Quantitative System Specs */}
              <div>
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3.5 py-1 text-xs font-bold tracking-wider text-cyan-200">
                  <Activity size={13} className="text-cyan-300" />
                  <span>DEEP INFRASTRUCTURE</span>
                </div>
                <h2 className="font-outfit text-3xl font-black leading-[0.95] tracking-[-0.04em] text-white sm:text-5xl lg:text-6xl">
                  Speed without compromise.
                  <span className="block surreal-text-gradient">Precision without noise.</span>
                </h2>
                <p className="mt-6 max-w-xl text-base font-normal leading-relaxed text-slate-300 sm:text-lg">
                  Every prediction trade on Polymarket is an on-chain event. Baleen captures, validates, and simulates copy execution across isolated sleeves before retail orderbooks shift.
                </p>

                {/* Technical Specs List */}
                <div className="mt-10 grid gap-4 sm:grid-cols-2">
                  {[
                    { title: 'Envio Hypersync RPC', desc: 'Direct Polygon chain indexing at sub-120ms latency' },
                    { title: 'Dynamic Kelly Fraction', desc: 'Continuous sizing optimization per market conviction' },
                    { title: 'Algorithmic Pruning', desc: 'Automated removal if win rate drops below 75%' },
                    { title: 'Non-Custodial Sandbox', desc: 'Risk-free simulated executions with live orderbook math' },
                  ].map((spec) => (
                    <div
                      key={spec.title}
                      className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 backdrop-blur-xl"
                    >
                      <div className="flex items-center gap-2 font-mono text-sm font-bold text-cyan-200">
                        <CheckCircle size={15} className="text-emerald-400" />
                        <span>{spec.title}</span>
                      </div>
                      <p className="mt-1.5 text-xs text-white/60 leading-relaxed">{spec.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right Column: Floating Liquid Glass Visual Mockup */}
              <div className="relative mx-auto w-full max-w-[480px]">
                <div className="liquid-glass-card relative overflow-hidden rounded-[32px] border border-white/20 p-6 shadow-2xl">
                  {/* Subtle Inner Refraction */}
                  <div className="relative h-64 w-full overflow-hidden rounded-2xl sm:h-72">
                    <Image
                      src="/images/baleen-liquid-glass.jpg"
                      alt="Apple Liquid Glass floating card with live balance and chromatic refraction edges"
                      fill
                      sizes="(max-width: 768px) 100vw, 480px"
                      className="object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#060c1b] via-transparent to-transparent" />
                  </div>

                  {/* Floating Pill Highlights */}
                  <div className="mt-6 flex items-center justify-between border-t border-white/10 pt-4">
                    <div>
                      <div className="text-[10px] font-bold uppercase tracking-wider text-white/50">
                        Sandbox Capital Allocated
                      </div>
                      <div className="font-mono text-2xl font-black text-white">$10,000.00</div>
                    </div>
                    <span className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 font-mono text-xs font-bold text-emerald-300">
                      Instant Guest Access
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* High-Impact Closing CTA Banner (Apple Liquid Glass & Pacific Surrealism Theme) */}
      <section className="relative overflow-hidden bg-[#060c1b] px-5 py-24 text-white sm:px-8 sm:py-36">
        {/* Ambient Orbit Glow */}
        <div className="pointer-events-none absolute -right-20 top-0 size-[500px] rounded-full bg-cyan-500/15 blur-[100px]" />
        <div className="pointer-events-none absolute -left-20 bottom-0 size-[500px] rounded-full bg-emerald-500/10 blur-[100px]" />

        <div className="relative mx-auto max-w-[1380px]">
          <div className="liquid-glass-card relative overflow-hidden rounded-[36px] border border-white/20 p-8 sm:p-16 lg:p-20 shadow-2xl">
            <div className="relative z-10 flex flex-col justify-between gap-10 lg:flex-row lg:items-end">
              <div className="max-w-3xl">
                <span className="font-mono text-xs font-extrabold uppercase tracking-widest text-cyan-300">
                  READY TO TEST ALPHA?
                </span>
                <h2 className="mt-4 font-outfit text-4xl font-black leading-[0.92] tracking-[-0.055em] text-white sm:text-6xl lg:text-7xl">
                  The whales have moved.
                  <span className="block surreal-text-gradient">Are you tracking them?</span>
                </h2>
                <p className="mt-6 max-w-xl text-base font-normal leading-relaxed text-slate-300 sm:text-lg">
                  Join hundreds of prediction market researchers shadowing top Polymarket snipers with isolated risk, instant paper allocations, and sub-120ms execution.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <Link
                  href="/dashboard"
                  className="group inline-flex h-16 shrink-0 items-center justify-center gap-3 rounded-full bg-white px-8 text-sm font-extrabold text-slate-950 shadow-[0_12px_35px_rgba(79,228,241,0.25)] transition-all hover:bg-cyan-50 hover:shadow-[0_16px_45px_rgba(79,228,241,0.35)] active:scale-[0.98]"
                >
                  <span>Launch $10,000 Sandbox</span>
                  <ArrowRight size={18} className="transition-transform group-hover:translate-x-1" aria-hidden="true" />
                </Link>

                <Link
                  href="/auth/signup"
                  className="inline-flex h-16 shrink-0 items-center justify-center rounded-full border border-white/20 bg-white/[0.08] px-8 text-sm font-bold text-white backdrop-blur-xl transition-all hover:bg-white/[0.16] hover:border-white/30"
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
