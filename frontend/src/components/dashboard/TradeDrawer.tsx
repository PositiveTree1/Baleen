'use client';
import { useEffect } from 'react';
import { ExecutionLog } from '@/types';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ExternalLink, Activity, ArrowUpRight, ArrowDownRight, Users, ShieldCheck, Clock, DollarSign, Wallet, CheckCircle2 } from 'lucide-react';
import { TradePriceChart } from './TradePriceChart';
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
  const fillP = trade.fillPrice || trade.entryPrice || 0.0;
  const curP = trade.currentPrice || fillP;
  const pnl = trade.pnl ?? (fillP > 0 ? (isBuy ? (trade.size ?? 0) * ((curP - fillP) / fillP) : (trade.size ?? 0) * ((fillP - curP) / fillP)) : 0.0);
  const pnlPct = trade.pnlPct ?? (fillP > 0 ? (((curP - fillP) / fillP) * 100.0 * (isBuy ? 1 : -1)) : 0.0);
  const isProfit = pnl >= 0;
  const consensus = trade.consensus;
  const shares = fillP > 0 ? ((trade.size ?? 0) / fillP) : 0;
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
          className="fixed inset-0 bg-black/60 dark:bg-black/80 backdrop-blur-xs transition-opacity"
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
          className="relative w-full max-w-full sm:max-w-lg bg-white dark:bg-[#16171B] text-slate-900 dark:text-white shadow-2xl z-10 flex flex-col h-full border-l border-black/[0.08] dark:border-white/10"
        >
          {/* Header */}
          <div className="p-4 sm:p-6 border-b border-black/[0.06] dark:border-white/10 bg-slate-50 dark:bg-[#1C1D22] flex items-center justify-between">
            <div className="flex items-center gap-2.5 sm:gap-3">
              <div className={`p-2 sm:p-2.5 rounded-2xl border ${isBuy ? 'bg-emerald-50 dark:bg-[#00D09C]/10 border-emerald-200 dark:border-[#00D09C]/20 text-emerald-600 dark:text-[#00D09C]' : 'bg-rose-50 dark:bg-[#FF453A]/10 border-rose-200 dark:border-[#FF453A]/20 text-rose-600 dark:text-[#FF453A]'}`}>
                {isBuy ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
              </div>
              <div>
                <div className="flex items-center gap-1.5 sm:gap-2">
                  <span className={`text-[10px] sm:text-[11px] font-extrabold uppercase px-2 py-0.5 rounded-full border ${
                    isBuy 
                      ? 'bg-emerald-50 dark:bg-[#00D09C]/10 text-emerald-700 dark:text-[#00D09C] border-emerald-200 dark:border-[#00D09C]/30' 
                      : 'bg-rose-50 dark:bg-[#FF453A]/10 text-rose-700 dark:text-[#FF453A] border-rose-200 dark:border-[#FF453A]/30'
                  }`}>
                    {trade.side || 'BUY'} {outcomeLabel.toUpperCase()}
                  </span>
                  <span className="text-[9px] sm:text-[10px] font-mono font-bold text-slate-500 dark:text-[#8E8F99] bg-white dark:bg-[#2C2D35] px-1.5 sm:px-2 py-0.5 rounded-full border border-black/[0.06] dark:border-white/5">
                    {trade.status === 'FILLED' ? '🟢 OPEN' : '⚪ CLOSED'}
                  </span>
                </div>
                <p className="text-[10px] sm:text-[11px] font-mono text-slate-500 dark:text-[#8E8F99] flex items-center gap-1 mt-0.5 sm:mt-1">
                  <Clock size={11} />
                  {formatFrenchDateTime(trade.timestamp, true)}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close trade details drawer"
              className="p-2 rounded-xl text-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-[#24262E] transition-colors cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>

          {/* Content Body */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 sm:space-y-5">
            {/* Prediction Market Card */}
            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-[#8E8F99]">Prediction Market</div>
                <span className="text-[10px] font-mono font-bold text-indigo-700 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-200 dark:border-indigo-500/20">
                  {trade.marketCategory || 'General'}
                </span>
              </div>
              <div className="flex items-center gap-3">
                {trade.icon ? (
                  <img 
                    src={trade.icon} 
                    alt="" 
                    className="w-10 h-10 rounded-xl object-cover border border-black/10 dark:border-white/10 shrink-0 shadow-2xs" 
                  />
                ) : null}
                <div className="text-sm font-bold text-slate-900 dark:text-white leading-snug">
                  {trade.marketQuestion || 'Polymarket Event Prediction'}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-200/60 dark:border-indigo-500/20">
                  Selected Outcome: {outcomeLabel}
                </span>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-slate-200/70 dark:bg-[#2C2D35] text-slate-700 dark:text-slate-300">
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
              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 space-y-1">
                <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">Entry Fill Price</span>
                <div className="text-base font-bold font-mono text-slate-900 dark:text-white">
                  ${fillP.toFixed(3)}
                </div>
                <span className="text-[10px] text-slate-400 dark:text-[#8E8F99] font-mono">{shares.toFixed(1)} Shares</span>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 space-y-1">
                <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">
                  {trade.status === 'CLOSED' || trade.status === 'RESOLVED' || trade.side === 'SELL' ? 'Exit Settled Price' : 'Live Market Price'}
                </span>
                <div className="text-base font-bold font-mono text-slate-900 dark:text-white">
                  ${curP.toFixed(3)}
                </div>
                <span className="text-[10px] text-slate-400 dark:text-[#8E8F99] font-mono">
                  {trade.status === 'CLOSED' || trade.status === 'RESOLVED' ? 'Settled Valuation' : 'Live CLOB Midpoint'}
                </span>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 space-y-1">
                <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">Notional Size</span>
                <div className="text-base font-bold font-mono text-slate-900 dark:text-white">
                  ${(trade.size ?? 0).toFixed(2)}
                </div>
                <span className="text-[10px] text-slate-400 dark:text-[#8E8F99] font-mono">Sandbox USD</span>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 space-y-1">
                <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">Net Realized PnL</span>
                <div className={`text-base font-bold font-mono ${isProfit ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                  {isProfit ? '+' : ''}${pnl.toFixed(2)} ({isProfit ? '+' : ''}{pnlPct.toFixed(1)}%)
                </div>
                <span className="text-[10px] text-slate-400 dark:text-[#8E8F99] font-mono">Fee: -${(trade.feeUsd || 0).toFixed(2)}</span>
              </div>
            </div>

            {/* Price Chart */}
            <TradePriceChart 
              tradeId={trade.id}
              fillPrice={fillP} 
              currentPrice={curP} 
              side={trade.side} 
            />

            {/* Mirrored Source Whale Card */}
            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-slate-200 dark:bg-[#2C2D35] flex items-center justify-center font-bold text-sm text-slate-800 dark:text-white shrink-0">
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
                  className="px-3 py-1.5 rounded-full bg-slate-200 dark:bg-[#2C2D35] hover:bg-slate-300 dark:hover:bg-[#3C3E48] text-xs font-bold text-slate-900 dark:text-white transition-all cursor-pointer"
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
              className="w-full py-3 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black text-xs font-bold flex items-center justify-center gap-2 hover:bg-slate-800 dark:hover:bg-slate-200 transition-all cursor-pointer shadow-sm"
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
