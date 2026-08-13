import { Hero } from '@/components/landing/Hero';
import { LiveTicker } from '@/components/landing/LiveTicker';
import { FeaturesGrid } from '@/components/landing/FeaturesGrid';
import { Leaderboard } from '@/components/landing/Leaderboard';
import Image from 'next/image';
import Link from 'next/link';

export default function LandingPage() {
  return (
    <main className="flex-1 flex flex-col">
      <nav className="flex items-center justify-between p-6 lg:px-20 border-b border-white/5 bg-baleen-obsidian/80 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <Image src="/logo.png" alt="Baleen Logo" width={32} height={32} className="w-8 h-8 object-contain" />
          <span className="font-bold text-xl tracking-tight text-baleen-white">Baleen</span>
        </div>
        <div className="flex gap-4">
          <Link href="/auth/login" className="text-sm font-medium text-baleen-muted hover:text-baleen-white transition-colors flex items-center px-4">
            Sign In
          </Link>
          <Link href="/auth/signup" className="text-sm font-medium px-4 py-2 bg-white/10 hover:bg-white/20 text-baleen-white rounded-lg transition-colors border border-white/10">
            Get Started
          </Link>
        </div>
      </nav>

      <Hero />
      <LiveTicker />
      <FeaturesGrid />
      <Leaderboard />
      
      <footer className="py-12 text-center border-t border-white/5 text-baleen-muted text-sm">
        <p>© {new Date().getFullYear()} Baleen Protocol. All rights reserved.</p>
      </footer>
    </main>
  );
}
