import { Tier } from '@/types';
import { Sparkles } from 'lucide-react';

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
      colors = 'bg-gradient-to-r from-amber-100 via-amber-50 to-amber-100 text-amber-950 border-amber-300 shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(245,158,11,0.25)]';
      label = 'Gold Sniper';
      break;
    case 'standard':
      colors = 'bg-slate-100 text-slate-700 border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]';
      label = 'Standard';
      break;
    case 'dormant':
      colors = 'bg-amber-50 text-amber-800 border-amber-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]';
      label = 'Dormant';
      break;
    case 'pending':
      colors = 'bg-slate-100 text-slate-600 border-black/[0.06] shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]';
      label = 'Pending';
      break;
    case 'rejected':
      colors = 'bg-rose-50 text-rose-800 border-rose-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]';
      label = 'Rejected';
      break;
    default:
      colors = 'bg-slate-100 text-slate-700 border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]';
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wide border ${colors} ${className} transition-all`}>
      {isGold && <Sparkles size={11} className="text-amber-600 animate-spin-slow" />}
      {label}
    </span>
  );
}
