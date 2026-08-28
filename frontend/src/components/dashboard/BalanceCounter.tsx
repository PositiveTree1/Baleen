'use client';
import { motion, useMotionValue, animate, useTransform } from 'framer-motion';
import { useEffect, useState, useRef } from 'react';
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
    <div className="flex flex-col items-center sm:items-start gap-4 select-none w-full">
      {/* Subtitle & Badge */}
      <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-[#8E8F99]">
        <span>Personal · USD</span>
        <span className="w-1 h-1 rounded-full bg-slate-400 dark:bg-[#8E8F99]" />
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold text-slate-700 dark:text-white bg-slate-200/80 dark:bg-[#2C2D35] border border-black/[0.04] dark:border-white/5 shadow-2xs">
          Sandbox
        </span>
      </div>

      {/* Main Authoritative Balance */}
      <div className="flex flex-col sm:flex-row sm:items-baseline gap-3">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-950 dark:text-white font-outfit">
          <motion.span>{displayValue}</motion.span>
        </h1>

        {/* PnL Pill Badge */}
        {hasPnl && (
          <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold font-mono ${
            isPositive 
              ? 'text-emerald-700 dark:text-[#00D09C] bg-emerald-50 dark:bg-[#00D09C]/10 border border-emerald-200 dark:border-[#00D09C]/20' 
              : 'text-rose-700 dark:text-[#FF453A] bg-rose-50 dark:bg-[#FF453A]/10 border border-rose-200 dark:border-[#FF453A]/20'
          }`}>
            {isPositive ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
            <span>
              {isPositive ? '+' : ''}${pnl?.toFixed(2)} ({isPositive ? '+' : ''}{pnlPct?.toFixed(2)}%) · All time
            </span>
          </div>
        )}
      </div>

      {/* Revolut 4-Action Circular Button Row */}
      <div className="flex items-center justify-center sm:justify-start gap-5 sm:gap-6 pt-2">
        {/* Action 1: Mirror / Add */}
        <div className="flex flex-col items-center gap-1.5">
          <button
            onClick={onMirrorClick}
            className="revolut-circle-btn cursor-pointer shadow-xs dark:shadow-lg"
            title="Mirror Top Polymarket Whales"
          >
            <Plus size={22} className="text-slate-800 dark:text-white" />
          </button>
          <span className="text-xs font-semibold text-slate-700 dark:text-white/90">Mirror</span>
        </div>

        {/* Action 2: Move / Rebalance */}
        <div className="flex flex-col items-center gap-1.5">
          <button
            onClick={onRebalanceClick}
            className="revolut-circle-btn cursor-pointer shadow-xs dark:shadow-lg"
            title="Rebalance Basket Allocation"
          >
            <ArrowLeftRight size={20} className="text-slate-800 dark:text-white" />
          </button>
          <span className="text-xs font-semibold text-slate-700 dark:text-white/90">Rebalance</span>
        </div>

        {/* Action 3: Analytics */}
        <div className="flex flex-col items-center gap-1.5">
          <button
            onClick={onAnalyticsClick}
            className="revolut-circle-btn cursor-pointer shadow-xs dark:shadow-lg"
            title="View Portfolio Analytics"
          >
            <BarChart2 size={20} className="text-slate-800 dark:text-white" />
          </button>
          <span className="text-xs font-semibold text-slate-700 dark:text-white/90">Analytics</span>
        </div>

        {/* Action 4: Reset */}
        {onResetClick && (
          <div className="flex flex-col items-center gap-1.5">
            <button
              onClick={onResetClick}
              className="revolut-circle-btn cursor-pointer shadow-xs dark:shadow-lg hover:border-rose-500/40"
              title="Reset Sandbox Balance"
            >
              <RotateCcw size={19} className="text-slate-600 dark:text-white/80" />
            </button>
            <span className="text-xs font-semibold text-slate-700 dark:text-white/90">Reset</span>
          </div>
        )}
      </div>
    </div>
  );
}
