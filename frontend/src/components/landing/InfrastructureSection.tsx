'use client';
import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight } from 'lucide-react';

export function InfrastructureSection() {
  return (
    <section id="infrastructure" className="py-24 px-6 lg:px-20 border-t border-black/[0.06] bg-white">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Left Text Column */}
          <div className="lg:col-span-5 space-y-6">
            <span className="text-[11px] font-bold tracking-[0.2em] uppercase text-slate-400 font-mono">
              Built for Performance
            </span>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-950 tracking-[-0.03em] leading-[1.12]">
              Institutional-grade <br />
              infrastructure.
            </h2>
            <p className="text-base text-slate-600 leading-relaxed max-w-md font-normal">
              Engineered for speed, security and precision. Baleen runs on a robust infrastructure designed for professional traders.
            </p>
          </div>

          {/* Middle Stats Column */}
          <div className="lg:col-span-3 space-y-8 lg:border-l lg:border-black/[0.06] lg:pl-10">
            <div>
              <div className="text-3xl font-extrabold text-slate-950 font-mono tracking-tight">&lt; 1s</div>
              <div className="text-xs text-slate-500 font-medium mt-1">Execution latency</div>
            </div>
            <div>
              <div className="text-3xl font-extrabold text-slate-950 font-mono tracking-tight">99.9%</div>
              <div className="text-xs text-slate-500 font-medium mt-1">Uptime</div>
            </div>
            <div>
              <div className="text-3xl font-extrabold text-slate-950 font-mono tracking-tight">Bank-grade</div>
              <div className="text-xs text-slate-500 font-medium mt-1">Security</div>
            </div>
          </div>

          {/* Right Dark Obsidian Silk CTA Card */}
          <div className="lg:col-span-4">
            <div className="relative rounded-3xl bg-slate-950 p-8 sm:p-10 text-white shadow-2xl overflow-hidden border border-white/10 space-y-6">
              {/* Generated Liquid Obsidian Silk Texture Background */}
              <div className="absolute inset-0 w-full h-full pointer-events-none select-none z-0">
                <Image
                  src="/images/cta_obsidian_silk.jpg"
                  alt="Liquid Obsidian Silk Texture"
                  fill
                  className="object-cover opacity-60 mix-blend-luminosity"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-slate-950/50 to-slate-950/70" />
              </div>
              
              <div className="relative z-10 space-y-3">
                <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-slate-400 font-mono">
                  Ready to get started?
                </span>
                <h3 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white leading-snug">
                  Join the next generation of prediction trading.
                </h3>
              </div>

              <div className="relative z-10 pt-2">
                <Link href="/auth/signup">
                  <button className="flex items-center gap-2 px-6 py-3.5 rounded-full bg-white text-slate-950 hover:bg-slate-100 text-sm font-bold transition-all shadow-sm active:scale-[0.98] cursor-pointer">
                    <span>Get Started Free</span>
                    <ArrowRight size={15} />
                  </button>
                </Link>
              </div>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
