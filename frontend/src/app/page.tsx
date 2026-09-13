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
    <main className="baleen-landing min-h-screen w-full overflow-x-hidden bg-[#060709] text-white selection:bg-[#00D09C] selection:text-black relative">
      {/* 1. Global SVG Liquid Filters for Metaball Fusion and Caustics */}
      <LiquidGlassFilter />

      {/* 2. Interactive Studio Background with Volumetric Oceanic Caustics */}
      <LiquidParallaxBackground />

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

      {/* 10. Pristine Obsidian Studio Footer with Mobile Safe Area Clearance */}
      <footer className="relative z-10 px-4 pb-36 pt-16 text-white sm:px-6 sm:pb-16 border-t border-white/10 bg-[#060709]/90 backdrop-blur-2xl">
        <div className="mx-auto max-w-[1240px] overflow-hidden rounded-[2.5rem] border border-white/10 bg-[#0c0e14]/70 p-6 sm:p-12 backdrop-blur-3xl shadow-2xl">
          <div className="flex flex-col justify-between gap-8 md:flex-row md:items-end">
            <div>
              <BrandLogo size="lg" className="baleen-footer-logo" />
              <p className="mt-4 max-w-md text-sm leading-relaxed text-zinc-400">
                Autonomous Polymarket whale conviction execution. Continuous Envio Hypersync indexing with dynamically isolated risk sleeves.
              </p>
            </div>

            <div className="flex flex-wrap gap-x-8 gap-y-3 text-xs sm:text-sm font-mono font-semibold text-zinc-400">
              <Link href="#advantages" className="transition-colors hover:text-white">
                Architecture
              </Link>
              <Link href="#simulator" className="transition-colors hover:text-white">
                Sleeve Model
              </Link>
              <Link href="#infrastructure" className="transition-colors hover:text-white">
                Telemetry
              </Link>
              <Link href="/dashboard" className="transition-colors hover:text-white">
                Sandbox
              </Link>
              <Link href="/auth/login" className="transition-colors hover:text-white">
                Sign In
              </Link>
            </div>
          </div>

          <div className="mt-10 flex flex-col gap-3 border-t border-white/10 pt-6 text-xs text-zinc-500 sm:flex-row sm:items-center sm:justify-between font-mono">
            <span>© {new Date().getFullYear()} Baleen Quant. All rights reserved.</span>
            <span>Non-custodial paper trading sandbox. Algorithmic prediction simulation only.</span>
          </div>
        </div>
      </footer>
    </main>
  );
}
