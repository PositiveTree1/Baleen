'use client';
import { motion, HTMLMotionProps } from 'framer-motion';
import { ReactNode } from 'react';

interface ButtonProps extends HTMLMotionProps<'button'> {
  variant?: 'primary' | 'secondary' | 'danger';
  children: ReactNode;
}

export function Button({ variant = 'primary', children, className = '', ...props }: ButtonProps) {
  const baseClasses = 'px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer flex items-center justify-center gap-2';
  let variantClasses = '';
  
  if (variant === 'primary') {
    variantClasses = 'bg-white text-zinc-950 font-semibold hover:bg-zinc-200 shadow-sm hover:shadow-apple-glow active:scale-[0.98]';
  } else if (variant === 'secondary') {
    variantClasses = 'bg-white/[0.06] text-white border border-white/10 hover:bg-white/[0.12] hover:border-white/20 active:scale-[0.98]';
  } else if (variant === 'danger') {
    variantClasses = 'bg-rose-500/15 text-rose-400 border border-rose-500/25 hover:bg-rose-500/25 hover:border-rose-500/40 active:scale-[0.98]';
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
