'use client';
import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Command, ArrowRight, Wallet, Activity, ShieldCheck, Sparkles, Volume2, VolumeX, RotateCw, ExternalLink, X } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { soundFx } from '@/lib/sound';

interface CommandPaletteProps {
  onSelectWallet?: (address: string) => void;
}

export function CommandPalette({ onSelectWallet }: CommandPaletteProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [soundEnabled, setSoundEnabled] = useState(false);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const toggleSound = () => {
    const next = soundFx.toggleSound();
    setSoundEnabled(next);
  };

  const executeAction = (action: () => void) => {
    soundFx.playChime('click');
    action();
    setIsOpen(false);
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
      id: 'sound',
      label: soundEnabled ? 'Mute Trade Signal Chimes' : 'Enable Live Signal Audio Chimes',
      category: 'Audio & FX',
      icon: soundEnabled ? VolumeX : Volume2,
      action: toggleSound,
    },
    {
      id: 'polymarket',
      label: 'Open Polymarket Live Prediction Terminal',
      category: 'External',
      icon: ExternalLink,
      action: () => window.open('https://polymarket.com', '_blank'),
    },
  ];

  const filteredCommands = defaultCommands.filter(
    (c) =>
      c.label.toLowerCase().includes(query.toLowerCase()) ||
      c.category.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <>
      {/* Keyboard Shortcut Hint in bottom-right corner */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-40 hidden sm:flex items-center gap-2 px-3.5 py-2 rounded-2xl bg-white/90 hover:bg-white text-slate-700 border border-black/[0.08] shadow-[0_4px_16px_rgba(0,0,0,0.08)] backdrop-blur-xl transition-all hover:scale-105 active:scale-95 text-xs font-semibold cursor-pointer group"
      >
        <Command size={13} className="text-slate-400 group-hover:text-slate-900 transition-colors" />
        <span className="font-mono text-[11px] text-slate-500">Quick Command</span>
        <kbd className="px-1.5 py-0.5 rounded-md bg-slate-100 border border-black/[0.06] text-[10px] font-mono font-bold text-slate-600">
          ⌘K
        </kbd>
      </button>

      {/* Modal Overlay */}
      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4 overflow-y-auto">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="fixed inset-0 bg-slate-950/40 backdrop-blur-md cursor-pointer"
            />

            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -15 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              className="relative w-full max-w-xl rounded-3xl bg-white border border-black/[0.1] shadow-2xl overflow-hidden z-10"
            >
              {/* Search Bar Input */}
              <div className="flex items-center gap-3 p-4 px-6 border-b border-black/[0.06] bg-slate-50/50">
                <Search size={18} className="text-slate-400 shrink-0" />
                <input
                  ref={inputRef}
                  type="text"
                  placeholder="Type a command, search 0x address, or navigate..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full bg-transparent text-sm text-slate-900 placeholder-slate-400 focus:outline-none font-medium"
                />
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1 text-slate-400 hover:text-slate-700 rounded-lg transition-colors cursor-pointer"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Action List */}
              <div className="p-3 max-h-[340px] overflow-y-auto space-y-1">
                {query.startsWith('0x') && onSelectWallet && (
                  <div
                    onClick={() => executeAction(() => onSelectWallet(query))}
                    className="flex items-center justify-between p-3 rounded-2xl bg-indigo-50/80 hover:bg-indigo-100/80 border border-indigo-200 text-xs font-semibold text-indigo-950 cursor-pointer group"
                  >
                    <div className="flex items-center gap-3">
                      <Wallet size={16} className="text-indigo-600" />
                      <div>
                        <div className="font-bold">Inspect Whale Audit</div>
                        <div className="text-[11px] font-mono text-indigo-700">{query}</div>
                      </div>
                    </div>
                    <ArrowRight size={14} className="text-indigo-600 group-hover:translate-x-1 transition-transform" />
                  </div>
                )}

                {filteredCommands.map((cmd) => (
                  <div
                    key={cmd.id}
                    onClick={() => executeAction(cmd.action)}
                    className="flex items-center justify-between p-3 rounded-2xl hover:bg-slate-100 text-xs font-semibold text-slate-800 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-xl bg-slate-100 group-hover:bg-white text-slate-700 shadow-sm border border-black/[0.04]">
                        <cmd.icon size={15} />
                      </div>
                      <div>
                        <div className="text-slate-900">{cmd.label}</div>
                        <div className="text-[10px] font-mono text-slate-400">{cmd.category}</div>
                      </div>
                    </div>
                    <ArrowRight size={14} className="text-slate-400 group-hover:text-slate-900 group-hover:translate-x-1 transition-all" />
                  </div>
                ))}
              </div>

              {/* Footer */}
              <div className="p-3 px-6 bg-slate-50 border-t border-black/[0.06] flex items-center justify-between text-[11px] text-slate-500 font-medium">
                <div className="flex items-center gap-4">
                  <span>Navigation: <kbd className="font-mono bg-white px-1.5 py-0.5 rounded border shadow-xs">↑↓</kbd></span>
                  <span>Select: <kbd className="font-mono bg-white px-1.5 py-0.5 rounded border shadow-xs">↵</kbd></span>
                </div>
                <div className="font-mono font-bold text-slate-700">
                  BALEEN PROTOCOL
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
