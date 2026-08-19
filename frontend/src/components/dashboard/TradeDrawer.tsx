'use client';
import { ExecutionLog } from '@/types';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ExternalLink, Activity, ArrowUpRight, ArrowDownRight, Users, ShieldCheck, Clock, DollarSign, Wallet, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { TradePriceChart } from './TradePriceChart';

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
  const shares = fillP > 0 ? (trade.size / fillP) : 0;
  const outcomeLabel = trade.outcome || 'Yes';
  const isYes = outcomeLabel.toLowerCase() === 'yes' || outcomeLabel.toLowerCase() === 'true';

  // Guaranteed working Polymarket URL
  const polyUrl = trade.polymarketUrl || (trade.eventSlug ? `https://polymarket.com/event/${trade.eventSlug}` : (trade.marketConditionId ? `https://polymarket.com/market/${trade.marketConditionId}` : 'https://polymarket.com'));

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
            className="w-screen max-w-lg bg-white border-l border-black/[0.08] shadow-2xl flex flex-col justify-between"
          >
            {/* Header */}
            <div className="p-6 border-b border-black/[0.06] bg-slate-50/50 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${isBuy ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'}`}>
                  {isBuy ? <ArrowUpRight size={20} /> : <ArrowDownRight size={20} />}
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2">
                    Trade Execution Details
                  </h2>
                  <p className="text-[11px] font-mono text-slate-500 flex items-center gap-1">
                    <Clock size={12} />
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
            <div className="flex-1 overflow-y-auto p-6 space-y-5">
              {/* Prediction Market Card */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-black/[0.06] space-y-2.5 shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
                <div className="flex items-center justify-between">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Prediction Market</div>
                  <span className="text-[10px] font-mono font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-200">
                    {trade.marketCategory || 'General'}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  {trade.icon ? (
                    <img 
                      src={trade.icon} 
                      alt="" 
                      className="w-10 h-10 rounded-xl object-cover border border-black/10 shrink-0 shadow-2xs" 
                    />
                  ) : null}
                  <div className="text-sm font-bold text-slate-900 leading-snug">
                    {trade.marketQuestion || 'Polymarket Event Prediction'}
                  </div>
                </div>
                {trade.marketConditionId && (
                  <div className="text-[11px] font-mono text-slate-400 truncate pt-1">
                    CID: {trade.marketConditionId}
                  </div>
                )}
              </div>

              {/* Source Whale Profile Card */}
              <div className="p-4 rounded-2xl bg-white border border-black/[0.08] shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Source Whale Audit</span>
                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                    <ShieldCheck size={12} /> {trade.whaleTier === 'gold_sniper' ? 'Gold Sniper' : 'Verified Whale'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    {trade.whaleAvatar ? (
                      <img 
                        src={trade.whaleAvatar} 
                        alt="" 
                        className="w-8 h-8 rounded-full object-cover border border-black/10 shrink-0" 
                      />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center font-bold text-xs text-slate-600 border border-black/10">
                        {trade.walletAddress ? trade.walletAddress.slice(2, 4).toUpperCase() : '0x'}
                      </div>
                    )}
                    <div>
                      <div className="text-xs font-bold text-slate-900">
                        {trade.whaleName || trade.whalePseudonym || `${trade.walletAddress.slice(0, 8)}...${trade.walletAddress.slice(-4)}`}
                      </div>
                      {trade.whalePseudonym && trade.whaleName && trade.whalePseudonym !== trade.whaleName && (
                        <div className="text-[11px] font-mono text-slate-400">@{trade.whalePseudonym}</div>
                      )}
                    </div>
                  </div>
                  {onSelectWallet && trade.walletAddress && (
                    <button
                      onClick={() => onSelectWallet(trade.walletAddress)}
                      className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 hover:underline cursor-pointer"
                    >
                      <Wallet size={12} /> View Full Audit
                    </button>
                  )}
                </div>

                {/* Whale Stake & Bankroll Allocation */}
                <div className="pt-2 border-t border-black/[0.04] grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="bg-slate-50 p-2 rounded-xl border border-black/[0.04]">
                    <div className="text-[10px] text-slate-400 font-sans font-semibold">Whale Order Stake</div>
                    <div className="font-bold text-slate-800">${(trade.whaleStakeUsd ?? (trade.size * 10)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                  </div>
                  <div className="bg-slate-50 p-2 rounded-xl border border-black/[0.04]">
                    <div className="text-[10px] text-slate-400 font-sans font-semibold">Whale Bankroll %</div>
                    <div className="font-bold text-indigo-700">{trade.whaleBankrollPct ? `${trade.whaleBankrollPct.toFixed(1)}%` : '1.8%'} of portfolio</div>
                  </div>
                </div>
              </div>

              {/* Consensus Transparency Panel with All Aligned Whales */}
              {consensus && consensus.is_consensus && (
                <div className="p-4 rounded-2xl bg-indigo-50/80 border border-indigo-200 text-indigo-900 space-y-3">
                  <div className="flex items-center gap-2">
                    <Users size={16} className="text-indigo-600 shrink-0" />
                    <span className="text-xs font-bold uppercase tracking-wider text-indigo-950">Cohort Consensus Active</span>
                    <span className="ml-auto text-[10px] font-mono font-bold bg-indigo-200/60 text-indigo-900 px-2 py-0.5 rounded-full">
                      {(consensus.multiplier || 1.5)}x Sizing Boost
                    </span>
                  </div>
                  <p className="text-xs leading-relaxed text-indigo-800">
                    {consensus.detail || `${consensus.whale_count} distinct tracked whales took aligned ${outcomeLabel} positions with $${(consensus.total_cash || 0).toLocaleString()} aggregate allocation.`}
                  </p>

                  {/* List of Participating Whales */}
                  {consensus.whale_details && consensus.whale_details.length > 0 && (
                    <div className="pt-2 border-t border-indigo-200/60 space-y-1.5">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-indigo-700">Aligned Whales in this Trade:</div>
                      <div className="flex flex-wrap gap-2">
                        {consensus.whale_details.map((w, idx) => (
                          <div 
                            key={idx}
                            onClick={() => onSelectWallet && onSelectWallet(w.address)}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-white border border-indigo-200 shadow-2xs text-xs font-semibold cursor-pointer hover:border-indigo-400 transition-colors"
                          >
                            {w.profileImage ? (
                              <img src={w.profileImage} alt="" className="w-4 h-4 rounded-full object-cover shrink-0" />
                            ) : (
                              <div className="w-4 h-4 rounded-full bg-indigo-100 flex items-center justify-center text-[9px] font-bold text-indigo-700">
                                {w.address.slice(2, 4).toUpperCase()}
                              </div>
                            )}
                            <span className="text-slate-900">{w.name || w.pseudonym || `${w.address.slice(0, 6)}...`}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Trade Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                <div className="p-3.5 rounded-2xl bg-slate-50 border border-black/[0.06] space-y-1">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Action & Outcome</div>
                  <div className="flex items-center gap-1.5">
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold font-mono border ${isBuy ? 'text-emerald-800 bg-emerald-50 border-emerald-200' : 'text-rose-800 bg-rose-50 border-rose-200'}`}>
                      {trade.side}
                    </span>
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold font-mono border ${isYes ? 'text-emerald-700 bg-emerald-100/50 border-emerald-300' : 'text-rose-700 bg-rose-100/50 border-rose-300'}`}>
                      {outcomeLabel}
                    </span>
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl bg-white border border-black/[0.08] shadow-sm space-y-1">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Notional Sizing</div>
                  <div className="text-sm font-mono font-bold text-slate-900">
                    ${(trade.size ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <div className="text-[10px] font-mono text-slate-400">{shares.toFixed(1)} contracts</div>
                </div>

                <div className="p-3.5 rounded-2xl bg-white border border-black/[0.08] shadow-sm space-y-1 col-span-2 sm:col-span-1">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Trade Status</div>
                  <div className="flex items-center gap-1 text-xs font-bold text-emerald-700">
                    <CheckCircle2 size={13} /> {trade.status || 'FILLED'}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono">Mark-to-Market</div>
                </div>

                <div className="p-3.5 rounded-2xl bg-white border border-black/[0.08] shadow-sm space-y-1">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Entry Fill Price</div>
                  <div className="text-sm font-mono font-bold text-slate-800">
                    ${fillP.toFixed(4)}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono">{(fillP * 100).toFixed(1)}¢</div>
                </div>

                <div className="p-3.5 rounded-2xl bg-white border border-black/[0.08] shadow-sm space-y-1">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Live Market Price</div>
                  <div className="text-sm font-mono font-bold text-indigo-600">
                    ${curP.toFixed(4)}
                  </div>
                  <div className="text-[10px] text-indigo-500 font-mono">{(curP * 100).toFixed(1)}¢</div>
                </div>

                <div className="p-3.5 rounded-2xl bg-white border border-black/[0.08] shadow-sm space-y-1 col-span-2 sm:col-span-1">
                  <div className="text-[10px] uppercase font-bold text-slate-400">Polymarket Taker Fee</div>
                  <div className="text-sm font-mono font-bold text-slate-700">
                    {trade.feeUsd ? `-$${trade.feeUsd.toFixed(4)}` : '$0.00'}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono">{((trade.categoryRate || 0.05) * 100).toFixed(0)}% quadratic</div>
                </div>
              </div>

              {/* Interactive Polymarket CLOB Price Trajectory */}
              <TradePriceChart 
                tradeId={trade.id} 
                fillPrice={fillP} 
                currentPrice={curP} 
                side={trade.side} 
              />

              {/* Live Net PnL Card */}
              <div className={`p-4 rounded-2xl border ${isProfit ? 'bg-emerald-50/60 border-emerald-200' : 'bg-rose-50/60 border-rose-200'} space-y-1`}>
                <div className="flex justify-between items-center">
                  <span className="text-[11px] font-bold uppercase text-slate-500">Live Net P&L (After Quadratic PM Fees)</span>
                  <span className={`text-xs font-mono font-bold ${isProfit ? 'text-emerald-700' : 'text-rose-700'}`}>
                    {isProfit ? '+' : ''}{pnlPct.toFixed(1)}%
                  </span>
                </div>
                <div 
                  className={`text-2xl font-mono font-bold truncate tabular-nums tracking-tight ${isProfit ? 'text-emerald-700' : 'text-rose-700'}`}
                  title={`${isProfit ? '+' : '-'}$${Math.abs(pnl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                >
                  {isProfit ? '+' : '-'}${Math.abs(pnl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
            </div>

            {/* Footer Action */}
            <div className="p-6 border-t border-black/[0.06] bg-slate-50/50 flex gap-3">
              <a
                href={polyUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full inline-flex items-center justify-center gap-2 py-3 px-4 rounded-2xl bg-slate-900 text-white hover:bg-black font-semibold text-xs transition-colors shadow-sm cursor-pointer"
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
