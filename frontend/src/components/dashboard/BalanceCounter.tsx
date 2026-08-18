'use client';
import { motion, useSpring, useTransform } from 'framer-motion';
import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface BalanceCounterProps {
  balance: number | null;
  pnl?: number | null;
  pnlPct?: number | null;
}

export function BalanceCounter({ balance, pnl, pnlPct }: BalanceCounterProps) {
  const initial = balance ?? 10000;
  const springValue = useSpring(initial, { stiffness: 100, damping: 28, restDelta: 0.01 });
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    if (balance !== null && balance !== undefined) {
      springValue.set(balance);
    }
  }, [balance, springValue]);

  const displayValue = useTransform(springValue, (latest) => {
    return `$${Math.max(0, latest).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  });

  const hasPnl = pnl !== undefined && pnl !== null && pnl !== 0;
  const isPositive = (pnl ?? 0) >= 0;

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-500 font-semibold tracking-wide">Available Sandbox Capital</span>
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold text-slate-700 bg-slate-100 border border-black/[0.06] shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]">
          Paper
        </span>
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

