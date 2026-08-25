'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight, ShieldCheck, Zap, TrendingUp, Sparkles, ChevronRight } from 'lucide-react';

export function Hero() {
  return (
    <section className="relative min-h-[85vh] sm:min-h-[88vh] flex items-center justify-center px-6 lg:px-20 overflow-hidden bg-white">
      {/* Background Whale Visual with Smooth Atmospheric Gradients */}
      <div className="absolute inset-0 w-full h-full pointer-events-none select-none z-0">
        <Image
          src="/bgImage.jpeg"
          alt="Baleen Atmospheric Background"
          fill
          priority
          quality={95}
          className="object-cover object-right sm:object-center opacity-90 sm:opacity-100"
        />
        {/* Soft atmospheric white gradients to ensure perfect left-side contrast */}
        <div className="absolute inset-0 bg-gradient-to-r from-white via-white/80 to-transparent w-full sm:w-[65%] z-1" />
        <div className="absolute inset-0 bg-gradient-to-b from-white/40 via-transparent to-white z-1" />
      </div>

      <div className="max-w-7xl mx-auto w-full relative z-10 py-16 sm:py-24">
        <div className="max-w-xl sm:max-w-2xl flex flex-col items-start gap-6 sm:gap-8">
          
          {/* Eyebrow Tag */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/90 backdrop-blur-xl border border-black/[0.08] shadow-[inset_0_1px_1px_rgba(255,255,255,1),0_2px_6px_rgba(0,0,0,0.03)]"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[11px] font-bold tracking-[0.2em] uppercase text-slate-700 font-mono">
              Smarter trading. Simpler.
            </span>
          </motion.div>

          {/* Main Title */}
          <motion.h1
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-slate-950 leading-[1.06]"
          >
            Mirror the top 1% <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-slate-950 via-slate-700 to-slate-900">
              on Polymarket.
            </span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-base sm:text-lg lg:text-xl text-slate-600 leading-relaxed font-normal max-w-xl"
          >
            Baleen is an institutional copy-trading engine for Polymarket. Discover verified prediction whales, size positions dynamically, and mirror smart money fills with sub-second latency.
          </motion.p>

          {/* Action CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-wrap items-center gap-3.5 pt-2"
          >
            <Link href="/auth/signup">
              <button className="flex items-center gap-2.5 px-7 py-3.5 rounded-full bg-slate-950 text-white hover:bg-slate-800 text-sm font-semibold transition-all shadow-[0_2px_8px_rgba(0,0,0,0.12),0_12px_24px_-6px_rgba(15,23,42,0.2)] hover:shadow-lg active:scale-[0.98] cursor-pointer group">
                <span>Get Started Free</span>
                <ArrowRight size={15} className="group-hover:translate-x-0.5 transition-transform" />
              </button>
            </Link>
            <Link href="#advantage">
              <button className="flex items-center gap-2 px-6 py-3.5 rounded-full bg-white/80 hover:bg-white border border-white/90 text-slate-800 text-sm font-semibold transition-all backdrop-blur-2xl shadow-[inset_0_1px_1px_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.04)] hover:shadow cursor-pointer">
                <span>Explore The Advantage</span>
                <ChevronRight size={14} className="text-slate-400" />
              </button>
            </Link>
          </motion.div>

          {/* 3 Minimal Feature Badges */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="grid grid-cols-1 sm:grid-cols-3 gap-5 pt-8 mt-4 border-t border-black/[0.06] w-full"
          >
            <div className="flex items-start gap-2.5">
              <div className="p-1.5 rounded-xl bg-white/90 border border-black/[0.06] text-slate-800 shadow-2xs mt-0.5">
                <ShieldCheck size={16} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-950">Verified Wallets</h4>
                <p className="text-[11px] text-slate-500 mt-0.5">Only audited smart money</p>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <div className="p-1.5 rounded-xl bg-white/90 border border-black/[0.06] text-slate-800 shadow-2xs mt-0.5">
                <Zap size={16} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-950">Real-Time Sync</h4>
                <p className="text-[11px] text-slate-500 mt-0.5">38ms execution speed</p>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <div className="p-1.5 rounded-xl bg-white/90 border border-black/[0.06] text-slate-800 shadow-2xs mt-0.5">
                <TrendingUp size={16} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-950">Dynamic Sizing</h4>
                <p className="text-[11px] text-slate-500 mt-0.5">Automated risk limits</p>
              </div>
            </div>
          </motion.div>

        </div>
      </div>
    </section>
  );
}
