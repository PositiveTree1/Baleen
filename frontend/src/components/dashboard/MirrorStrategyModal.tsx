'use client';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ShieldCheck, Zap, Sliders, CheckCircle2, UserCheck, Plus, ExternalLink, ArrowRight } from 'lucide-react';
import { fetchWallets, getCachedWallets } from '@/lib/api-client';
import { Wallet } from '@/types';

interface MirrorStrategyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectWallet?: (address: string) => void;
}

export function MirrorStrategyModal({ isOpen, onClose, onSelectWallet }: MirrorStrategyModalProps) {
  const [wallets, setWallets] = useState<Wallet[]>(() => getCachedWallets() || []);
  const [multipliers, setMultipliers] = useState<Record<string, number>>({});
  const [activeWhales, setActiveWhales] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (isOpen) {
      fetchWallets().then((data) => {
        if (data && data.length > 0) {
          setWallets(data);
          setActiveWhales((prev) => {
            const next = { ...prev };
            data.forEach((w) => {
              if (next[w.address] === undefined) {
                next[w.address] = !w.dormant;
              }
            });
            return next;
          });
          setMultipliers((prev) => {
            const next = { ...prev };
            data.forEach((w) => {
              if (next[w.address] === undefined) {
                next[w.address] = w.tier === 'gold_sniper' ? 1.5 : 1.0;
              }
            });
            return next;
          });
        }
      });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const toggleWhale = (addr: string) => {
    setActiveWhales(prev => ({ ...prev, [addr]: !prev[addr] }));
  };

  const setMultiplier = (addr: string, val: number) => {
    setMultipliers(prev => ({ ...prev, [addr]: val }));
  };

  return (
    <div className="fixed inset-0 bg-black/60 dark:bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-3 sm:p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        className="revolut-card bg-white dark:bg-[#16171B] border border-black/10 dark:border-white/10 p-4 sm:p-7 rounded-[22px] sm:rounded-[28px] max-w-2xl w-full space-y-4 sm:space-y-6 shadow-2xl max-h-[90vh] flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-black/[0.06] dark:border-white/10 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <Plus size={20} />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-950 dark:text-white">Whale Copy Strategy &amp; Multipliers</h3>
              <p className="text-xs text-slate-500 dark:text-[#8E8F99]">Configure auto-copying weights across verified Polymarket indexers</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-full text-slate-400 dark:text-[#8E8F99] hover:bg-slate-100 dark:hover:bg-[#1C1D22] transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Strategy Overview */}
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="p-3 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Index Whales</span>
            <div className="text-lg font-bold text-slate-950 dark:text-white font-mono mt-0.5">{wallets.length} Active</div>
          </div>
          <div className="p-3 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Execution Mode</span>
            <div className="text-lg font-bold text-emerald-600 dark:text-[#00D09C] font-mono mt-0.5">Live Autopilot</div>
          </div>
          <div className="p-3 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Slippage Tolerance</span>
            <div className="text-lg font-bold text-slate-950 dark:text-white font-mono mt-0.5">1.5 Cents</div>
          </div>
        </div>

        {/* Whales Multipliers List */}
        <div className="flex-1 overflow-y-auto space-y-2 pr-1 divide-y divide-black/[0.04] dark:divide-white/5">
          {wallets.map((w) => {
            const name = w.name || w.pseudonym || `${w.address.slice(0, 6)}...${w.address.slice(-4)}`;
            const isEnabled = activeWhales[w.address] ?? true;
            const mult = multipliers[w.address] ?? 1.0;

            return (
              <div key={w.address} className="pt-2.5 flex items-center justify-between p-2 rounded-2xl hover:bg-slate-50 dark:hover:bg-[#1C1D22] transition-colors">
                <div className="flex items-center gap-3 min-w-0">
                  <button
                    onClick={() => toggleWhale(w.address)}
                    className={`w-6 h-6 rounded-full flex items-center justify-center transition-all cursor-pointer ${
                      isEnabled ? 'bg-[#00D09C] text-black' : 'bg-slate-200 dark:bg-[#2C2D35] text-slate-400'
                    }`}
                  >
                    <CheckCircle2 size={15} />
                  </button>
                  <div 
                    className="cursor-pointer"
                    onClick={() => {
                      if (onSelectWallet) {
                        onClose();
                        onSelectWallet(w.address);
                      }
                    }}
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-slate-900 dark:text-white">{name}</span>
                      {w.tier === 'gold_sniper' && (
                        <span className="text-[9px] bg-amber-50 dark:bg-amber-400/10 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-400/20 px-1.5 rounded-full font-bold">
                          Gold
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-slate-500 dark:text-[#8E8F99] font-mono">
                      {(w.winRate > 1 ? w.winRate : w.winRate * 100).toFixed(0)}% Win Rate • ${(w.pnl || 0).toLocaleString()} PnL
                    </span>
                  </div>
                </div>

                {/* Multiplier Slider Pill */}
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-mono font-bold text-slate-700 dark:text-white">{mult.toFixed(1)}x</span>
                  <div className="flex rounded-full bg-slate-200 dark:bg-[#2C2D35] p-0.5 text-[10px] font-bold">
                    {[1.0, 1.5, 2.0].map((v) => (
                      <button
                        key={v}
                        onClick={() => setMultiplier(w.address, v)}
                        className={`px-2 py-0.5 rounded-full transition-all ${
                          mult === v ? 'bg-white dark:bg-[#16171B] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99]'
                        }`}
                      >
                        {v}x
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer Actions */}
        <div className="pt-3 border-t border-black/[0.06] dark:border-white/10 flex justify-between items-center">
          <span className="text-xs text-slate-500 dark:text-[#8E8F99] font-mono">All orders executed via CLOB taker limit</span>
          <button
            onClick={onClose}
            className="px-6 py-2.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black text-xs font-bold hover:bg-slate-800 dark:hover:bg-slate-200 transition-all cursor-pointer shadow-sm"
          >
            Save Strategy
          </button>
        </div>
      </motion.div>
    </div>
  );
}
