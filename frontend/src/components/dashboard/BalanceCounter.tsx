'use client';
import { motion, useSpring, useTransform } from 'framer-motion';
import { useEffect, useState } from 'react';

interface BalanceCounterProps {
  balance: number | null;
}

export function BalanceCounter({ balance }: BalanceCounterProps) {
  const springValue = useSpring(0, { stiffness: 50, damping: 20 });
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    if (balance !== null) {
      springValue.set(balance);
    }
  }, [balance, springValue]);

  const displayValue = useTransform(springValue, (latest) => {
    return `$${latest.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  });

  return (
    <div className="flex flex-col">
      <span className="text-sm text-baleen-muted mb-1 uppercase tracking-wider font-medium">Available Balance</span>
      {isClient && balance !== null ? (
        <motion.span className="text-4xl md:text-5xl font-bold text-baleen-white font-mono tracking-tight">
          {displayValue}
        </motion.span>
      ) : (
        <span className="text-4xl md:text-5xl font-bold text-baleen-white font-mono tracking-tight opacity-50">
          $0.00
        </span>
      )}
    </div>
  );
}
