'use client';
import { Hero } from '@/components/landing/Hero';
import { AdvantageSection } from '@/components/landing/AdvantageSection';
import { InfrastructureSection } from '@/components/landing/InfrastructureSection';
import { BrandLogo } from '@/components/ui/BrandLogo';
import Link from 'next/link';

export default function LandingPage() {
  return (
    <main className="flex-1 flex flex-col bg-white text-slate-900 selection:bg-slate-900 selection:text-white min-h-screen">
      {/* Apple Minimalist Glass Header */}
      <nav className="flex items-center justify-between py-4 px-6 lg:px-20 border-b border-black/[0.06] bg-white/90 backdrop-blur-xl sticky top-0 z-50">
        <BrandLogo href="/" size="md" />
        
        {/* Navigation Links */}
        <div className="hidden md:flex items-center gap-8 text-xs font-medium text-slate-600">
          <Link href="#advantage" className="hover:text-slate-950 transition-colors">
            Features
          </Link>
          <Link href="#advantage" className="hover:text-slate-950 transition-colors">
            How it works
          </Link>
          <Link href="#infrastructure" className="hover:text-slate-950 transition-colors">
            Pricing
          </Link>
          <Link href="#infrastructure" className="hover:text-slate-950 transition-colors">
            About
          </Link>
        </div>

        {/* Auth CTA Buttons */}
        <div className="flex items-center gap-4">
          <Link href="/auth/login" className="text-xs font-semibold text-slate-600 hover:text-slate-950 transition-colors">
            Sign in
          </Link>
          <Link href="/auth/signup">
            <button className="flex items-center gap-1.5 px-4 py-2 bg-slate-950 text-white hover:bg-slate-800 rounded-full text-xs font-semibold transition-all shadow-xs active:scale-[0.98] cursor-pointer">
              <span>Get Started Free</span>
              <span className="text-slate-400">→</span>
            </button>
          </Link>
        </div>
      </nav>

      {/* Hero Section with Dual Device Showcase */}
      <Hero />

      {/* The Advantage Section with Whale Visual & 4-Step Flow */}
      <AdvantageSection />

      {/* Infrastructure & Final Obsidian CTA Card */}
      <InfrastructureSection />

      {/* Clean Minimalist Footer */}
      <footer className="py-12 border-t border-black/[0.06] bg-white text-slate-500 text-xs">
        <div className="max-w-7xl mx-auto px-6 lg:px-20 flex flex-col sm:flex-row items-center justify-between gap-4">
          <BrandLogo size="sm" />
          <p>© {new Date().getFullYear()} Baleen. All rights reserved. Automated non-custodial copy-trading.</p>
        </div>
      </footer>
    </main>
  );
}
