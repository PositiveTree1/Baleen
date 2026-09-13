'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, useMotionValue, useSpring } from 'framer-motion';
import { Sparkles, Sliders, Layers, Shield, Zap } from 'lucide-react';

type MorphMode = 'wwdc-fused' | 'interactive' | 'sleeves';

export function LiquidGlassHeroCanvas() {
  const [mode, setMode] = useState<MorphMode>('wwdc-fused');
  const [tick, setTick] = useState(0);
  const [mouseTilt, setMouseTilt] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  // Drag physics for interactive fluid mode
  const dragX = useMotionValue(0);
  const dragY = useMotionValue(0);
  const springX = useSpring(dragX, { stiffness: 300, damping: 24 });
  const springY = useSpring(dragY, { stiffness: 300, damping: 24 });

  // Floating breathing loop
  useEffect(() => {
    let animId: number;
    const start = performance.now();
    const loop = (now: number) => {
      setTick((now - start) * 0.001);
      animId = requestAnimationFrame(loop);
    };
    animId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animId);
  }, []);

  // Parallax tilt tracking
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    const y = ((e.clientY - rect.top) / rect.height) * 2 - 1;
    setMouseTilt({ x, y });
  };

  const handleMouseLeave = () => {
    setMouseTilt({ x: 0, y: 0 });
  };

  // Autonomous breathing
  const floatY = Math.sin(tick * 1.6) * 6;
  const pulseScale = 1 + Math.sin(tick * 2.2) * 0.015;

  // Interactive dynamic coordinates
  const currentDragX = mode === 'interactive' ? springX.get() : Math.sin(tick * 1.2) * 12;
  const currentDragY = mode === 'interactive' ? springY.get() : Math.cos(tick * 1.5) * 5;

  const c1x = 195 + currentDragX;
  const c1y = 140 + currentDragY;
  const r1 = 64;

  const c2x = 385;
  const c2y = 140;
  const r2 = 78;

  const dx = c2x - c1x;
  const dy = c2y - c1y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const isBonded = dist < 280;

  // Fluid meniscus waist control points
  const midX = (c1x + c2x) / 2;
  const midY = (c1y + c2y) / 2;
  const waistThickness = Math.max(8, 54 - (dist - 190) * 0.38);

  const topC1X = c1x;
  const topC1Y = c1y - r1 + 3;
  const topC2X = c2x - 30;
  const topC2Y = c2y - r2 + 3;
  const topMidY = midY - waistThickness;

  const botC1X = c1x;
  const botC1Y = c1y + r1 - 3;
  const botC2X = c2x - 30;
  const botC2Y = c2y + r2 - 3;
  const botMidY = midY + waistThickness;

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="relative w-full max-w-4xl mx-auto mt-6 sm:mt-10 select-none px-2 sm:px-0 overflow-hidden"
    >
      {/* Mode Capsule Switcher */}
      <div className="flex items-center justify-center mb-5 sm:mb-6 px-2">
        <div className="liquid-dock liquid-chromatic-rim p-1 sm:p-1.5 rounded-full grid grid-cols-3 w-full max-w-[340px] sm:max-w-md shadow-2xl backdrop-blur-3xl border border-white/15 bg-black/50">
          <button
            type="button"
            onClick={() => {
              setMode('wwdc-fused');
              dragX.set(0);
              dragY.set(0);
            }}
            className={`flex items-center justify-center gap-1.5 py-1.5 sm:py-2 px-2 rounded-full text-[10px] sm:text-xs font-mono font-bold transition-all text-center ${
              mode === 'wwdc-fused'
                ? 'bg-white text-black shadow-lg scale-[1.02]'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            <Sparkles size={12} className={mode === 'wwdc-fused' ? 'text-black' : 'text-[#00D09C]'} />
            <span className="sm:hidden">Dumbbell</span>
            <span className="hidden sm:inline">WWDC25 Glass</span>
          </button>

          <button
            type="button"
            onClick={() => setMode('interactive')}
            className={`flex items-center justify-center gap-1.5 py-1.5 sm:py-2 px-2 rounded-full text-[10px] sm:text-xs font-mono font-bold transition-all text-center ${
              mode === 'interactive'
                ? 'bg-white text-black shadow-lg scale-[1.02]'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            <Sliders size={12} className={mode === 'interactive' ? 'text-black' : 'text-cyan-400'} />
            <span className="sm:hidden">Fluid Drag</span>
            <span className="hidden sm:inline">Fluid Drag</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setMode('sleeves');
              dragX.set(0);
              dragY.set(0);
            }}
            className={`flex items-center justify-center gap-1.5 py-1.5 sm:py-2 px-2 rounded-full text-[10px] sm:text-xs font-mono font-bold transition-all text-center ${
              mode === 'sleeves'
                ? 'bg-white text-black shadow-lg scale-[1.02]'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            <Layers size={12} className={mode === 'sleeves' ? 'text-black' : 'text-purple-400'} />
            <span className="sm:hidden">5 Sleeves</span>
            <span className="hidden sm:inline">5 Sleeves</span>
          </button>
        </div>
      </div>

      {/* Main Glass Stage */}
      <div className="relative min-h-[360px] sm:min-h-[440px] w-full rounded-[32px] sm:rounded-[36px] border border-white/15 bg-gradient-to-b from-[#0c0e14]/90 via-[#07080b]/95 to-[#040507] backdrop-blur-3xl overflow-hidden shadow-2xl p-4 sm:p-8 flex flex-col justify-between">
        {/* Clean Studio Perspective Grid (Matching Reference 4) */}
        <div
          className="absolute inset-0 pointer-events-none opacity-25"
          style={{
            backgroundImage: `linear-gradient(to right, rgba(255, 255, 255, 0.09) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.09) 1px, transparent 1px)`,
            backgroundSize: '56px 56px',
            transform: `translate3d(${mouseTilt.x * -6}px, ${mouseTilt.y * -6}px, 0)`,
            transition: 'transform 0.4s ease-out',
          }}
        />

        {/* Volumetric Oceanic Illumination */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div
            className="absolute top-1/4 left-1/4 w-88 h-88 rounded-full bg-[#00D09C]/15 blur-[110px] transition-transform duration-700 ease-out"
            style={{
              transform: `translate3d(${mouseTilt.x * 20}px, ${mouseTilt.y * 15}px, 0)`,
            }}
          />
          <div
            className="absolute bottom-1/4 right-1/4 w-88 h-88 rounded-full bg-cyan-500/15 blur-[110px] transition-transform duration-700 ease-out"
            style={{
              transform: `translate3d(${mouseTilt.x * -20}px, ${mouseTilt.y * -15}px, 0)`,
            }}
          />
        </div>

        {/* Underlying Polymarket Alpha Conviction Track */}
        <div className="absolute top-1/2 -translate-y-1/2 inset-x-2 sm:inset-x-12 pointer-events-none z-0 overflow-hidden">
          <div className="h-8 sm:h-12 w-full rounded-full bg-gradient-to-r from-cyan-500/20 via-[#00D09C]/30 to-purple-500/20 blur-[1px] border border-white/10 flex items-center justify-between px-3 sm:px-8 text-[9px] sm:text-xs font-mono text-zinc-300">
            <span className="flex items-center gap-1.5 shrink-0">
              <span className="size-1.5 sm:size-2 rounded-full bg-[#00D09C] animate-ping" />
              <span className="font-bold text-white text-[9px] sm:text-xs">CTF #68,291</span>
            </span>
            <span className="text-[#00D09C] font-bold hidden md:inline tracking-wider">91.4% WHALE CONVICTION</span>
            <span className="shrink-0 text-[9px] sm:text-xs font-semibold text-cyan-300">Sub-120ms Envio</span>
          </div>
        </div>

        {/* Fluid Glass Center Stage */}
        <div className="relative z-10 flex-1 flex items-center justify-center my-2 sm:my-3 w-full max-w-full overflow-hidden">
          {/* MODE 1: PURE VECTOR WWDC25 LIQUID GLASS DUMBBELL (Zero Watermark, 100% Procedural) */}
          {mode === 'wwdc-fused' && (
            <motion.div
              style={{
                y: floatY,
                scale: pulseScale,
                rotateX: mouseTilt.y * -8,
                rotateY: mouseTilt.x * 8,
              }}
              className="relative w-full max-w-[560px] h-[200px] sm:h-[260px] flex items-center justify-center cursor-pointer transition-transform duration-200"
              onClick={() => setMode('interactive')}
            >
              <svg
                viewBox="0 0 600 280"
                className="w-full h-full overflow-visible pointer-events-auto filter drop-shadow-[0_24px_45px_rgba(0,0,0,0.85)]"
              >
                <defs>
                  {/* Optical Glass Body Linear Gradient */}
                  <linearGradient id="wwdc-glass-body" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="rgba(255, 255, 255, 0.26)" />
                    <stop offset="35%" stopColor="rgba(255, 255, 255, 0.05)" />
                    <stop offset="70%" stopColor="rgba(255, 255, 255, 0.02)" />
                    <stop offset="100%" stopColor="rgba(255, 255, 255, 0.16)" />
                  </linearGradient>

                  {/* Top Specular Crescent Gradient */}
                  <linearGradient id="wwdc-top-specular" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="rgba(255, 255, 255, 0)" />
                    <stop offset="15%" stopColor="rgba(255, 255, 255, 0.95)" />
                    <stop offset="42%" stopColor="rgba(255, 255, 255, 0.75)" />
                    <stop offset="52%" stopColor="rgba(255, 255, 255, 0.3)" />
                    <stop offset="68%" stopColor="rgba(255, 255, 255, 0.95)" />
                    <stop offset="90%" stopColor="rgba(255, 255, 255, 0.85)" />
                    <stop offset="100%" stopColor="rgba(255, 255, 255, 0)" />
                  </linearGradient>

                  {/* Chromatic Rainbow Edge Refraction (Red to Violet Prismatic Dispersion) */}
                  <linearGradient id="wwdc-chromatic-edge" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="rgba(255, 69, 58, 0.85)" />
                    <stop offset="22%" stopColor="rgba(255, 159, 10, 0.9)" />
                    <stop offset="45%" stopColor="rgba(48, 209, 88, 0.9)" />
                    <stop offset="65%" stopColor="rgba(0, 208, 156, 0.95)" />
                    <stop offset="82%" stopColor="rgba(56, 189, 248, 0.9)" />
                    <stop offset="100%" stopColor="rgba(192, 132, 252, 0.85)" />
                  </linearGradient>

                  {/* Radial Inner Volume Glint */}
                  <radialGradient id="wwdc-inner-glint" cx="30%" cy="30%" r="70%">
                    <stop offset="0%" stopColor="rgba(255, 255, 255, 0.35)" />
                    <stop offset="45%" stopColor="rgba(255, 255, 255, 0.04)" />
                    <stop offset="100%" stopColor="rgba(0, 0, 0, 0.35)" />
                  </radialGradient>
                </defs>

                {/* 1. Ambient Glass Drop Shadow */}
                <path
                  d="M 195 72 C 235 72, 255 116, 285 116 C 315 116, 330 56, 365 56 L 415 56 A 84 84 0 0 1 415 224 L 365 224 C 330 224, 315 164, 285 164 C 255 164, 235 208, 195 208 A 68 68 0 0 1 195 72 Z"
                  fill="rgba(0, 0, 0, 0.6)"
                  transform="translate(0, 16)"
                  filter="blur(16px)"
                />

                {/* 2. Glass Body Mesh (Translucent Optical Volume) */}
                <path
                  d="M 195 64 C 235 64, 255 108, 285 108 C 315 108, 330 48, 365 48 L 415 48 A 84 84 0 0 1 415 216 L 365 216 C 330 216, 315 156, 285 156 C 255 156, 235 200, 195 200 A 68 68 0 0 1 195 64 Z"
                  fill="url(#wwdc-glass-body)"
                  stroke="rgba(255, 255, 255, 0.35)"
                  strokeWidth="1.5"
                />

                {/* 3. Inner Refraction Surface Fill */}
                <path
                  d="M 195 64 C 235 64, 255 108, 285 108 C 315 108, 330 48, 365 48 L 415 48 A 84 84 0 0 1 415 216 L 365 216 C 330 216, 315 156, 285 156 C 255 156, 235 200, 195 200 A 68 68 0 0 1 195 64 Z"
                  fill="url(#wwdc-inner-glint)"
                  opacity="0.85"
                />

                {/* 4. Left Lobe Bevel Refraction Ring */}
                <ellipse
                  cx="195"
                  cy="132"
                  rx="54"
                  ry="54"
                  fill="none"
                  stroke="rgba(255, 255, 255, 0.15)"
                  strokeWidth="1.2"
                />

                {/* 5. Right Capsule Bevel Refraction Ring */}
                <rect
                  x="335"
                  y="62"
                  width="135"
                  height="140"
                  rx="70"
                  fill="none"
                  stroke="rgba(255, 255, 255, 0.15)"
                  strokeWidth="1.2"
                />

                {/* 6. Top Specular Crescent Arc Highlight (Crisp White Reflection) */}
                <path
                  d="M 142 108 C 160 76, 180 65, 195 65 C 235 65, 255 109, 285 109 C 315 109, 330 49, 365 49 L 415 49 C 465 49, 492 84, 496 126"
                  fill="none"
                  stroke="url(#wwdc-top-specular)"
                  strokeWidth="3"
                  strokeLinecap="round"
                />

                {/* 7. Bottom Chromatic Dispersion Rainbow Fringe */}
                <path
                  d="M 152 158 C 170 192, 182 201, 195 201 C 235 201, 255 157, 285 157 C 315 157, 330 217, 365 217 L 415 217 C 465 217, 492 180, 496 142"
                  fill="none"
                  stroke="url(#wwdc-chromatic-edge)"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />

                {/* 8. Inner Specular Glints */}
                <path
                  d="M 160 98 A 45 45 0 0 1 215 78"
                  fill="none"
                  stroke="rgba(255, 255, 255, 0.85)"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
                <path
                  d="M 360 62 L 420 62 A 55 55 0 0 1 465 102"
                  fill="none"
                  stroke="rgba(255, 255, 255, 0.85)"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>

              {/* Overlaid Live Quantitative Telemetry Floating Inside Glass */}
              <div className="absolute inset-0 flex items-center justify-between px-6 sm:px-16 pointer-events-none">
                {/* Left Lobe Telemetry: Whale Conviction */}
                <div className="flex flex-col items-center justify-center w-[110px] sm:w-[150px] text-center">
                  <div className="size-2 sm:size-2.5 rounded-full bg-[#00D09C] shadow-[0_0_12px_#00D09C] animate-pulse" />
                  <div className="text-[9px] sm:text-xs font-mono font-black text-white mt-1 uppercase tracking-wider drop-shadow-md">
                    WHALE #0x12a9
                  </div>
                  <div className="text-[8px] sm:text-[10px] font-mono font-bold text-[#00D09C] drop-shadow-md mt-0.5">
                    91.4% Alpha
                  </div>
                </div>

                {/* Right Lobe Telemetry: Isolated Risk Sleeve */}
                <div className="flex flex-col items-end justify-center w-[140px] sm:w-[200px] pr-1 sm:pr-8 text-right font-mono">
                  <div className="text-[7px] sm:text-[10px] font-bold text-zinc-300 uppercase tracking-widest drop-shadow-md">
                    ISOLATED SLEEVE
                  </div>
                  <div className="text-xs sm:text-xl font-black text-white drop-shadow-md tabular-nums">
                    $2,000.00
                  </div>
                  <div className="text-[7px] sm:text-[10px] font-bold text-cyan-300 mt-0.5 flex items-center gap-1">
                    <Zap size={9} />
                    <span>Sub-120ms Envio</span>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* MODE 2: INTERACTIVE FLUID DRAG & MENISCUS SURFACE TENSION */}
          {mode === 'interactive' && (
            <div className="relative w-full max-w-[560px] h-[200px] sm:h-[260px] flex items-center justify-between px-2 sm:px-8 overflow-hidden">
              {/* Dynamic SVG Liquid Meniscus Bridge */}
              <svg
                viewBox="0 0 600 280"
                className="absolute inset-0 w-full h-full pointer-events-none overflow-visible filter drop-shadow-[0_20px_40px_rgba(0,0,0,0.8)]"
              >
                <defs>
                  <linearGradient id="fluid-glass-surface" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="rgba(255, 255, 255, 0.32)" />
                    <stop offset="40%" stopColor="rgba(255, 255, 255, 0.08)" />
                    <stop offset="100%" stopColor="rgba(255, 255, 255, 0.22)" />
                  </linearGradient>

                  <linearGradient id="fluid-bridge-chromatic" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#FF453A" stopOpacity="0.85" />
                    <stop offset="35%" stopColor="#38BDF8" stopOpacity="0.9" />
                    <stop offset="70%" stopColor="#00D09C" stopOpacity="0.9" />
                    <stop offset="100%" stopColor="#C084FC" stopOpacity="0.85" />
                  </linearGradient>
                </defs>

                {/* Dynamic Meniscus Waist Bridge */}
                {isBonded && (
                  <g>
                    <path
                      d={`M ${topC1X} ${topC1Y} Q ${midX} ${topMidY} ${topC2X} ${topC2Y} L ${botC2X} ${botC2Y} Q ${midX} ${botMidY} ${botC1X} ${botC1Y} Z`}
                      fill="url(#fluid-glass-surface)"
                      stroke="rgba(255, 255, 255, 0.4)"
                      strokeWidth="1.2"
                    />
                    <path
                      d={`M ${topC1X} ${topC1Y} Q ${midX} ${topMidY} ${topC2X} ${topC2Y}`}
                      fill="none"
                      stroke="rgba(255, 255, 255, 0.95)"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                    />
                    <path
                      d={`M ${botC1X} ${botC1Y} Q ${midX} ${botMidY} ${botC2X} ${botC2Y}`}
                      fill="none"
                      stroke="url(#fluid-bridge-chromatic)"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                    />
                  </g>
                )}
              </svg>

              {/* Draggable Fluid Glass Droplet 1 */}
              <motion.div
                drag
                dragConstraints={{ left: -50, right: 80, top: -40, bottom: 40 }}
                dragElastic={0.25}
                onDrag={(_, info) => {
                  dragX.set(info.offset.x);
                  dragY.set(info.offset.y);
                }}
                onDragEnd={() => {
                  dragX.set(0);
                  dragY.set(0);
                }}
                className="relative size-24 sm:size-32 rounded-full cursor-grab active:cursor-grabbing flex flex-col items-center justify-center p-2 sm:p-3 shadow-2xl z-20 shrink-0"
                style={{
                  x: springX,
                  y: springY,
                  background:
                    'radial-gradient(120% 120% at 35% 25%, rgba(255,255,255,0.38) 0%, rgba(255,255,255,0.08) 55%, rgba(0,0,0,0.45) 100%)',
                  border: '1.5px solid rgba(255, 255, 255, 0.45)',
                  backdropFilter: 'blur(32px) saturate(220%)',
                  boxShadow:
                    'inset 0 3px 3px 0 rgba(255,255,255,0.95), inset 0 -3px 3px 0 rgba(0,0,0,0.6), 0 20px 45px -10px rgba(0,0,0,0.85)',
                }}
              >
                <div className="absolute top-2 inset-x-3 h-4 rounded-full bg-gradient-to-b from-white/95 to-transparent pointer-events-none" />

                <span className="size-2 rounded-full bg-[#00D09C] animate-ping" />
                <span className="font-mono text-[9px] sm:text-xs font-black text-white mt-1 tracking-wider">
                  DRAG ME
                </span>
                <span className="text-[7px] sm:text-[9px] font-mono text-[#00D09C] font-bold">
                  {isBonded ? 'BONDED' : 'PINCHED'}
                </span>

                <div className="absolute bottom-1.5 inset-x-4 h-1 rounded-full bg-gradient-to-r from-red-400/60 via-cyan-400/70 to-purple-400/60 blur-[0.5px] pointer-events-none" />
              </motion.div>

              {/* Base Liquid Glass Sleeve Capsule 2 */}
              <div
                className="relative h-28 sm:h-36 w-44 sm:w-64 rounded-[32px] sm:rounded-[40px] flex items-center justify-between px-4 sm:px-7 shadow-2xl z-10 shrink-0"
                style={{
                  background:
                    'radial-gradient(130% 120% at 50% 20%, rgba(255,255,255,0.32) 0%, rgba(255,255,255,0.06) 60%, rgba(0,0,0,0.45) 100%)',
                  border: '1.5px solid rgba(255, 255, 255, 0.42)',
                  backdropFilter: 'blur(32px) saturate(220%)',
                  boxShadow:
                    'inset 0 3px 3px 0 rgba(255,255,255,0.9), inset 0 -3px 3px 0 rgba(0,0,0,0.6), 0 24px 55px -10px rgba(0,0,0,0.85)',
                }}
              >
                <div className="absolute top-2 inset-x-4 h-4 rounded-full bg-gradient-to-b from-white/95 to-transparent pointer-events-none" />

                <div className="font-mono">
                  <div className="text-[8px] sm:text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                    ISOLATED SLEEVE
                  </div>
                  <div className="text-sm sm:text-xl font-black text-white tabular-nums">$2,000.00</div>
                  <div className="text-[8px] sm:text-[9px] font-semibold text-[#00D09C]">Guard: Safe</div>
                </div>

                <div className="flex flex-col items-end gap-1 font-mono">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[9px] sm:text-[10px] font-bold border transition-colors ${
                      isBonded
                        ? 'border-[#00D09C]/50 bg-[#00D09C]/20 text-[#00D09C]'
                        : 'border-cyan-400/50 bg-cyan-400/20 text-cyan-300'
                    }`}
                  >
                    {isBonded ? 'Fused' : 'Isolated'}
                  </span>
                  <span className="text-[7px] sm:text-[8px] text-zinc-400">91.4% Win</span>
                </div>

                <div className="absolute bottom-1.5 inset-x-5 h-1 rounded-full bg-gradient-to-r from-cyan-400/60 via-[#00D09C]/70 to-purple-400/60 blur-[0.5px] pointer-events-none" />
              </div>
            </div>
          )}

          {/* MODE 3: 5 ISOLATED RISK SLEEVE DROPLETS */}
          {mode === 'sleeves' && (
            <div className="grid grid-cols-5 gap-1.5 sm:gap-4 w-full max-w-2xl px-1">
              {[
                { label: 'Sleeve A', whale: '0x12a9', cap: '$2,000', win: '94.2%', color: '#00D09C' },
                { label: 'Sleeve B', whale: '0x7bf3', cap: '$2,000', win: '89.6%', color: '#38BDF8' },
                { label: 'Sleeve C', whale: '0x4981', cap: '$2,000', win: '91.8%', color: '#C084FC' },
                { label: 'Sleeve D', whale: '0xce92', cap: '$2,000', win: '92.4%', color: '#00D09C' },
                { label: 'Sleeve E', whale: '0x38e1', cap: '$2,000', win: '88.9%', color: '#38BDF8' },
              ].map((sleeve, idx) => (
                <motion.div
                  key={sleeve.label}
                  initial={{ scale: 0.8, opacity: 0, y: 16 }}
                  animate={{ scale: 1, opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, delay: idx * 0.05 }}
                  className="liquid-glass-lens liquid-chromatic-rim group relative flex flex-col items-center justify-between p-2 sm:p-4 rounded-2xl sm:rounded-3xl cursor-pointer hover:scale-105 transition-all shadow-xl backdrop-blur-2xl"
                >
                  <div className="absolute top-1 inset-x-2 h-2 rounded-full bg-gradient-to-b from-white/90 to-transparent pointer-events-none opacity-90" />
                  <span className="text-[8px] sm:text-[10px] font-mono text-zinc-400 font-bold">{sleeve.label}</span>
                  <div className="my-1 sm:my-2 size-6 sm:size-10 rounded-full border border-white/20 bg-white/[0.08] flex items-center justify-center font-mono text-[9px] font-black text-white shadow-inner">
                    <Shield size={12} style={{ color: sleeve.color }} />
                  </div>
                  <div className="text-center font-mono">
                    <div className="text-[9px] sm:text-xs font-black text-white">{sleeve.cap}</div>
                    <div className="text-[7px] sm:text-[9px] font-bold" style={{ color: sleeve.color }}>
                      {sleeve.win}
                    </div>
                  </div>
                  <div className="absolute bottom-1 inset-x-2 h-0.5 rounded-full bg-gradient-to-r from-cyan-400/40 via-purple-400/40 to-amber-400/40 opacity-70 pointer-events-none" />
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Bottom Status Bar */}
        <div className="relative z-20 flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-white/10 font-mono text-xs text-zinc-400">
          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-[#00D09C] animate-pulse" />
            <span className="text-white font-bold text-[9px] sm:text-[11px]">OPTICAL LIQUID GLASS</span>
            <span className="text-white/20">|</span>
            <span className="text-[9px] sm:text-[11px] text-zinc-400 truncate max-w-[140px] sm:max-w-none">
              {mode === 'wwdc-fused'
                ? 'WWDC25 Concept Procedural Optics'
                : mode === 'interactive'
                ? 'Surface Tension Physics'
                : 'Isolated Boundaries'}
            </span>
          </div>

          <div className="flex items-center gap-2 sm:gap-3 text-[9px] sm:text-[11px]">
            <span className="text-zinc-400">
              Meniscus:{' '}
              <strong className="text-white font-bold">
                {mode === 'wwdc-fused' ? 'Bonded' : isBonded ? 'Bonded' : 'Separated'}
              </strong>
            </span>
            <span className="text-white/20">·</span>
            <span className="text-zinc-400">
              Prism Rim: <strong className="text-[#00D09C] font-bold">Active</strong>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
