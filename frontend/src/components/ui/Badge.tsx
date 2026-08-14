import { Tier } from '@/types';

interface BadgeProps {
  tier: Tier | string;
  className?: string;
}

export function Badge({ tier, className = '' }: BadgeProps) {
  let colors = '';
  let label = tier || 'Standard';

  switch (tier) {
    case 'gold_sniper':
      colors = 'bg-emerald-50 text-emerald-800 border-emerald-300/80 shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_1px_2px_rgba(16,185,129,0.06)]';
      label = 'Gold Sniper';
      break;
    case 'standard':
      colors = 'bg-zinc-100 text-zinc-700 border-zinc-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]';
      label = 'Standard';
      break;
    case 'dormant':
      colors = 'bg-amber-50 text-amber-800 border-amber-300/80 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]';
      label = 'Dormant';
      break;
    case 'pending':
      colors = 'bg-amber-50 text-amber-800 border-amber-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]';
      label = 'Pending';
      break;
    case 'rejected':
      colors = 'bg-rose-50 text-rose-800 border-rose-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]';
      label = 'Rejected';
      break;
    default:
      colors = 'bg-zinc-100 text-zinc-700 border-zinc-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]';
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold tracking-wide border ${colors} ${className}`}>
      {label}
    </span>
  );
}
