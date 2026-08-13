'use client';
import { motion, HTMLMotionProps } from 'framer-motion';
import { ReactNode } from 'react';

interface ButtonProps extends HTMLMotionProps<'button'> {
  variant?: 'primary' | 'secondary' | 'danger';
  children: ReactNode;
}

export function Button({ variant = 'primary', children, className = '', ...props }: ButtonProps) {
  const baseClasses = 'px-4 py-2 rounded-lg font-medium transition-colors focus:outline-none disabled:opacity-50';
  let variantClasses = '';
  
  if (variant === 'primary') {
    variantClasses = 'bg-gradient-to-r from-baleen-cyan to-baleen-blue text-baleen-obsidian hover:shadow-[0_0_15px_rgba(0,242,254,0.4)]';
  } else if (variant === 'secondary') {
    variantClasses = 'bg-baleen-slate text-baleen-white border border-white/10 hover:bg-white/5';
  } else if (variant === 'danger') {
    variantClasses = 'bg-baleen-red/20 text-baleen-red border border-baleen-red/50 hover:bg-baleen-red/30';
  }
  
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`${baseClasses} ${variantClasses} ${className}`}
      {...props}
    >
      {children}
    </motion.button>
  );
}
