'use client';
import { motion, HTMLMotionProps } from 'framer-motion';
import { ReactNode } from 'react';

interface ButtonProps extends HTMLMotionProps<'button'> {
  variant?: 'primary' | 'secondary' | 'danger';
  children: ReactNode;
}

export function Button({ variant = 'primary', children, className = '', ...props }: ButtonProps) {
  const baseClasses = 'px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer flex items-center justify-center gap-2 select-none active:scale-[0.98]';
  let variantClasses = '';
  
  if (variant === 'primary') {
    variantClasses = 'bg-[#0F172A] hover:bg-[#1E293B] text-white font-semibold border border-black/20 shadow-[inset_0_1px_0_rgba(255,255,255,0.2),0_2px_6px_rgba(0,0,0,0.12),0_8px_16px_-4px_rgba(0,0,0,0.08)]';
  } else if (variant === 'secondary') {
    variantClasses = 'bg-white hover:bg-zinc-50 text-zinc-900 border border-black/[0.12] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_1px_3px_rgba(0,0,0,0.06),0_4px_8px_-2px_rgba(0,0,0,0.03)]';
  } else if (variant === 'danger') {
    variantClasses = 'bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_1px_2px_rgba(225,29,72,0.06)]';
  }
  
  return (
    <motion.button
      whileTap={{ scale: 0.98 }}
      className={`${baseClasses} ${variantClasses} ${className}`}
      {...props}
    >
      {children}
    </motion.button>
  );
}
