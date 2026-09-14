'use client';

import React from 'react';
import { soundFx } from '@/lib/sound';

interface LiquidToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
  className?: string;
}

export function LiquidToggle({
  checked,
  onChange,
  label,
  disabled = false,
  className = '',
}: LiquidToggleProps) {
  const handleToggle = () => {
    if (disabled) return;
    soundFx.playSlider();
    onChange(!checked);
  };

  return (
    <div
      onClick={handleToggle}
      className={`inline-flex items-center gap-3 cursor-pointer select-none ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      } ${className}`}
      role="switch"
      aria-checked={checked}
      tabIndex={disabled ? -1 : 0}
      onKeyDown={(e) => {
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault();
          handleToggle();
        }
      }}
    >
      <div className={`liquid-toggle-track ${checked ? 'active' : ''}`}>
        <div className="liquid-toggle-thumb" />
      </div>
      {label && (
        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
          {label}
        </span>
      )}
    </div>
  );
}
