'use client';
import { motion, AnimatePresence } from 'framer-motion';
import { X, BarChart2, TrendingUp, ShieldCheck, Zap, Layers, Award, Clock, DollarSign, Activity } from 'lucide-react';
import { ExecutionLog, PortfolioSummary } from '@/types';

interface DeepAnalyticsModalProps {
  isOpen: boolean;
  onClose: () => void;
  portfolio: PortfolioSummary | null;
  logs: ExecutionLog[];
}

export function DeepAnalyticsModal({ isOpen, onClose, portfolio, logs }: DeepAnalyticsModalProps) {
  if (!isOpen) return null;

  const totalTrades = portfolio?.filledTradesCount ?? logs.length;
  const wins = portfolio?.allTimeWins ?? logs.filter(l => (l.pnl ?? 0) > 0).length;
  const losses = portfolio?.allTimeLosses ?? logs.filter(l => (l.pnl ?? 0) < 0).length;
  const evaluated = wins + losses;
  const winRate = portfolio?.allTimeWinRate ?? (evaluated > 0 ? (wins / evaluated) * 100 : 0.0);
  const totalPnL = portfolio?.totalPnlUsd ?? logs.reduce((acc, l) => acc + (l.pnl ?? 0.0), 0.0);
  const startBal = portfolio?.startingBalance ?? 10000.0;
  const returnPct = startBal > 0 ? (totalPnL / startBal) * 100 : 0.0;
  const totalFees = portfolio?.totalFeesPaidUsd ?? logs.reduce((acc, l) => acc + (l.feeUsd || 0.0), 0.0);
  const notional = portfolio?.totalNotionalInvested ?? logs.reduce((acc, l) => acc + (l.size ?? 0.0), 0.0);
  const feeRate = notional > 0 ? (totalFees / notional) * 100 : 0.0;

  return (
    <div className="fixed inset-0 bg-black/60 dark:bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-3 sm:p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        className="revolut-card bg-white dark:bg-[#16171B] border border-black/10 dark:border-white/10 p-4 sm:p-7 rounded-[22px] sm:rounded-[28px] max-w-2xl w-full space-y-4 sm:space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-black/[0.06] dark:border-white/10 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <BarChart2 size={20} />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-950 dark:text-white">Authoritative Portfolio Analytics</h3>
              <p className="text-xs text-slate-500 dark:text-[#8E8F99]">Mark-to-market performance, win rates &amp; taker fee attribution</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-full text-slate-400 dark:text-[#8E8F99] hover:bg-slate-100 dark:hover:bg-[#1C1D22] transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* 6 Key Quantitative Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 space-y-1">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Net Return</span>
            <div className={`text-lg font-bold font-mono ${totalPnL >= 0 ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF3B30]'}`}>
              {totalPnL >= 0 ? '+' : ''}${totalPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <span className="text-[10px] text-slate-400 font-mono">
              {returnPct >= 0 ? '+' : ''}{returnPct.toFixed(2)}% on ${startBal.toLocaleString()}
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 space-y-1">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Historical Win Rate</span>
            <div className="text-lg font-bold text-slate-950 dark:text-white font-mono">
              {winRate.toFixed(1)}%
            </div>
            <span className="text-[10px] text-slate-400 font-mono">{wins}W / {losses}L</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 space-y-1">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Total Executions</span>
            <div className="text-lg font-bold text-slate-950 dark:text-white font-mono">
              {totalTrades.toLocaleString()}
            </div>
            <span className="text-[10px] text-slate-400 font-mono">CLOB Fills</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 space-y-1">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Notional Traded</span>
            <div className="text-lg font-bold text-slate-950 dark:text-white font-mono">
              ${notional.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </div>
            <span className="text-[10px] text-slate-400 font-mono">Aggregate Volume</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 space-y-1">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Taker Fees Paid</span>
            <div className="text-lg font-bold text-slate-950 dark:text-white font-mono">
              ${totalFees.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
            <span className="text-[10px] text-slate-400 font-mono">{feeRate.toFixed(2)}% Avg Fee</span>
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
            Baleen monitors Polymarket CLOB liquidity in real-time. When a copied whale executes, Baleen verifies that live slippage is $\le \$0.015$ (1.5 cents) and expected edge is $\ge 2.5\times$ taker fee. All mark-to-market values are backed by authoritative database snapshots.
          </p>
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-black/[0.06] dark:border-white/10 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black text-xs font-bold hover:bg-slate-800 dark:hover:bg-slate-200 transition-all cursor-pointer shadow-sm"
          >
            Close Analytics
          </button>
        </div>
      </motion.div>
    </div>
  );
}
