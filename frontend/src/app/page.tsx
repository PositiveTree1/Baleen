'use client';

import Link from 'next/link';
import { ArrowRight, Moon, Sun, Sparkles } from 'lucide-react';
import { Hero } from '@/components/landing/Hero';
import { LiveTicker } from '@/components/landing/LiveTicker';
import { AdvantageSection } from '@/components/landing/AdvantageSection';
import { ProfitSimulator } from '@/components/landing/ProfitSimulator';
import { Leaderboard } from '@/components/landing/Leaderboard';
import { InfrastructureSection } from '@/components/landing/InfrastructureSection';
import { MobileGlassDock } from '@/components/landing/MobileGlassDock';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { useTheme } from '@/context/ThemeContext';

export default function LandingPage() {
  const { theme, toggleTheme } = useTheme();

  return (
    <main className="baleen-landing min-h-screen overflow-x-hidden bg-[#040914] text-white">
      {/* Apple Liquid Glass Floating Header Navigation */}
      <header className="fixed inset-x-0 top-0 z-50 px-3 pt-3 sm:px-6 sm:pt-5 pointer-events-none">
        <nav
          className="baleen-nav pointer-events-auto mx-auto flex h-14 max-w-[1380px] items-center justify-between rounded-full px-3 sm:h-16 sm:px-6"
          aria-label="Primary navigation"
        >
          {/* Brand Logo */}
          <BrandLogo href="/" size="md" className="baleen-hero-logo" />

          {/* Desktop Nav Items */}
          <div className="hidden items-center gap-1 rounded-full bg-white/[0.06] p-1 text-[13px] font-semibold text-white/80 backdrop-blur-md lg:flex border border-white/10">
            <Link
              href="#advantages"
              className="rounded-full px-4 py-2 transition-colors hover:bg-white/15 hover:text-white"
            >
              System Edge
            </Link>
            <Link
              href="#simulator"
              className="rounded-full px-4 py-2 transition-colors hover:bg-white/15 hover:text-white"
            >
              Simulator
            </Link>
            <Link
              href="#leaderboard"
              className="rounded-full px-4 py-2 transition-colors hover:bg-white/15 hover:text-white"
            >
              Whale Basket
            </Link>
            <Link
              href="/dashboard"
              className="rounded-full px-4 py-2 transition-colors hover:bg-white/15 hover:text-white"
            >
              Dashboard
            </Link>
          </div>

          {/* Action CTAs */}
          <div className="flex items-center gap-2 sm:gap-3">
            <button
              type="button"
              onClick={toggleTheme}
              aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
              className="grid size-10 place-items-center rounded-full text-white/80 transition-colors hover:bg-white/10 hover:text-white"
            >
              {theme === 'light' ? <Moon size={17} aria-hidden="true" /> : <Sun size={17} aria-hidden="true" />}
            </button>

            <Link
              href="/auth/login"
              className="hidden rounded-full px-4 py-2 text-[13px] font-bold text-white transition-colors hover:bg-white/10 sm:block"
            >
              Sign In
            </Link>

            <Link
              href="/dashboard"
              className="group inline-flex h-10 items-center gap-2 rounded-full bg-white px-4 text-[13px] font-extrabold text-slate-950 shadow-[0_4px_20px_rgba(79,228,241,0.25)] transition-transform hover:scale-[1.02] active:scale-[0.98] sm:px-5"
            >
              <span>Sandbox</span>
              <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <Hero />

      {/* Live Trade Ticker */}
      <LiveTicker />

      {/* Architectural Advantage (4 Apple Glass Cards) */}
      <AdvantageSection />

      {/* Interactive Revolut Compounding Simulator */}
      <ProfitSimulator />

      {/* Whale Discovery Basket Leaderboard */}
      <Leaderboard />

      {/* Deep Infrastructure & High-Impact Closing CTA Banner */}
      <InfrastructureSection />

      {/* Mobile Liquid Glass Bottom Navigation Dock */}
      <MobileGlassDock />

      {/* Footer */}
      <footer className="bg-[#02050b] px-4 pb-20 pt-20 text-white sm:px-6 sm:pb-8">
        <div className="mx-auto max-w-[1380px] overflow-hidden rounded-[2rem] border border-white/10 bg-[#060c1b]/80 p-6 sm:p-12 backdrop-blur-2xl">
          <div className="flex flex-col justify-between gap-10 md:flex-row md:items-end">
            <div>
              <BrandLogo size="lg" className="baleen-footer-logo" />
              <p className="mt-4 max-w-md text-sm leading-relaxed text-white/60 sm:text-base">
                Quantitative Polymarket whale shadow execution. High-conviction alpha with strict isolated risk limits and sub-120ms latency.
              </p>
            </div>

            <div className="flex flex-wrap gap-x-8 gap-y-3 text-sm font-semibold text-white/70">
              <Link href="#advantages" className="transition-colors hover:text-white">
                System Edge
              </Link>
              <Link href="#simulator" className="transition-colors hover:text-white">
                Simulator
              </Link>
              <Link href="#leaderboard" className="transition-colors hover:text-white">
                Whales
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

