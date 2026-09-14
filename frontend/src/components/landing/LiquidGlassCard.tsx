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
      className={`glass-card group relative overflow-hidden rounded-[32px] p-7 transition-all ${className}`}
      style={{
        background:
          'linear-gradient(145deg, rgba(255, 255, 255, 0.88) 0%, rgba(240, 247, 255, 0.72) 100%)',
        border: '1px solid rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(28px) saturate(190%)',
        WebkitBackdropFilter: 'blur(28px) saturate(190%)',
        boxShadow:
          'inset 0 1.5px 1px 0 rgba(255, 255, 255, 1), inset 0 -1px 1.5px 0 rgba(2, 132, 199, 0.12), 0 8px 24px -4px rgba(15, 23, 42, 0.05), 0 16px 40px -8px rgba(2, 132, 199, 0.08)',
      }}
    >
      {/* 1. Top Specular Crescent Highlight Arc */}
      <div className="absolute top-0 inset-x-6 h-1 rounded-full bg-gradient-to-b from-white via-white/80 to-transparent pointer-events-none opacity-90 group-hover:opacity-100 transition-opacity" />

      {/* 2. Interactive Specular Light Glint (Follows Cursor) */}
      <div
        className="pointer-events-none absolute -inset-px rounded-[32px] opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background: `radial-gradient(400px circle at ${mousePos.x}% ${mousePos.y}%, rgba(255, 255, 255, 0.45), transparent 50%)`,
        }}
      />

      {/* 3. Subtle Chromatic Dispersion Rim (Spectral Rainbow Glint) */}
      <div className="pointer-events-none absolute inset-0 rounded-[32px] border border-transparent group-hover:border-white/40 transition-colors">
        <div
          className="absolute inset-0 rounded-[32px] opacity-30 group-hover:opacity-75 transition-opacity pointer-events-none"
          style={{
            background:
              'linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(56,189,248,0.45) 20%, rgba(129,140,248,0.35) 45%, rgba(52,211,153,0.40) 70%, rgba(244,114,182,0.35) 88%, rgba(255,255,255,0.90) 100%)',
            mask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
            maskComposite: 'exclude',
            WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
            WebkitMaskComposite: 'xor',
            padding: '1.2px',
          }}
        />
      </div>

      {/* 4. Bottom Refraction Glow */}
      <div className="absolute bottom-0 inset-x-8 h-px bg-gradient-to-r from-transparent via-[#0EA5E9]/35 to-transparent pointer-events-none opacity-60 group-hover:opacity-90 transition-opacity" />

      {/* Content Container */}
      <div className="relative z-10 text-slate-900">{children}</div>
    </motion.div>
  );
}
