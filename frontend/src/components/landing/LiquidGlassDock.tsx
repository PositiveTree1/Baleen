'use client';

import { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Sparkles, Activity, Layers, ArrowRight, Moon, Sun, Volume2, VolumeX } from 'lucide-react';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { LiquidOrbButton } from '@/components/ui/LiquidOrbButton';
import { useTheme } from '@/context/ThemeContext';
import { soundFx } from '@/lib/sound';

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
  const [soundEnabled, setSoundEnabled] = useState<boolean>(() => (typeof window !== 'undefined' ? soundFx.isEnabled() : false));
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="fixed inset-x-0 top-0 z-50 px-3 pt-3 sm:px-6 sm:pt-5 pointer-events-none">
      <nav
        className="glass-dock glass-chromatic-bezel pointer-events-auto mx-auto flex h-14 w-full max-w-[1240px] items-center justify-between rounded-full px-3 sm:h-16 sm:px-6 shadow-xl border border-white/20"
        aria-label="Primary navigation"
      >
        {/* Brand Logo */}
        <BrandLogo href="/" size="sm" className="baleen-hero-logo shrink-0 sm:hidden" />
        <BrandLogo href="/" size="md" className="baleen-hero-logo shrink-0 hidden sm:inline-flex" />

        {/* Desktop 3D Liquid Lens Navigation Dock (visionOS Convex Glass Capsule) */}
        <div className="hidden lg:flex items-center gap-1.5 relative rounded-full bg-white/[0.06] p-1.5 border border-white/10 backdrop-blur-2xl shadow-inner">
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
                onClick={() => {
                  soundFx.playTap();
                  setActiveTab(item.id);
                }}
                className="relative z-10 flex items-center gap-2 px-5 py-2 text-xs font-mono font-bold transition-colors"
                style={{
                  color: isActive ? '#FFFFFF' : isHovered ? '#FFFFFF' : '#94A3B8',
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
                        'radial-gradient(120% 120% at 50% 10%, rgba(255, 255, 255, 0.32) 0%, rgba(90, 170, 255, 0.20) 55%, rgba(10, 45, 110, 0.45) 100%)',
                      borderTop: '2px solid rgba(255, 255, 255, 0.8)',
                      borderBottom: '1.5px solid rgba(2, 132, 199, 0.40)',
                      borderLeft: '1px solid rgba(255, 255, 255, 0.30)',
                      borderRight: '1px solid rgba(255, 255, 255, 0.30)',
                      boxShadow:
                        'inset 0 2.5px 2px 0 rgba(255, 255, 255, 0.70), inset 0 -1.5px 1.5px 0 rgba(0, 18, 55, 0.60), 0 8px 24px -4px rgba(0, 12, 38, 0.50)',
                      backdropFilter: 'blur(24px) saturate(210%)',
                      WebkitBackdropFilter: 'blur(24px) saturate(210%)',
                    }}
                  >
                    {/* Top Specular Crescent Arc Highlight */}
                    <div className="absolute top-1 inset-x-3 h-2 rounded-full bg-gradient-to-b from-white/80 to-transparent pointer-events-none" />

                    {/* Inner Optical Lens Magnification Glow */}
                    <div className="absolute inset-0 rounded-[22px] bg-radial-[at_50%_50%] from-white/20 via-transparent to-transparent pointer-events-none" />

                    {/* Bottom Chromatic Refraction Arc */}
                    <div className="absolute bottom-1 inset-x-4 h-1 rounded-full bg-gradient-to-r from-sky-400/60 via-cyan-400/70 to-indigo-400/60 pointer-events-none blur-[0.5px]" />
                  </motion.div>
                )}

                <Icon
                  size={14}
                  className={`transition-all duration-200 ${
                    isActive ? 'scale-110 text-sky-400 drop-shadow-xs' : 'text-slate-400'
                  }`}
                />
                <span className={isActive ? 'font-black' : 'font-medium'}>{item.label}</span>
              </Link>
            );
          })}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 sm:gap-2.5 shrink-0">
          {/* BentoMotion Sound FX Orb Button */}
          <LiquidOrbButton
            size="sm"
            onClick={() => {
              const state = soundFx.toggleSound();
              setSoundEnabled(state);
            }}
            aria-label={soundEnabled ? 'Mute sound effects' : 'Enable sound effects'}
            title={soundEnabled ? 'Mute sound' : 'Enable audio feedback'}
          >
            {soundEnabled ? (
              <Volume2 size={13} className="text-sky-400" aria-hidden="true" />
            ) : (
              <VolumeX size={13} className="text-slate-400" aria-hidden="true" />
            )}
          </LiquidOrbButton>

          {/* BentoMotion Theme Orb Button */}
          <LiquidOrbButton
            size="sm"
            onClick={toggleTheme}
            aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
            title={theme === 'light' ? 'Dark mode' : 'Light mode'}
          >
            {theme === 'light' ? (
              <Moon size={13} className="text-slate-300" aria-hidden="true" />
            ) : (
              <Sun size={13} className="text-amber-400" aria-hidden="true" />
            )}
          </LiquidOrbButton>

          <Link
            href="/auth/login"
            onClick={() => soundFx.playTap()}
            className="hidden sm:block rounded-full px-3.5 py-1.5 text-xs font-mono font-bold text-slate-300 transition-colors hover:text-white hover:bg-white/10"
          >
            Sign In
          </Link>

          <Link
            href="/dashboard"
            onClick={() => soundFx.playWhoosh()}
            className="glass-button group inline-flex h-9 sm:h-11 items-center gap-1.5 sm:gap-2 px-3.5 sm:px-5 text-[11px] sm:text-xs font-mono font-black text-white shadow-md hover:scale-105 active:scale-95 transition-all rounded-full"
          >
            <span className="hidden sm:inline">Launch Sandbox</span>
            <span className="sm:hidden">Launch</span>
            <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5 text-sky-400" aria-hidden="true" />
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
      <div className="glass-dock glass-chromatic-bezel pointer-events-auto mx-auto flex w-full max-w-[360px] items-center justify-between gap-1 rounded-full p-1.5 shadow-xl border border-white/20">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          const Icon = item.icon;

          return (
            <Link
              key={item.id}
              href={item.href}
              onClick={() => {
                soundFx.playTap();
                setActiveTab(item.id);
              }}
              className="relative z-10 flex flex-1 items-center justify-center gap-1.5 rounded-full py-2 px-2 text-[11px] font-mono font-bold transition-all text-center"
              style={{
                color: isActive ? '#FFFFFF' : '#94A3B8',
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
                      'radial-gradient(110% 120% at 50% 10%, rgba(255, 255, 255, 0.32) 0%, rgba(90, 170, 255, 0.20) 55%, rgba(10, 45, 110, 0.45) 100%)',
                    borderTop: '2px solid rgba(255, 255, 255, 0.8)',
                    borderBottom: '1.5px solid rgba(2, 132, 199, 0.40)',
                    boxShadow:
                      'inset 0 2px 2px 0 rgba(255, 255, 255, 0.70), inset 0 -1.5px 1.5px 0 rgba(0, 18, 55, 0.60), 0 8px 20px rgba(0, 12, 38, 0.45)',
                    backdropFilter: 'blur(24px) saturate(210%)',
                    WebkitBackdropFilter: 'blur(24px) saturate(210%)',
                  }}
                >
                  <div className="absolute top-0.5 inset-x-2 h-1.5 rounded-full bg-gradient-to-b from-white/80 to-transparent pointer-events-none" />
                  <div className="absolute bottom-0.5 inset-x-3 h-0.5 rounded-full bg-gradient-to-r from-sky-400/60 via-cyan-400/70 to-indigo-400/60 pointer-events-none" />
                </motion.div>
              )}

              <Icon
                size={13}
                className={`transition-all ${
                  isActive ? 'scale-110 text-sky-400 drop-shadow-xs' : 'text-slate-400'
                }`}
              />
              <span className="truncate">{item.mobileLabel}</span>
            </Link>
          );
        })}

        {/* Sandbox Launch Pill */}
        <Link
          href="/dashboard"
          onClick={() => soundFx.playWhoosh()}
          className="flex items-center gap-1.5 rounded-full bg-gradient-to-r from-sky-500 to-cyan-500 px-3.5 py-2 text-[11px] font-mono font-black text-white shadow-md transition-transform active:scale-95 shrink-0 hover:from-sky-400 hover:to-cyan-400"
        >
          <span>Sandbox</span>
          <ArrowRight size={12} className="text-white" />
        </Link>
      </div>
    </div>
  );
}
