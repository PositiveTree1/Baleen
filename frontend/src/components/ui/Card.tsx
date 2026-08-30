import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  variant?: 'default' | 'elevated' | 'interactive' | 'obsidian' | 'subtle';
  className?: string;
  onClick?: () => void;
}

export function Card({ children, variant = 'default', className = '', onClick }: CardProps) {
  let variantClasses = 'bg-white dark:bg-[#16171B] border border-black/[0.06] dark:border-white/10 rounded-[26px] p-6 shadow-2xs';
  
  if (variant === 'elevated') {
    variantClasses = 'bg-white dark:bg-[#16171B] border border-black/[0.06] dark:border-white/10 rounded-[26px] p-6 shadow-md';
  } else if (variant === 'interactive') {
    variantClasses = 'bg-white dark:bg-[#16171B] border border-black/[0.06] dark:border-white/10 rounded-[26px] p-6 shadow-2xs hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C]';
  } else if (variant === 'obsidian') {
    variantClasses = 'bg-[#16171B] text-white border border-white/10 rounded-[28px] p-8 shadow-xl';
  } else if (variant === 'subtle') {
    variantClasses = 'bg-[#F1F3F5] dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 rounded-[22px] p-5';
  }
  
  return (
    <div className={`${variantClasses} ${className}`} onClick={onClick}>
      {children}
    </div>
  );
}
