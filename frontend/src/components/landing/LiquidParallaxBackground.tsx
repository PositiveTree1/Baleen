'use client';

import { useEffect, useState, useRef } from 'react';
import Image from 'next/image';

export function LiquidParallaxBackground() {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [scrollY, setScrollY] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let animationFrameId = 0;

    const handleMouseMove = (e: MouseEvent) => {
      // Normalize mouse coordinates from -1 to 1
      const x = (e.clientX / window.innerWidth) * 2 - 1;
      const y = (e.clientY / window.innerHeight) * 2 - 1;
      setMousePos({ x, y });
    };

    const handleScroll = () => {
      setScrollY(window.scrollY);
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    window.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('scroll', handleScroll);
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div 
      ref={containerRef}
      className="fixed inset-0 pointer-events-none overflow-hidden z-0 bg-[#07080A]"
      aria-hidden="true"
    >
      {/* 1. Deep Ocean Abyss & Baleen Whale Master Layer */}
      <div 
        className="absolute inset-0 transition-transform duration-700 ease-out will-change-transform scale-105"
        style={{
          transform: `translate3d(${mousePos.x * -14}px, ${mousePos.y * -10 + scrollY * -0.06}px, 0)`
        }}
      >
        <Image
          src="/images/baleen_abyssal_whale.jpg"
          alt=""
          fill
          priority
          sizes="100vw"
          className="object-cover object-center opacity-55 mix-blend-luminosity brightness-[0.75] contrast-[1.15]"
        />
      </div>

      {/* 2. Volumetric Deep Oceanic Lighting & Caustics */}
      <div 
        className="absolute inset-0 bg-radial-[at_50%_15%] from-cyan-950/25 via-[#07080A]/60 to-[#07080A] opacity-90 transition-transform duration-1000 ease-out"
        style={{
          transform: `translate3d(${mousePos.x * 10}px, ${mousePos.y * 6}px, 0)`
        }}
      />

      {/* 3. Floating 3D Liquid Glass Metaball Lens (Foreground Depth Plane 1) */}
      <div 
        className="absolute top-[18%] right-[8%] w-[260px] sm:w-[420px] h-[160px] sm:h-[240px] transition-transform duration-500 ease-out will-change-transform hidden md:block opacity-75"
        style={{
          transform: `translate3d(${mousePos.x * 28}px, ${mousePos.y * 22 + scrollY * -0.12}px, 0)`
        }}
      >
        <div className="relative w-full h-full rounded-full liquid-glass-lens liquid-chromatic-rim p-2 flex items-center justify-center">
          <div className="absolute inset-3 rounded-full overflow-hidden opacity-45 mix-blend-screen pointer-events-none">
            <Image
              src="/images/baleen_liquid_glass.jpg"
              alt=""
              fill
              sizes="420px"
              className="object-contain"
            />
          </div>
        </div>
      </div>

      {/* 4. Floating 3D Liquid Droplet (Foreground Depth Plane 2) */}
      <div 
        className="absolute top-[55%] left-[5%] w-[180px] sm:w-[260px] h-[120px] sm:h-[180px] transition-transform duration-300 ease-out will-change-transform hidden lg:block opacity-60"
        style={{
          transform: `translate3d(${mousePos.x * -22}px, ${mousePos.y * -16 + scrollY * -0.18}px, 0)`
        }}
      >
        <div className="relative w-full h-full rounded-full liquid-glass-lens liquid-chromatic-rim" />
      </div>

      {/* 5. Edge Refraction Vignettes (Ensures readability and deep dark obsidian tone) */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#07080A]/85 via-transparent to-[#07080A] pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-r from-[#07080A]/90 via-transparent to-[#07080A]/90 pointer-events-none" />
    </div>
  );
}
