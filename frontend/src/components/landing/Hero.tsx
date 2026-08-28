'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight, ShieldCheck, Zap, TrendingUp, ChevronRight } from 'lucide-react';

export function Hero() {
  return (
    <section className="relative min-h-[80vh] sm:min-h-[84vh] flex items-center px-6 lg:px-20 overflow-hidden bg-[#F8F9FB] dark:bg-[#000000] transition-colors duration-150">
      {/* Background Whale Visual */}
      <div className="absolute inset-0 w-full h-full pointer-events-none select-none z-0">
        <Image
          src="/images/whale_tail_hero.jpg"
          alt="Baleen Whale Breaching Horizon"
          fill
          priority
          quality={100}
          className="object-cover object-right-bottom sm:object-right opacity-85 dark:opacity-35"
        />
        {/* Revolut Clean Neutral Contrast Gradients */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#F8F9FB] via-[#F8F9FB]/90 to-transparent dark:from-[#000000] dark:via-[#000000]/95 dark:to-transparent w-full sm:w-[58%] z-1" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#F8F9FB]/20 to-[#F8F9FB] dark:from-transparent dark:via-[#000000]/30 dark:to-[#000000] z-1" />
      </div>

      <div className="max-w-7xl mx-auto w-full relative z-10 pt-10 sm:pt-14 pb-16 sm:pb-20">
        <div className="max-w-xl sm:max-w-2xl flex flex-col items-start gap-6 sm:gap-7">
          
          {/* Main Headline - Revolut Clean Typography */}
          <motion.h1
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-5xl sm:text-6xl lg:text-7xl font-outfit font-extrabold tracking-[-0.04em] text-slate-950 dark:text-white leading-[1.02]"
          >
            Mirror the top 1% <br />
            <span className="text-slate-500 dark:text-[#8E8F99]">
              on Polymarket.
            </span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.08 }}
            className="text-base sm:text-lg text-slate-600 dark:text-[#8E8F99] leading-relaxed font-normal max-w-lg"
          >
            Baleen is an institutional copy-trading engine for Polymarket. Discover verified prediction snipers, size positions dynamically, and mirror smart money fills with sub-second latency.
          </motion.p>

          {/* Action CTAs - Revolut Matte Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.16 }}
            className="flex flex-wrap items-center gap-3.5 pt-2"
          >
            <Link href="/auth/signup">
              <button className="flex items-center gap-2.5 px-8 py-4 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black hover:bg-slate-800 dark:hover:bg-slate-200 text-sm font-bold transition-all shadow-md active:scale-[0.98] cursor-pointer group">
                <span>Get Started</span>
                <ArrowRight size={15} className="group-hover:translate-x-0.5 transition-transform" />
              </button>
            </Link>
            <Link href="/dashboard">
              <button className="flex items-center gap-2 px-6 py-4 rounded-full bg-white dark:bg-[#16171B] hover:bg-slate-100 dark:hover:bg-[#24262E] border border-black/[0.08] dark:border-white/10 text-slate-900 dark:text-white text-sm font-bold transition-all shadow-xs cursor-pointer">
                <span>View Dashboard</span>
                <ChevronRight size={14} className="text-slate-400 dark:text-[#8E8F99]" />
              </button>
            </Link>
          </motion.div>

          {/* 3 Revolut Minimal Monochrome Badges */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.24 }}
            className="grid grid-cols-1 sm:grid-cols-3 gap-5 pt-8 mt-2 border-t border-black/[0.06] dark:border-white/10 w-full max-w-xl"
          >
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-2xl bg-white dark:bg-[#16171B] border border-black/[0.06] dark:border-white/10 text-slate-900 dark:text-white shadow-2xs mt-0.5">
                <ShieldCheck size={16} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-950 dark:text-white">Audited Snipers</h4>
                <p className="text-[11px] text-slate-500 dark:text-[#8E8F99] mt-0.5">&gt;70% Wilson win rate</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="p-2 rounded-2xl bg-white dark:bg-[#16171B] border border-black/[0.06] dark:border-white/10 text-slate-900 dark:text-white shadow-2xs mt-0.5">
                <Zap size={16} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-950 dark:text-white">CLOB Sub-second</h4>
                <p className="text-[11px] text-slate-500 dark:text-[#8E8F99] mt-0.5">&lt;1.5¢ slippage limit</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="p-2 rounded-2xl bg-white dark:bg-[#16171B] border border-black/[0.06] dark:border-white/10 text-slate-900 dark:text-white shadow-2xs mt-0.5">
                <TrendingUp size={16} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-950 dark:text-white">Consensus Sizing</h4>
                <p className="text-[11px] text-slate-500 dark:text-[#8E8F99] mt-0.5">Dynamic 1.5x alpha</p>
              </div>
            </div>
          </motion.div>

        </div>
      </div>
    </section>
  );
}
