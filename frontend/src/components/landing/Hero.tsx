'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight, ShieldCheck, Zap, TrendingUp, ChevronRight, Activity, Award } from 'lucide-react';

export function Hero() {
  return (
    <section className="relative min-h-[82vh] flex items-center px-6 lg:px-20 overflow-hidden bg-[#F8F9FB] dark:bg-[#000000] transition-colors duration-150">
      {/* Background Whale Visual with Guaranteed Full-Fluke Visibility */}
      <div className="absolute inset-0 w-full h-full pointer-events-none select-none z-0">
        <Image
          src="/images/whale_tail_hero.jpg"
          alt="Baleen Whale Breaching Horizon"
          fill
          priority
          quality={100}
          className="object-cover object-right-bottom sm:object-right opacity-90 dark:opacity-40"
        />
        {/* Soft atmospheric white gradients for light mode and dark obsidian gradients for dark mode */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#F8F9FB] via-[#F8F9FB]/85 to-transparent dark:from-[#000000] dark:via-[#000000]/90 dark:to-transparent w-full sm:w-[60%] z-1" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#F8F9FB]/30 to-[#F8F9FB] dark:from-transparent dark:via-[#000000]/40 dark:to-[#000000] z-1" />
      </div>

      <div className="max-w-7xl mx-auto w-full relative z-10 pt-8 sm:pt-10 pb-16 sm:pb-20">
        <div className="max-w-xl sm:max-w-2xl flex flex-col items-start gap-6 sm:gap-7">
          
          {/* Eyebrow Pill with Glow Animation */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/90 dark:bg-[#16171B]/90 backdrop-blur-xl border border-black/[0.08] dark:border-white/10 shadow-[0_0_20px_rgba(0,208,156,0.15)]"
          >
            <span className="w-2 h-2 rounded-full bg-[#00D09C] animate-pulse" />
            <span className="text-[11px] font-bold tracking-[0.2em] uppercase text-slate-800 dark:text-white font-mono">
              Algorithmic Whale Index
            </span>
          </motion.div>

          {/* Main Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.08 }}
            className="text-4xl sm:text-6xl lg:text-7xl font-outfit font-extrabold tracking-[-0.035em] text-slate-950 dark:text-white leading-[1.04]"
          >
            Mirror the top 1% <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 via-teal-500 to-indigo-600 dark:from-[#00D09C] dark:via-[#34D399] dark:to-indigo-400">
              on Polymarket.
            </span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.16 }}
            className="text-base sm:text-lg text-slate-600 dark:text-[#8E8F99] leading-relaxed font-normal max-w-lg"
          >
            Baleen is an institutional copy-trading engine for Polymarket. Discover verified prediction snipers, size positions dynamically, and mirror smart money fills with sub-second latency.
          </motion.p>

          {/* Action CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.24 }}
            className="flex flex-wrap items-center gap-4 pt-1"
          >
            <Link href="/auth/signup">
              <button className="flex items-center gap-2.5 px-8 py-4 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black hover:bg-slate-800 dark:hover:bg-slate-200 text-sm font-bold transition-all shadow-lg hover:shadow-xl active:scale-[0.98] cursor-pointer group">
                <span>Start Copying Whales</span>
                <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
              </button>
            </Link>
            <Link href="/dashboard">
              <button className="flex items-center gap-2 px-6 py-4 rounded-full bg-white/80 dark:bg-[#16171B] hover:bg-white dark:hover:bg-[#24262E] border border-black/[0.08] dark:border-white/10 text-slate-800 dark:text-white text-sm font-bold transition-all backdrop-blur-2xl shadow-sm cursor-pointer">
                <Activity size={16} className="text-[#00D09C]" />
                <span>Live Sandbox Demo</span>
              </button>
            </Link>
          </motion.div>

          {/* 3 Feature Badges */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.32 }}
            className="grid grid-cols-1 sm:grid-cols-3 gap-5 pt-6 mt-2 border-t border-black/[0.06] dark:border-white/10 w-full max-w-xl"
          >
            <div className="flex items-start gap-2.5">
              <div className="p-2 rounded-xl bg-white dark:bg-[#16171B] border border-black/[0.06] dark:border-white/10 text-[#00D09C] shadow-2xs mt-0.5">
                <ShieldCheck size={16} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-950 dark:text-white">Audited Snipers</h4>
                <p className="text-[11px] text-slate-500 dark:text-[#8E8F99] mt-0.5">&gt;70% Wilson win rate</p>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <div className="p-2 rounded-xl bg-white dark:bg-[#16171B] border border-black/[0.06] dark:border-white/10 text-amber-500 shadow-2xs mt-0.5">
                <Zap size={16} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-950 dark:text-white">CLOB Sub-second</h4>
                <p className="text-[11px] text-slate-500 dark:text-[#8E8F99] mt-0.5">&lt;1.5¢ slippage tolerance</p>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <div className="p-2 rounded-xl bg-white dark:bg-[#16171B] border border-black/[0.06] dark:border-white/10 text-indigo-500 shadow-2xs mt-0.5">
                <TrendingUp size={16} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-950 dark:text-white">Consensus Multiplier</h4>
                <p className="text-[11px] text-slate-500 dark:text-[#8E8F99] mt-0.5">1.5x on aligned whales</p>
              </div>
            </div>
          </motion.div>

        </div>
      </div>
    </section>
  );
}
