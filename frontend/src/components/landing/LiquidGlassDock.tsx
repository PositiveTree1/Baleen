'use client';

import { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Sparkles, Activity, Layers, ArrowRight, Moon, Sun } from 'lucide-react';
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
        className="glass-dock glass-chromatic-bezel pointer-events-auto mx-auto flex h-14 w-full max-w-[1240px] items-center justify-between rounded-full px-3 sm:h-16 sm:px-6 shadow-xl border border-white/95"
        aria-label="Primary navigation"
      >
        {/* Brand Logo */}
        <BrandLogo href="/" size="sm" className="baleen-hero-logo shrink-0 sm:hidden" />
        <BrandLogo href="/" size="md" className="baleen-hero-logo shrink-0 hidden sm:inline-flex" />

        {/* Desktop 3D Liquid Lens Navigation Dock (visionOS Convex Glass Capsule) */}
        <div className="hidden lg:flex items-center gap-1.5 relative rounded-full bg-sky-50/80 p-1.5 border border-sky-100/80 backdrop-blur-2xl shadow-inner">
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
                  color: isActive ? '#0F172A' : isHovered ? '#0F172A' : '#475569',
                }}
              >
                {/* 3D Liquid Lens Active Indicator (Convex Glass Bubble Protruding Vertically Beyond Capsule) */}
                {isActive && (
                  <motion.div
                    layoutId="desktop-liquid-lens-bubble"
                    transition={{
                      type: 'spring',
                      stiffness: 400,
                      damping: 28,
                      mass: 0.8,
                    }}
                    className="absolute -top-2.5 -bottom-2.5 -left-1.5 -right-1.5 rounded-[22px] z-[-1] pointer-events-none"
                    style={{
                      background:
                        'radial-gradient(120% 120% at 50% 10%, rgba(255, 255, 255, 0.98) 0%, rgba(224, 242, 254, 0.80) 55%, rgba(186, 230, 253, 0.50) 100%)',
                      borderTop: '2px solid rgba(255, 255, 255, 1)',
                      borderBottom: '1.5px solid rgba(2, 132, 199, 0.25)',
                      borderLeft: '1px solid rgba(255, 255, 255, 0.85)',
                      borderRight: '1px solid rgba(255, 255, 255, 0.85)',
                      boxShadow:
                        'inset 0 2.5px 2px 0 rgba(255, 255, 255, 1), inset 0 -1.5px 1.5px 0 rgba(2, 132, 199, 0.15), 0 8px 24px -4px rgba(2, 132, 199, 0.18)',
                      backdropFilter: 'blur(24px) saturate(210%)',
                      WebkitBackdropFilter: 'blur(24px) saturate(210%)',
                    }}
                  >
                    {/* Top Specular Crescent Arc Highlight */}
                    <div className="absolute top-1 inset-x-3 h-2 rounded-full bg-gradient-to-b from-white to-transparent pointer-events-none" />

                    {/* Inner Optical Lens Magnification Glow */}
                    <div className="absolute inset-0 rounded-[22px] bg-radial-[at_50%_50%] from-white/30 via-transparent to-transparent pointer-events-none" />

                    {/* Bottom Chromatic Refraction Arc */}
                    <div className="absolute bottom-1 inset-x-4 h-1 rounded-full bg-gradient-to-r from-sky-400/60 via-cyan-400/70 to-indigo-400/60 pointer-events-none blur-[0.5px]" />
                  </motion.div>
                )}

                <Icon
                  size={14}
                  className={`transition-all duration-200 ${
                    isActive ? 'scale-110 text-sky-600 drop-shadow-xs' : 'text-slate-500'
                  }`}
                />
                <span className={isActive ? 'font-black' : 'font-medium'}>{item.label}</span>
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
            className="grid size-8 sm:size-9 place-items-center rounded-full text-slate-700 transition-colors hover:bg-sky-50 hover:text-slate-950"
          >
            {theme === 'light' ? <Moon size={15} aria-hidden="true" /> : <Sun size={15} aria-hidden="true" />}
          </button>

          <Link
            href="/auth/login"
            className="hidden sm:block rounded-full px-3.5 py-1.5 text-xs font-mono font-bold text-slate-700 transition-colors hover:text-slate-950 hover:bg-sky-50"
          >
            Sign In
          </Link>

          <Link
            href="/dashboard"
            className="glass-button group inline-flex h-9 sm:h-11 items-center gap-1.5 sm:gap-2 px-3.5 sm:px-5 text-[11px] sm:text-xs font-mono font-black text-slate-900 shadow-md hover:scale-105 active:scale-95 transition-all border border-white/95"
          >
            <span className="hidden sm:inline">Launch Sandbox</span>
            <span className="sm:hidden">Launch</span>
            <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5 text-sky-600" aria-hidden="true" />
          </Link>
        </div>
      </nav>
    </header>
  );
}

