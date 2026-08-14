'use client';
import { motion, AnimatePresence } from 'framer-motion';
import { ReactNode } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  title?: string;
}

export function Modal({ isOpen, onClose, children, title }: ModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 16 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
          >
            <div className="bg-white rounded-3xl border border-black/10 shadow-[0_20px_50px_rgba(0,0,0,0.15)] w-full max-w-lg overflow-hidden pointer-events-auto">
              <div className="flex justify-between items-center p-5 border-b border-black/[0.06] bg-zinc-50/50">
                {title && <h3 className="text-base font-semibold text-zinc-900 tracking-tight">{title}</h3>}
                <button onClick={onClose} className="p-1 text-zinc-400 hover:text-zinc-700 hover:bg-black/5 rounded-full transition-colors">
                  <X size={18} />
                </button>
              </div>
              <div className="p-6">
                {children}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
