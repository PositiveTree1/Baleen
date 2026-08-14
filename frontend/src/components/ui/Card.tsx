import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  variant?: 'default' | 'elevated' | 'interactive';
  className?: string;
}

export function Card({ children, variant = 'default', className = '' }: CardProps) {
  let variantClasses = 'glass-card rounded-2xl p-6';
  
  if (variant === 'elevated') {
    variantClasses = 'skeuo-surface rounded-2xl p-6 shadow-skeuo-card';
  } else if (variant === 'interactive') {
    variantClasses = 'glass-card glass-card-hover rounded-2xl p-6 cursor-pointer';
  }
  
  return (
    <div className={`${variantClasses} ${className}`}>
      {children}
    </div>
  );
}
