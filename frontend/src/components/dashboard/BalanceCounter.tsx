'use client';
import { motion, useMotionValue, animate, useTransform } from 'framer-motion';
import { useEffect, useState, useRef } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface BalanceCounterProps {
  balance: number | null;
  pnl?: number | null;
  pnlPct?: number | null;
  onResetClick?: () => void;
}

export function BalanceCounter({ balance, pnl, pnlPct, onResetClick }: BalanceCounterProps) {
  const motionVal = useMotionValue(10000.0);
  const [isClient, setIsClient] = useState(false);
  const prevBalanceRef = useRef<number>(10000.0);

  useEffect(() => {
    setIsClient(true);
    if (balance !== null && balance !== undefined) {
      const target = balance;
      prevBalanceRef.current = target;
      
      const controls = animate(motionVal, target, {
        duration: 0.65,
        ease: [0.16, 1, 0.3, 1] // Clean easeOutExpo — glides directly to target with zero overshoot
      });
      return () => controls.stop();
    }
  }, [balance, motionVal]);

  const displayValue = useTransform(motionVal, (latest) => {
    return `$${Math.max(0, latest).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  });

  const hasPnl = pnl !== undefined && pnl !== null && pnl !== 0;
  const isPositive = (pnl ?? 0) >= 0;

  return (
    <div className="flex flex-col gap-1.5 select-none">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-slate-500 font-semibold tracking-wide">Available Sandbox Capital</span>
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold text-slate-700 bg-slate-100 border border-black/[0.06] shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]">
          Paper
        </span>
        {onResetClick && (
          <button
            onClick={onResetClick}
            className="text-[10px] font-mono font-bold text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 px-2 py-0.5 rounded-full border border-black/[0.06] transition-colors cursor-pointer"
            title="Reset sandbox capital amount"
          >
            Reset
          </button>
        )}
        {hasPnl && (
          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border shadow-[inset_0_1px_0_rgba(255,255,255,0.8)] ${
            isPositive 
              ? 'text-emerald-800 bg-emerald-50 border-emerald-200' 
              : 'text-rose-800 bg-rose-50 border-rose-200'
          }`}>
            {isPositive ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
            {isPositive ? '+' : ''}${Math.abs(pnl!).toFixed(2)} ({isPositive ? '+' : ''}{(pnlPct ?? 0).toFixed(2)}%)
          </span>
        )}
      </div>
      {isClient && balance !== null && balance !== undefined ? (
        <motion.span className="text-4xl sm:text-5xl font-bold text-slate-900 font-mono tracking-tight">
          {displayValue}
        </motion.span>
      ) : (
        <span className="text-4xl sm:text-5xl font-bold text-slate-900 font-mono tracking-tight opacity-40">
          $10,000.00
        </span>
      )}
    </div>
  );
}
