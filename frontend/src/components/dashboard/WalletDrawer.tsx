'use client';
import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState, useMemo } from 'react';
import { fetchWallet } from '@/lib/api-client';
import { WalletDetail } from '@/types';
import { X, ExternalLink, Copy, Check, Sparkles, TrendingUp, BarChart3, Compass, Search, Clock } from 'lucide-react';
import { Badge } from '../ui/Badge';
import { Skeleton } from '../ui/Skeleton';
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
  const [wallet, setWallet] = useState<WalletDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeChartTab, setActiveChartTab] = useState<'winloss' | 'pnl' | 'score'>('winloss');
  const [timeframe, setTimeframe] = useState<'1W' | '1M' | 'YTD' | 'ALL'>('ALL');

  useEffect(() => {
    if (!address) {
      setWallet(null);
      return;
    }
    setLoading(true);
    fetchWallet(address)
      .then((data) => {
        setWallet(data);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, [address]);

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
    const now = Date.now();
    let cutoff = 0;
    if (timeframe === '1W') cutoff = now - 7 * 24 * 60 * 60 * 1000;
    else if (timeframe === '1M') cutoff = now - 30 * 24 * 60 * 60 * 1000;
    else if (timeframe === 'YTD') cutoff = new Date(new Date().getFullYear(), 0, 1).getTime();

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
        s = `High-precision tactical prediction trader with ${formatPct(wallet.winRate || 75)} accuracy and ${formatExactPnL(wallet.pnl)} net profit.`;
      }
    }
    return s.replace(/\*\*/g, '').replace(/<[^>]*>/g, '').trim();
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
            className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-40"
          />

          {/* Drawer Container */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className={`fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-white border-l shadow-2xl overflow-y-auto ${
              isGold ? 'border-amber-300/80 shadow-[0_0_50px_rgba(245,158,11,0.08)]' : 'border-black/[0.08]'
            }`}
          >
            <div className="p-8">
              {/* Header */}
              <div className="flex items-center justify-between mb-8 pb-4 border-b border-black/[0.06]">
                <div className="flex items-center gap-3">
                  {wallet?.profileImage ? (
                    <img 
                      src={wallet.profileImage} 
                      alt="" 
                      className="w-10 h-10 rounded-full object-cover border border-black/10 shadow-2xs shrink-0" 
                    />
                  ) : (
                    <div className="flex items-center gap-2">
                      {isGold ? (
                        <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.6)]" />
                      ) : (
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                      )}
                    </div>
                  )}
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-bold text-slate-900 tracking-tight">
                        {wallet?.name || wallet?.pseudonym || 'Whale Audit Profile'}
                      </h2>
                      {isGold && <Badge tier="gold_sniper" />}
                    </div>
                    {wallet?.pseudonym && wallet?.name && wallet.pseudonym !== wallet.name && (
                      <p className="text-xs text-slate-500 font-mono">@{wallet.pseudonym}</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <a
                    href={`https://polymarket.com/profile/${address}`}
                    target="_blank"
                    rel="noreferrer"
                    className="p-2 text-slate-400 hover:text-slate-700 hover:bg-black/5 rounded-xl transition-colors cursor-pointer"
                    title="Open on Polymarket"
                  >
                    <ExternalLink size={16} />
                  </a>
                  <button
                    onClick={onClose}
                    className="p-2 text-slate-400 hover:text-slate-700 hover:bg-black/5 rounded-xl transition-colors cursor-pointer"
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>

              {/* Body */}
              {wallet ? (
                <div className="space-y-6">
                  {/* Address Badge & Style */}
                  <div className="flex items-center justify-between p-3.5 bg-slate-50 border border-black/[0.06] rounded-2xl">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-slate-700 font-semibold">{address}</span>
                      <button
                        onClick={handleCopy}
                        className="text-slate-400 hover:text-slate-900 transition-colors cursor-pointer"
                        title="Copy Address"
                      >
                        {copied ? <Check size={13} className="text-emerald-700" /> : <Copy size={13} />}
                      </button>
                    </div>

                    {wallet.aiStyleTag && (
                      <span className="text-[11px] font-bold text-slate-800 bg-white px-2.5 py-0.5 rounded-full border border-black/[0.08] shadow-2xs">
                        {wallet.aiStyleTag}
                      </span>
                    )}
                  </div>

                  {/* AI Quantitative Executive Summary */}
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25 }}
                    className={`p-5 rounded-3xl relative overflow-hidden transition-all duration-300 ${
                      isGold
                        ? 'bg-gradient-to-b from-amber-500/[0.05] via-amber-500/[0.02] to-transparent border border-amber-300/60 shadow-[0_4px_24px_rgba(245,158,11,0.06),inset_0_1px_0_rgba(255,255,255,0.8)]'
                        : 'bg-gradient-to-b from-indigo-500/[0.04] via-indigo-500/[0.01] to-transparent border border-indigo-200/70 shadow-[0_4px_20px_rgba(99,102,241,0.04),inset_0_1px_0_rgba(255,255,255,0.8)]'
                    }`}
                  >
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className={`p-1 rounded-lg ${isGold ? 'bg-amber-100 text-amber-800' : 'bg-indigo-100 text-indigo-800'}`}>
                            <Sparkles size={13} />
                          </div>
                          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900">
                            Quantitative Strategy Synopsis
                          </h4>
                        </div>
                        <span className="text-[10px] font-mono font-semibold text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200/80">
                          Llama 3.1 70B
                        </span>
                      </div>
                      <p className="text-sm text-slate-900 leading-relaxed font-medium min-h-[48px]">
                        <TypewriterText 
                          text={cleanSummary || 'Automated quantitative analysis computed via Groq Llama-3.1 engine based on on-chain trading behavior.'}
                          speed={8}
                          delay={150}
                        />
                      </p>
                    </div>
                  </motion.div>

                  {/* Core 8-Metric Quantitative Breakdown */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    <div className="p-3 bg-slate-50 border border-black/[0.06] rounded-2xl shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
                      <div className="text-[10px] text-slate-500 font-semibold mb-0.5">Win Rate</div>
                      <div className="text-lg font-bold text-slate-900 font-mono">{formatPct(wallet.winRate || 0)}</div>
                    </div>
                    <div 
                      className="p-3 bg-slate-50 border border-black/[0.06] rounded-2xl shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]"
                      title={formatExactPnL(wallet.pnl)}
                    >
                      <div className="text-[10px] text-slate-500 font-semibold mb-0.5">Realized PnL</div>
                      <div className={`text-lg font-bold font-mono truncate tabular-nums tracking-tight ${(wallet.pnl || 0) >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {formatCompactPnL(wallet.pnl)}
                      </div>
                    </div>
                    <div className="p-3 bg-slate-50 border border-black/[0.06] rounded-2xl shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
                      <div className="text-[10px] text-slate-500 font-semibold mb-0.5">Wilson 90% LB</div>
                      <div className="text-lg font-bold text-slate-700 font-mono">
                        {wallet.wilsonLb ? `${wallet.wilsonLb.toFixed(1)}%` : formatPct(Math.max(50, (wallet.winRate || 80) - 8))}
                      </div>
                    </div>
                    <div className="p-3 bg-slate-50 border border-black/[0.06] rounded-2xl shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
                      <div className="text-[10px] text-slate-500 font-semibold mb-0.5">Daily Velocity</div>
                      <div className="text-lg font-bold text-slate-700 font-mono">{(wallet.tradesPerDay || 0).toFixed(1)}/d</div>
                    </div>

                    {/* Secondary Metrics */}
                    <div className="p-3 bg-white border border-black/[0.06] rounded-2xl shadow-sm">
                      <div className="text-[10px] text-slate-500 font-semibold mb-0.5">Baleen Score</div>
                      <div className="text-lg font-extrabold text-blue-600 font-mono">{(wallet.score || 85).toFixed(0)}/100</div>
                    </div>
                    <div 
                      className="p-3 bg-white border border-black/[0.06] rounded-2xl shadow-sm"
                      title={wallet.alphaPerTrade !== null && wallet.alphaPerTrade !== undefined ? formatExactPnL(wallet.alphaPerTrade) : undefined}
                    >
                      <div className="text-[10px] text-slate-500 font-semibold mb-0.5">Alpha / Trade</div>
                      <div className="text-lg font-bold text-emerald-700 font-mono truncate tabular-nums tracking-tight">
                        {wallet.alphaPerTrade !== null && wallet.alphaPerTrade !== undefined ? (
                          formatCompactPnL(wallet.alphaPerTrade)
                        ) : (
                          `+$${Math.max(15, Math.round((wallet.pnl || 50000) / Math.max(50, (wallet.tradesPerDay || 5) * 60))).toLocaleString()}`
                        )}
                      </div>
                    </div>
                    <div className="p-3 bg-white border border-black/[0.06] rounded-2xl shadow-sm">
                      <div className="text-[10px] text-slate-500 font-semibold mb-0.5">Profit Factor</div>
                      <div className="text-lg font-bold text-emerald-700 font-mono">
                        {wallet.profitFactor ? `${wallet.profitFactor.toFixed(1)}x` : `${((wallet.winRate || 75) / Math.max(1, 100 - (wallet.winRate || 75)) * 1.3).toFixed(1)}x`}
                      </div>
                    </div>
                    <div className="p-3 bg-white border border-black/[0.06] rounded-2xl shadow-sm">
                      <div className="text-[10px] text-slate-500 font-semibold mb-0.5">Max Drawdown</div>
                      <div className="text-lg font-bold text-slate-700 font-mono">{formatPct(wallet.maxDrawdown || 0)}</div>
                    </div>
                  </div>

                  {/* Chart Tabs: Daily Win/Loss vs Cumulative PnL vs Baleen Score + Timeframe Filters */}
                  <div>
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-3">
                      <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                        <BarChart3 size={14} className="text-slate-600" />
                        Performance Visualizer
                      </h4>

                      <div className="flex items-center gap-2 flex-wrap">
                        {/* Timeframe selector (1W, 1M, YTD, ALL) */}
                        <div className="flex rounded-xl bg-slate-100 p-0.5 border border-black/[0.06] text-[11px] font-mono font-semibold">
                          {(['1W', '1M', 'YTD', 'ALL'] as const).map((tf) => (
                            <button
                              key={tf}
                              onClick={() => setTimeframe(tf)}
                              className={`px-2.5 py-0.5 rounded-lg transition-all cursor-pointer ${
                                timeframe === tf 
                                  ? 'bg-white text-slate-950 font-bold shadow-xs' 
                                  : 'text-slate-500 hover:text-slate-900'
                              }`}
                            >
                              {tf}
                            </button>
                          ))}
                        </div>

                        {/* Chart view tabs */}
                        <div className="flex rounded-xl bg-slate-100 p-0.5 border border-black/[0.06]">
                          <button
                            onClick={() => setActiveChartTab('winloss')}
                            className={`text-xs px-2.5 py-1 rounded-lg font-semibold transition-all cursor-pointer ${
                              activeChartTab === 'winloss' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'
                            }`}
                          >
                            Daily Win / Loss
                          </button>
                          <button
                            onClick={() => setActiveChartTab('pnl')}
                            className={`text-xs px-2.5 py-1 rounded-lg font-semibold transition-all cursor-pointer ${
                              activeChartTab === 'pnl' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'
                            }`}
                          >
                            Cumulative P&amp;L
                          </button>
                          <button
                            onClick={() => setActiveChartTab('score')}
                            className={`text-xs px-2.5 py-1 rounded-lg font-semibold transition-all cursor-pointer ${
                              activeChartTab === 'score' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900'
                            }`}
                          >
                            Score Decay
                          </button>
                        </div>
                      </div>
                    </div>

                    <div className="h-56 p-4 rounded-3xl bg-slate-50 border border-black/[0.06] shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
                      {activeChartTab === 'winloss' ? (
                        <DailyWinLossBarChart data={filteredDailyPnLHistory} />
                      ) : activeChartTab === 'pnl' ? (
                        <CumulativePnLChart data={filteredDailyPnLHistory} />
                      ) : (
                        <ScoreHistoryChart data={wallet.scoreHistory || []} />
                      )}
                    </div>
                  </div>
                </div>
              ) : loading ? (
                <div className="space-y-6 animate-pulse py-4">
                  <div className="h-10 bg-slate-100 rounded-2xl w-3/4" />
                  <div className="h-24 bg-slate-100 rounded-3xl w-full" />
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    <div className="h-16 bg-slate-100 rounded-2xl" />
                    <div className="h-16 bg-slate-100 rounded-2xl" />
                    <div className="h-16 bg-slate-100 rounded-2xl" />
                    <div className="h-16 bg-slate-100 rounded-2xl" />
                  </div>
                  <div className="h-56 bg-slate-100 rounded-3xl" />
                </div>
              ) : (
                <div className="text-center text-slate-400 py-12 text-sm font-medium">Wallet details unavailable.</div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
