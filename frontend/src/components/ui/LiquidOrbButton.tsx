'use client';

import React from 'react';
import { soundFx } from '@/lib/sound';

interface LiquidOrbButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  size?: 'sm' | 'md' | 'lg';
  active?: boolean;
  playSound?: boolean;
  children: React.ReactNode;
}

export function LiquidOrbButton({
  size = 'md',
  active = false,
  playSound = true,
  className = '',
  onClick,
  children,
  ...props
}: LiquidOrbButtonProps) {
  const sizeClasses = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-12 h-12 text-base',
  }[size];

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (playSound) {
      soundFx.playTap();
    }
    if (onClick) {
      onClick(e);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`liquid-orb-btn inline-flex items-center justify-center shrink-0 select-none ${sizeClasses} ${
        active ? 'ring-2 ring-sky-400/80 shadow-[0_0_20px_rgba(56,189,248,0.4)]' : ''
      } ${className}`}
      {...props}
    >
      <span className="relative z-10 flex items-center justify-center">
        {children}
      </span>
    </button>
  );
}
