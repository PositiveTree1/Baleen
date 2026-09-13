'use client';

import { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Sparkles, Activity, Layers, ArrowRight, Moon, Sun, Shield } from 'lucide-react';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { useTheme } from '@/context/ThemeContext';

interface NavItem {
  id: string;
  label: string;
  mobileLabel: string;
  href: string;
  icon: typeof Sparkles;
}

const navItems: NavItem[] = [
  { id: 'advantages', label: 'Architecture', mobileLabel: 'System', href: '#advantages', icon: Sparkles },
  { id: 'simulator', label: 'Sleeve Model', mobileLabel: 'Sleeves', href: '#simulator', icon: Layers },
  { id: 'telemetry', label: 'Telemetry', mobileLabel: 'Metrics', href: '#infrastructure', icon: Activity },
];

export function LiquidGlassHeader() {
  const [activeTab, setActiveTab] = useState<string>('advantages');
  const [hoveredTab, setHoveredTab] = useState<string | null>(null);
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="fixed inset-x-0 top-0 z-50 px-3 pt-3 sm:px-6 sm:pt-5 pointer-events-none">
      <nav
        className="liquid-dock liquid-chromatic-rim pointer-events-auto mx-auto flex h-14 w-full max-w-[1240px] items-center justify-between rounded-full px-3 sm:h-16 sm:px-6 shadow-2xl backdrop-blur-3xl border border-white/15 bg-[#08090d]/85"
        aria-label="Primary navigation"
      >
        {/* Brand Logo */}
        <BrandLogo href="/" size="sm" className="baleen-hero-logo shrink-0 sm:hidden" />
        <BrandLogo href="/" size="md" className="baleen-hero-logo shrink-0 hidden sm:inline-flex" />

        {/* Desktop 3D Liquid Lens Navigation Dock (Matching Reference 2 Convex Glass Bubble) */}
        <div className="hidden lg:flex items-center gap-1.5 relative rounded-full bg-black/60 p-1.5 border border-white/10 backdrop-blur-2xl">
          {navItems.map((item) => {
            const isHovered = hoveredTab === item.id;
            const isActive = activeTab === item.id;
            const Icon = item.icon;

            return (
              <Link
                key={item.id}
                href={item.href}
                onMouseEnter={() => setHoveredTab(item.id)}
                onMouseLeave={() => setHoveredTab(null)}
                onClick={() => setActiveTab(item.id)}
                className="relative z-10 flex items-center gap-2 px-5 py-2 text-xs font-mono font-bold transition-colors"
                style={{
                  color: isActive || isHovered ? '#FFFFFF' : 'rgba(255, 255, 255, 0.6)',
                }}
              >
                {/* 3D Liquid Lens Active Indicator (Convex Glass Bubble Protruding Vertically Beyond Capsule) */}
                {isActive && (
                  <motion.div
                    layoutId="desktop-liquid-lens-bubble"
                    transition={{
                      type: 'spring',
                      stiffness: 420,
                      damping: 30,
                      mass: 0.8,
                    }}
                    className="absolute -top-2.5 -bottom-2.5 -left-1.5 -right-1.5 rounded-[22px] z-[-1] pointer-events-none"
                    style={{
                      background:
                        'radial-gradient(120% 120% at 50% 10%, rgba(255, 255, 255, 0.32) 0%, rgba(255, 255, 255, 0.06) 55%, rgba(0, 0, 0, 0.6) 100%)',
                      borderTop: '2px solid rgba(255, 255, 255, 0.95)',
                      borderBottom: '1.5px solid rgba(0, 208, 156, 0.6)',
                      borderLeft: '1px solid rgba(255, 255, 255, 0.35)',
                      borderRight: '1px solid rgba(255, 255, 255, 0.35)',
                      boxShadow:
                        'inset 0 3px 3px 0 rgba(255, 255, 255, 0.95), inset 0 -3px 3px 0 rgba(0, 0, 0, 0.6), 0 16px 32px -6px rgba(0, 0, 0, 0.95)',
                      backdropFilter: 'blur(28px) saturate(220%)',
                    }}
                  >
                    {/* Top Specular Crescent Arc Highlight */}
                    <div className="absolute top-1 inset-x-3 h-2 rounded-full bg-gradient-to-b from-white/95 to-transparent pointer-events-none" />

                    {/* Inner Optical Lens Magnification Glow */}
                    <div className="absolute inset-0 rounded-[22px] bg-radial-[at_50%_50%] from-white/20 via-transparent to-transparent pointer-events-none" />

                    {/* Bottom Chromatic Refraction Arc */}
                    <div className="absolute bottom-1 inset-x-4 h-1 rounded-full bg-gradient-to-r from-cyan-400/60 via-white/80 to-purple-400/60 pointer-events-none blur-[0.5px]" />
                  </motion.div>
                )}

                <Icon
                  size={14}
                  className={`transition-all duration-200 ${
                    isActive ? 'scale-110 text-[#00D09C] drop-shadow-[0_0_8px_#00D09C]' : 'text-zinc-400'
                  }`}
                />
                <span className={isActive ? 'font-black drop-shadow-md' : 'font-medium'}>{item.label}</span>
              </Link>
            );
          })}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
            className="grid size-8 sm:size-9 place-items-center rounded-full text-white/80 transition-colors hover:bg-white/10 hover:text-white"
          >
            {theme === 'light' ? <Moon size={15} aria-hidden="true" /> : <Sun size={15} aria-hidden="true" />}
          </button>

          <Link
            href="/auth/login"
            className="hidden sm:block rounded-full px-3.5 py-1.5 text-xs font-mono font-bold text-white/80 transition-colors hover:text-white hover:bg-white/10"
          >
            Sign In
          </Link>

          <Link
            href="/dashboard"
            className="liquid-pill-btn group inline-flex h-9 sm:h-11 items-center gap-1.5 sm:gap-2 px-3.5 sm:px-5 text-[11px] sm:text-xs font-mono font-black text-white shadow-xl hover:scale-105 active:scale-95 transition-all border border-white/25 bg-radial-[at_50%_0%] from-white/25 via-white/10 to-black/40"
          >
            <span className="hidden sm:inline">Launch Sandbox</span>
            <span className="sm:hidden">Launch</span>
            <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5 text-[#00D09C]" aria-hidden="true" />
          </Link>
        </div>
      </nav>
    </header>
  );
}

