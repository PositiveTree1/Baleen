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
        ease: [0.16, 1, 0.3, 1]
      });
      return () => controls.stop();
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
      <div className="flex items-center gap-2 text-xs font-semibold text-[#8E8F99]">
        <span>Personal · USD</span>
        <span className="w-1 h-1 rounded-full bg-[#8E8F99]" />
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white bg-[#2C2D35]">
          Sandbox
        </span>
      </div>

      {/* Main Authoritative Balance */}
      <div className="flex flex-col sm:flex-row sm:items-baseline gap-3">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-white font-outfit">
          {isClient ? (
            <motion.span>{displayValue}</motion.span>
          ) : (
            `$${(balance ?? 10000).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
          )}
        </h1>

        {/* PnL Pill Badge */}
        {hasPnl && (
          <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold font-mono ${
            isPositive 
              ? 'text-[#00D09C] bg-[#00D09C]/10 border border-[#00D09C]/20' 
              : 'text-[#FF453A] bg-[#FF453A]/10 border border-[#FF453A]/20'
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
            className="revolut-circle-btn cursor-pointer shadow-lg"
            title="Mirror Top Polymarket Whales"
          >
            <Plus size={22} className="text-white" />
          </button>
          <span className="text-xs font-semibold text-white/90">Mirror</span>
        </div>

        {/* Action 2: Move / Rebalance */}
        <div className="flex flex-col items-center gap-1.5">
          <button
            onClick={onRebalanceClick}
            className="revolut-circle-btn cursor-pointer shadow-lg"
            title="Rebalance Basket Allocation"
          >
            <ArrowLeftRight size={20} className="text-white" />
          </button>
          <span className="text-xs font-semibold text-white/90">Rebalance</span>
        </div>

        {/* Action 3: Analytics */}
        <div className="flex flex-col items-center gap-1.5">
          <button
            onClick={onAnalyticsClick}
            className="revolut-circle-btn cursor-pointer shadow-lg"
            title="View Portfolio Analytics"
          >
            <BarChart2 size={20} className="text-white" />
          </button>
          <span className="text-xs font-semibold text-white/90">Analytics</span>
        </div>

        {/* Action 4: Reset */}
        {onResetClick && (
          <div className="flex flex-col items-center gap-1.5">
            <button
              onClick={onResetClick}
              className="revolut-circle-btn cursor-pointer shadow-lg hover:border-rose-500/40"
              title="Reset Sandbox Balance"
            >
              <RotateCcw size={19} className="text-white/80" />
            </button>
            <span className="text-xs font-semibold text-white/90">Reset</span>
          </div>
        )}
      </div>
    </div>
  );
}
