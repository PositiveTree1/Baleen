'use client';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { ReactNode, useEffect, useRef, useId, useSyncExternalStore } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

const emptySubscribe = () => () => {};
const getClientSnapshot = () => true;
const getServerSnapshot = () => false;

function useIsClient() {
  return useSyncExternalStore(emptySubscribe, getClientSnapshot, getServerSnapshot);
}

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: ReactNode;
  title?: string;
  subtitle?: string;
  ariaLabel?: string;
  ariaDescribedBy?: string;
  className?: string;
  contentClassName?: string;
  maxWidth?: string;
  initialFocusRef?: React.RefObject<HTMLElement | null>;
  hideCloseButton?: boolean;
}

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([type="hidden"]):not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (el) =>
      !el.hasAttribute('disabled') &&
      el.getAttribute('aria-hidden') !== 'true' &&
      !el.closest('[aria-hidden="true"]') &&
      (el.offsetWidth > 0 || el.offsetHeight > 0 || el.getClientRects().length > 0)
  );
}

// Global reference counting for background scroll-lock and inertness
let activeModalCount = 0;
let originalBodyOverflow = '';
let originalBodyPaddingRight = '';
const originalInertStates = new Map<HTMLElement, { inert: boolean; ariaHidden: string | null }>();

function lockBackground() {
  activeModalCount++;
  if (activeModalCount === 1) {
    if (typeof window !== 'undefined' && typeof document !== 'undefined') {
      // 1. Scroll lock with scrollbar width compensation
      originalBodyOverflow = document.body.style.overflow;
      originalBodyPaddingRight = document.body.style.paddingRight;
      const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
      document.body.style.overflow = 'hidden';
      if (scrollbarWidth > 0) {
        document.body.style.paddingRight = `${scrollbarWidth}px`;
      }

      // 2. Background inertness: make all siblings of modal portal inert and aria-hidden
      const siblings = Array.from(document.body.children).filter(
        (el): el is HTMLElement =>
          el instanceof HTMLElement &&
          !el.hasAttribute('data-baleen-modal-portal') &&
          el.tagName !== 'SCRIPT' &&
          el.tagName !== 'STYLE'
      );

      siblings.forEach((el) => {
        originalInertStates.set(el, {
          inert: Boolean(el.inert),
          ariaHidden: el.getAttribute('aria-hidden'),
        });
        el.setAttribute('aria-hidden', 'true');
        el.setAttribute('inert', '');
        el.inert = true;
      });
    }
  }
}

function unlockBackground() {
  activeModalCount = Math.max(0, activeModalCount - 1);
  if (activeModalCount === 0) {
    if (typeof document !== 'undefined') {
      // 1. Restore scroll
      document.body.style.overflow = originalBodyOverflow;
      document.body.style.paddingRight = originalBodyPaddingRight;

      // 2. Restore inertness
      originalInertStates.forEach((state, el) => {
        if (document.contains(el)) {
          if (state.inert) {
            el.setAttribute('inert', '');
            el.inert = true;
          } else {
            el.removeAttribute('inert');
            el.inert = false;
          }

          if (state.ariaHidden !== null) {
            el.setAttribute('aria-hidden', state.ariaHidden);
          } else {
            el.removeAttribute('aria-hidden');
          }
        }
      });
      originalInertStates.clear();
    }
  }
}

