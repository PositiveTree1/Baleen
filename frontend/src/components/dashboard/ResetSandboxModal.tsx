'use client';
import { useState } from 'react';
import { resetSandboxAmount, clearAllCache } from '@/lib/api-client';
import { motion, AnimatePresence } from 'framer-motion';
import { RotateCcw, X, DollarSign, Check, AlertCircle, ShieldAlert, Sparkles } from 'lucide-react';
import { Button } from '../ui/Button';

interface ResetSandboxModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId?: string;
  currentBalance: number;
  onResetComplete: () => void;
}

const PRESETS = [500, 1000, 5000, 10000, 25000];

export function ResetSandboxModal({
  isOpen,
  onClose,
  userId,
  currentBalance,
  onResetComplete
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
        onResetComplete();
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
          className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm"
        />

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          className="relative w-full max-w-md bg-white rounded-3xl p-6 shadow-2xl border border-black/[0.08] overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-black/[0.06]">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-2xl bg-amber-50 text-amber-700 flex items-center justify-center border border-amber-200">
                <RotateCcw size={18} />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Reset Sandbox Capital</h3>
                <p className="text-xs text-slate-500">Restart your paper trading simulation</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          {/* Body */}
          <div className="py-5 space-y-5">
            {/* Current Balance Notice */}
            <div className="p-3.5 rounded-2xl bg-slate-50 border border-black/[0.06] flex items-center justify-between text-xs font-mono">
              <span className="text-slate-500">Current Balance:</span>
              <span className="font-bold text-slate-900">${currentBalance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            </div>

            {/* Quick Presets */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-2">
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
                          ? 'bg-slate-950 text-white border-slate-950 shadow-md'
                          : 'bg-white text-slate-700 hover:bg-slate-50 border-black/[0.08]'
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
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-1.5">
                Or Custom USD Amount
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 font-mono font-bold text-sm">$</span>
                <input
                  type="number"
                  min="20"
                  max="1000000"
                  step="100"
                  value={customAmount}
                  onChange={(e) => handleCustomChange(e.target.value)}
                  className="w-full pl-8 pr-4 py-2.5 rounded-xl border border-black/[0.1] font-mono text-sm font-bold text-slate-900 bg-white focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                  placeholder="10000"
                />
              </div>
            </div>

            {/* Info Callout */}
            <div className="p-3 rounded-2xl bg-amber-50/70 border border-amber-200/80 flex items-start gap-2.5 text-xs text-amber-900">
              <ShieldAlert size={16} className="text-amber-700 shrink-0 mt-0.5" />
              <p className="leading-relaxed text-[11px]">
                Resetting will clear past paper fills, reset your Mark-to-Market high-water mark, and initialize a fresh performance curve.
              </p>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-black/[0.06]">
            <Button
              variant="secondary"
              onClick={onClose}
              disabled={loading}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleConfirm}
              disabled={loading || !selectedAmount}
              className="bg-slate-950 hover:bg-slate-800 text-white text-xs flex items-center gap-2"
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
