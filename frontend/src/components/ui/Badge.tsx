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
      colors = 'bg-amber-500/[0.05] text-amber-900 border-amber-400/40 shadow-[0_1px_2px_rgba(245,158,11,0.06)]';
      label = 'Gold Tier Alpha';
      break;
    case 'standard':
      colors = 'bg-slate-50 text-slate-700 border-black/[0.08]';
      label = 'Standard Whale';
      break;
    case 'dormant':
      colors = 'bg-slate-50 text-slate-500 border-black/[0.06]';
      label = 'Inactive';
      break;
    case 'pending':
      colors = 'bg-slate-50 text-slate-500 border-black/[0.06]';
      label = 'Pending Audit';
      break;
    case 'rejected':
      colors = 'bg-rose-50/50 text-rose-700 border-rose-200/60';
      label = 'Filtered';
      break;
    default:
      colors = 'bg-slate-50 text-slate-700 border-black/[0.08]';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold tracking-tight border ${colors} ${className} transition-all`}>
      {tier === 'gold_sniper' && <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />}
      {label}
    </span>
  );
}
