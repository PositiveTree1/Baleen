'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, ArrowRight, Wallet, Activity, ShieldCheck, Sparkles, X } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { soundFx } from '@/lib/sound';
import { fetchWallets, getCachedWallets } from '@/lib/api-client';
import type { Wallet as WalletData } from '@/types';

interface CommandPaletteProps {
  isOpen?: boolean;
  onClose?: () => void;
  onSelectWallet?: (address: string) => void;
}

export function CommandPalette({ isOpen: controlledIsOpen, onClose: controlledOnClose, onSelectWallet }: CommandPaletteProps) {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [wallets, setWallets] = useState<WalletData[]>(() => getCachedWallets() || []);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const isPaletteOpen = controlledIsOpen !== undefined ? controlledIsOpen : internalIsOpen;

  const handleClose = useCallback(() => {
    if (controlledOnClose) {
      controlledOnClose();
    } else {
      setInternalIsOpen(false);
    }
  }, [controlledOnClose]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (controlledIsOpen !== undefined) {
          if (controlledIsOpen && controlledOnClose) controlledOnClose();
        } else {
          setInternalIsOpen((prev) => !prev);
        }
      }
      if (e.key === 'Escape' && isPaletteOpen) {
        handleClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [controlledIsOpen, controlledOnClose, isPaletteOpen, handleClose]);

  useEffect(() => {
    if (isPaletteOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      fetchWallets().then(data => {
        if (data && data.length > 0) setWallets(data);
      });
    }
  }, [isPaletteOpen]);

  const executeAction = (action: () => void) => {
    soundFx.playChime('click');
    action();
    handleClose();
  };

  const defaultCommands = [
    {
      id: 'dashboard',
      label: 'Open Dashboard Control Plane',
      category: 'Navigation',
      icon: Activity,
      action: () => router.push('/dashboard'),
    },
    {
      id: 'admin',
      label: 'Open Engine Admin & Diagnostics',
      category: 'Navigation',
      icon: ShieldCheck,
      action: () => router.push('/admin'),
    },
    {
      id: 'settings',
      label: 'Open User Settings & Risk Regime',
      category: 'Navigation',
      icon: Sparkles,
      action: () => router.push('/settings'),
    },
  ];

  const filteredWallets = query.trim()
    ? wallets.filter(
        (w) =>
          w.address.toLowerCase().includes(query.toLowerCase()) ||
          (w.name || '').toLowerCase().includes(query.toLowerCase()) ||
          (w.pseudonym || '').toLowerCase().includes(query.toLowerCase())
      )
    : [];

  const filteredCommands = query.trim()
    ? defaultCommands.filter((c) =>
        c.label.toLowerCase().includes(query.toLowerCase()) ||
        c.category.toLowerCase().includes(query.toLowerCase())
      )
    : defaultCommands;

  return (
    <AnimatePresence>
      {isPaletteOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 sm:pt-32 p-4 glass-modal-backdrop">
          {/* Backdrop click to close */}
          <div className="fixed inset-0" onClick={handleClose} />

          {/* Palette Container */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -10 }}
            transition={{ duration: 0.15 }}
            role="dialog"
            aria-modal="true"
            aria-label="Command Palette"
            className="relative w-full max-w-xl glass-modal rounded-[28px] overflow-hidden z-10 flex flex-col max-h-[70vh]"
          >
            {/* Search Input */}
            <div className="flex items-center gap-3 px-5 py-4 border-b border-sky-100/60 dark:border-white/10 bg-white/40 dark:bg-white/[0.02]">
              <Search size={18} className="text-slate-400 dark:text-[#8E8F99] shrink-0" />
              <input
                ref={inputRef}
                type="text"
                placeholder="Search whales, prediction markets, or jump to..."
                aria-label="Search whales, prediction markets, or jump to"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full bg-transparent text-sm text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-[#8E8F99] focus:outline-none"
              />
              {query && (
                <button
                  onClick={() => setQuery('')}
                  aria-label="Clear search query"
                  className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-white rounded-md cursor-pointer"
                >
                  <X size={14} />
                </button>
              )}
              <span className="text-[10px] font-mono text-slate-500 dark:text-[#8E8F99] bg-slate-100 dark:bg-white/10 px-2 py-0.5 rounded-md border border-black/[0.04] dark:border-white/5 font-semibold">
                ESC
              </span>
            </div>

            {/* Results Area */}
            <div className="flex-1 overflow-y-auto p-3 space-y-4">
              {/* Matched Wallets */}
              {filteredWallets.length > 0 && (
                <div className="space-y-1">
                  <div className="px-3 py-1 text-[10px] font-bold text-slate-400 dark:text-[#8E8F99] uppercase tracking-wider">
                    Candidate Whales (Paper Basket)
                  </div>
                  {filteredWallets.slice(0, 5).map((w) => {
                    const whaleLabel = w.name || w.pseudonym || `${w.address.slice(0, 6)}...${w.address.slice(-4)}`;
                    return (
                      <div
                        key={w.address}
                        role="button"
                        tabIndex={0}
                        aria-label={`Select whale ${whaleLabel}`}
                        onClick={() => {
                          if (onSelectWallet) onSelectWallet(w.address);
                          handleClose();
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            if (onSelectWallet) onSelectWallet(w.address);
                            handleClose();
                          }
                        }}
                        className="flex items-center justify-between p-3 rounded-2xl hover:bg-white/60 dark:hover:bg-white/[0.04] border border-transparent hover:border-sky-100/60 dark:hover:border-white/5 transition-all cursor-pointer group focus:outline-none focus:ring-1 focus:ring-indigo-500/40"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="w-8 h-8 rounded-full bg-sky-50 dark:bg-white/10 flex items-center justify-center font-bold text-xs text-slate-800 dark:text-white shrink-0 border border-sky-100/60 dark:border-white/10">
                            <Wallet size={14} />
                          </div>
                          <div className="min-w-0">
                            <span className="text-xs font-bold text-slate-900 dark:text-white truncate block">
                              {whaleLabel}
                            </span>
                            <span className="text-[10px] font-mono text-slate-400 dark:text-[#8E8F99]">
                              {w.winRate == null ? 'Unavailable' : `${(w.winRate > 1 ? w.winRate : w.winRate * 100).toFixed(0)}%`} Win Rate • {w.pnl == null ? 'Unavailable' : `$${w.pnl.toLocaleString()}`} Source PnL
                            </span>
                          </div>
                        </div>
                        <ArrowRight size={14} className="text-slate-400 group-hover:text-slate-900 dark:group-hover:text-white transition-colors" />
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Quick Navigation Commands */}
              <div className="space-y-1">
                <div className="px-3 py-1 text-[10px] font-bold text-slate-400 dark:text-[#8E8F99] uppercase tracking-wider">
                  Quick Actions &amp; Views
                </div>
                {filteredCommands.map((cmd) => {
                  const Icon = cmd.icon;
                  return (
                    <div
                      key={cmd.id}
                      role="button"
                      tabIndex={0}
                      aria-label={`Execute action: ${cmd.label}`}
                      onClick={() => executeAction(cmd.action)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          executeAction(cmd.action);
                        }
                      }}
                      className="flex items-center justify-between p-3 rounded-2xl hover:bg-white/60 dark:hover:bg-white/[0.04] border border-transparent hover:border-sky-100/60 dark:hover:border-white/5 transition-all cursor-pointer group focus:outline-none focus:ring-1 focus:ring-indigo-500/40"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-sky-50 dark:bg-white/10 flex items-center justify-center text-slate-600 dark:text-white shrink-0 border border-sky-100/60 dark:border-white/10">
                          <Icon size={15} />
                        </div>
                        <span className="text-xs font-semibold text-slate-800 dark:text-white">
                          {cmd.label}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400 dark:text-[#8E8F99]">
                        {cmd.category}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
