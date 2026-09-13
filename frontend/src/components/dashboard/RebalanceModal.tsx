'use client';
import { useState } from 'react';
import { ArrowLeftRight, CheckCircle2, Sliders, RefreshCw, ShieldCheck, Zap } from 'lucide-react';
import { Modal } from '../ui/Modal';

export interface RebalanceModalProps {
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
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Portfolio Capital Rebalancer"
      subtitle="Simulate paper weight allocation across candidate whale indexers"
      maxWidth="max-w-lg"
    >
      <div className="space-y-4 sm:space-y-6">
        {/* Rebalancing Strategies */}
        <div className="space-y-2.5" role="radiogroup" aria-label="Rebalancing Algorithm">
          <label className="text-xs font-semibold text-slate-500 dark:text-[#8E8F99] uppercase tracking-wider">
            Rebalancing Algorithm
          </label>

          <div
            role="radio"
            aria-checked={strategy === 'pnl_weighted'}
            tabIndex={0}
            onClick={() => setStrategy('pnl_weighted')}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setStrategy('pnl_weighted');
              }
            }}
            className={`p-4 rounded-2xl border transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-indigo-500 ${
              strategy === 'pnl_weighted'
                ? 'bg-slate-50 dark:bg-[#1C1D22] border-indigo-500 shadow-sm'
                : 'border-black/[0.06] dark:border-white/10 hover:border-black/20 dark:hover:border-white/20'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Sliders size={16} className={strategy === 'pnl_weighted' ? 'text-indigo-500' : 'text-slate-400'} />
                <span className="text-sm font-bold text-slate-900 dark:text-white">PnL-Weighted Dynamic Tilt</span>
              </div>
              {strategy === 'pnl_weighted' && <CheckCircle2 size={16} className="text-indigo-500" />}
            </div>
            <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-1 pl-6.5">
              Whales with higher 30-day realized profits receive proportionally higher position allocations.
            </p>
          </div>

          <div
            role="radio"
            aria-checked={strategy === 'winrate_weighted'}
            tabIndex={0}
            onClick={() => setStrategy('winrate_weighted')}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setStrategy('winrate_weighted');
              }
            }}
            className={`p-4 rounded-2xl border transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-indigo-500 ${
              strategy === 'winrate_weighted'
                ? 'bg-slate-50 dark:bg-[#1C1D22] border-indigo-500 shadow-sm'
                : 'border-black/[0.06] dark:border-white/10 hover:border-black/20 dark:hover:border-white/20'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <ShieldCheck size={16} className={strategy === 'winrate_weighted' ? 'text-indigo-500' : 'text-slate-400'} />
                <span className="text-sm font-bold text-slate-900 dark:text-white">Consistency / Winrate Bias</span>
              </div>
              {strategy === 'winrate_weighted' && <CheckCircle2 size={16} className="text-indigo-500" />}
            </div>
            <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-1 pl-6.5">
              Maximizes trade frequency of high-probability snipers (Win rate &gt; 70%) to minimize drawdown.
            </p>
          </div>

          <div
            role="radio"
            aria-checked={strategy === 'equal'}
            tabIndex={0}
            onClick={() => setStrategy('equal')}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setStrategy('equal');
              }
            }}
            className={`p-4 rounded-2xl border transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-indigo-500 ${
              strategy === 'equal'
                ? 'bg-slate-50 dark:bg-[#1C1D22] border-indigo-500 shadow-sm'
                : 'border-black/[0.06] dark:border-white/10 hover:border-black/20 dark:hover:border-white/20'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Zap size={16} className={strategy === 'equal' ? 'text-indigo-500' : 'text-slate-400'} />
                <span className="text-sm font-bold text-slate-900 dark:text-white">Equal Sizing (1 / N)</span>
              </div>
              {strategy === 'equal' && <CheckCircle2 size={16} className="text-indigo-500" />}
            </div>
            <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-1 pl-6.5">
              Distributes capital equally across all active wallets without quantitative weighting.
            </p>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="pt-3 border-t border-black/[0.06] dark:border-white/10 flex justify-between items-center">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2.5 rounded-full text-slate-500 dark:text-[#8E8F99] text-xs font-semibold hover:text-slate-900 dark:hover:text-white transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleExecute}
            disabled={isExecuting || success}
            className="px-6 py-2.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black text-xs font-bold hover:bg-slate-800 dark:hover:bg-slate-200 transition-all cursor-pointer flex items-center gap-1.5 shadow-sm disabled:opacity-50"
          >
            {isExecuting && <RefreshCw size={13} className="animate-spin" />}
            {success ? '✓ Paper Weights Updated!' : 'Update Paper Weights'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
