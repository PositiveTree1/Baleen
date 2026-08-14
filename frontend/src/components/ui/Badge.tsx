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
      colors = 'bg-amber-50/90 text-amber-950 border-amber-300 shadow-[0_1px_4px_rgba(245,158,11,0.12)]';
      label = 'Gold Tier';
      break;
    case 'standard':
      colors = 'bg-slate-100/90 text-slate-800 border-slate-200/90 shadow-sm';
      label = 'Standard Whale';
      break;
    case 'dormant':
      colors = 'bg-slate-50 text-slate-500 border-slate-200';
      label = 'Inactive';
      break;
    case 'pending':
      colors = 'bg-slate-50 text-slate-500 border-slate-200';
      label = 'Pending Audit';
      break;
    case 'rejected':
      colors = 'bg-rose-50 text-rose-700 border-rose-200';
      label = 'Filtered';
      break;
    default:
      colors = 'bg-slate-100 text-slate-800 border-slate-200';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold tracking-tight border ${colors} ${className} transition-all`}>
      {isGold && <Sparkles size={13} className="text-amber-600 fill-amber-500/30 shrink-0" />}
      <span>{label}</span>
    </span>
  );
}
