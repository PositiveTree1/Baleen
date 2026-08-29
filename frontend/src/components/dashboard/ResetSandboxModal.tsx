'use client';
import { useState } from 'react';
import { resetSandboxAmount, clearAllCache } from '@/lib/api-client';
import { motion, AnimatePresence } from 'framer-motion';
import { RotateCcw, X, Check, ShieldAlert } from 'lucide-react';
import { Button } from '../ui/Button';

interface ResetSandboxModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId?: string;
  currentBalance: number;
  onResetComplete?: () => void;
  onComplete?: () => void;
}

const PRESETS = [500, 1000, 5000, 10000, 25000];

export function ResetSandboxModal({
  isOpen,
  onClose,
  userId,
  currentBalance,
  onResetComplete,
  onComplete
}: ResetSandboxModalProps) {
  const [selectedAmount, setSelectedAmount] = useState<number>(10000);
  const [customAmount, setCustomAmount] = useState<string>('10000');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handlePreset = (amount: number) => {
    setSelectedAmount(amount);
    setCustomAmount(amount.toString());
  };

  const handleCustomChange = (val: string) => {
    setCustomAmount(val);
    const num = parseFloat(val);
    if (!isNaN(num) && num > 0) {
      setSelectedAmount(num);
    }
  };

  const handleConfirm = async () => {
    const finalAmount = parseFloat(customAmount) || selectedAmount || 10000;
    if (finalAmount <= 0) return;

    setLoading(true);
    const ok = await resetSandboxAmount(userId, finalAmount);
    setLoading(false);

    if (ok) {
      clearAllCache();
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        if (onResetComplete) onResetComplete();
        if (onComplete) onComplete();
        onClose();
        window.location.reload();
      }, 500);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-slate-950/60 dark:bg-black/80 backdrop-blur-sm"
        />

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          className="relative w-full max-w-md bg-white dark:bg-[#16171B] rounded-3xl p-6 shadow-2xl border border-black/[0.08] dark:border-white/10 overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-black/[0.06] dark:border-white/10">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-2xl bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 flex items-center justify-center border border-amber-200 dark:border-amber-500/20">
                <RotateCcw size={18} />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">Reset Sandbox Capital</h3>
                <p className="text-xs text-slate-500 dark:text-zinc-400">Restart your paper trading simulation</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 dark:text-zinc-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-[#1C1D22] transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          {/* Body */}
          <div className="py-5 space-y-5">
            {/* Current Balance Notice */}
            <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/10 flex items-center justify-between text-xs font-mono">
              <span className="text-slate-500 dark:text-zinc-400">Current Balance:</span>
              <span className="font-bold text-slate-900 dark:text-white">${currentBalance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            </div>

            {/* Quick Presets */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400 block mb-2">
                Select Starting Capital
              </label>
              <div className="grid grid-cols-3 gap-2">
                {PRESETS.map((amount) => {
                  const isSelected = selectedAmount === amount;
                  return (
                    <button
                      key={amount}
                      type="button"
                      onClick={() => handlePreset(amount)}
                      className={`p-2.5 rounded-xl font-mono text-xs font-bold transition-all border ${
                        isSelected
                          ? 'bg-slate-950 dark:bg-white text-white dark:text-slate-950 border-slate-950 dark:border-white shadow-md'
                          : 'bg-white dark:bg-[#1C1D22] text-slate-700 dark:text-zinc-300 hover:bg-slate-50 dark:hover:bg-[#25262C] border-black/[0.08] dark:border-zinc-700'
                      }`}
                    >
                      ${amount.toLocaleString()}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Custom Amount Input */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-zinc-400 block mb-1.5">
                Or Custom USD Amount
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-zinc-500 font-mono font-bold text-sm">$</span>
                <input
                  type="number"
                  min="20"
                  max="1000000"
                  step="100"
                  value={customAmount}
                  onChange={(e) => handleCustomChange(e.target.value)}
                  className="w-full pl-8 pr-4 py-2.5 rounded-xl border border-black/[0.1] dark:border-zinc-700 font-mono text-sm font-bold text-slate-900 dark:text-white bg-white dark:bg-[#1C1D22] focus:outline-none focus:border-indigo-500 dark:focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 dark:focus:ring-indigo-900/30 placeholder:text-slate-400 dark:placeholder:text-zinc-500"
                  placeholder="10000"
                />
              </div>
            </div>

            {/* Info Callout */}
            <div className="p-3 rounded-2xl bg-amber-50/70 dark:bg-amber-500/10 border border-amber-200/80 dark:border-amber-500/20 flex items-start gap-2.5 text-xs text-amber-900 dark:text-amber-300">
              <ShieldAlert size={16} className="text-amber-700 dark:text-amber-400 shrink-0 mt-0.5" />
              <p className="leading-relaxed text-[11px]">
                Resetting will clear past paper fills, reset your Mark-to-Market high-water mark, and initialize a fresh performance curve.
              </p>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-black/[0.06] dark:border-white/10">
            <Button
              variant="secondary"
              onClick={onClose}
              disabled={loading}
              className="text-xs dark:bg-[#1C1D22] dark:text-zinc-300 dark:border-zinc-700 dark:hover:bg-[#25262C]"
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleConfirm}
              disabled={loading || !selectedAmount}
              className="bg-slate-950 hover:bg-slate-800 dark:bg-white dark:hover:bg-zinc-200 text-white dark:text-slate-950 text-xs flex items-center gap-2 font-bold dark:border-transparent"
            >
              {loading ? (
                <>
                  <RotateCcw size={14} className="animate-spin" />
                  <span>Resetting...</span>
                </>
              ) : success ? (
                <>
                  <Check size={14} className="text-emerald-400" />
                  <span>Reset Complete!</span>
                </>
              ) : (
                <>
                  <RotateCcw size={14} />
                  <span>Reset to ${selectedAmount.toLocaleString()}</span>
                </>
              )}
            </Button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
