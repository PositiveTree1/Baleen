import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  variant?: 'default' | 'elevated' | 'interactive';
  className?: string;
}

export function Card({ children, variant = 'default', className = '' }: CardProps) {
  let variantClasses = 'glass-card rounded-xl p-6';
  
  if (variant === 'elevated') {
    variantClasses += ' shadow-lg';
  } else if (variant === 'interactive') {
    variantClasses += ' transition-all hover:glow-cyan cursor-pointer';
  }
  
  return (
    <div className={`${variantClasses} ${className}`}>
      {children}
    </div>
  );
}