export function LiquidGlassMobileDock() {
  const [activeTab, setActiveTab] = useState<string>('advantages');

  return (
    <div className="fixed bottom-[calc(1rem+env(safe-area-inset-bottom,0px))] inset-x-3 z-40 sm:hidden pointer-events-none">
      <div className="glass-dock glass-chromatic-bezel pointer-events-auto mx-auto flex w-full max-w-[360px] items-center justify-between gap-1 rounded-full p-1.5 shadow-xl border border-white/95">
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
                color: isActive ? '#0F172A' : '#475569',
              }}
            >
              {/* Mobile 3D Convex Liquid Lens Bubble Protruding Over Capsule */}
              {isActive && (
                <motion.div
                  layoutId="mobile-liquid-lens-bubble"
                  transition={{
                    type: 'spring',
                    stiffness: 400,
                    damping: 28,
                    mass: 0.8,
                  }}
                  className="absolute -top-1.5 -bottom-1.5 -left-1 -right-1 rounded-full z-[-1] pointer-events-none"
                  style={{
                    background:
                      'radial-gradient(110% 120% at 50% 10%, rgba(255, 255, 255, 0.98) 0%, rgba(224, 242, 254, 0.80) 55%, rgba(186, 230, 253, 0.50) 100%)',
                    borderTop: '2px solid rgba(255, 255, 255, 1)',
                    borderBottom: '1.5px solid rgba(2, 132, 199, 0.25)',
                    boxShadow:
                      'inset 0 2px 2px 0 rgba(255, 255, 255, 1), inset 0 -1.5px 1.5px 0 rgba(2, 132, 199, 0.15), 0 8px 20px rgba(2, 132, 199, 0.15)',
                    backdropFilter: 'blur(24px) saturate(210%)',
                    WebkitBackdropFilter: 'blur(24px) saturate(210%)',
                  }}
                >
                  <div className="absolute top-0.5 inset-x-2 h-1.5 rounded-full bg-gradient-to-b from-white to-transparent pointer-events-none" />
                  <div className="absolute bottom-0.5 inset-x-3 h-0.5 rounded-full bg-gradient-to-r from-sky-400/60 via-cyan-400/70 to-indigo-400/60 pointer-events-none" />
                </motion.div>
              )}

              <Icon
                size={13}
                className={`transition-all ${
                  isActive ? 'scale-110 text-sky-600 drop-shadow-xs' : 'text-slate-500'
                }`}
              />
              <span className="truncate">{item.mobileLabel}</span>
            </Link>
          );
        })}

        {/* Sandbox Launch Pill */}
        <Link
          href="/dashboard"
          className="flex items-center gap-1.5 rounded-full bg-gradient-to-r from-sky-600 to-cyan-600 px-3.5 py-2 text-[11px] font-mono font-black text-white shadow-md transition-transform active:scale-95 shrink-0 hover:from-sky-500 hover:to-cyan-500"
        >
          <span>Sandbox</span>
          <ArrowRight size={12} className="text-white" />
        </Link>
      </div>
    </div>
  );
}
