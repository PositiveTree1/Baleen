'use client';
import { motion, useSpring, useTransform } from 'framer-motion';
import { useEffect, useState } from 'react';

interface BalanceCounterProps {
  balance: number | null;
}

export function BalanceCounter({ balance }: BalanceCounterProps) {
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

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-500 font-semibold tracking-wide">Available Sandbox Capital</span>
        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold text-slate-700 bg-slate-100 border border-black/[0.06] shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]">
          Paper
        </span>
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
