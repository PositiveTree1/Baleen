'use client';

import { useState, useRef, MouseEvent, ReactNode } from 'react';
import { motion } from 'framer-motion';

interface LiquidGlassCardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}

export function LiquidGlassCard({ children, className = '', onClick }: LiquidGlassCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [mousePos, setMousePos] = useState({ x: 50, y: 50 });

  const handleMouseMove = (e: MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setMousePos({ x, y });
  };

  return (
    <motion.div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onClick={onClick}
      whileHover={{ y: -3, scale: 1.01 }}
      transition={{ type: 'spring', stiffness: 350, damping: 25 }}
      className={`group relative overflow-hidden rounded-[32px] p-7 transition-all ${className}`}
      style={{
        background:
          'linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.02) 50%, rgba(255, 255, 255, 0.06) 100%)',
        border: '1px solid rgba(255, 255, 255, 0.16)',
        backdropFilter: 'blur(32px) saturate(190%) contrast(104%)',
        boxShadow:
          'inset 0 1.5px 1px 0 rgba(255, 255, 255, 0.65), inset 0 -1.5px 1.5px 0 rgba(0, 0, 0, 0.4), 0 24px 60px -12px rgba(0, 0, 0, 0.85)',
      }}
    >
      {/* 1. Top Specular Crescent Highlight Arc */}
      <div className="absolute top-0 inset-x-6 h-1 rounded-full bg-gradient-to-b from-white/90 via-white/40 to-transparent pointer-events-none opacity-80 group-hover:opacity-100 transition-opacity" />

      {/* 2. Interactive Specular Light Glint (Follows Cursor) */}
      <div
        className="pointer-events-none absolute -inset-px rounded-[32px] opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background: `radial-gradient(400px circle at ${mousePos.x}% ${mousePos.y}%, rgba(255, 255, 255, 0.15), transparent 45%)`,
        }}
      />

      {/* 3. Subtle Chromatic Dispersion Rim (Spectral Rainbow Glint) */}
      <div className="pointer-events-none absolute inset-0 rounded-[32px] border border-transparent group-hover:border-white/20 transition-colors">
        <div
          className="absolute inset-0 rounded-[32px] opacity-25 group-hover:opacity-60 transition-opacity pointer-events-none"
          style={{
            background:
              'linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(56,189,248,0.3) 25%, rgba(192,132,252,0.3) 50%, rgba(52,211,153,0.35) 75%, rgba(255,255,255,0.4) 100%)',
            mask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
            maskComposite: 'exclude',
            WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
            WebkitMaskComposite: 'xor',
            padding: '1px',
          }}
        />
      </div>

      {/* 4. Bottom Refraction Glow */}
      <div className="absolute bottom-0 inset-x-8 h-px bg-gradient-to-r from-transparent via-[#00D09C]/40 to-transparent pointer-events-none opacity-50 group-hover:opacity-80 transition-opacity" />

      {/* Content Container */}
      <div className="relative z-10">{children}</div>
    </motion.div>
  );
}
