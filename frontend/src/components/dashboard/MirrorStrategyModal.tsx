'use client';
import { useState, useEffect } from 'react';
import { ShieldCheck, Zap, Sliders, CheckCircle2, UserCheck, Plus, ExternalLink, ArrowRight } from 'lucide-react';
import { fetchWallets, getCachedWallets } from '@/lib/api-client';
import { Wallet } from '@/types';
import { Modal } from '../ui/Modal';

export interface MirrorStrategyModalProps {
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
      let savedMults: Record<string, number> = {};
      let savedActive: Record<string, boolean> = {};
      if (typeof window !== 'undefined') {
        try {
          savedMults = JSON.parse(localStorage.getItem('baleen_whale_multipliers') || '{}');
          savedActive = JSON.parse(localStorage.getItem('baleen_active_whales') || '{}');
        } catch {}
      }

      fetchWallets().then((data) => {
        if (data && data.length > 0) {
          setWallets(data);
          setActiveWhales((prev) => {
            const next = { ...prev, ...savedActive };
            data.forEach((w) => {
              if (next[w.address] === undefined) {
                next[w.address] = !w.dormant;
              }
            });
            return next;
          });
          setMultipliers((prev) => {
            const next = { ...prev, ...savedMults };
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

  const toggleWhale = (addr: string) => {
    setActiveWhales(prev => ({ ...prev, [addr]: !prev[addr] }));
  };

  const setMultiplier = (addr: string, val: number) => {
    setMultipliers(prev => ({ ...prev, [addr]: val }));
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Whale Copy Strategy & Multipliers"
      subtitle="Configure paper copy weights across candidate Polymarket indexers"
      maxWidth="max-w-2xl"
    >
      <div className="space-y-4 sm:space-y-6">
        {/* Strategy Overview */}
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="p-3 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Index Whales</span>
            <div className="text-lg font-bold text-slate-950 dark:text-white font-mono mt-0.5">{wallets.length} Active</div>
          </div>
          <div className="p-3 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Execution Mode</span>
            <div className="text-lg font-bold text-emerald-600 dark:text-[#00D09C] font-mono mt-0.5">Paper Autopilot</div>
          </div>
          <div className="p-3 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-[#8E8F99] uppercase">Slippage Tolerance</span>
            <div className="text-lg font-bold text-slate-950 dark:text-white font-mono mt-0.5">1.5 Cents</div>
          </div>
        </div>

        {/* Whales Multipliers List */}
        <div className="max-h-[50vh] overflow-y-auto space-y-2 pr-1 divide-y divide-black/[0.04] dark:divide-white/5">
          {wallets.map((w) => {
            const name = w.name || w.pseudonym || `${w.address.slice(0, 6)}...${w.address.slice(-4)}`;
            const isEnabled = activeWhales[w.address] ?? true;
            const mult = multipliers[w.address] ?? 1.0;

            return (
              <div key={w.address} className="pt-2.5 flex items-center justify-between p-2 rounded-2xl hover:bg-slate-50 dark:hover:bg-[#1C1D22] transition-colors">
                <div className="flex items-center gap-3 min-w-0">
                  <button
                    type="button"
                    onClick={() => toggleWhale(w.address)}
                    aria-label={`Toggle paper copy for ${name}`}
                    className={`w-6 h-6 rounded-full flex items-center justify-center transition-all cursor-pointer ${
                      isEnabled ? 'bg-[#00D09C] text-black' : 'bg-slate-200 dark:bg-[#2C2D35] text-slate-400'
                    }`}
                  >
                    {isEnabled ? <CheckCircle2 size={14} /> : <div className="w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-600" />}
                  </button>
                  <div className="truncate">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-900 dark:text-white truncate">{name}</span>
                      {w.tier === 'gold_sniper' && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-amber-500/10 text-amber-500 font-bold border border-amber-500/20">
                          Gold
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-slate-500 dark:text-[#8E8F99] font-mono">
                      <span>WR: {w.winRate !== undefined && w.winRate !== null ? `${(w.winRate * 100).toFixed(0)}%` : '—'}</span>
                      <span>•</span>
                      <span>PnL: {w.pnl !== undefined && w.pnl !== null ? `${w.pnl >= 0 ? '+' : ''}${(w.pnl / 1000).toFixed(1)}k` : '—'}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex rounded-full bg-slate-200 dark:bg-[#2C2D35] p-0.5 text-[10px] font-bold">
                    {[1.0, 1.5, 2.0].map((v) => (
                      <button
                        key={v}
                        type="button"
                        onClick={() => setMultiplier(w.address, v)}
                        aria-label={`Set multiplier ${v}x for ${name}`}
                        className={`px-2 py-0.5 rounded-full transition-all cursor-pointer ${
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
          <span className="text-xs text-slate-500 dark:text-[#8E8F99] font-mono">All paper orders simulated via CLOB taker limit</span>
          <button
            type="button"
            onClick={() => {
              if (typeof window !== 'undefined') {
                localStorage.setItem('baleen_whale_multipliers', JSON.stringify(multipliers));
                localStorage.setItem('baleen_active_whales', JSON.stringify(activeWhales));
              }
              onClose();
            }}
            className="px-6 py-2.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black text-xs font-bold hover:bg-slate-800 dark:hover:bg-slate-200 transition-all cursor-pointer shadow-sm"
          >
            Save Strategy
          </button>
        </div>
      </div>
    </Modal>
  );
}
