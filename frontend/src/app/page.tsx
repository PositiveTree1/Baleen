import { Hero } from '@/components/landing/Hero';
import { LiveTicker } from '@/components/landing/LiveTicker';
import { FeaturesGrid } from '@/components/landing/FeaturesGrid';
import { Leaderboard } from '@/components/landing/Leaderboard';
import Image from 'next/image';
import Link from 'next/link';

export default function LandingPage() {
  return (
    <main className="flex-1 flex flex-col bg-[#090A0F] text-white selection:bg-white selection:text-black">
      <nav className="flex items-center justify-between py-4 px-6 lg:px-20 border-b border-white/[0.06] bg-[#090A0F]/80 backdrop-blur-2xl sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <Image src="/logo.png" alt="Baleen Logo" width={28} height={28} className="w-7 h-7 object-contain" />
          <span className="font-semibold text-lg tracking-tight text-white">Baleen</span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/auth/login" className="text-xs font-medium text-zinc-400 hover:text-white transition-colors px-3 py-1.5 rounded-lg hover:bg-white/[0.05]">
            Sign In
          </Link>
          <Link href="/auth/signup" className="text-xs font-semibold px-4 py-2 bg-white text-zinc-950 hover:bg-zinc-200 rounded-xl transition-all shadow-sm">
            Get Started
          </Link>
        </div>
      </nav>

      <Hero />
      <LiveTicker />
      <FeaturesGrid />
      <Leaderboard />
      
      <footer className="py-16 text-center border-t border-white/[0.06] bg-black text-zinc-500 text-xs">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Image src="/logo.png" alt="Baleen" width={20} height={20} className="w-5 h-5 opacity-60" />
            <span className="font-medium text-zinc-400">Baleen Protocol</span>
          </div>
          <p>© {new Date().getFullYear()} Baleen Protocol. All rights reserved. Automated non-custodial copy engine.</p>
        </div>
      </footer>
    </main>
  );
}
