'use client';

import Link from 'next/link';
import { Hero } from '@/components/landing/Hero';
import { LiveTicker } from '@/components/landing/LiveTicker';
import { AdvantageSection } from '@/components/landing/AdvantageSection';
import { LiquidSleeveSimulator } from '@/components/landing/LiquidSleeveSimulator';
import { InfrastructureSection } from '@/components/landing/InfrastructureSection';
import { LiquidGlassHeader, LiquidGlassMobileDock } from '@/components/landing/LiquidGlassDock';
import { LiquidParallaxBackground } from '@/components/landing/LiquidParallaxBackground';
import { LiquidGlassFilter } from '@/components/landing/LiquidGlassFilter';
import { BrandLogo } from '@/components/ui/BrandLogo';

export default function LandingPage() {
  return (
    <main className="baleen-landing min-h-screen w-full overflow-x-hidden bg-[#020b18] text-white selection:bg-sky-500 selection:text-white relative">
      {/* 1. Global SVG Liquid Filters for Metaball Fusion and Caustics */}
      <LiquidGlassFilter />

      {/* 3. Floating 3D Liquid Glass Navigation Dock (visionOS / iOS 26) */}
      <LiquidGlassHeader />

      {/* 4. Hero Section with Interactive Liquid Glass Morphing Centerpiece */}
      <Hero />

      {/* 5. Live Polymarket Execution Marquee */}
      <LiveTicker />

      {/* 6. Architectural Advantage (4 Tactile Liquid Glass Cards) */}
      <AdvantageSection />

      {/* 7. Interactive Liquid Glass Sleeve Simulator & Capital Allocation Engine */}
      <LiquidSleeveSimulator />

      {/* 8. Deep Infrastructure & High-Impact Closing CTA Banner */}
      <InfrastructureSection />

      {/* 9. Mobile iOS 26 Liquid Glass Bottom Navigation Dock */}
      <LiquidGlassMobileDock />

      {/* 10. Oceanic Liquid Glass Footer with Mobile Safe Area Clearance */}
      <footer className="relative z-10 px-4 pb-36 pt-16 text-white sm:px-6 sm:pb-16 border-t border-white/10 bg-[#020b18]/60 backdrop-blur-2xl">
        <div className="glass-card mx-auto max-w-[1240px] overflow-hidden rounded-[2.5rem] p-6 sm:p-12 shadow-2xl">
          <div className="flex flex-col justify-between gap-8 md:flex-row md:items-end">
            <div>
              <BrandLogo size="lg" className="baleen-footer-logo" />
              <p className="mt-4 max-w-md text-sm leading-relaxed text-slate-300">
                Autonomous Polymarket whale conviction execution. Continuous Envio Hypersync indexing with dynamically isolated risk sleeves.
              </p>
            </div>

            <div className="flex flex-wrap gap-x-8 gap-y-3 text-xs sm:text-sm font-mono font-semibold text-slate-300">
              <Link href="#advantages" className="transition-colors hover:text-sky-400">
                Architecture
              </Link>
              <Link href="#simulator" className="transition-colors hover:text-sky-400">
                Sleeve Model
              </Link>
              <Link href="#infrastructure" className="transition-colors hover:text-sky-400">
                Telemetry
              </Link>
              <Link href="/dashboard" className="transition-colors text-sky-400 hover:text-sky-300">
                Launch Terminal →
              </Link>
              <Link href="/auth/login" className="transition-colors hover:text-sky-400">
                Sign In
              </Link>
            </div>
          </div>

          <div className="mt-10 flex flex-col gap-3 border-t border-white/10 pt-6 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between font-mono">
            <span>© {new Date().getFullYear()} Baleen Quant. All rights reserved.</span>
            <span>Non-custodial paper trading sandbox. Algorithmic prediction simulation only.</span>
          </div>
        </div>
      </footer>
    </main>
  );
}
