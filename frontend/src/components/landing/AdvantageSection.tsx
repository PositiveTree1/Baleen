'use client';

import { motion } from 'framer-motion';
import { Shield, Zap, Target, Layers, ArrowUpRight } from 'lucide-react';
import Link from 'next/link';

const advantages = [
  {
    icon: Layers,
    title: 'Isolated $2,000 Sleeves',
    kicker: 'RISK QUARANTINE',
    color: 'from-cyan-500/20 to-cyan-500/0',
    borderColor: 'border-cyan-400/30',
    badgeColor: 'text-cyan-300 bg-cyan-500/10 border-cyan-400/20',
    description:
      'Capital is segmented into strictly isolated sleeves ($2,000 each on a $10,000 bankroll). Contagion from an unexpected loss in one market cannot erode the capital of your other whale positions.',
    stat: '$2,000',
    statLabel: 'Sleeve Cap',
  },
  {
    icon: Target,
    title: '$1.00 Floor Sizing Engine',
    kicker: 'EXECUTION CLEARANCE',
    color: 'from-emerald-500/20 to-emerald-500/0',
    borderColor: 'border-emerald-400/30',
    badgeColor: 'text-emerald-300 bg-emerald-500/10 border-emerald-400/20',
    description:
      'Polymarket enforces strict minimum order sizes. Baleen dynamically clamps micro-trades to a $1.00 floor or safely skips sub-threshold noise without distorting your portfolio allocation.',
    stat: '$1.00',
    statLabel: 'Min Order Floor',
  },
  {
    icon: Shield,
    title: 'Asymmetric Binary Alpha',
    kicker: 'MATHEMATICAL EDGE',
    color: 'from-amber-500/20 to-amber-500/0',
    borderColor: 'border-amber-400/30',
    badgeColor: 'text-amber-300 bg-amber-500/10 border-amber-400/20',
    description:
      'We filter for snipers exploiting probability asymmetry (p · [1 - p]). By executing on binary mispricings where odds heavily exceed market consensus, win rates reach 88%–94%.',
    stat: '91.4%',
    statLabel: 'Observed Win Rate',
  },
  {
    icon: Zap,
    title: 'Sub-120ms Envio Pipeline',
    kicker: 'HYPERSYNC RPC',
    color: 'from-indigo-500/20 to-indigo-500/0',
    borderColor: 'border-indigo-400/30',
    badgeColor: 'text-indigo-300 bg-indigo-500/10 border-indigo-400/20',
    description:
      'Direct indexer streams on Polygon monitor whale order creation events at the mempool and block level, replicating fills before retail liquidity pools suffer adverse selection.',
    stat: '<120ms',
    statLabel: 'Copy Latency',
  },
];

export function AdvantageSection() {
  return (
    <section id="advantages" className="relative overflow-hidden bg-[#040914] px-5 py-24 text-white sm:px-8 sm:py-32 lg:px-12">
      {/* Background Ambience */}
      <div className="pointer-events-none absolute left-1/2 top-0 -translate-x-1/2 w-[800px] h-96 bg-cyan-500/5 blur-[120px]" />

      <div className="relative mx-auto max-w-[1380px]">
        {/* Section Header */}
        <div className="max-w-3xl">
          <p className="section-kicker">ARCHITECTURAL ADVANTAGE</p>
          <h2 className="mt-4 font-outfit text-4xl font-black leading-[0.95] tracking-[-0.05em] text-white sm:text-6xl">
            Built like an institution.
            <span className="block surreal-text-gradient">Engineered for copy alpha.</span>
          </h2>
          <p className="mt-6 max-w-xl text-base font-normal leading-relaxed text-slate-300 sm:text-lg">
            Standard copy trading blindsides retail investors with slippage and contagion. Baleen enforces mathematical safeguards built specifically for binary prediction markets.
          </p>
        </div>

        {/* 4 Liquid Glass Advantage Cards */}
        <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {advantages.map((adv, index) => (
            <motion.div
              key={adv.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className={`liquid-glass-card group relative flex flex-col justify-between overflow-hidden rounded-[28px] border p-7 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl ${adv.borderColor}`}
            >
              {/* Card Gradient Glow */}
              <div className={`pointer-events-none absolute inset-0 bg-gradient-to-b ${adv.color} opacity-30 group-hover:opacity-60 transition-opacity`} />

              <div className="relative z-10">
                {/* Header Icon + Kicker */}
                <div className="flex items-center justify-between">
                  <div className="grid size-12 place-items-center rounded-2xl border border-white/15 bg-white/[0.08] backdrop-blur-xl">
                    <adv.icon size={22} className="text-white" />
                  </div>
                  <span className={`rounded-full border px-2.5 py-1 font-mono text-[10px] font-bold tracking-wider ${adv.badgeColor}`}>
                    {adv.kicker}
                  </span>
                </div>

                <h3 className="mt-6 font-outfit text-xl font-bold tracking-tight text-white sm:text-2xl">
                  {adv.title}
                </h3>
                <p className="mt-3 text-xs leading-relaxed text-slate-300/85 sm:text-sm">
                  {adv.description}
                </p>
              </div>

              {/* Bottom Stat Pill */}
              <div className="relative z-10 mt-8 border-t border-white/10 pt-4 flex items-center justify-between">
                <div>
                  <div className="font-mono text-2xl font-black text-white">{adv.stat}</div>
                  <div className="text-[10px] font-mono font-semibold text-white/50">{adv.statLabel}</div>
                </div>
                <Link
                  href="/dashboard"
                  className="grid size-9 place-items-center rounded-full border border-white/10 bg-white/[0.05] text-white/60 transition-all group-hover:border-white/30 group-hover:bg-white group-hover:text-black"
                  aria-label={`Explore ${adv.title}`}
                >
                  <ArrowUpRight size={15} />
                </Link>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
