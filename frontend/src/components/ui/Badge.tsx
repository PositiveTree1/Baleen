import { Tier } from '@/types';

interface BadgeProps {
  tier: Tier | string;
  className?: string;
}

export function Badge({ tier, className = '' }: BadgeProps) {
  let colors = '';
  let label = tier;

  switch (tier) {
    case 'gold_sniper':
      colors = 'bg-baleen-green/10 text-baleen-green border-baleen-green/50 shadow-[0_0_10px_rgba(16,185,129,0.3)]';
      label = 'Gold Sniper';
      break;
    case 'standard':
      colors = 'bg-baleen-slate text-baleen-muted border-white/10';
      label = 'Standard';
      break;
    case 'dormant':
      colors = 'bg-amber-500/10 text-amber-500 border-amber-500/50';
      label = 'Dormant';
      break;
    default:
      colors = 'bg-baleen-slate text-baleen-white border-white/10';
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colors} ${className}`}>
      {label}
    </span>
  );
}
