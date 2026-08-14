'use client';
import { motion, useSpring, useTransform } from 'framer-motion';
import { useEffect, useState } from 'react';

interface BalanceCounterProps {
  balance: number | null;
}

export function BalanceCounter({ balance }: BalanceCounterProps) {
  const springValue = useSpring(0, { stiffness: 60, damping: 22 });
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    if (balance !== null && balance !== undefined) {
      springValue.set(balance);
    }
  }, [balance, springValue]);

  const displayValue = useTransform(springValue, (latest) => {
    return `$${latest.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  });

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <span className="text-xs text-zinc-400 font-medium tracking-wide">Available Sandbox Capital</span>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono text-zinc-400 bg-white/[0.06] border border-white/[0.08]">
          Paper
        </span>
      </div>
      {isClient && balance !== null && balance !== undefined ? (
        <motion.span className="text-4xl sm:text-5xl font-bold text-white font-mono tracking-tight">
          {displayValue}
        </motion.span>
      ) : (
        <span className="text-4xl sm:text-5xl font-bold text-white font-mono tracking-tight opacity-40">
          $10,000.00
        </span>
      )}
    </div>
  );
}
