'use client';

import Link from 'next/link';
import { ArrowRight, Moon, Sun } from 'lucide-react';
import { Hero } from '@/components/landing/Hero';
import { LiveTicker } from '@/components/landing/LiveTicker';
import { AdvantageSection } from '@/components/landing/AdvantageSection';
import { InfrastructureSection } from '@/components/landing/InfrastructureSection';
import { MobileGlassDock } from '@/components/landing/MobileGlassDock';
import { LiquidParallaxBackground } from '@/components/landing/LiquidParallaxBackground';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { useTheme } from '@/context/ThemeContext';

export default function LandingPage() {
  const { theme, toggleTheme } = useTheme();

  return (
    <main className="baleen-landing min-h-screen overflow-x-hidden bg-[#07080A] text-white selection:bg-[#00D09C] selection:text-black relative">
      {/* 1. Interactive Oceanic Abyss & Liquid Glass Parallax Background */}
      <LiquidParallaxBackground />

      {/* 2. Floating Liquid Glass Capsule Navigation (Matching WWDC25 Glass Dock) */}
      <header className="fixed inset-x-0 top-0 z-50 px-3 pt-3 sm:px-6 sm:pt-5 pointer-events-none">
        <nav
          className="liquid-dock liquid-chromatic-rim pointer-events-auto mx-auto flex h-14 max-w-[1240px] items-center justify-between rounded-full px-3.5 sm:h-16 sm:px-6 shadow-2xl"
          aria-label="Primary navigation"
        >
          {/* Brand Logo */}
          <BrandLogo href="/" size="md" className="baleen-hero-logo" />

          {/* Desktop Nav Items */}
          <div className="hidden items-center gap-1.5 rounded-full bg-white/[0.04] p-1 text-[13px] font-semibold text-white/80 backdrop-blur-md lg:flex border border-white/10">
            <Link
              href="#advantages"
              className="rounded-full px-4 py-1.5 transition-colors hover:bg-white/10 hover:text-white"
            >
              Architecture
            </Link>
            <Link
              href="#infrastructure"
              className="rounded-full px-4 py-1.5 transition-colors hover:bg-white/10 hover:text-white"
            >
              Telemetry
            </Link>
            <Link
              href="/dashboard"
              className="rounded-full px-4 py-1.5 transition-colors hover:bg-white/10 hover:text-white"
            >
              Dashboard
            </Link>
          </div>

          {/* Action Controls */}
          <div className="flex items-center gap-2 sm:gap-3">
            <button
              type="button"
              onClick={toggleTheme}
              aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
              className="grid size-9 place-items-center rounded-full text-white/80 transition-colors hover:bg-white/10 hover:text-white"
            >
              {theme === 'light' ? <Moon size={16} aria-hidden="true" /> : <Sun size={16} aria-hidden="true" />}
            </button>

            <Link
              href="/auth/login"
              className="hidden rounded-full px-3.5 py-1.5 text-[13px] font-bold text-white/80 transition-colors hover:text-white sm:block"
            >
              Sign In
            </Link>

            <Link
              href="/dashboard"
              className="liquid-pill-btn group inline-flex h-9 sm:h-10 items-center gap-2 px-4 sm:px-5 text-[12px] sm:text-[13px] font-extrabold text-white shadow-lg"
            >
              <span>Launch Sandbox</span>
              <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5 text-[#00D09C]" aria-hidden="true" />
            </Link>
          </div>
        </nav>
      </header>

      {/* 3. Hero Section (Centered Liquid Glass Focus) */}
      <Hero />

      {/* 4. Live Polymarket Order Execution Tape */}
      <LiveTicker />

      {/* 5. Architectural Advantage (Liquid Glass Cards) */}
      <AdvantageSection />

      {/* 6. Deep Infrastructure & High-Impact Closing CTA Banner */}
      <InfrastructureSection />

      {/* 7. Mobile Liquid Glass Bottom Navigation Dock */}
      <MobileGlassDock />

      {/* 8. Pristine Obsidian Footer */}
      <footer className="relative z-10 px-4 pb-20 pt-16 text-white sm:px-6 sm:pb-8 border-t border-white/10 bg-[#07080A]/90 backdrop-blur-2xl">
        <div className="mx-auto max-w-[1240px] overflow-hidden rounded-[2rem] border border-white/10 bg-[#0E1015]/80 p-6 sm:p-12 backdrop-blur-3xl">
          <div className="flex flex-col justify-between gap-8 md:flex-row md:items-end">
            <div>
              <BrandLogo size="lg" className="baleen-footer-logo" />
              <p className="mt-4 max-w-md text-sm leading-relaxed text-white/60">
                Quantitative Polymarket whale shadow execution. Filtering millions of trades to extract verified, non-bot alpha across isolated sleeves.
              </p>
            </div>

            <div className="flex flex-wrap gap-x-8 gap-y-3 text-sm font-semibold text-white/70">
              <Link href="#advantages" className="transition-colors hover:text-white">
                Architecture
              </Link>
              <Link href="#infrastructure" className="transition-colors hover:text-white">
                Telemetry
              </Link>
              <Link href="/dashboard" className="transition-colors hover:text-white">
                Dashboard
              </Link>
              <Link href="/auth/login" className="transition-colors hover:text-white">
                Sign In
              </Link>
              <Link href="/auth/signup" className="transition-colors hover:text-white">
                Create Account
              </Link>
            </div>
          </div>

          <div className="mt-10 flex flex-col gap-3 border-t border-white/10 pt-5 text-xs text-white/40 sm:flex-row sm:items-center sm:justify-between font-mono">
            <span>© {new Date().getFullYear()} Baleen Quant. All rights reserved.</span>
            <span>Non-custodial paper trading sandbox. Educational and algorithmic simulation only.</span>
          </div>
        </div>
      </footer>
    </main>
  );
}
