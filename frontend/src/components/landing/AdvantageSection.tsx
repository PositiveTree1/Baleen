'use client';
import Image from 'next/image';

export function AdvantageSection() {
  const steps = [
    {
      num: '01',
      title: 'Discover',
      desc: 'Find verified, high-performing traders with proven track records.',
    },
    {
      num: '02',
      title: 'Configure',
      desc: 'Set your risk, size, and strategy with full control.',
    },
    {
      num: '03',
      title: 'Copy',
      desc: 'Let Baleen handle the execution with sub-second latency.',
    },
    {
      num: '04',
      title: 'Grow',
      desc: 'Track your performance and compound over time.',
    },
  ];

  return (
    <section id="advantage" className="py-24 px-6 lg:px-20 border-t border-black/[0.06] bg-[#FAFAFC]">
      <div className="max-w-7xl mx-auto space-y-20">
        
        {/* Top Header & Whale Image Showcase */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          {/* Left Text */}
          <div className="lg:col-span-5 space-y-6">
            <span className="text-[11px] font-bold tracking-[0.2em] uppercase text-slate-400 font-mono">
              The Advantage
            </span>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-950 tracking-tight leading-[1.15]">
              Trade with the <br />
              best, automatically.
            </h2>
            <p className="text-base text-slate-600 leading-relaxed max-w-md font-normal">
              Baleen gives you access to the smartest traders on Polymarket, with full transparency and control. You decide who to follow, how much to allocate, and when to adjust.
            </p>
          </div>

          {/* Right Whale Image */}
          <div className="lg:col-span-7 relative h-72 sm:h-84 lg:h-96 w-full rounded-3xl overflow-hidden shadow-xl border border-black/[0.06]">
            <Image
              src="/bgImage.jpeg"
              alt="Baleen Whale Breaching"
              fill
              className="object-cover object-center"
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-transparent" />
          </div>

        </div>

        {/* 4 Step Process Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 pt-10 border-t border-black/[0.06]">
          {steps.map((s, idx) => (
            <div key={idx} className="space-y-3">
              <div className="text-xs font-bold font-mono text-slate-400">{s.num}</div>
              <h3 className="text-lg font-bold text-slate-950 tracking-tight">{s.title}</h3>
              <p className="text-sm text-slate-600 leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}
