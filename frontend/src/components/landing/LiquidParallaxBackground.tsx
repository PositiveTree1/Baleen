'use client';

import { useEffect, useState } from 'react';

export function LiquidParallaxBackground() {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth) * 2 - 1;
      const y = (e.clientY / window.innerHeight) * 2 - 1;
      setMousePos({ x, y });
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div
      className="fixed inset-0 pointer-events-none overflow-hidden z-0 bg-[#060709]"
      aria-hidden="true"
    >
      {/* 1. Subtle WWDC Studio Perspective Grid Plane */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `linear-gradient(to right, rgba(255, 255, 255, 0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.05) 1px, transparent 1px)`,
          backgroundSize: '64px 64px',
          transform: `translate3d(${mousePos.x * -8}px, ${mousePos.y * -8}px, 0)`,
          transition: 'transform 0.5s ease-out',
        }}
      />

      {/* 2. Atmospheric Oceanic Volumetric Caustic Orbs */}
      <div
        className="absolute -top-40 left-1/2 -translate-x-1/2 w-[900px] h-[500px] rounded-full bg-gradient-to-b from-[#00D09C]/12 via-cyan-500/8 to-transparent blur-[120px] transition-transform duration-700 ease-out"
        style={{
          transform: `translate3d(calc(-50% + ${mousePos.x * 20}px), ${mousePos.y * 15}px, 0)`,
        }}
      />

      <div
        className="absolute top-1/3 -left-48 w-[600px] h-[600px] rounded-full bg-cyan-600/8 blur-[140px] transition-transform duration-1000 ease-out"
        style={{
          transform: `translate3d(${mousePos.x * -25}px, ${mousePos.y * -20}px, 0)`,
        }}
      />

      <div
        className="absolute top-2/3 -right-48 w-[600px] h-[600px] rounded-full bg-purple-600/8 blur-[140px] transition-transform duration-1000 ease-out"
        style={{
          transform: `translate3d(${mousePos.x * 25}px, ${mousePos.y * 20}px, 0)`,
        }}
      />

      {/* 3. Subtle Edge Refraction Vignette */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#060709]/40 to-[#060709] pointer-events-none" />
      <div className="absolute inset-0 bg-radial-[at_50%_50%] from-transparent via-[#060709]/20 to-[#060709] pointer-events-none" />
    </div>
  );
}