export function LiquidGlassMobileDock() {
  const [activeTab, setActiveTab] = useState<string>('advantages');

  return (
    <div className="fixed bottom-4 inset-x-3 z-40 sm:hidden pointer-events-none">
      <div className="pointer-events-auto mx-auto flex w-full max-w-[360px] items-center justify-between gap-1 rounded-full p-1.5 border border-white/20 bg-[#090B0F]/90 shadow-2xl backdrop-blur-3xl">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          const Icon = item.icon;

          return (
            <Link
              key={item.id}
              href={item.href}
              onClick={() => setActiveTab(item.id)}
              className="relative z-10 flex flex-1 items-center justify-center gap-1.5 rounded-full py-2 px-2 text-[11px] font-mono font-bold transition-all text-center"
              style={{
                color: isActive ? '#FFFFFF' : 'rgba(255, 255, 255, 0.6)',
              }}
            >
              {/* Mobile 3D Convex Liquid Lens Bubble Protruding Over Capsule */}
              {isActive && (
                <motion.div
                  layoutId="mobile-liquid-lens-bubble"
                  transition={{
                    type: 'spring',
                    stiffness: 450,
                    damping: 32,
                  }}
                  className="absolute -top-1.5 -bottom-1.5 -left-1 -right-1 rounded-full z-[-1] pointer-events-none"
                  style={{
                    background:
                      'radial-gradient(110% 120% at 50% 10%, rgba(255, 255, 255, 0.35) 0%, rgba(255, 255, 255, 0.08) 55%, rgba(0, 0, 0, 0.6) 100%)',
                    borderTop: '2px solid rgba(255, 255, 255, 0.95)',
                    borderBottom: '1.5px solid rgba(0, 208, 156, 0.6)',
                    boxShadow:
                      'inset 0 2px 2px 0 rgba(255, 255, 255, 0.9), inset 0 -2px 2px 0 rgba(0, 0, 0, 0.6), 0 10px 24px rgba(0, 0, 0, 0.85)',
                    backdropFilter: 'blur(24px) saturate(220%)',
                  }}
                >
                  <div className="absolute top-0.5 inset-x-2 h-1.5 rounded-full bg-gradient-to-b from-white/95 to-transparent pointer-events-none" />
                  <div className="absolute bottom-0.5 inset-x-3 h-0.5 rounded-full bg-gradient-to-r from-cyan-400/60 via-white/80 to-purple-400/60 pointer-events-none" />
                </motion.div>
              )}

              <Icon
                size={13}
                className={`transition-all ${
                  isActive ? 'scale-110 text-[#00D09C] drop-shadow-[0_0_6px_#00D09C]' : 'text-zinc-400'
                }`}
              />
              <span className="truncate">{item.mobileLabel}</span>
            </Link>
          );
        })}

        {/* Sandbox Launch Pill */}
        <Link
          href="/dashboard"
          className="flex items-center gap-1.5 rounded-full bg-white px-3.5 py-2 text-[11px] font-mono font-black text-black shadow-lg transition-transform active:scale-95 shrink-0 hover:bg-zinc-100"
        >
          <span>Sandbox</span>
          <ArrowRight size={12} className="text-[#00D09C]" />
        </Link>
      </div>
    </div>
  );
}
