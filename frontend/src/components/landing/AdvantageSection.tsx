'use client';
import { motion } from 'framer-motion';
import { Search, Sliders, Zap, TrendingUp, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export function AdvantageSection() {
  const steps = [
    {
      num: '01',
      title: 'Discover',
      tag: 'On-Chain Scoring',
      desc: 'Find verified, hyper-consistent prediction traders with audited Wilson score confidence bounds and clean PnL histories.',
      icon: Search,
      color: '#00D09C'
    },
    {
      num: '02',
      title: 'Configure',
      tag: 'Risk Management',
      desc: 'Set your portfolio risk regime, sizing multipliers (1.0x - 2.0x), and category tolerances with quantitative precision.',
      icon: Sliders,
      color: '#FF7A00'
    },
    {
      num: '03',
      title: 'Copy',
      tag: 'HyperSync Engine',
      desc: 'Let Baleen automatically mirror smart money fills on Polymarket CLOB with sub-second execution speed.',
      icon: Zap,
      color: '#FF2D78'
    },
    {
      num: '04',
      title: 'Compound',
      tag: 'MTM Rebalancing',
      desc: 'Track live portfolio performance in real-time, inspect daily win/loss attribution, and compound returns on autopilot.',
      icon: TrendingUp,
      color: '#6366F1'
    },
  ];

  return (
    <section id="advantage" className="py-24 px-6 lg:px-20 border-t border-black/[0.06] dark:border-white/10 bg-[#FAFAFC] dark:bg-[#0A0B0E] transition-colors duration-150">
      <div className="max-w-7xl mx-auto space-y-16">
        
        {/* Header Title */}
        <div className="max-w-2xl space-y-4">
          <span className="text-[11px] font-bold tracking-[0.2em] uppercase text-slate-400 dark:text-[#8E8F99] font-mono">
            How It Works
          </span>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-950 dark:text-white tracking-tight leading-[1.12]">
            Trade with the best, <br />
            automatically.
          </h2>
          <p className="text-base sm:text-lg text-slate-600 dark:text-[#8E8F99] leading-relaxed font-normal">
            Baleen gives you access to the smartest traders on Polymarket with full transparency and control. You decide who to follow, how much to allocate, and when to adjust.
          </p>
        </div>

        {/* 4 Step Process Grid with Revolut Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((s, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: idx * 0.1 }}
              className="p-8 rounded-[28px] bg-white dark:bg-[#16171B] border border-black/[0.06] dark:border-white/10 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 space-y-5 flex flex-col justify-between group"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold font-mono text-slate-400 dark:text-[#8E8F99] tracking-wider">{s.num}</span>
                  <div 
                    className="w-10 h-10 rounded-2xl flex items-center justify-center transition-colors border border-black/[0.06] dark:border-white/10 bg-slate-50 dark:bg-[#1C1D22]"
                    style={{ color: s.color }}
                  >
                    <s.icon size={18} />
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-bold text-slate-950 dark:text-white tracking-tight">{s.title}</h3>
                  <span className="text-[11px] font-mono font-medium text-slate-400 dark:text-[#8E8F99] block mt-0.5">{s.tag}</span>
                </div>

                <p className="text-sm text-slate-600 dark:text-[#8E8F99] leading-relaxed font-normal">{s.desc}</p>
              </div>

              <div className="pt-4 border-t border-black/[0.04] dark:border-white/5 flex items-center gap-1.5 text-xs font-bold text-slate-950 dark:text-white group-hover:text-[#00D09C] transition-colors">
                <span>View Methodology</span>
                <ArrowRight size={13} />
              </div>
            </motion.div>
          ))}
        </div>

      </div>
    </section>
  );
}
