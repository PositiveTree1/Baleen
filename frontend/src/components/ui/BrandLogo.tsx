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
    sm: { w: 20, h: 20, cls: 'w-5 h-5' },
    md: { w: 26, h: 26, cls: 'w-6.5 h-6.5' },
    lg: { w: 34, h: 34, cls: 'w-8.5 h-8.5' }
  };

  const textSizes = {
    sm: 'text-sm tracking-[0.14em]',
    md: 'text-base tracking-[0.16em]',
    lg: 'text-xl tracking-[0.18em]'
  };

  const content = (
    <div className={`inline-flex items-center gap-2.5 group select-none ${className}`}>
      <div className="relative flex items-center justify-center rounded-2xl bg-gradient-to-br from-slate-900 via-slate-800 to-slate-950 p-1.5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.4),0_2px_8px_rgba(0,0,0,0.15)] group-hover:scale-105 transition-transform duration-200">
        <Image 
          src="/logo.png" 
          alt="Baleen" 
          width={imgSizes[size].w} 
          height={imgSizes[size].h} 
          className={`${imgSizes[size].cls} object-contain filter invert drop-shadow`}
        />
        {/* Soft cold ice cyan ambient pulse */}
        <div className="absolute inset-0 rounded-2xl bg-cyan-400/15 filter blur-sm -z-10 group-hover:bg-cyan-400/30 transition-colors" />
      </div>

      <div className="flex flex-col">
        <span className={`font-brand-futuristic font-black uppercase text-slate-950 ${textSizes[size]} transition-colors group-hover:text-slate-800`}>
          BALEEN
        </span>
        {subtitle && (
          <span className="text-[10px] font-mono text-slate-400 font-semibold tracking-wider -mt-1 uppercase">
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
