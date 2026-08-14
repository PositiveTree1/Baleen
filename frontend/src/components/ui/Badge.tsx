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
      colors = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25';
      label = 'Gold Sniper';
      break;
    case 'standard':
      colors = 'bg-white/[0.05] text-zinc-300 border-white/10';
      label = 'Standard';
      break;
    case 'dormant':
      colors = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      label = 'Dormant';
      break;
    case 'pending':
      colors = 'bg-amber-500/10 text-amber-300 border-amber-500/20';
      label = 'Pending';
      break;
    case 'rejected':
      colors = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      label = 'Rejected';
      break;
    default:
      colors = 'bg-white/[0.05] text-zinc-300 border-white/10';
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium tracking-wide border ${colors} ${className}`}>
      {label}
    </span>
  );
}
