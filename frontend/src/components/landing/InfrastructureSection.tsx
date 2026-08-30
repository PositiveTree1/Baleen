'use client';
import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';

export function InfrastructureSection() {
  return (
    <section id="infrastructure" className="py-14 sm:py-24 px-4 sm:px-6 lg:px-20 border-t border-black/[0.06] dark:border-white/10 bg-white dark:bg-[#000000] transition-colors duration-150 scroll-mt-20">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Left Text Column */}
          <div className="lg:col-span-5 space-y-6">
            <span className="text-[11px] font-bold tracking-[0.2em] uppercase text-slate-400 dark:text-[#8E8F99] font-mono">
              Built for Performance
            </span>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-950 dark:text-white tracking-[-0.03em] leading-[1.12] text-balance">
              Institutional-grade <br />
              infrastructure.
            </h2>
            <p className="text-base text-slate-600 dark:text-[#8E8F99] leading-relaxed max-w-md font-normal">
              Engineered for speed, security and precision. Baleen runs on a robust async execution engine designed for automated prediction market copy-trading.
            </p>
          </div>

          {/* Middle Stats Column */}
          <div className="lg:col-span-3 space-y-8 lg:border-l lg:border-black/[0.06] dark:lg:border-white/10 lg:pl-10">
            <div>
              <div className="text-3xl font-extrabold text-slate-950 dark:text-white font-mono tracking-tight tabular-nums">&lt; 350ms</div>
              <div className="text-xs text-slate-500 dark:text-[#8E8F99] font-semibold mt-1">CLOB Taker Latency</div>
            </div>
            <div>
              <div className="text-3xl font-extrabold text-slate-950 dark:text-white font-mono tracking-tight tabular-nums">99.98%</div>
              <div className="text-xs text-slate-500 dark:text-[#8E8F99] font-semibold mt-1">Engine Uptime</div>
            </div>
            <div>
              <div className="text-3xl font-extrabold text-slate-950 dark:text-white font-mono tracking-tight tabular-nums">1.5 Cents</div>
              <div className="text-xs text-slate-500 dark:text-[#8E8F99] font-semibold mt-1">Max Slippage Limit</div>
            </div>
          </div>

          {/* Right Obsidian CTA Card */}
          <div className="lg:col-span-4">
            <motion.div 
              initial={{ opacity: 0, scale: 0.96 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              className="relative rounded-[28px] bg-[#16171B] p-8 sm:p-10 text-white shadow-2xl overflow-hidden border border-white/10 space-y-6"
            >
              {/* Obsidian Texture Background */}
              <div className="absolute inset-0 w-full h-full pointer-events-none select-none z-0" aria-hidden="true">
                <Image
                  src="/images/cta_obsidian_silk.jpg"
                  alt="Liquid Obsidian Silk Texture"
                  fill
                  className="object-cover opacity-45 mix-blend-luminosity"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#16171B] via-[#16171B]/70 to-[#16171B]/50" />
              </div>
              
              <div className="relative z-10 space-y-3">
                <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-slate-400 font-mono">
                  Ready to start?
                </span>
                <h3 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white leading-snug text-balance">
                  Join the next generation of prediction trading.
                </h3>
              </div>

              <div className="relative z-10 pt-2">
                <Link href="/auth/signup">
                  <button 
                    className="flex items-center gap-2.5 px-7 py-3.5 rounded-full bg-white text-black hover:bg-slate-200 text-sm font-bold transition-all shadow-md active:scale-[0.98] cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] focus-visible:ring-offset-2 focus-visible:ring-offset-[#16171B]"
                    aria-label="Get Started Free with Baleen"
                  >
                    <span>Get Started Free</span>
                    <ArrowRight size={15} aria-hidden="true" />
                  </button>
                </Link>
              </div>
            </motion.div>
          </div>

        </div>
      </div>
    </section>
  );
}
