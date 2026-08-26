'use client';
import { useMemo } from 'react';
import { ExecutionLog } from '@/types';
import { HelpCircle, TrendingUp, Award, Layers } from 'lucide-react';

interface ScorecardWidgetProps {
  logs?: ExecutionLog[];
  totalFilledTrades?: number;
  allTimeWinRate?: number;
  allTimeWins?: number;
  allTimeLosses?: number;
  sizeMode?: 'small' | 'medium' | 'full';
}

export function ScorecardWidget({
  logs = [],
  totalFilledTrades = 5049,
  allTimeWinRate,
  allTimeWins,
  allTimeLosses,
  sizeMode = 'small'
}: ScorecardWidgetProps) {
  const { winCount, lossCount, winRate, activePositionsCount } = useMemo(() => {
    let wins = 0;
    let losses = 0;
    const activeConditions = new Set<string>();

    for (const log of logs) {
      const pnl = log.pnl ?? 0;
      if (pnl >= 0) wins++;
      else losses++;

      if (log.side === 'BUY' && log.status === 'FILLED' && !log.marketQuestion?.toLowerCase().includes('resolved')) {
        activeConditions.add(log.marketConditionId || log.id);
      }
    }

    const total = wins + losses;
    const wr = total > 0 ? (wins / total) * 100 : 0;

    return {
      winCount: wins,
      lossCount: losses,
      winRate: wr,
      activePositionsCount: activeConditions.size
    };
  }, [logs]);

  const effectiveWinRate = allTimeWinRate !== undefined ? allTimeWinRate : winRate;
  const effectiveWins = allTimeWins !== undefined ? allTimeWins : winCount;
  const effectiveLosses = allTimeLosses !== undefined ? allTimeLosses : lossCount;

  return (
    <div className="p-6 rounded-3xl apple-glass light-refraction relative overflow-hidden flex flex-col justify-between space-y-4 h-full">
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Execution Scorecard</span>
          <span className="text-[11px] font-mono font-bold text-slate-700 px-2.5 py-0.5 rounded-full bg-slate-100 border border-black/[0.06]">
            {totalFilledTrades.toLocaleString()} Lifetime Fills
          </span>
        </div>
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className="text-3xl font-extrabold font-mono text-slate-900">
            {effectiveWinRate.toFixed(1)}%
          </span>
          <span className="text-xs font-mono font-semibold text-slate-500">
            Win Rate ({effectiveWins.toLocaleString()}W / {effectiveLosses.toLocaleString()}L)
          </span>
        </div>
      </div>

      {/* Win/Loss Bar */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs font-bold font-mono">
          <span className="text-emerald-700">
            {effectiveWins.toLocaleString()} Won
          </span>
          <span className="text-rose-700">
            {effectiveLosses.toLocaleString()} Lost
          </span>
        </div>
        <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden flex shadow-inner">
          <div 
            className="bg-emerald-500 transition-all duration-500" 
            style={{ width: `${Math.max(5, Math.min(95, effectiveWinRate))}%` }} 
          />
          <div 
            className="bg-rose-500 transition-all duration-500" 
            style={{ width: `${Math.max(5, Math.min(95, 100 - effectiveWinRate))}%` }} 
          />
        </div>
        <div className="flex justify-between text-[10px] font-mono font-semibold text-slate-400">
          <span className="text-emerald-700">
            {effectiveWins.toLocaleString()} Profitable Fills
          </span>
          <span className="text-rose-700">
            {effectiveLosses.toLocaleString()} Unprofitable Fills
          </span>
        </div>
      </div>

      {/* Sizing, Active Positions vs Total Platform Order Fills */}
      <div className="grid grid-cols-2 gap-2 pt-2 border-t border-black/[0.06]">
        <div className="p-3 rounded-2xl bg-white/40 backdrop-blur-md border border-white/60 shadow-[inset_0_1px_1px_rgba(255,255,255,0.7)] space-y-0.5">
          <div className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1">
            Active Positions
            <span title="A Position is your active aggregated contracts in an open prediction market." className="cursor-help text-slate-400 hover:text-slate-600">
              <HelpCircle size={10} />
            </span>
          </div>
          <div className="text-sm font-mono font-bold text-emerald-700">{activePositionsCount} Open</div>
        </div>
        <div className="p-3 rounded-2xl bg-white/40 backdrop-blur-md border border-white/60 shadow-[inset_0_1px_1px_rgba(255,255,255,0.7)] space-y-0.5">
          <div className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1">
            Total Executions
            <span title="Total cumulative trade executions recorded in the Baleen database across all 4 days." className="cursor-help text-slate-400 hover:text-slate-600">
              <HelpCircle size={10} />
            </span>
          </div>
          <div className="text-sm font-mono font-bold text-slate-900">
            {totalFilledTrades.toLocaleString()} Fills
          </div>
        </div>
      </div>
    </div>
  );
}