export function Modal({
  isOpen,
  onClose,
  children,
  title,
  subtitle,
  ariaLabel,
  ariaDescribedBy,
  className = '',
  contentClassName,
  maxWidth = 'max-w-lg',
  initialFocusRef,
  hideCloseButton = false,
}: ModalProps) {
  const isClient = useIsClient();
  const cardRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const triggerElementRef = useRef<HTMLElement | null>(null);

  const titleId = useId();
  const descriptionId = useId();
  const shouldReduceMotion = useReducedMotion();

  // Capture trigger element before opening, restore focus on closing
  useEffect(() => {
    if (isOpen) {
      triggerElementRef.current = (document.activeElement as HTMLElement) || null;
      lockBackground();
      return () => {
        unlockBackground();
      };
    } else if (triggerElementRef.current) {
      const trigger = triggerElementRef.current;
      triggerElementRef.current = null;
      if (document.contains(trigger)) {
        trigger.focus();
      } else {
        const main = document.querySelector('main') || document.body;
        if (main && typeof main.focus === 'function') {
          main.focus();
        }
      }
    }
  }, [isOpen]);

  // Clean up focus restoration on unmount
  useEffect(() => {
    return () => {
      if (triggerElementRef.current) {
        const trigger = triggerElementRef.current;
        triggerElementRef.current = null;
        if (document.contains(trigger)) {
          trigger.focus();
        }
      }
    };
  }, []);

  // Global document-level keydown handler for focus trap and Escape
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        onClose();
        return;
      }

      if (e.key !== 'Tab') return;

      const container = cardRef.current;
      if (!container) return;

      const focusableElements = getFocusableElements(container);

      if (focusableElements.length === 0) {
        e.preventDefault();
        container.focus();
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      const activeElement = document.activeElement;

      if (e.shiftKey) {
        if (activeElement === firstElement || !container.contains(activeElement)) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        if (activeElement === lastElement || !container.contains(activeElement)) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown, true);
    return () => {
      document.removeEventListener('keydown', handleKeyDown, true);
    };
  }, [isOpen, onClose]);

  // Set initial focus upon opening
  useEffect(() => {
    if (!isOpen) return;

    const frameId = requestAnimationFrame(() => {
      if (initialFocusRef?.current) {
        initialFocusRef.current.focus();
        return;
      }

      const container = cardRef.current;
      if (!container) return;

      // Look for explicit autofocus element
      const autoFocusTarget = container.querySelector<HTMLElement>(
        '[data-autofocus], [autofocus]'
      );
      if (autoFocusTarget && !autoFocusTarget.hasAttribute('disabled')) {
        autoFocusTarget.focus();
        return;
      }

      // Default to first enabled, visible focusable element or close button
      const focusable = getFocusableElements(container);
      if (focusable.length > 0) {
        focusable[0].focus();
      } else if (closeButtonRef.current) {
        closeButtonRef.current.focus();
      } else {
        container.focus();
      }
    });

    return () => cancelAnimationFrame(frameId);
  }, [isOpen, initialFocusRef]);

  // Motion variants supporting reduced motion preferences
  const backdropMotion = {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
    transition: { duration: shouldReduceMotion ? 0 : 0.2 },
  };

  const dialogMotion = {
    initial: shouldReduceMotion
      ? { opacity: 1, scale: 1, y: 0 }
      : { opacity: 0, scale: 0.96, y: 12 },
    animate: { opacity: 1, scale: 1, y: 0 },
    exit: shouldReduceMotion
      ? { opacity: 0, scale: 1, y: 0 }
      : { opacity: 0, scale: 0.96, y: 12 },
    transition: {
      duration: shouldReduceMotion ? 0 : 0.2,
      ease: [0.16, 1, 0.3, 1] as [number, number, number, number],
    },
  };

  if (!isClient || typeof document === 'undefined') {
    return null;
  }

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <div
          data-baleen-modal-portal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 overflow-y-auto overscroll-contain"
        >
          {/* Accessible Backdrop */}
          <motion.div
            {...backdropMotion}
            onClick={onClose}
            className="fixed inset-0 glass-modal-backdrop"
            aria-hidden="true"
          />

          {/* Dialog Container */}
          <motion.div
            {...dialogMotion}
            className={`relative z-10 w-full ${maxWidth} max-h-[calc(100dvh-2rem)] flex flex-col glass-modal rounded-[24px] sm:rounded-[28px] overflow-hidden focus:outline-none ${className}`}
            role="dialog"
            aria-modal="true"
            aria-labelledby={title ? titleId : undefined}
            aria-describedby={subtitle ? descriptionId : ariaDescribedBy}
            aria-label={!title ? ariaLabel || 'Dialog Window' : undefined}
            tabIndex={-1}
            ref={cardRef}
          >
            {/* Header */}
            {title ? (
              <div className="flex justify-between items-center px-5 sm:px-6 py-4 border-b border-white/10 bg-white/[0.02] shrink-0">
                <div className="pr-4">
                  <h3
                    id={titleId}
                    className="text-sm sm:text-base font-bold text-white tracking-tight"
                  >
                    {title}
                  </h3>
                  {subtitle && (
                    <p
                      id={descriptionId}
                      className="text-xs text-slate-400 mt-0.5"
                    >
                      {subtitle}
                    </p>
                  )}
                </div>
                {!hideCloseButton && (
                  <button
                    ref={closeButtonRef}
                    type="button"
                    onClick={onClose}
                    aria-label="Close dialog"
                    className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/40 ml-auto shrink-0 cursor-pointer"
                  >
                    <X size={16} aria-hidden="true" />
                  </button>
                )}
              </div>
            ) : !hideCloseButton ? (
              <button
                ref={closeButtonRef}
                type="button"
                onClick={onClose}
                aria-label="Close dialog"
                className="absolute top-4 right-4 z-20 w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/40 cursor-pointer"
              >
                <X size={16} aria-hidden="true" />
              </button>
            ) : null}

            {/* Scrollable Body */}
            <div
              className={
                contentClassName ??
                'p-5 sm:p-6 text-white overflow-y-auto overscroll-contain flex-1'
              }
            >
              {children}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body
  );
}
