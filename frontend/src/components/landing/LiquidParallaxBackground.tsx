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
      className="fixed inset-0 pointer-events-none overflow-hidden z-0 bg-gradient-to-b from-[#F0F7FF] via-[#E0F2FE]/30 to-[#F0F7FF]"
      aria-hidden="true"
    >
      {/* 1. Subtle Arctic Studio Perspective Grid Plane */}
      <div
        className="absolute inset-0 opacity-40"
        style={{
          backgroundImage: `linear-gradient(to right, rgba(2, 132, 199, 0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(2, 132, 199, 0.04) 1px, transparent 1px)`,
          backgroundSize: '64px 64px',
          transform: `translate3d(${mousePos.x * -8}px, ${mousePos.y * -8}px, 0)`,
          transition: 'transform 0.5s ease-out',
        }}
      />

      {/* 2. Atmospheric Glacial Volumetric Caustic Orbs */}
      <div
        className="absolute -top-40 left-1/2 -translate-x-1/2 w-[900px] h-[500px] rounded-full bg-gradient-to-b from-sky-300/20 via-cyan-200/15 to-transparent blur-[120px] transition-transform duration-700 ease-out"
        style={{
          transform: `translate3d(calc(-50% + ${mousePos.x * 20}px), ${mousePos.y * 15}px, 0)`,
        }}
      />

      <div
        className="absolute top-1/3 -left-48 w-[600px] h-[600px] rounded-full bg-sky-200/25 blur-[140px] transition-transform duration-1000 ease-out"
        style={{
          transform: `translate3d(${mousePos.x * -25}px, ${mousePos.y * -20}px, 0)`,
        }}
      />

      <div
        className="absolute top-2/3 -right-48 w-[600px] h-[600px] rounded-full bg-indigo-200/20 blur-[140px] transition-transform duration-1000 ease-out"
        style={{
          transform: `translate3d(${mousePos.x * 25}px, ${mousePos.y * 20}px, 0)`,
        }}
      />

      {/* 3. Subtle Edge Refraction Vignette */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-sky-50/20 to-sky-100/30 pointer-events-none" />
      <div className="absolute inset-0 bg-radial-[at_50%_50%] from-transparent via-sky-50/10 to-sky-100/20 pointer-events-none" />
    </div>
  );
}
