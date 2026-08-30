import { Tier } from '@/types';
import { Sparkles, Shield } from 'lucide-react';

interface BadgeProps {
  tier: Tier | string;
  className?: string;
}

export function Badge({ tier, className = '' }: BadgeProps) {
  let colors = '';
  let label = tier || 'Standard';
  let isGold = false;

  switch (tier) {
    case 'gold_sniper':
      isGold = true;
      colors = 'bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-300 border-amber-300 dark:border-amber-700/50 shadow-2xs';
      label = 'Gold Tier';
      break;
    case 'standard':
      colors = 'bg-slate-100 dark:bg-[#1C1D22] text-slate-800 dark:text-slate-200 border-slate-200 dark:border-white/10 shadow-2xs';
      label = 'Standard Whale';
      break;
    case 'dormant':
      colors = 'bg-slate-100/70 dark:bg-[#1C1D22]/60 text-slate-500 dark:text-[#8E8F99] border-slate-200 dark:border-white/5';
      label = 'Inactive';
      break;
    case 'pending':
      colors = 'bg-sky-50 dark:bg-sky-950/40 text-sky-800 dark:text-sky-300 border-sky-200 dark:border-sky-800/40';
      label = 'Pending Audit';
      break;
    case 'rejected':
      colors = 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-[#FF453A] border-rose-200 dark:border-rose-800/40';
      label = 'Filtered';
      break;
    default:
      colors = 'bg-slate-100 dark:bg-[#1C1D22] text-slate-800 dark:text-slate-200 border-slate-200 dark:border-white/10';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-tight border ${colors} ${className} transition-colors`}>
      {isGold && <Sparkles size={12} aria-hidden="true" className="text-amber-600 dark:text-amber-400 fill-amber-500/30 shrink-0" />}
      <span>{label}</span>
    </span>
  );
}
