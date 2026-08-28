interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rounded' | 'card';
}

export function Skeleton({ className = '', variant = 'rounded' }: SkeletonProps) {
  const variantStyles = {
    text: 'h-4 w-full rounded-md',
    circular: 'rounded-full',
    rounded: 'rounded-2xl',
    card: 'rounded-[26px] p-5'
  };

  return (
    <div className={`animate-shimmer border border-black/[0.04] dark:border-white/5 ${variantStyles[variant]} ${className}`} />
  );
}
