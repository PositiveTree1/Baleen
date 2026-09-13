'use client';
import { BarChart2, ShieldCheck } from 'lucide-react';
import { ExecutionLog, PortfolioSummary } from '@/types';
import { Modal } from '../ui/Modal';

export interface DeepAnalyticsModalProps {
  isOpen: boolean;
  onClose: () => void;
  portfolio: PortfolioSummary | null;
  logs: ExecutionLog[];
}

export function DeepAnalyticsModal({ isOpen, onClose, portfolio, logs }: DeepAnalyticsModalProps) {
  const totalTrades = portfolio?.filledTradesCount ?? logs.length;
  const evaluatedLogs = logs.filter(l => l.pnl !== null && l.pnl !== undefined);
  const omittedEvidenceCount = portfolio ? 0 : logs.length - evaluatedLogs.length;
  const wins = portfolio?.allTimeWins ?? evaluatedLogs.filter(l => l.pnl! > 0).length;
  const losses = portfolio?.allTimeLosses ?? evaluatedLogs.filter(l => l.pnl! < 0).length;
  const evaluated = wins + losses;
  const winRate = portfolio?.allTimeWinRate ?? (evaluated > 0 ? (wins / evaluated) * 100 : null);
  const totalPnL = portfolio?.totalPnlUsd ?? (evaluatedLogs.length > 0 ? evaluatedLogs.reduce((acc, l) => acc + l.pnl!, 0.0) : null);
  const startBal = portfolio?.startingBalance ?? null;
  const returnPct = totalPnL !== null && startBal !== null && startBal > 0 ? (totalPnL / startBal) * 100 : null;
  const feeLogs = logs.filter(l => l.feeUsd !== null && l.feeUsd !== undefined);
  const totalFees = portfolio?.totalFeesPaidUsd ?? (feeLogs.length > 0 ? feeLogs.reduce((acc, l) => acc + l.feeUsd!, 0.0) : null);
  const notional = portfolio?.totalNotionalInvested ?? logs.reduce((acc, l) => acc + (l.size ?? 0.0), 0.0);
  const feeRate = totalFees !== null && notional > 0 ? (totalFees / notional) * 100 : null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Paper Portfolio Analytics"
      subtitle="Paper mark-to-market performance, win rates & simulated taker fee attribution"
      maxWidth="max-w-2xl"
    >
      <div className="space-y-4 sm:space-y-6">
        {/* 6 Key Quantitative Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 space-y-1">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">{omittedEvidenceCount > 0 ? 'Known-record PnL' : 'Net Return'}</span>
            <div className={`text-lg font-bold font-mono ${totalPnL === null ? 'text-slate-400' : totalPnL >= 0 ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF3B30]'}`}>
              {totalPnL === null ? 'Unavailable' : `${totalPnL >= 0 ? '+' : ''}$${totalPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
            </div>
            <span className="text-[10px] text-slate-400 font-mono">
              {returnPct === null || startBal === null ? (omittedEvidenceCount > 0 ? `Known-record subtotal · ${omittedEvidenceCount} omitted` : 'Coverage unavailable') : `${returnPct >= 0 ? '+' : ''}${returnPct.toFixed(2)}% on $${startBal.toLocaleString()}`}
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 space-y-1">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Win Rate</span>
            <div className="text-lg font-bold text-slate-950 dark:text-white font-mono">
              {winRate === null ? 'Unavailable' : `${winRate.toFixed(1)}%`}
            </div>
            <span className="text-[10px] text-slate-400 font-mono">
              {wins}W - {losses}L ({totalTrades} Fills){omittedEvidenceCount > 0 ? ` · ${omittedEvidenceCount} omitted` : ''}
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 space-y-1">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">{omittedEvidenceCount > 0 ? 'Known-record Fees' : 'Total Fees Paid'}</span>
            <div className="text-lg font-bold text-slate-950 dark:text-white font-mono">
              {totalFees === null ? 'Unavailable' : `$${totalFees.toFixed(2)}`}
            </div>
            <span className="text-[10px] text-slate-400 font-mono">
              {feeRate === null ? (omittedEvidenceCount > 0 ? `${omittedEvidenceCount} omitted` : 'Coverage unavailable') : `${feeRate.toFixed(3)}% Avg Drag`}
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 space-y-1">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Capital Deployed</span>
            <div className="text-lg font-bold text-slate-950 dark:text-white font-mono">
              ${notional.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
            </div>
            <span className="text-[10px] text-slate-400 font-mono">
              {startBal === null ? 'Coverage unavailable' : `Turnover: ${(notional / (startBal || 1)).toFixed(1)}x`}
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 space-y-1">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Execution Model</span>
            <div className="text-lg font-bold text-emerald-600 dark:text-[#00D09C] font-mono">
              Pure Taker
            </div>
            <span className="text-[10px] text-slate-400 font-mono">Polymarket Fee Schedule</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 space-y-1">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Consensus Alpha</span>
            <div className="text-lg font-bold text-indigo-600 dark:text-indigo-400 font-mono">
              +1.5x Sizing
            </div>
            <span className="text-[10px] text-slate-400 font-mono">&ge;2 Whales Aligned</span>
          </div>
        </div>

        {/* Execution Engine Description */}
        <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 space-y-2">
          <h4 className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
            <ShieldCheck size={14} className="text-[#00D09C]" />
            Anti-Frontrunning &amp; Quadratic Execution Guard
          </h4>
          <p className="text-[11px] text-slate-600 dark:text-[#8E8F99] leading-relaxed">
            Baleen monitors Polymarket CLOB orderbook feeds. In paper simulation, executions evaluate slippage (&le; $0.015) and expected edge (&ge; 2.5&times; taker fee) before recording paper fills. All mark-to-market values are backed by database simulation snapshots.
          </p>
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-black/[0.06] dark:border-white/10 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-6 py-2.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black text-xs font-bold hover:bg-slate-800 dark:hover:bg-slate-200 transition-all cursor-pointer shadow-sm"
          >
            Close Analytics
          </button>
        </div>
      </div>
    </Modal>
  );
}
