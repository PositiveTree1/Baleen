import { Hero } from '@/components/landing/Hero';
import { LiveTicker } from '@/components/landing/LiveTicker';
import { ProfitSimulator } from '@/components/landing/ProfitSimulator';
import { FeaturesGrid } from '@/components/landing/FeaturesGrid';
import { Leaderboard } from '@/components/landing/Leaderboard';
import { BrandLogo } from '@/components/ui/BrandLogo';
import Image from 'next/image';
import Link from 'next/link';

export default function LandingPage() {
  return (
    <main className="flex-1 flex flex-col bg-[#F8F9FB] text-slate-900 selection:bg-slate-900 selection:text-white min-h-screen">
      {/* Apple Frosted Glass Header */}
      <nav className="flex items-center justify-between py-4 px-6 lg:px-20 border-b border-black/[0.06] bg-white/80 backdrop-blur-2xl sticky top-0 z-50 shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
        <BrandLogo href="/" size="md" />
        <div className="flex items-center gap-3">
          <Link href="/auth/login" className="text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors px-3 py-1.5 rounded-xl hover:bg-black/5">
            Sign In
          </Link>
          <Link href="/auth/signup" className="text-xs font-semibold px-4 py-2 bg-slate-900 text-white hover:bg-slate-800 rounded-xl transition-all shadow-[0_1px_2px_rgba(0,0,0,0.1),0_2px_6px_rgba(0,0,0,0.06)] active:scale-[0.98]">
            Get Started Free
          </Link>
        </div>
      </nav>

      <Hero />
      <LiveTicker />
      <ProfitSimulator />
      <Leaderboard />
      <FeaturesGrid />
      
      <footer className="py-16 text-center border-t border-black/[0.06] bg-white text-slate-500 text-xs">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <BrandLogo size="sm" subtitle="HyperSync Engine" />
          <p>© {new Date().getFullYear()} Baleen Protocol. All rights reserved. Automated non-custodial copy engine.</p>
        </div>
      </footer>
    </main>
  );
}
