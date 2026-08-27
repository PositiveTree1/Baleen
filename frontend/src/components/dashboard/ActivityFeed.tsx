'use client';
import { useEffect, useState, useCallback } from 'react';
import { fetchSystemEvents } from '@/lib/api-client';
import { X, Bell, Filter, TrendingUp, AlertTriangle, CheckCircle2, Info, Wallet, ShieldAlert } from 'lucide-react';
import { SystemEvent } from '@/types';

interface ActivityFeedProps {
  isOpen: boolean;
  onClose: () => void;
}

const EVENT_ICONS: Record<string, { icon: React.ReactNode; color: string; bg: string }> = {
  TRADE_COPIED: { icon: <TrendingUp size={14} />, color: 'text-emerald-600 dark:text-[#00D09C]', bg: 'bg-emerald-50 dark:bg-[#00D09C]/10 border-emerald-200 dark:border-[#00D09C]/20' },
  TRADE_SKIPPED_SLIPPAGE: { icon: <ShieldAlert size={14} />, color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/20' },
  TRADE_SKIPPED_EV: { icon: <AlertTriangle size={14} />, color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/20' },
  TRADE_SKIPPED_CATEGORY: { icon: <AlertTriangle size={14} />, color: 'text-orange-600 dark:text-orange-400', bg: 'bg-orange-50 dark:bg-orange-500/10 border-orange-200 dark:border-orange-500/20' },
  WALLET_DISCOVERED: { icon: <Wallet size={14} />, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-500/10 border-blue-200 dark:border-blue-500/20' },
  WALLET_PROMOTED: { icon: <CheckCircle2 size={14} />, color: 'text-emerald-600 dark:text-[#00D09C]', bg: 'bg-emerald-50 dark:bg-[#00D09C]/10 border-emerald-200 dark:border-[#00D09C]/20' },
  WALLET_REJECTED: { icon: <ShieldAlert size={14} />, color: 'text-rose-600 dark:text-[#FF453A]', bg: 'bg-rose-50 dark:bg-[#FF453A]/10 border-rose-200 dark:border-[#FF453A]/20' },
};

const DEFAULT_ICON = { icon: <Info size={14} />, color: 'text-slate-600 dark:text-slate-400', bg: 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700' };

function timeAgo(dateStr: string): string {
  if (!dateStr) return '';
  try {
    const diff = Date.now() - new Date(dateStr).getTime();
    const secs = Math.floor(diff / 1000);
    if (secs < 60) return `${secs}s ago`;
    const mins = Math.floor(secs / 60);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  } catch {
    return '';
  }
}

export function ActivityFeed({ isOpen, onClose }: ActivityFeedProps) {
  const [events, setEvents] = useState<SystemEvent[]>([]);
  const [filter, setFilter] = useState<string>('all');

  const loadEvents = useCallback(async () => {
    const data = await fetchSystemEvents(200, filter === 'all' ? undefined : filter);
    if (data && data.length > 0) setEvents(data as any);
  }, [filter]);

  useEffect(() => {
    if (!isOpen) return;
    loadEvents();
    const interval = setInterval(loadEvents, 5000);
    return () => clearInterval(interval);
  }, [isOpen, loadEvents]);

  if (!isOpen) return null;

  const filters = [
    { key: 'all', label: 'All' },
    { key: 'TRADE_COPIED', label: 'Trades' },
    { key: 'WALLET_PROMOTED', label: 'Wallets' },
    { key: 'TRADE_SKIPPED_SLIPPAGE', label: 'Skipped' },
  ];

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 dark:bg-black/80 backdrop-blur-sm z-50 transition-opacity"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-full max-w-md bg-white dark:bg-[#16171B] border-l border-black/[0.08] dark:border-white/10 shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-black/[0.06] dark:border-white/10 bg-slate-50 dark:bg-[#1C1D22]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/20">
              <Bell size={16} />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-white">Activity Feed</h2>
              <p className="text-[11px] text-slate-500 dark:text-[#8E8F99] font-medium">{events.length} events</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl hover:bg-slate-200/60 dark:hover:bg-[#2C2D35] text-slate-400 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white transition-colors cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-1.5 px-5 py-3 border-b border-black/[0.04] dark:border-white/5 overflow-x-auto">
          <Filter size={12} className="text-slate-400 dark:text-[#8E8F99] shrink-0" />
          {filters.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-3 py-1 rounded-full text-[11px] font-semibold transition-all cursor-pointer whitespace-nowrap ${
                filter === f.key
                  ? 'bg-slate-900 dark:bg-white text-white dark:text-black shadow-2xs'
                  : 'text-slate-500 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-[#1C1D22]'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Events List */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          {events.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-slate-400 dark:text-[#8E8F99]">
              <Bell size={28} className="mb-3 opacity-40" />
              <p className="text-sm font-medium">No events yet</p>
              <p className="text-xs">System notifications will appear here</p>
            </div>
          ) : (
            events.map((evt) => {
              const style = EVENT_ICONS[evt.eventType] || DEFAULT_ICON;
              return (
                <div
                  key={evt.id}
                  className="p-3.5 rounded-2xl bg-white dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 shadow-2xs hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start gap-2.5">
                    <div className={`p-1.5 rounded-lg border shrink-0 mt-0.5 ${style.bg}`}>
                      <span className={style.color}>{style.icon}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-bold text-slate-900 dark:text-white truncate">
                          {evt.title}
                        </span>
                        <span className="text-[10px] text-slate-400 dark:text-[#8E8F99] font-mono shrink-0">
                          {timeAgo(evt.createdAt)}
                        </span>
                      </div>
                      {evt.detail && (
                        <p className="text-[11px] text-slate-600 dark:text-[#8E8F99] mt-1 leading-relaxed line-clamp-2">
                          {evt.detail}
                        </p>
                      )}
                      {evt.relatedAddress && (
                        <span className="inline-block mt-1.5 text-[10px] font-mono text-slate-500 dark:text-[#8E8F99] bg-slate-50 dark:bg-[#2C2D35] px-1.5 py-0.5 rounded border border-black/[0.04] dark:border-white/5">
                          {evt.relatedAddress.slice(0, 6)}...{evt.relatedAddress.slice(-4)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </>
  );
}
