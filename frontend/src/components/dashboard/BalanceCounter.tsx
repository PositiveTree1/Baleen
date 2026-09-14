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
  const initialVal = balance ?? 0.0;
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
    <div className="glass-card p-5 sm:p-7 rounded-[28px] border border-sky-100/80 dark:border-white/10 shadow-sm flex flex-col items-start gap-3 sm:gap-4 select-none w-full">
      {/* Subtitle & Badge */}
      <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
        <span>Personal · USD</span>
        <span className="w-1 h-1 rounded-full bg-slate-400" aria-hidden="true" />
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold text-white bg-white/10 border border-white/20 shadow-2xs">
          Sandbox
        </span>
      </div>

      {/* Main Authoritative Balance */}
      <div className="flex flex-col sm:flex-row sm:items-baseline gap-2 sm:gap-3" aria-live="polite">
        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-white font-outfit tabular-nums">
          {balance === null || balance === undefined ? <span>Unavailable</span> : <motion.span>{displayValue}</motion.span>}
        </h1>

        {/* PnL Pill Badge */}
        {hasPnl && (
          <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] sm:text-xs font-bold font-mono tabular-nums border shadow-2xs ${
            isPositive 
              ? 'text-emerald-400 bg-emerald-500/10 border-emerald-400/30' 
              : 'text-rose-400 bg-rose-500/10 border-rose-400/30'
          }`}>
            {isPositive ? <TrendingUp size={12} aria-hidden="true" /> : <TrendingDown size={12} aria-hidden="true" />}
            <span>
              {isPositive ? '+' : ''}${pnl?.toFixed(2)} ({isPositive ? '+' : ''}{pnlPct?.toFixed(2)}%) · All time
            </span>
          </div>
        )}
      </div>

      {/* 4-Action Circular Button Row with Fluid Spring Physics */}
      <div className="flex items-center justify-between sm:justify-start gap-4 sm:gap-7 pt-2 w-full max-w-sm sm:max-w-none">
        {/* Action 1: Mirror / Add */}
        <div className="flex flex-col items-center gap-1.5">
          <motion.button
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.94 }}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            onClick={onMirrorClick}
            aria-label="Mirror top Polymarket whales"
            className="w-12 h-12 sm:w-14 sm:h-14 rounded-full glass-button flex items-center justify-center cursor-pointer shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0284C7] focus-visible:ring-offset-2"
          >
            <Plus size={20} className="text-white" aria-hidden="true" />
          </motion.button>
          <span className="text-[11px] sm:text-xs font-bold text-slate-200">Mirror</span>
        </div>

        {/* Action 2: Move / Rebalance */}
        <div className="flex flex-col items-center gap-1.5">
          <motion.button
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.94 }}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            onClick={onRebalanceClick}
            aria-label="Rebalance basket allocation"
            className="w-12 h-12 sm:w-14 sm:h-14 rounded-full glass-button flex items-center justify-center cursor-pointer shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0284C7] focus-visible:ring-offset-2"
          >
            <ArrowLeftRight size={18} className="text-white" aria-hidden="true" />
          </motion.button>
          <span className="text-[11px] sm:text-xs font-bold text-slate-200">Rebalance</span>
        </div>

        {/* Action 3: Analytics */}
        <div className="flex flex-col items-center gap-1.5">
          <motion.button
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.94 }}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            onClick={onAnalyticsClick}
            aria-label="View portfolio analytics"
            className="w-12 h-12 sm:w-14 sm:h-14 rounded-full glass-button flex items-center justify-center cursor-pointer shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0284C7] focus-visible:ring-offset-2"
          >
            <BarChart2 size={18} className="text-white" aria-hidden="true" />
          </motion.button>
          <span className="text-[11px] sm:text-xs font-bold text-slate-200">Analytics</span>
        </div>

        {/* Action 4: Reset */}
        {onResetClick && (
          <div className="flex flex-col items-center gap-1.5">
            <motion.button
              whileHover={{ scale: 1.08 }}
              whileTap={{ scale: 0.94 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}
              onClick={onResetClick}
              aria-label="Reset sandbox balance"
              className="w-12 h-12 sm:w-14 sm:h-14 rounded-full glass-button hover:bg-rose-950/40 hover:border-rose-400/50 flex items-center justify-center cursor-pointer shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500 focus-visible:ring-offset-2"
            >
              <RotateCcw size={17} className="text-slate-300 hover:text-rose-400" aria-hidden="true" />
            </motion.button>
            <span className="text-[11px] sm:text-xs font-bold text-slate-200">Reset</span>
          </div>
        )}
      </div>
    </div>
  );
}
