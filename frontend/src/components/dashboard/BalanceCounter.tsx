'use client';
import { motion, useMotionValue, animate, useTransform } from 'framer-motion';
import { useEffect, useRef } from 'react';
import { Plus, ArrowLeftRight, BarChart2, RotateCcw, TrendingUp, TrendingDown } from 'lucide-react';

interface BalanceCounterProps {
  balance: number | null;
  pnl?: number | null;
  pnlPct?: number | null;
  onResetClick?: () => void;
  onAnalyticsClick?: () => void;
  onRebalanceClick?: () => void;
  onMirrorClick?: () => void;
}

export function BalanceCounter({ 
  balance, 
  pnl, 
  pnlPct, 
  onResetClick,
  onAnalyticsClick,
  onRebalanceClick,
  onMirrorClick
}: BalanceCounterProps) {
  const initialVal = balance ?? 10000.0;
  const motionVal = useMotionValue(initialVal);
  const isFirstMount = useRef(true);

  useEffect(() => {
    if (balance !== null && balance !== undefined) {
      if (isFirstMount.current) {
        motionVal.set(balance);
        isFirstMount.current = false;
      } else {
        const controls = animate(motionVal, balance, {
          duration: 0.4,
          ease: [0.16, 1, 0.3, 1]
        });
        return () => controls.stop();
      }
    }
  }, [balance, motionVal]);

  const displayValue = useTransform(motionVal, (latest) => {
    return `$${Math.max(0, latest).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  });

  const hasPnl = pnl !== undefined && pnl !== null;
  const isPositive = (pnl ?? 0) >= 0;

  return (
    <div className="flex flex-col items-start gap-3 sm:gap-4 select-none w-full">
      {/* Subtitle & Badge */}
      <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-[#8E8F99]">
        <span>Personal · USD</span>
        <span className="w-1 h-1 rounded-full bg-slate-400 dark:bg-[#8E8F99]" aria-hidden="true" />
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold text-slate-700 dark:text-white bg-slate-200/80 dark:bg-[#2C2D35] border border-black/[0.04] dark:border-white/5 shadow-2xs">
          Sandbox
        </span>
      </div>

      {/* Main Authoritative Balance */}
      <div className="flex flex-col sm:flex-row sm:items-baseline gap-2 sm:gap-3" aria-live="polite">
        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-950 dark:text-white font-outfit tabular-nums">
          <motion.span>{displayValue}</motion.span>
        </h1>

        {/* PnL Pill Badge */}
        {hasPnl && (
          <div className={`inline-flex items-center gap-1.5 px-2.5 sm:px-3 py-0.5 sm:py-1 rounded-full text-[11px] sm:text-xs font-bold font-mono tabular-nums ${
            isPositive 
              ? 'text-emerald-700 dark:text-[#00D09C] bg-emerald-50 dark:bg-[#00D09C]/10 border border-emerald-200 dark:border-[#00D09C]/20' 
              : 'text-rose-700 dark:text-[#FF453A] bg-rose-50 dark:bg-[#FF453A]/10 border border-rose-200 dark:border-[#FF453A]/20'
          }`}>
            {isPositive ? <TrendingUp size={12} aria-hidden="true" /> : <TrendingDown size={12} aria-hidden="true" />}
            <span>
              {isPositive ? '+' : ''}${pnl?.toFixed(2)} ({isPositive ? '+' : ''}{pnlPct?.toFixed(2)}%) · All time
            </span>
          </div>
        )}
      </div>

      {/* 4-Action Circular Button Row */}
      <div className="flex items-center justify-between sm:justify-start gap-3 sm:gap-6 pt-1 sm:pt-2 w-full max-w-sm sm:max-w-none">
        {/* Action 1: Mirror / Add */}
        <div className="flex flex-col items-center gap-1.5">
          <button
            onClick={onMirrorClick}
            aria-label="Mirror top Polymarket whales"
            className="w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 flex items-center justify-center transition-all cursor-pointer shadow-xs dark:shadow-lg active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] focus-visible:ring-offset-2 focus-visible:ring-offset-[#F8F9FB] dark:focus-visible:ring-offset-black"
          >
            <Plus size={20} className="text-slate-800 dark:text-white" aria-hidden="true" />
          </button>
          <span className="text-[11px] sm:text-xs font-semibold text-slate-700 dark:text-white/90">Mirror</span>
        </div>

        {/* Action 2: Move / Rebalance */}
        <div className="flex flex-col items-center gap-1.5">
          <button
            onClick={onRebalanceClick}
            aria-label="Rebalance basket allocation"
            className="w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 flex items-center justify-center transition-all cursor-pointer shadow-xs dark:shadow-lg active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] focus-visible:ring-offset-2 focus-visible:ring-offset-[#F8F9FB] dark:focus-visible:ring-offset-black"
          >
            <ArrowLeftRight size={18} className="text-slate-800 dark:text-white" aria-hidden="true" />
          </button>
          <span className="text-[11px] sm:text-xs font-semibold text-slate-700 dark:text-white/90">Rebalance</span>
        </div>

        {/* Action 3: Analytics */}
        <div className="flex flex-col items-center gap-1.5">
          <button
            onClick={onAnalyticsClick}
            aria-label="View portfolio analytics"
            className="w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 flex items-center justify-center transition-all cursor-pointer shadow-xs dark:shadow-lg active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] focus-visible:ring-offset-2 focus-visible:ring-offset-[#F8F9FB] dark:focus-visible:ring-offset-black"
          >
            <BarChart2 size={18} className="text-slate-800 dark:text-white" aria-hidden="true" />
          </button>
          <span className="text-[11px] sm:text-xs font-semibold text-slate-700 dark:text-white/90">Analytics</span>
        </div>

        {/* Action 4: Reset */}
        {onResetClick && (
          <div className="flex flex-col items-center gap-1.5">
            <button
              onClick={onResetClick}
              aria-label="Reset sandbox balance"
              className="w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-rose-50 dark:hover:bg-rose-950/40 border border-black/[0.08] dark:border-white/10 flex items-center justify-center transition-all cursor-pointer shadow-xs dark:shadow-lg active:scale-95 hover:border-rose-500/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] focus-visible:ring-offset-2 focus-visible:ring-offset-[#F8F9FB] dark:focus-visible:ring-offset-black"
            >
              <RotateCcw size={17} className="text-slate-600 dark:text-white/80" aria-hidden="true" />
            </button>
            <span className="text-[11px] sm:text-xs font-semibold text-slate-700 dark:text-white/90">Reset</span>
          </div>
        )}
      </div>
    </div>
  );
}
