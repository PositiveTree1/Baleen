'use client';
import { Hero } from '@/components/landing/Hero';
import { AdvantageSection } from '@/components/landing/AdvantageSection';
import { InfrastructureSection } from '@/components/landing/InfrastructureSection';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { useTheme } from '@/context/ThemeContext';
import { Sun, Moon } from 'lucide-react';
import Link from 'next/link';

export default function LandingPage() {
  const { theme, toggleTheme } = useTheme();

  return (
    <main className="flex-1 flex flex-col bg-[#F8F9FB] dark:bg-[#000000] text-slate-900 dark:text-white selection:bg-[#00D09C] selection:text-black min-h-screen transition-colors duration-150">
      {/* Minimalist Glass Navigation Header */}
      <nav className="flex items-center justify-between py-4 px-6 lg:px-20 border-b border-black/[0.06] dark:border-white/[0.08] bg-white/80 dark:bg-[#000000]/90 backdrop-blur-xl sticky top-0 z-50">
        <BrandLogo href="/" size="md" />
        
        {/* Navigation Links */}
        <div className="hidden md:flex items-center gap-8 text-xs font-semibold text-slate-600 dark:text-[#8E8F99]">
          <Link href="#advantage" className="hover:text-slate-950 dark:hover:text-white transition-colors">
            Features
          </Link>
          <Link href="#advantage" className="hover:text-slate-950 dark:hover:text-white transition-colors">
            How It Works
          </Link>
          <Link href="#infrastructure" className="hover:text-slate-950 dark:hover:text-white transition-colors">
            Architecture
          </Link>
        </div>

        {/* Right Action CTAs & Theme Switcher */}
        <div className="flex items-center gap-3 sm:gap-4">
          <button
            onClick={toggleTheme}
            className="w-9 h-9 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-white flex items-center justify-center transition-all cursor-pointer shadow-2xs"
            title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
          >
            {theme === 'light' ? <Moon size={15} /> : <Sun size={15} className="text-amber-400" />}
          </button>

          <Link href="/auth/login" className="text-xs font-bold text-slate-700 dark:text-white hover:text-slate-950 dark:hover:text-[#00D09C] transition-colors">
            Sign in
          </Link>
          <Link href="/auth/signup">
            <button className="flex items-center gap-1.5 px-4 py-2 bg-slate-950 dark:bg-white text-white dark:text-black hover:bg-slate-800 dark:hover:bg-slate-200 rounded-full text-xs font-bold transition-all shadow-xs active:scale-[0.98] cursor-pointer">
              <span>Get Started</span>
              <span className="text-slate-400 dark:text-slate-600">→</span>
            </button>
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <Hero />

      {/* Advantage Section */}
      <AdvantageSection />

      {/* Infrastructure Section */}
      <InfrastructureSection />

      {/* Clean Footer */}
      <footer className="py-12 border-t border-black/[0.06] dark:border-white/[0.08] bg-[#F8F9FB] dark:bg-[#0A0B0E] text-slate-500 dark:text-[#8E8F99] text-xs">
        <div className="max-w-7xl mx-auto px-6 lg:px-20 flex flex-col sm:flex-row items-center justify-between gap-4">
          <BrandLogo size="sm" />
          <p>© {new Date().getFullYear()} Baleen. All rights reserved. Automated non-custodial copy-trading.</p>
        </div>
      </footer>
    </main>
  );
}
