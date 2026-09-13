'use client';

import Image from 'next/image';
import Link from 'next/link';
import { ArrowRight, ShieldCheck, Zap, Layers, Activity, CheckCircle, Cpu, Lock, ArrowUpRight } from 'lucide-react';

export function InfrastructureSection() {
  return (
    <>
      {/* Deep Quantitative Infrastructure Showcase */}
      <section id="infrastructure" className="relative overflow-hidden bg-[#07080A] px-5 py-24 text-white sm:px-8 sm:py-32 lg:px-12 border-b border-white/10">
        <div className="mx-auto max-w-[1380px]">
          <div className="apple-glass-card relative overflow-hidden rounded-[36px] border border-white/10 bg-[#0E1015]/90 p-6 sm:p-12 lg:p-16">
            <div className="grid gap-12 lg:grid-cols-[1.1fr_.9fr] lg:items-center">
              {/* Left Column: Quantitative System Specs */}
              <div>
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3.5 py-1 text-xs font-bold tracking-wider text-zinc-300 font-mono">
                  <Activity size={13} className="text-[#00D09C]" />
                  <span>DEEP INFRASTRUCTURE</span>
                </div>
                <h2 className="font-outfit text-3xl font-black leading-[0.95] tracking-[-0.04em] text-white sm:text-5xl lg:text-6xl">
                  Speed without compromise.
                  <span className="block text-zinc-400 font-extrabold">Precision without noise.</span>
                </h2>
                <p className="mt-6 max-w-xl text-base font-normal leading-relaxed text-zinc-400 sm:text-lg">
                  Every prediction trade on Polymarket is an on-chain event. Baleen captures, validates, and simulates copy execution across isolated sleeves before retail orderbooks shift.
                </p>

                {/* Technical Specs List */}
                <div className="mt-10 grid gap-4 sm:grid-cols-2 font-mono">
                  {[
                    { title: 'Envio Hypersync RPC', desc: 'Direct Polygon chain indexing at sub-120ms latency' },
                    { title: 'Dynamic Kelly Fraction', desc: 'Continuous sizing optimization per market conviction' },
                    { title: 'Algorithmic Pruning', desc: 'Automated sleeve isolation when variance shifts' },
                    { title: 'Non-Custodial Sandbox', desc: 'Risk-free simulated executions with live orderbook math' },
                  ].map((spec) => (
                    <div
                      key={spec.title}
                      className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 backdrop-blur-xl"
                    >
                      <div className="flex items-center gap-2 text-sm font-bold text-white">
                        <CheckCircle size={15} className="text-[#00D09C]" />
                        <span>{spec.title}</span>
                      </div>
                      <p className="mt-1.5 text-xs text-zinc-400 leading-relaxed font-sans">{spec.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right Column: Apple Optical Glass Live Telemetry Card */}
              <div className="relative mx-auto w-full max-w-[480px]">
                <div className="apple-glass-card apple-lens-refraction relative overflow-hidden rounded-[32px] border border-white/15 bg-[#12141A] p-6 shadow-2xl">
                  {/* Telemetry Visualizer */}
                  <div className="rounded-2xl border border-white/10 bg-black/50 p-5 space-y-4">
                    <div className="flex items-center justify-between border-b border-white/10 pb-3 font-mono text-xs">
                      <span className="flex items-center gap-2 text-zinc-400">
                        <Cpu size={14} className="text-[#00D09C]" />
                        <span>HYPERSYNC PIPELINE</span>
                      </span>
                      <span className="text-[#00D09C] font-bold">ONLINE</span>
                    </div>

                    <div className="space-y-2 font-mono text-xs">
                      <div className="flex justify-between text-zinc-400">
                        <span>Mempool Ingestion:</span>
                        <span className="text-white">sub-35ms</span>
                      </div>
                      <div className="flex justify-between text-zinc-400">
                        <span>CLOB Book Matching:</span>
                        <span className="text-white">sub-50ms</span>
                      </div>
                      <div className="flex justify-between text-zinc-400">
                        <span>Isolated Sleeve Guard:</span>
                        <span className="text-[#00D09C]">Active ($2k Cap)</span>
                      </div>
                      <div className="flex justify-between text-zinc-400">
                        <span>Sizing Engine:</span>
                        <span className="text-white">Kelly Fractional</span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-white/10 flex items-center justify-between text-[11px] font-mono text-zinc-500">
                      <span>Polygon Block #68,291,048</span>
                      <span>0.00% Slippage Target</span>
                    </div>
                  </div>

                  {/* Highlights */}
                  <div className="mt-6 flex items-center justify-between border-t border-white/10 pt-4">
                    <div>
                      <div className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 font-mono">
                        Sandbox Capital Ready
                      </div>
                      <div className="font-mono text-2xl font-black text-white tabular-nums">$10,000.00</div>
                    </div>
                    <span className="rounded-full border border-[#00D09C]/30 bg-[#00D09C]/10 px-3 py-1 font-mono text-xs font-bold text-[#00D09C]">
                      Guest Instant Access
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* High-Impact Closing CTA Banner (Matte Black Obsidian Silk Metallic) */}
      <section className="relative overflow-hidden bg-[#07080A] px-5 py-24 text-white sm:px-8 sm:py-36">
        <div className="relative mx-auto max-w-[1380px]">
          <div className="matte-metallic-card relative overflow-hidden rounded-[36px] border border-white/15 p-8 sm:p-16 lg:p-20 shadow-2xl">
            {/* Obsidian Silk Texture in CTA */}
            <div className="absolute inset-0 z-0 select-none overflow-hidden opacity-30">
              <Image
                src="/images/cta_obsidian_silk.jpg"
                alt="Matte black obsidian silk texture"
                fill
                sizes="100vw"
                className="object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-[#07080A] via-[#07080A]/85 to-transparent" />
            </div>

            <div className="relative z-10 flex flex-col justify-between gap-10 lg:flex-row lg:items-end">
              <div className="max-w-3xl">
                <span className="font-mono text-xs font-extrabold uppercase tracking-widest text-[#00D09C]">
                  READY TO TEST ALPHA?
                </span>
                <h2 className="mt-4 font-outfit text-4xl font-black leading-[0.92] tracking-[-0.05em] text-white sm:text-6xl lg:text-7xl">
                  The whales have moved.
                  <span className="block text-zinc-400 font-extrabold">Are you tracking them?</span>
                </h2>
                <p className="mt-6 max-w-xl text-base font-normal leading-relaxed text-zinc-400 sm:text-lg">
                  Join prediction market researchers shadowing top Polymarket snipers with isolated risk, instant paper allocations, and sub-120ms execution.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <Link
                  href="/dashboard"
                  className="group inline-flex h-15 shrink-0 items-center justify-center gap-3 rounded-full bg-white px-8 text-sm font-extrabold text-black shadow-2xl transition-all hover:bg-zinc-200 active:scale-[0.98]"
                >
                  <span>Launch $10,000 Sandbox</span>
                  <ArrowRight size={17} className="transition-transform group-hover:translate-x-1" aria-hidden="true" />
                </Link>

                <Link
                  href="/auth/signup"
                  className="inline-flex h-15 shrink-0 items-center justify-center rounded-full border border-white/15 bg-white/[0.04] px-8 text-sm font-bold text-white backdrop-blur-xl transition-all hover:bg-white/[0.08] hover:border-white/25"
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
