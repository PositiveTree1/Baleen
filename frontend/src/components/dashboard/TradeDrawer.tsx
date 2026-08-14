'use client';
import { ExecutionLog } from '@/types';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ExternalLink, Activity, ArrowUpRight, ArrowDownRight, Users, ShieldCheck, Clock, DollarSign, Wallet } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface TradeDrawerProps {
  trade: ExecutionLog | null;
  onClose: () => void;
  onSelectWallet?: (address: string) => void;
}

export function TradeDrawer({ trade, onClose, onSelectWallet }: TradeDrawerProps) {
  if (!trade) return null;

  const isBuy = trade.side === 'BUY';
  const fillP = trade.fillPrice || trade.entryPrice || 0.5;
  const curP = trade.currentPrice || fillP;
  const pnl = trade.pnl ?? (isBuy ? trade.size * ((curP - fillP) / fillP) : trade.size * ((fillP - curP) / fillP));
  const pnlPct = trade.pnlPct ?? (((curP - fillP) / fillP) * 100.0 * (isBuy ? 1 : -1));
  const isProfit = pnl >= 0;
  const consensus = trade.consensus;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-hidden">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm transition-opacity cursor-pointer"
        />

        <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="w-screen max-w-md bg-white border-l border-black/[0.08] shadow-2xl flex flex-col justify-between"
          >
            {/* Header */}
            <div className="p-6 border-b border-black/[0.06] bg-slate-50/50 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center ${isBuy ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'}`}>
                  {isBuy ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2">
                    Execution Details
                  </h2>
                  <p className="text-[11px] font-mono text-slate-500">
                    {trade.timestamp ? new Date(trade.timestamp).toLocaleString([], { dateStyle: 'medium', timeStyle: 'medium' }) : '--'}
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-black/5 transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Market Question */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-black/[0.06] space-y-2 shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Prediction Market</div>
                <div className="text-sm font-bold text-slate-900 leading-snug">
                  {trade.marketQuestion || 'Polymarket Event Prediction'}
                </div>
                {trade.marketConditionId && (
                  <div className="text-[11px] font-mono text-slate-400 truncate pt-1">
                    CID: {trade.marketConditionId}
                  </div>
                )}
              </div>

              {/* Consensus Banner if applicable */}
              {consensus && consensus.is_consensus && (
                <div className="p-3.5 rounded-2xl bg-indigo-50 border border-indigo-200 text-indigo-900 flex items-center gap-3">
                  <Users size={18} className="text-indigo-600 shrink-0" />
                  <div className="text-xs">
                    <span className="font-bold">Cohort Consensus Active:</span> {consensus.whale_count} tracked whales holding this outcome with ${(consensus.total_cash || 0).toLocaleString()} aggregate allocation.
                  </div>
                </div>
              )}

              {/* Trade Metrics Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-4 rounded-2xl bg-white border border-black/[0.08] shadow-sm space-y-1">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Side / Direction</div>
                  <div className="flex items-center gap-1.5">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold font-mono border ${isBuy ? 'text-emerald-800 bg-emerald-50 border-emerald-200' : 'text-rose-800 bg-rose-50 border-rose-200'}`}>
                      {trade.side}
                    </span>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-white border border-black/[0.08] shadow-sm space-y-1">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Notional Size</div>
                  <div className="text-sm font-mono font-bold text-slate-900">
                    ${(trade.size ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-white border border-black/[0.08] shadow-sm space-y-1">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Fill Price</div>
                  <div className="text-sm font-mono font-bold text-slate-800">
                    ${fillP.toFixed(3)}
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-white border border-black/[0.08] shadow-sm space-y-1">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Live Market Price</div>
                  <div className="text-sm font-mono font-bold text-indigo-600">
                    ${curP.toFixed(3)}
                  </div>
                </div>
              </div>

              {/* Live PnL Box */}
              <div className={`p-4 rounded-2xl border ${isProfit ? 'bg-emerald-50/50 border-emerald-200' : 'bg-rose-50/50 border-rose-200'} space-y-1`}>
                <div className="flex justify-between items-center">
                  <span className="text-[11px] font-bold uppercase text-slate-500">Live Mark-to-Market P&L</span>
                  <span className={`text-xs font-mono font-bold ${isProfit ? 'text-emerald-700' : 'text-rose-700'}`}>
                    {isProfit ? '+' : ''}{pnlPct.toFixed(1)}%
                  </span>
                </div>
                <div className={`text-2xl font-mono font-bold ${isProfit ? 'text-emerald-700' : 'text-rose-700'}`}>
                  {isProfit ? '+' : '-'}${Math.abs(pnl).toFixed(2)}
                </div>
              </div>

              {/* Whale Source & Link */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-black/[0.06] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-slate-500 uppercase">Source Whale</span>
                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                    <ShieldCheck size={12} /> Verified Cohort
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-slate-800 font-bold">
                    {trade.walletAddress ? `${trade.walletAddress.slice(0, 10)}...${trade.walletAddress.slice(-6)}` : '0x000...'}
                  </span>
                  {onSelectWallet && trade.walletAddress && (
                    <button
                      onClick={() => onSelectWallet(trade.walletAddress)}
                      className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 hover:underline cursor-pointer"
                    >
                      <Wallet size={12} /> View Whale Audit
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Footer Action */}
            <div className="p-6 border-t border-black/[0.06] bg-slate-50/50 flex gap-3">
              <a
                href={trade.polymarketUrl || `https://polymarket.com/event/${trade.marketConditionId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-2xl bg-slate-900 text-white hover:bg-black font-semibold text-xs transition-colors shadow-sm"
              >
                <ExternalLink size={14} /> Open Event on Polymarket
              </a>
            </div>
          </motion.div>
        </div>
      </div>
    </AnimatePresence>
  );
}
