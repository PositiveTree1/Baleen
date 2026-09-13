'use client';

import Link from 'next/link';
import { Sparkles, Trophy, Calculator, ArrowRight } from 'lucide-react';

export function MobileGlassDock() {
  return (
    <div className="fixed bottom-4 inset-x-3 z-40 sm:hidden pointer-events-none">
      <div className="apple-glass pointer-events-auto mx-auto flex max-w-sm items-center justify-between gap-1 rounded-full p-2 border border-white/15 bg-[#0E1015]/95 shadow-2xl backdrop-blur-3xl">
        <Link
          href="#advantages"
          className="flex items-center gap-1.5 rounded-full px-3 py-2 text-[11px] font-bold text-zinc-300 transition-colors hover:bg-white/10 hover:text-white font-mono"
        >
          <Sparkles size={14} className="text-zinc-400" />
          <span>System</span>
        </Link>

        <Link
          href="#simulator"
          className="flex items-center gap-1.5 rounded-full px-3 py-2 text-[11px] font-bold text-zinc-300 transition-colors hover:bg-white/10 hover:text-white font-mono"
        >
          <Calculator size={14} className="text-zinc-400" />
          <span>Model</span>
        </Link>

        <Link
          href="#leaderboard"
          className="flex items-center gap-1.5 rounded-full px-3 py-2 text-[11px] font-bold text-zinc-300 transition-colors hover:bg-white/10 hover:text-white font-mono"
        >
          <Trophy size={14} className="text-[#00D09C]" />
          <span>Whales</span>
        </Link>

        <Link
          href="/dashboard"
          className="flex items-center gap-1.5 rounded-full bg-white px-3.5 py-2 text-[11px] font-black text-black shadow-md transition-transform active:scale-95"
        >
          <span>Sandbox</span>
          <ArrowRight size={12} />
        </Link>
      </div>
    </div>
  );
}
