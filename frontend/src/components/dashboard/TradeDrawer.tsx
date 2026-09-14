'use client';
import { useEffect } from 'react';
import { ExecutionLog } from '@/types';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ExternalLink, Activity, ArrowUpRight, ArrowDownRight, Users, ShieldCheck, Clock, DollarSign, Wallet, CheckCircle2 } from 'lucide-react';
import { TradePriceChart } from './TradePriceChart';
import { LiquidOrbButton } from '../ui/LiquidOrbButton';
import { formatFrenchDateTime } from '@/lib/formatters';

interface TradeDrawerProps {
  trade: ExecutionLog | null;
  onClose: () => void;
  onSelectWallet?: (address: string) => void;
}

export function TradeDrawer({ trade, onClose, onSelectWallet }: TradeDrawerProps) {
  useEffect(() => {
    if (!trade) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [trade, onClose]);
  if (!trade) return null;

  const isBuy = trade.side === 'BUY';
  const fillP = trade.fillPrice ?? trade.entryPrice;
  const curP = trade.currentPrice ?? null;
  const pnl = trade.pnl ?? null;
  const pnlPct = trade.pnlPct ?? null;
  const isClosed = trade.status === 'CLOSED' || trade.status === 'RESOLVED' || trade.side === 'SELL';
  const effectivePnl = pnl !== null ? pnl : (isClosed ? 0.0 : (trade.feeUsd ? -trade.feeUsd : null));
  const effectivePnlPct = pnlPct !== null ? pnlPct : (trade.size && effectivePnl !== null ? (effectivePnl / trade.size) * 100 : null);
  const derivedExitP = (isClosed && curP === null && fillP && (trade.size ?? 0) > 0 && effectivePnl !== null)
    ? Math.max(0, Math.min(1, ((trade.size ?? 0) + effectivePnl + (trade.feeUsd ?? 0)) / ((trade.size ?? 0) / fillP)))
    : null;
  const displayCurP = curP ?? (trade.side === 'SELL' ? fillP : derivedExitP);
  const isProfit = effectivePnl !== null && effectivePnl >= 0;
  const consensus = trade.consensus;
  const shares = fillP !== null && fillP > 0 ? ((trade.size ?? 0) / fillP) : null;
  const outcomeLabel = trade.outcome || 'Yes';

  const polyUrl = trade.polymarketUrl || (trade.eventSlug ? `https://polymarket.com/event/${trade.eventSlug}` : (trade.marketConditionId ? `https://polymarket.com/market/${trade.marketConditionId}` : 'https://polymarket.com'));

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-slate-900/60 dark:bg-black/80 backdrop-blur-sm z-40"
        />

        {/* Slide-out Panel */}
        <motion.div
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 28, stiffness: 280 }}
          role="dialog"
          aria-modal="true"
          aria-label="Trade Execution Drawer"
          className="relative w-full max-w-full sm:max-w-lg bg-white/95 text-slate-950 shadow-2xl z-50 flex flex-col h-full border-l border-slate-200 backdrop-blur-2xl"
        >
          {/* Header */}
          <div className="p-4 sm:p-6 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
            <div className="flex items-center gap-2.5 sm:gap-3">
              <div className={`p-2 sm:p-2.5 rounded-2xl border ${isBuy ? 'bg-emerald-500/10 border-emerald-500/20 text-[#00D09C]' : 'bg-rose-500/10 border-rose-500/20 text-[#FF453A]'}`}>
                {isBuy ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
              </div>
              <div>
                <div className="flex items-center gap-1.5 sm:gap-2">
                  <span className={`text-[10px] sm:text-[11px] font-extrabold uppercase px-2 py-0.5 rounded-full border ${
                    isBuy 
                      ? 'bg-emerald-500/10 text-emerald-700 dark:text-[#00D09C] border-emerald-500/30' 
                      : 'bg-rose-500/10 text-rose-700 dark:text-[#FF453A] border-rose-500/30'
                  }`}>
                    {trade.side || 'BUY'} {outcomeLabel.toUpperCase()}
                  </span>
                  <span className="text-[9px] sm:text-[10px] font-mono font-bold text-slate-500 dark:text-[#8E8F99] bg-white/80 dark:bg-white/10 px-1.5 sm:px-2 py-0.5 rounded-full border border-sky-100/60 dark:border-white/10">
                    {trade.status === 'FILLED' ? '🟢 OPEN' : '⚪ CLOSED'}
                  </span>
                </div>
                <p className="text-[10px] sm:text-[11px] font-mono text-slate-500 dark:text-[#8E8F99] flex items-center gap-1 mt-0.5 sm:mt-1">
                  <Clock size={11} />
                  {formatFrenchDateTime(trade.timestamp, true)}
                </p>
              </div>
            </div>
            <LiquidOrbButton
              size="sm"
              onClick={onClose}
              aria-label="Close trade details drawer"
              title="Close"
            >
              <X size={15} />
            </LiquidOrbButton>
          </div>

          {/* Content Body */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 sm:space-y-5">
            {/* Prediction Market Card */}
            <div className="p-4 rounded-2xl glass-card space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-[#8E8F99]">Prediction Market</div>
                <span className="text-[10px] font-mono font-bold text-indigo-700 dark:text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/20">
                  {trade.marketCategory || 'General'}
                </span>
              </div>
              <div className="flex items-center gap-3">
                {trade.icon ? (
                  <img 
                    src={trade.icon} 
                    alt="" 
                    className="w-10 h-10 rounded-xl object-cover border border-sky-100/60 dark:border-white/10 shrink-0 shadow-xs" 
                  />
                ) : null}
                <div className="text-sm font-bold text-slate-900 dark:text-white leading-snug">
                  {trade.marketQuestion || 'Polymarket Event Prediction'}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-500/20">
                  Selected Outcome: {outcomeLabel}
                </span>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-slate-200/70 dark:bg-white/10 text-slate-700 dark:text-slate-300">
                  Side: {trade.side || 'BUY'}
                </span>
                {trade.marketConditionId && (
                  <span className="text-[10px] font-mono text-slate-400 dark:text-[#8E8F99] truncate">
                    CID: {trade.marketConditionId.slice(0, 10)}...{trade.marketConditionId.slice(-6)}
                  </span>
                )}
              </div>
            </div>

            {/* Pricing & Execution Grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3.5 rounded-2xl glass-card space-y-1">
                <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">
                  {trade.side === 'SELL' ? 'Sell Execution Fill' : 'Entry Fill Price'}
                </span>
                <div className="text-base font-bold font-mono text-slate-900 dark:text-white">
                  {fillP === null ? 'Unavailable' : `$${fillP.toFixed(3)}`}
                </div>
                <span className="text-[10px] text-slate-400 dark:text-[#8E8F99] font-mono">{shares === null ? 'Shares unavailable' : `${shares.toFixed(1)} Shares`}</span>
              </div>

              <div className="p-3.5 rounded-2xl glass-card space-y-1">
                <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">
                  {trade.status === 'CLOSED' || trade.status === 'RESOLVED' || trade.side === 'SELL' ? 'Exit Settled Price' : 'Live Market Price'}
                </span>
                <div className="text-base font-bold font-mono text-slate-900 dark:text-white">
                  {displayCurP !== null
                    ? `$${displayCurP.toFixed(3)}`
                    : (trade.status === 'FILLED' && fillP !== null ? `$${fillP.toFixed(3)}` : isClosed ? (fillP !== null ? `$${fillP.toFixed(3)}` : 'Settled') : 'Unavailable')}
                </div>
                <span className="text-[10px] text-slate-400 dark:text-[#8E8F99] font-mono">
                  {displayCurP !== null
                    ? (isClosed ? (trade.side === 'SELL' ? 'Closing Sell Fill' : 'Settled Valuation') : 'Live CLOB Midpoint')
                    : (trade.status === 'FILLED' && fillP !== null ? 'At Entry Fill' : 'Price unavailable')}
                </span>
              </div>

              <div className="p-3.5 rounded-2xl glass-card space-y-1">
                <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">Notional Size</span>
                <div className="text-base font-bold font-mono text-slate-900 dark:text-white">
                  ${(trade.size ?? 0).toFixed(2)}
                </div>
                <span className="text-[10px] text-slate-400 dark:text-[#8E8F99] font-mono">Sandbox USD</span>
              </div>

              <div className="p-3.5 rounded-2xl glass-card space-y-1">
                <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">
                  {trade.status === 'CLOSED' || trade.status === 'RESOLVED' ? 'Net Realized PnL' : 'Unrealized PnL (MTM)'}
                </span>
                <div className={`text-base font-bold font-mono ${isProfit ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                  {effectivePnl === null ? '$0.00' : `${effectivePnl >= 0 ? '+' : ''}$${effectivePnl.toFixed(2)}${effectivePnlPct === null ? '' : ` (${effectivePnl >= 0 ? '+' : ''}${effectivePnlPct.toFixed(1)}%)`}`}
                </div>
                <span className="text-[10px] text-slate-400 dark:text-[#8E8F99] font-mono">Fee: {trade.feeUsd === null || trade.feeUsd === undefined ? '$0.00' : `-$${trade.feeUsd.toFixed(2)}`}</span>
              </div>
            </div>

            {/* Price Chart */}
            <TradePriceChart 
              tradeId={trade.id}
              fillPrice={fillP} 
              currentPrice={displayCurP ?? fillP} 
              side={trade.side} 
            />

            {/* Mirrored Source Whale Card */}
            <div className="p-4 rounded-2xl glass-card flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-sky-100/60 dark:bg-white/10 flex items-center justify-center font-bold text-sm text-slate-800 dark:text-white shrink-0 border border-sky-100/60 dark:border-white/10">
                  <Wallet size={16} />
                </div>
                <div>
                  <span className="text-xs font-bold text-slate-900 dark:text-white block">
                    {trade.whaleName || trade.whalePseudonym || 'Whale Signal'}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400 dark:text-[#8E8F99]">
                    {trade.walletAddress ? `${trade.walletAddress.slice(0, 6)}...${trade.walletAddress.slice(-4)}` : 'On-chain Whale'}
                  </span>
                </div>
              </div>

              {trade.walletAddress && onSelectWallet && (
                <button
                  onClick={() => onSelectWallet(trade.walletAddress!)}
                  className="glass-button px-3 py-1.5 rounded-full text-xs font-bold text-white transition-all cursor-pointer"
                >
                  View Whale
                </button>
              )}
            </div>

            {/* Polymarket Link CTA */}
            <a
              href={polyUrl}
              target="_blank"
              rel="noreferrer"
              className="w-full py-3.5 rounded-2xl glass-button text-white text-xs font-bold flex items-center justify-center gap-2 cursor-pointer shadow-lg"
            >
              <span>Inspect on Polymarket Orderbook</span>
              <ExternalLink size={14} />
            </a>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
