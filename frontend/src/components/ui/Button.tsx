'use client';
import { motion, HTMLMotionProps } from 'framer-motion';
import { ReactNode } from 'react';

export interface ButtonProps extends HTMLMotionProps<'button'> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success';
  size?: 'sm' | 'md' | 'lg';
  children: ReactNode;
}

export function Button({ 
  variant = 'primary', 
  size = 'md',
  children, 
  className = '', 
  ...props 
}: ButtonProps) {
  const baseClasses = 'inline-flex items-center justify-center font-semibold rounded-full transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] focus-visible:ring-offset-2 focus-visible:ring-offset-[#F8F9FB] dark:focus-visible:ring-offset-black disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer select-none active:scale-[0.98]';
  
  // Size variations
  let sizeClasses = 'px-4 py-2 text-sm gap-2';
  if (size === 'sm') {
    sizeClasses = 'px-3 py-1.5 text-xs gap-1.5';
  } else if (size === 'lg') {
    sizeClasses = 'px-6 py-3.5 text-base gap-2.5';
  }

  // Variant styles
  let variantClasses = '';
  if (variant === 'primary') {
    variantClasses = 'bg-slate-950 hover:bg-slate-800 text-white dark:bg-white dark:hover:bg-slate-200 dark:text-black shadow-sm';
  } else if (variant === 'secondary') {
    variantClasses = 'bg-[#F1F3F5] hover:bg-[#E2E6EA] text-slate-800 dark:bg-[#1C1D22] dark:hover:bg-[#2C2D35] dark:text-white border border-black/[0.08] dark:border-white/10 shadow-2xs';
  } else if (variant === 'outline') {
    variantClasses = 'bg-transparent hover:bg-black/5 dark:hover:bg-white/5 text-slate-900 dark:text-white border border-black/[0.12] dark:border-white/15';
  } else if (variant === 'ghost') {
    variantClasses = 'bg-transparent hover:bg-black/5 dark:hover:bg-white/10 text-slate-700 dark:text-[#8E8F99] hover:text-slate-950 dark:hover:text-white';
  } else if (variant === 'danger') {
    variantClasses = 'bg-rose-50 hover:bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:hover:bg-rose-900/60 dark:text-[#FF453A] border border-rose-200 dark:border-rose-800/40';
  } else if (variant === 'success') {
    variantClasses = 'bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:hover:bg-emerald-900/60 dark:text-[#00D09C] border border-emerald-200 dark:border-emerald-800/40';
  }
  
  return (
    <motion.button
      whileTap={{ scale: 0.98 }}
      className={`${baseClasses} ${sizeClasses} ${variantClasses} ${className}`}
      {...props}
    >
      {children}
    </motion.button>
  );
}
