'use client';

import { motion } from 'framer-motion';
import { Shield, Zap, Target, Layers, ArrowUpRight } from 'lucide-react';
import Link from 'next/link';

const advantages = [
  {
    icon: Layers,
    title: 'Isolated $2,000 Sleeves',
    kicker: 'RISK QUARANTINE',
    description:
      'Capital is segmented into strictly isolated sleeves ($2,000 each on a $10,000 bankroll). Contagion from an unexpected loss in one market cannot erode the capital of your other whale positions.',
    stat: '$2,000',
    statLabel: 'Sleeve Cap',
  },
  {
    icon: Target,
    title: '$1.00 Floor Sizing Engine',
    kicker: 'EXECUTION CLEARANCE',
    description:
      'Polymarket enforces strict minimum order sizes. Baleen dynamically clamps micro-trades to a $1.00 floor or safely skips sub-threshold noise without distorting your portfolio allocation.',
    stat: '$1.00',
    statLabel: 'Min Order Floor',
  },
  {
    icon: Shield,
    title: 'Asymmetric Binary Alpha',
    kicker: 'MATHEMATICAL EDGE',
    description:
      'We filter for snipers exploiting probability asymmetry. By executing on binary mispricings where odds heavily exceed market consensus, win rates reach 88%–94%.',
    stat: '91.4%',
    statLabel: 'Observed Win Rate',
  },
  {
    icon: Zap,
    title: 'Sub-120ms Envio Pipeline',
    kicker: 'HYPERSYNC RPC',
    description:
      'Direct indexer streams on Polygon monitor whale order creation events at the mempool and block level, replicating fills before retail liquidity pools suffer adverse selection.',
    stat: '<120ms',
    statLabel: 'Copy Latency',
  },
];

export function AdvantageSection() {
  return (
    <section id="advantages" className="relative overflow-hidden bg-[#07080A] px-5 py-24 text-white sm:px-8 sm:py-32 lg:px-12 border-b border-white/10">
      <div className="relative mx-auto max-w-[1380px]">
        {/* Section Header */}
        <div className="max-w-3xl">
          <p className="font-mono text-xs font-bold tracking-widest text-[#00D09C] uppercase">
            ARCHITECTURAL ADVANTAGE
          </p>
          <h2 className="mt-4 font-outfit text-4xl font-black leading-[0.95] tracking-[-0.05em] text-white sm:text-6xl">
            Built like an institution.
            <span className="block text-zinc-400 font-extrabold">Engineered for copy alpha.</span>
          </h2>
          <p className="mt-6 max-w-xl text-base font-normal leading-relaxed text-zinc-400 sm:text-lg">
            Standard copy trading blindsides retail investors with slippage and contagion. Baleen enforces mathematical safeguards built specifically for binary prediction markets.
          </p>
        </div>

        {/* 4 Matte Metallic Apple Glass Cards */}
        <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {advantages.map((adv, index) => (
            <motion.div
              key={adv.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className="apple-glass-card group relative flex flex-col justify-between overflow-hidden rounded-[28px] border border-white/10 bg-[#0E1015]/90 p-7 transition-all duration-300 hover:border-white/20 hover:scale-[1.01] hover:shadow-2xl"
            >
              <div className="relative z-10">
                {/* Header Icon + Kicker */}
                <div className="flex items-center justify-between">
                  <div className="grid size-11 place-items-center rounded-2xl border border-white/10 bg-white/[0.04]">
                    <adv.icon size={20} className="text-white" />
                  </div>
                  <span className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 font-mono text-[10px] font-bold tracking-wider text-zinc-300">
                    {adv.kicker}
                  </span>
                </div>

                <h3 className="mt-6 font-outfit text-xl font-bold tracking-tight text-white sm:text-2xl">
                  {adv.title}
                </h3>
                <p className="mt-3 text-xs leading-relaxed text-zinc-400 sm:text-sm">
                  {adv.description}
                </p>
              </div>

              {/* Bottom Stat Pill */}
              <div className="relative z-10 mt-8 border-t border-white/10 pt-4 flex items-center justify-between">
                <div>
                  <div className="font-mono text-2xl font-black text-white tabular-nums">{adv.stat}</div>
                  <div className="text-[10px] font-mono font-semibold text-zinc-500">{adv.statLabel}</div>
                </div>
                <Link
                  href="/dashboard"
                  className="grid size-9 place-items-center rounded-full border border-white/10 bg-white/[0.04] text-zinc-400 transition-all group-hover:border-white/30 group-hover:bg-white group-hover:text-black"
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
