'use client';
import { motion, AnimatePresence } from 'framer-motion';
import { ReactNode, useEffect } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  title?: string;
}

export function Modal({ isOpen, onClose, children, title }: ModalProps) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/40 dark:bg-black/80 backdrop-blur-md"
            aria-hidden="true"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
            role="dialog"
            aria-modal="true"
            aria-label={title || "Dialog Window"}
          >
            <div className="bg-white dark:bg-[#16171B] rounded-[28px] border border-black/[0.08] dark:border-white/10 shadow-2xl w-full max-w-lg overflow-hidden pointer-events-auto">
              <div className="flex justify-between items-center px-6 py-4 border-b border-black/[0.06] dark:border-white/10 bg-[#F8F9FB] dark:bg-[#1C1D22]/60">
                {title && <h3 className="text-sm font-bold text-slate-950 dark:text-white tracking-tight">{title}</h3>}
                <button 
                  onClick={onClose}
                  aria-label="Close dialog"
                  className="w-8 h-8 rounded-full flex items-center justify-center text-slate-500 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/10 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C]"
                >
                  <X size={16} aria-hidden="true" />
                </button>
              </div>
              <div className="p-6 text-slate-900 dark:text-white">
                {children}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
