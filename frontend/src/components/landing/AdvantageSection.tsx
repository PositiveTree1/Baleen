'use client';
import { motion } from 'framer-motion';
import { Search, Sliders, Zap, TrendingUp, ShieldCheck, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export function AdvantageSection() {
  const steps = [
    {
      num: '01',
      title: 'Discover',
      tag: 'On-Chain Scoring',
      desc: 'Find verified, high-performing traders with proven historical track records and audited Wilson confidence bounds.',
      icon: Search,
    },
    {
      num: '02',
      title: 'Configure',
      tag: 'Risk Management',
      desc: 'Set your portfolio risk parameters, position sizing weights, and category tolerances with complete precision.',
      icon: Sliders,
    },
    {
      num: '03',
      title: 'Copy',
      tag: 'HyperSync Engine',
      desc: 'Let Baleen automatically mirror smart money fills on Polymarket with sub-second execution latency.',
      icon: Zap,
    },
    {
      num: '04',
      title: 'Grow',
      tag: 'MTM Compounding',
      desc: 'Track live portfolio performance in real-time, inspect daily PnL attribution, and compound over time.',
      icon: TrendingUp,
    },
  ];

  return (
    <section id="advantage" className="py-28 px-6 lg:px-20 border-t border-black/[0.06] bg-[#FAFAFC]">
      <div className="max-w-7xl mx-auto space-y-16">
        
        {/* Header Title */}
        <div className="max-w-2xl space-y-4">
          <span className="text-[11px] font-bold tracking-[0.2em] uppercase text-slate-400 font-mono">
            The Advantage
          </span>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-950 tracking-tight leading-[1.12]">
            Trade with the best, <br />
            automatically.
          </h2>
          <p className="text-base sm:text-lg text-slate-600 leading-relaxed font-normal">
            Baleen gives you access to the smartest traders on Polymarket with full transparency and control. You decide who to follow, how much to allocate, and when to adjust.
          </p>
        </div>

        {/* 4 Step Process Grid with Apple Frosted Glass Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((s, idx) => (
            <div 
              key={idx} 
              className="p-8 rounded-3xl bg-white border border-black/[0.06] shadow-[inset_0_1px_1px_0_rgba(255,255,255,1),0_2px_8px_-2px_rgba(15,23,42,0.03),0_12px_24px_-6px_rgba(15,23,42,0.04)] hover:shadow-lg hover:-translate-y-1 transition-all duration-300 space-y-5 flex flex-col justify-between group"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold font-mono text-slate-400 tracking-wider">{s.num}</span>
                  <div className="w-9 h-9 rounded-xl bg-slate-50 group-hover:bg-slate-950 group-hover:text-white text-slate-800 border border-black/[0.06] flex items-center justify-center transition-colors">
                    <s.icon size={16} />
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-bold text-slate-950 tracking-tight">{s.title}</h3>
                  <span className="text-[11px] font-mono font-medium text-slate-400 block mt-0.5">{s.tag}</span>
                </div>

                <p className="text-sm text-slate-600 leading-relaxed font-normal">{s.desc}</p>
              </div>

              <div className="pt-4 border-t border-black/[0.04] flex items-center gap-1 text-xs font-semibold text-slate-950 group-hover:text-indigo-600 transition-colors">
                <span>Learn more</span>
                <ArrowRight size={12} className="group-hover:translate-x-1 transition-transform" />
              </div>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}
