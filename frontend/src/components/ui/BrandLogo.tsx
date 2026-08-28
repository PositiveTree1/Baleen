'use client';
import Link from 'next/link';
import Image from 'next/image';

interface BrandLogoProps {
  size?: 'sm' | 'md' | 'lg';
  href?: string;
  subtitle?: string;
  className?: string;
}

export function BrandLogo({ size = 'md', href = '/', subtitle, className = '' }: BrandLogoProps) {
  const imgSizes = {
    sm: { w: 22, h: 22, cls: 'w-5.5 h-5.5' },
    md: { w: 28, h: 28, cls: 'w-7 h-7' },
    lg: { w: 36, h: 36, cls: 'w-9 h-9' }
  };

  const textSizes = {
    sm: 'text-sm tracking-[0.14em]',
    md: 'text-base tracking-[0.16em]',
    lg: 'text-xl tracking-[0.18em]'
  };

  const content = (
    <div className={`inline-flex items-center gap-2.5 group select-none ${className}`}>
      <Image 
        src="/logo.png" 
        alt="Baleen Logo" 
        width={imgSizes[size].w} 
        height={imgSizes[size].h} 
        className={`${imgSizes[size].cls} object-contain dark:brightness-0 dark:invert group-hover:scale-105 transition-all duration-200`}
      />

      <div className="flex flex-col">
        <span className={`font-outfit font-black tracking-[0.12em] text-slate-950 dark:text-white ${textSizes[size]} transition-colors group-hover:text-slate-700 dark:group-hover:text-slate-200`}>
          BALEEN
        </span>
        {subtitle && (
          <span className="text-[10px] font-mono text-slate-400 dark:text-[#8E8F99] font-semibold tracking-wider -mt-0.5 uppercase">
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="focus:outline-none">
        {content}
      </Link>
    );
  }

  return content;
}
