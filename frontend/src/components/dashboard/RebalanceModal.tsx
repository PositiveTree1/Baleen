'use client';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ArrowLeftRight, CheckCircle2, Sliders, RefreshCw, ShieldCheck, Zap } from 'lucide-react';

interface RebalanceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRebalanceExecute?: () => void;
}

export function RebalanceModal({ isOpen, onClose, onRebalanceExecute }: RebalanceModalProps) {
  const [strategy, setStrategy] = useState<'equal' | 'pnl_weighted' | 'winrate_weighted'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('baleen_rebalance_strategy');
      if (saved === 'equal' || saved === 'pnl_weighted' || saved === 'winrate_weighted') return saved;
    }
    return 'pnl_weighted';
  });
  const [isExecuting, setIsExecuting] = useState(false);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleExecute = () => {
    setIsExecuting(true);
    if (typeof window !== 'undefined') {
      localStorage.setItem('baleen_rebalance_strategy', strategy);
    }
    setTimeout(() => {
      setIsExecuting(false);
      setSuccess(true);
      if (onRebalanceExecute) onRebalanceExecute();
      setTimeout(() => {
        setSuccess(false);
        onClose();
      }, 1200);
    }, 1000);
  };

  return (
    <div className="fixed inset-0 bg-black/60 dark:bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-3 sm:p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        className="revolut-card bg-white dark:bg-[#16171B] border border-black/10 dark:border-white/10 p-4 sm:p-7 rounded-[22px] sm:rounded-[28px] max-w-lg w-full space-y-4 sm:space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-black/[0.06] dark:border-white/10 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 flex items-center justify-center text-emerald-600 dark:text-[#00D09C]">
              <ArrowLeftRight size={20} />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-950 dark:text-white">Portfolio Capital Rebalancer</h3>
              <p className="text-xs text-slate-500 dark:text-[#8E8F99]">Re-allocate stake weights across active whale indexers</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-full text-slate-400 dark:text-[#8E8F99] hover:bg-slate-100 dark:hover:bg-[#1C1D22] transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Rebalancing Strategies */}
        <div className="space-y-2.5">
          <label className="text-xs font-semibold text-slate-500 dark:text-[#8E8F99] uppercase tracking-wider">
            Rebalancing Algorithm
          </label>

          <div
            onClick={() => setStrategy('pnl_weighted')}
            className={`p-4 rounded-2xl border transition-all cursor-pointer ${
              strategy === 'pnl_weighted'
                ? 'bg-slate-50 dark:bg-[#1C1D22] border-indigo-500 shadow-sm'
                : 'bg-white dark:bg-[#16171B] border-black/[0.06] dark:border-white/5 hover:border-black/20'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900 dark:text-white">📈 Alpha / PnL Weighted (Recommended)</span>
              {strategy === 'pnl_weighted' && <CheckCircle2 size={16} className="text-[#00D09C]" />}
            </div>
            <p className="text-[11px] text-slate-500 dark:text-[#8E8F99] mt-1 leading-relaxed">
              Allocates higher cash sizing to top-earning whales while reducing stakes on lower alpha accounts.
            </p>
          </div>

          <div
            onClick={() => setStrategy('winrate_weighted')}
            className={`p-4 rounded-2xl border transition-all cursor-pointer ${
              strategy === 'winrate_weighted'
                ? 'bg-slate-50 dark:bg-[#1C1D22] border-indigo-500 shadow-sm'
                : 'bg-white dark:bg-[#16171B] border-black/[0.06] dark:border-white/5 hover:border-black/20'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900 dark:text-white">🎯 Win-Rate Weighted</span>
              {strategy === 'winrate_weighted' && <CheckCircle2 size={16} className="text-[#00D09C]" />}
            </div>
            <p className="text-[11px] text-slate-500 dark:text-[#8E8F99] mt-1 leading-relaxed">
              Favors high consistency snipers with &gt;75% historical win rates to minimize drawdown.
            </p>
          </div>

          <div
            onClick={() => setStrategy('equal')}
            className={`p-4 rounded-2xl border transition-all cursor-pointer ${
              strategy === 'equal'
                ? 'bg-slate-50 dark:bg-[#1C1D22] border-indigo-500 shadow-sm'
                : 'bg-white dark:bg-[#16171B] border-black/[0.06] dark:border-white/5 hover:border-black/20'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900 dark:text-white">⚖️ Equal Weight (1/N)</span>
              {strategy === 'equal' && <CheckCircle2 size={16} className="text-[#00D09C]" />}
            </div>
            <p className="text-[11px] text-slate-500 dark:text-[#8E8F99] mt-1 leading-relaxed">
              Distributes capital evenly across all active index whales without bias.
            </p>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="pt-3 border-t border-black/[0.06] dark:border-white/10 flex justify-between items-center">
          <button
            onClick={onClose}
            className="px-4 py-2.5 rounded-full text-slate-500 dark:text-[#8E8F99] text-xs font-semibold hover:text-slate-900 dark:hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleExecute}
            disabled={isExecuting || success}
            className="px-6 py-2.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black text-xs font-bold hover:bg-slate-800 dark:hover:bg-slate-200 transition-all cursor-pointer flex items-center gap-1.5 shadow-sm disabled:opacity-50"
          >
            {isExecuting && <RefreshCw size={13} className="animate-spin" />}
            {success ? '✓ Portfolio Rebalanced!' : 'Execute Rebalance'}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
