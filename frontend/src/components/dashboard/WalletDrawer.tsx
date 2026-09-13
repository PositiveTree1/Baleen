'use client';
import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState, useMemo } from 'react';
import { fetchWallet } from '@/lib/api-client';
import { WalletDetail } from '@/types';
import { X, ExternalLink, Copy, Check, Sparkles, AlertCircle, RotateCw } from 'lucide-react';
import { Badge } from '../ui/Badge';
import { ScoreHistoryChart } from '../charts/ScoreHistoryChart';
import { CumulativePnLChart } from '../charts/CumulativePnLChart';
import { DailyWinLossBarChart } from '../charts/DailyWinLossBarChart';
import { TypewriterText } from '../ui/TypewriterText';
import { formatCompactPnL, formatExactPnL } from '@/lib/formatters';

interface WalletDrawerProps {
  address: string | null;
  onClose: () => void;
}

export function WalletDrawer({ address, onClose }: WalletDrawerProps) {
  useEffect(() => {
    if (!address) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [address, onClose]);

  const [wallet, setWallet] = useState<WalletDetail | null>(null);
  const [loading, setLoading] = useState(Boolean(address));
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadTrigger, setReloadTrigger] = useState(0);
  const [copied, setCopied] = useState(false);
  const [activeChartTab, setActiveChartTab] = useState<'winloss' | 'pnl' | 'score'>('winloss');
  const [timeframe, setTimeframe] = useState<'1W' | '1M' | 'YTD' | 'ALL'>('ALL');

  const [prevAddress, setPrevAddress] = useState(address);
  if (prevAddress !== address) {
    setPrevAddress(address);
    setWallet(null);
    setLoadError(null);
    setLoading(Boolean(address));
  }

  useEffect(() => {
    if (!address) return;
    let active = true;
    setLoading(true);

    fetchWallet(address)
      .then((data) => {
        if (!active) return;
        if (data) {
          setWallet(data);
          setLoadError(null);
        } else {
          setLoadError("Unable to retrieve stats for this wallet. It may have no confirmed activity or Polymarket API is rate-limiting.");
        }
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setLoadError("Failed to connect to backend control plane. Please retry.");
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [address, reloadTrigger]);

  const handleRetry = () => {
    setLoading(true);
    setLoadError(null);
    setReloadTrigger(prev => prev + 1);
  };

  const handleCopy = () => {
    if (address) {
      navigator.clipboard.writeText(address);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatPct = (val: number) => {
    const num = val > 1 ? val : val * 100;
    return `${num.toFixed(1)}%`;
  };

  const isGold = wallet?.tier === 'gold_sniper';

  // Filter daily PnL history according to selected timeframe (1W, 1M, YTD, ALL)
  const filteredDailyPnLHistory = useMemo(() => {
    const raw = wallet?.dailyPnLHistory || [];
    if (timeframe === 'ALL' || raw.length === 0) return raw;
    const latestDate = raw.reduce((max, pt) => {
      const t = pt.date ? new Date(pt.date).getTime() : 0;
      return t > max ? t : max;
    }, 0);
    const now = latestDate > 0 ? latestDate : 0;
    let cutoff = 0;
    if (timeframe === '1W') cutoff = now - 7 * 24 * 60 * 60 * 1000;
    else if (timeframe === '1M') cutoff = now - 30 * 24 * 60 * 60 * 1000;
    else if (timeframe === 'YTD') {
      const yr = latestDate > 0 ? new Date(latestDate).getFullYear() : 2026;
      cutoff = new Date(yr, 0, 1).getTime();
    }

    const filtered = raw.filter(pt => {
      try {
        const t = new Date(pt.date).getTime();
        return !isNaN(t) && t >= cutoff;
      } catch {
        return true;
      }
    });
    return filtered.length > 0 ? filtered : raw;
  }, [wallet?.dailyPnLHistory, timeframe]);

  const cleanSummary = (() => {
    if (!wallet?.aiSummary) return null;
    let s = wallet.aiSummary;
    if (s.includes("Metrics Provided:") || s.includes("<2 punchy") || s.includes("TAG:") || s.includes("Deconstruct Metrics")) {
      const parts = s.split(/(?:SUMMARY|Executive Summary):/i);
      if (parts.length > 1) {
        s = parts[1].split(/(?:TAG|Tag):/i)[0].trim();
      } else {
        s = wallet.winRate != null && wallet.pnl != null
          ? `Tactical prediction trader with ${formatPct(wallet.winRate)} accuracy and ${formatExactPnL(wallet.pnl)} net profit.`
          : '';
      }
    }
    const cleaned = s.replace(/\*\*/g, '').replace(/<[^>]*>/g, '').trim();
    return cleaned || null;
  })();

  return (
    <AnimatePresence>
      {address && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 dark:bg-black/80 backdrop-blur-sm z-40"
          />

          {/* Drawer Container */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className={`fixed inset-y-0 right-0 z-50 w-full max-w-full sm:max-w-xl bg-white dark:bg-[#16171B] border-l shadow-2xl overflow-y-auto ${
              isGold ? 'border-amber-400/50 dark:border-amber-400/30' : 'border-black/[0.08] dark:border-white/10'
            }`}
          >
            <div className="p-4 sm:p-8">
              {/* Header */}
              <div className="flex items-center justify-between mb-4 sm:mb-6 pb-3 sm:pb-4 border-b border-black/[0.06] dark:border-white/10">
                <div className="flex items-center gap-3">
                  <img 
                    src={wallet?.profileImage || `https://api.dicebear.com/7.x/identicon/svg?seed=${address}`} 
                    alt="" 
                    className="w-10 h-10 rounded-full object-cover border border-black/10 dark:border-white/10 shadow-2xs shrink-0 bg-slate-100 dark:bg-[#1C1D22]" 
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-bold text-slate-950 dark:text-white tracking-tight">
                        {wallet?.name || wallet?.pseudonym || 'Observed Whale Profile'}
                      </h2>
                      {isGold && <Badge tier="gold_sniper" />}
                    </div>
                    {wallet?.pseudonym && wallet?.name && wallet.pseudonym !== wallet.name && (
                      <p className="text-xs text-slate-500 dark:text-[#8E8F99] font-mono">@{wallet.pseudonym}</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <a
                    href={`https://polymarket.com/profile/${address}`}
                    target="_blank"
                    rel="noreferrer"
                    aria-label="Open profile on Polymarket"
                    className="p-2 text-slate-400 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-[#1C1D22] rounded-xl transition-colors cursor-pointer"
                    title="Open on Polymarket"
                  >
                    <ExternalLink size={16} />
                  </a>
                  <button
                    onClick={onClose}
                    aria-label="Close wallet drawer"
                    className="p-2 text-slate-400 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-[#1C1D22] rounded-xl transition-colors cursor-pointer"
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>

              {/* Body */}
              {wallet ? (
                <div className="space-y-6">
                  {/* Address Badge & Style */}
                  <div className="flex items-center justify-between p-3.5 bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 rounded-2xl">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-slate-800 dark:text-white font-semibold">{address}</span>
                      <button
                        onClick={handleCopy}
                        aria-label="Copy address"
                        className="text-slate-400 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white transition-colors cursor-pointer"
                        title="Copy Address"
                      >
                        {copied ? <Check size={13} className="text-[#00D09C]" /> : <Copy size={13} />}
                      </button>
                    </div>

                    {wallet.aiStyleTag && (
                      <span className="text-[11px] font-bold text-slate-800 dark:text-white bg-white dark:bg-[#2C2D35] px-2.5 py-0.5 rounded-full border border-black/[0.08] dark:border-white/5 shadow-2xs">
                        {wallet.aiStyleTag}
                      </span>
                    )}
                  </div>

                  {/* AI Quantitative Executive Summary */}
                  <div className="p-5 rounded-3xl relative overflow-hidden bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 shadow-sm">
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className={`p-1 rounded-lg ${isGold ? 'bg-amber-100 dark:bg-amber-400/10 text-amber-800 dark:text-amber-400' : 'bg-indigo-100 dark:bg-indigo-500/10 text-indigo-800 dark:text-indigo-400'}`}>
                            <Sparkles size={13} />
                          </div>
                          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                            Quantitative Strategy Synopsis
                          </h4>
                        </div>
                        <span className="text-[10px] font-mono font-semibold text-indigo-700 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/10 px-2.5 py-0.5 rounded-full border border-indigo-200/80 dark:border-indigo-500/20">
                          Llama 3.1 70B
                        </span>
                      </div>
                      <p className="text-sm text-slate-900 dark:text-white leading-relaxed font-medium min-h-[48px]">
                        <TypewriterText 
                          text={cleanSummary || 'Automated quantitative analysis computed via Groq Llama-3.1 engine based on on-chain trading behavior.'}
                          speed={8}
                          delay={150}
                        />
                      </p>
                    </div>
                  </div>

                  {/* Key Metrics Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-4 bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 rounded-2xl">
                      <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">Baleen Score</span>
                      <div className="text-xl font-bold font-mono text-slate-950 dark:text-white mt-0.5">
                        {wallet.score == null ? 'Unavailable' : wallet.score.toFixed(1)}
                      </div>
                      <span className="text-[10px] text-slate-400 dark:text-[#8E8F99]">Out of 100</span>
                    </div>

                    <div className="p-4 bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 rounded-2xl">
                      <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">Win Rate</span>
                      <div className="text-xl font-bold font-mono text-emerald-600 dark:text-[#00D09C] mt-0.5">
                        {wallet.winRate == null ? 'Unavailable' : formatPct(wallet.winRate)}
                      </div>
                      <span className="text-[10px] text-slate-400 dark:text-[#8E8F99]">Resolved Outcomes</span>
                    </div>

                    <div className="p-4 bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 rounded-2xl">
                      <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">Source Wallet PnL</span>
                      <div className={`text-xl font-bold font-mono mt-0.5 ${wallet.pnl == null ? 'text-slate-400 dark:text-[#8E8F99]' : wallet.pnl >= 0 ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                        {wallet.pnl == null ? 'Unavailable' : formatCompactPnL(wallet.pnl)}
                      </div>
                      <span className="text-[10px] text-slate-400 dark:text-[#8E8F99]">Source Historical Net</span>
                    </div>

                    <div className="p-4 bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5 rounded-2xl">
                      <span className="text-[10px] uppercase font-bold text-slate-400 dark:text-[#8E8F99]">Median Inter-trade Gap</span>
                      <div className="text-xl font-bold font-mono text-slate-950 dark:text-white mt-0.5">
                        {(() => {
                          const hrs = wallet.medianInterTradeGapHours;
                          if (hrs == null) return 'Unavailable';
                          return hrs >= 24 ? `${(hrs / 24).toFixed(1)}d` : `${hrs.toFixed(1)}h`;
                        })()}
                      </div>
                      <span className="text-[10px] text-slate-400 dark:text-[#8E8F99]">Between observed trades, not position duration</span>
                    </div>
                  </div>

                  {/* Chart Container Card */}
                  <div className="p-5 bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 rounded-3xl space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-black/[0.04] dark:border-white/5 pb-3">
                      {/* Sub-tabs */}
                      <div className="flex rounded-full bg-slate-200 dark:bg-[#2C2D35] p-0.5 text-xs font-bold">
                        <button
                          onClick={() => setActiveChartTab('winloss')}
                          className={`px-3 py-1 rounded-full transition-all ${activeChartTab === 'winloss' ? 'bg-white dark:bg-[#16171B] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99]'}`}
                        >
                          Daily Wins / Losses
                        </button>
                        <button
                          onClick={() => setActiveChartTab('pnl')}
                          className={`px-3 py-1 rounded-full transition-all ${activeChartTab === 'pnl' ? 'bg-white dark:bg-[#16171B] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99]'}`}
                        >
                          Cumulative PnL
                        </button>
                        <button
                          onClick={() => setActiveChartTab('score')}
                          className={`px-3 py-1 rounded-full transition-all ${activeChartTab === 'score' ? 'bg-white dark:bg-[#16171B] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99]'}`}
                        >
                          Score History
                        </button>
                      </div>

                      {/* Timeframe pills */}
                      <div className="flex rounded-full bg-slate-200 dark:bg-[#2C2D35] p-0.5 text-[10px] font-bold">
                        {(['1W', '1M', 'YTD', 'ALL'] as const).map(tf => (
                          <button
                            key={tf}
                            onClick={() => setTimeframe(tf)}
                            className={`px-2 py-0.5 rounded-full transition-all ${timeframe === tf ? 'bg-white dark:bg-[#16171B] text-slate-950 dark:text-white shadow-2xs' : 'text-slate-500 dark:text-[#8E8F99]'}`}
                          >
                            {tf}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Chart Container */}
                    <div className="h-56 w-full">
                      {activeChartTab === 'winloss' && (
                        <DailyWinLossBarChart data={filteredDailyPnLHistory} />
                      )}
                      {activeChartTab === 'pnl' && (
                        <CumulativePnLChart 
                          data={(() => {
                            if (!filteredDailyPnLHistory || filteredDailyPnLHistory.length === 0) return [];
                            if (timeframe === 'ALL') {
                              return filteredDailyPnLHistory.map(p => ({
                                date: p.date,
                                dailyPnL: p.dailyPnL ?? p.netPnL ?? 0,
                                cumulativePnL: p.cumulativePnL ?? p.dailyPnL ?? 0
                              }));
                            }
                            // Rebase cumulative PnL for selected window (1W, 1M, YTD)
                            let running = 0;
                            return filteredDailyPnLHistory.map(p => {
                              const daily = p.dailyPnL ?? p.netPnL ?? 0;
                              running += daily;
                              return {
                                date: p.date,
                                dailyPnL: daily,
                                cumulativePnL: Math.round(running * 100) / 100
                              };
                            });
                          })()} 
                        />
                      )}
                      {activeChartTab === 'score' && (
                        <ScoreHistoryChart data={wallet.scoreHistory || []} />
                      )}
                    </div>
                  </div>
                </div>
              ) : loadError && !loading ? (
                <div className="flex flex-col items-center justify-center p-8 text-center rounded-2xl bg-red-500/5 dark:bg-red-500/10 border border-red-500/20 space-y-4 my-8">
                  <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center text-red-500">
                    <AlertCircle size={24} />
                  </div>
                  <div className="space-y-1 max-w-sm">
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Unable to Load Wallet Stats</h3>
                    <p className="text-xs text-slate-500 dark:text-[#8E8F99] leading-relaxed">{loadError}</p>
                  </div>
                  <button
                    onClick={handleRetry}
                    className="flex items-center gap-2 px-4 py-2 bg-[#00D09C] hover:bg-[#00B084] text-black font-semibold text-xs rounded-xl transition-colors cursor-pointer shadow-xs"
                  >
                    <RotateCw size={14} />
                    <span>Retry Analysis</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="w-full h-12 rounded-2xl animate-shimmer" />
                  <div className="w-full h-20 rounded-2xl animate-shimmer" />
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[1, 2, 3, 4].map(i => (
                      <div key={i} className="h-20 rounded-2xl animate-shimmer" />
                    ))}
                  </div>
                  <div className="w-full h-56 rounded-2xl animate-shimmer" />
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
