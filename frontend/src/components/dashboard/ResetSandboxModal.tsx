'use client';
import { useState } from 'react';
import { resetSandboxAmount, clearAllCache } from '@/lib/api-client';
import { RotateCcw, Check, ShieldAlert } from 'lucide-react';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';

export interface ResetSandboxModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId?: string;
  currentBalance: number | null;
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
  onComplete,
}: ResetSandboxModalProps) {
  const [selectedAmount, setSelectedAmount] = useState<number>(10000);
  const [customAmount, setCustomAmount] = useState<string>('10000');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

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
        if (typeof window !== 'undefined') {
          window.location.reload();
        }
      }, 500);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Start a New Paper Run"
      subtitle="Archive this run and choose starting capital for the next one"
      maxWidth="max-w-md"
    >
      <div className="space-y-5">
        {/* Current Balance Notice */}
        <div className="p-3.5 rounded-2xl glass-card flex items-center justify-between text-xs font-mono">
          <span className="text-slate-500 dark:text-[#8E8F99]">Current Balance:</span>
          <span className="font-bold text-slate-900 dark:text-white">
            {currentBalance == null ? 'Unavailable' : `$${currentBalance.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          </span>
        </div>

        {/* Quick Presets */}
        <div>
          <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-[#8E8F99] block mb-2">
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
                  className={`p-2.5 rounded-xl font-mono text-xs font-bold transition-all border cursor-pointer ${
                    isSelected
                      ? 'glass-button text-white shadow-xs'
                      : 'bg-white/[0.06] text-slate-300 hover:text-white border-white/10 hover:bg-white/10'
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
          <label htmlFor="custom-sandbox-amount" className="text-xs font-bold uppercase tracking-wider text-slate-400 block mb-1.5">
            Or Custom USD Amount
          </label>
          <div className="relative">
            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 font-mono font-bold text-sm">
              $
            </span>
            <input
              id="custom-sandbox-amount"
              type="number"
              min="20"
              max="1000000"
              step="100"
              value={customAmount}
              aria-label="Custom USD Amount"
              onChange={(e) => handleCustomChange(e.target.value)}
              className="w-full pl-8 pr-4 py-2.5 rounded-xl border border-white/15 font-mono text-sm font-bold text-white bg-white/[0.06] focus:outline-none focus:border-sky-400/60 focus:ring-2 focus:ring-sky-400/20 placeholder:text-slate-400 backdrop-blur-md"
              placeholder="10000"
            />
          </div>
        </div>

        {/* Info Callout */}
        <div className="p-3 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-start gap-2.5 text-xs text-amber-200">
          <ShieldAlert size={16} className="text-amber-400 shrink-0 mt-0.5" />
          <p className="leading-relaxed text-[11px]">
            This archives the current paper run and starts a new run with the selected capital. Archived fills remain available for audit; no live or global account data is changed.
          </p>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/10">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="glass-button px-4 py-2 rounded-xl text-xs text-slate-300 hover:text-white"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={loading || !selectedAmount}
            className="glass-button px-5 py-2.5 rounded-xl text-white text-xs flex items-center gap-2 font-bold cursor-pointer shadow-md"
          >
            {loading ? (
              <>
                <RotateCcw size={14} className="animate-spin text-[#00D09C]" />
                <span>Resetting...</span>
              </>
            ) : success ? (
              <>
                <Check size={14} className="text-[#00D09C]" />
                <span>New Run Started!</span>
              </>
            ) : (
              <>
                <RotateCcw size={14} />
                <span>Start Run at ${selectedAmount.toLocaleString()}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </Modal>
  );
}
