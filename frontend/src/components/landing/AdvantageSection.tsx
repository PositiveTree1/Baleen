'use client';

import { motion } from 'framer-motion';
import { Shield, Zap, Target, Layers } from 'lucide-react';
import { LiquidGlassCard } from './LiquidGlassCard';

const advantages = [
  {
    icon: Layers,
    title: 'Adaptive Bankroll Sleeves',
    kicker: 'DYNAMIC ALLOCATION',
    description:
      'Capital is segmented into strictly isolated sleeves based on bankroll ($20 floor, $10,000 across 5 isolated $2,000 sleeves). A drawdown in one market cannot erode the capital of your other whale positions.',
    stat: '1–5',
    statLabel: 'Active Sleeves',
    color: '#00D09C',
  },
  {
    icon: Target,
    title: '$1.00 Floor Sizing Engine',
    kicker: 'EXECUTION CLEARANCE',
    description:
      'Polymarket enforces strict minimum contract increments. Baleen dynamically clamps micro-trades to a $1.00 floor or safely skips sub-threshold noise without distorting your portfolio allocation.',
    stat: '$1.00',
    statLabel: 'Min Order Floor',
    color: '#38BDF8',
  },
  {
    icon: Shield,
    title: 'Asymmetric Binary Alpha',
    kicker: 'MATHEMATICAL EDGE',
    description:
      'We filter for snipers exploiting probability asymmetry. By executing on binary mispricings where odds heavily exceed market consensus, observed win rates reach 88%–94%.',
    stat: '91.4%',
    statLabel: 'Observed Win Rate',
    color: '#C084FC',
  },
  {
    icon: Zap,
    title: 'Sub-120ms Envio Pipeline',
    kicker: 'HYPERSYNC RPC',
    description:
      'Direct indexer streams on Polygon monitor whale order creation events at the mempool and block level, replicating fills before retail liquidity pools suffer adverse selection.',
    stat: '<120ms',
    statLabel: 'Copy Latency',
    color: '#00D09C',
  },
];

export function AdvantageSection() {
  return (
    <section id="advantages" className="relative overflow-hidden px-4 sm:px-6 lg:px-8 py-24 sm:py-32 border-b border-sky-100/80">
      <div className="relative z-10 mx-auto max-w-[1240px]">
        {/* Section Header */}
        <div className="max-w-2xl">
          <span className="font-mono text-xs font-bold tracking-widest text-sky-700 uppercase">
            ARCHITECTURAL ADVANTAGE
          </span>
          <h2 className="mt-3 font-outfit text-3xl sm:text-5xl font-black leading-[1.02] tracking-tight text-slate-950">
            Built like an institution.
            <span className="block text-slate-600 font-extrabold">Engineered for copy alpha.</span>
          </h2>
          <p className="mt-4 text-sm sm:text-base text-slate-600 leading-relaxed">
            Standard copy trading blindsides retail investors with slippage and contagion. Baleen enforces mathematical safeguards built specifically for binary prediction markets.
          </p>
        </div>

        {/* 4 Optical Liquid Glass Cards */}
        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {advantages.map((adv, index) => (
            <motion.div
              key={adv.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.08 }}
            >
              <LiquidGlassCard className="h-full flex flex-col justify-between">
                <div>
                  {/* Top Bar: Icon + Kicker */}
                  <div className="flex items-center justify-between">
                    <div className="grid size-11 place-items-center rounded-2xl border border-sky-100 bg-sky-50/80 shadow-xs">
                      <adv.icon size={20} style={{ color: adv.color }} />
                    </div>
                    <span className="rounded-full border border-sky-100 bg-white/80 px-2.5 py-1 font-mono text-[10px] font-bold tracking-wider text-slate-700 shadow-xs">
                      {adv.kicker}
                    </span>
                  </div>

                  {/* Title & Description */}
                  <h3 className="mt-5 font-outfit text-xl font-bold tracking-tight text-slate-950">
                    {adv.title}
                  </h3>
                  <p className="mt-3 text-xs sm:text-sm leading-relaxed text-slate-600 font-sans">
                    {adv.description}
                  </p>
                </div>

                {/* Bottom Metric Stat */}
                <div className="mt-8 border-t border-sky-100/80 pt-4 flex items-center justify-between font-mono">
                  <div>
                    <div className="text-2xl font-black text-slate-950 tabular-nums tracking-tight">
                      {adv.stat}
                    </div>
                    <div className="text-[10px] font-semibold text-slate-500">{adv.statLabel}</div>
                  </div>
                  <div
                    className="size-2 rounded-full"
                    style={{ backgroundColor: adv.color, boxShadow: `0 0 8px ${adv.color}` }}
                  />
                </div>
              </LiquidGlassCard>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
