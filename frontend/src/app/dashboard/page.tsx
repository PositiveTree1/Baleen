'use client';
import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useSession } from 'next-auth/react';
import { PaperCopyPanel } from '@/components/dashboard/PaperCopyPanel';
import { BalanceCounter } from '@/components/dashboard/BalanceCounter';
import { LiveTape } from '@/components/dashboard/LiveTape';
import { WalletLeaderboard } from '@/components/dashboard/WalletLeaderboard';
import { TradeLog } from '@/components/dashboard/TradeLog';
import { PortfolioAnalytics } from '@/components/dashboard/PortfolioAnalytics';
import { WalletDrawer } from '@/components/dashboard/WalletDrawer';
import { TradeDrawer } from '@/components/dashboard/TradeDrawer';
import { ResetSandboxModal } from '@/components/dashboard/ResetSandboxModal';
import { MirrorStrategyModal } from '@/components/dashboard/MirrorStrategyModal';
import { RebalanceModal } from '@/components/dashboard/RebalanceModal';
import { DeepAnalyticsModal } from '@/components/dashboard/DeepAnalyticsModal';
import { ActivityFeed } from '@/components/dashboard/ActivityFeed';
import { CommandPalette } from '@/components/ui/CommandPalette';
import {
  fetchUserSettings,
  fetchPortfolioSummary,
  fetchExecutionLogs,
  getCachedExecutionLogs,
  getCachedPortfolioSummary,
  getCachedPortfolioSnapshots,
  fetchLiveDashboard,
  fetchWallets,
  getCachedWallets,
  setAuthToken,
  getAuthToken,
  clearAllCache,
  logoutBackend
} from '@/lib/api-client';
import { User, ExecutionLog, PortfolioSummary, LiveTradingDashboard, Wallet } from '@/types';
import { useTheme } from '@/context/ThemeContext';
import Link from 'next/link';
import {
  Settings,
  LogOut,
  Volume2,
  VolumeX,
  Bell,
  Search,
  Sun,
  Moon,
  ShieldCheck,
  AlertCircle,
  ExternalLink,
  Coins,
  TrendingUp,
  ArrowUpRight,
  Activity,
  Zap,
  Menu,
  X
} from 'lucide-react';
import { signOut } from 'next-auth/react';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { LiquidOrbButton } from '@/components/ui/LiquidOrbButton';
import { soundFx } from '@/lib/sound';

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const { theme, toggleTheme } = useTheme();
  const [selectedWallet, setSelectedWallet] = useState<string | null>(null);
  const [selectedTrade, setSelectedTrade] = useState<ExecutionLog | null>(null);

  const [user, setUser] = useState<User | null>(null);

  // User ID persistence: never drop to undefined during NextAuth background revalidation
  const [lastUserId, setLastUserId] = useState<string | undefined>(session?.user?.id);
  if (session?.user?.id && session.user.id !== lastUserId) {
    setLastUserId(session.user.id);
  }
  const effectiveUserId = session?.user?.id || user?.id || lastUserId;

  // View Mode: 'sandbox' | 'live'
  const [viewMode, setViewMode] = useState<'sandbox' | 'live'>('sandbox');
  const [liveDashboard, setLiveDashboard] = useState<LiveTradingDashboard | null>(null);

  // 4 Action Modals
  const [isResetOpen, setIsResetOpen] = useState(false);
  const [isMirrorOpen, setIsMirrorOpen] = useState(false);
  const [isRebalanceOpen, setIsRebalanceOpen] = useState(false);
  const [isAnalyticsOpen, setIsAnalyticsOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  const [activityOpen, setActivityOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [soundActive, setSoundActive] = useState(false);
  const [logs, setLogs] = useState<ExecutionLog[]>(() => getCachedExecutionLogs(session?.user?.id) || []);
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(() => getCachedPortfolioSummary(session?.user?.id) || null);
  const [wallets, setWallets] = useState<Wallet[]>(() => getCachedWallets() || []);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const accessToken = session?.user?.accessToken || (session as { accessToken?: string })?.accessToken;

  const handleDataRefresh = useCallback(() => {
    setRefreshTrigger((prev) => prev + 1);
  }, []);

  useEffect(() => {
    if (accessToken) {
      setAuthToken(accessToken);
    }
  }, [accessToken]);

  useEffect(() => {
    let isMounted = true;
    let loading = false;

    const loadData = async () => {
      if (typeof document !== 'undefined' && document.hidden) return;
      if (loading) return;
      loading = true;
      const token = accessToken || getAuthToken();
      if (token) {
        setAuthToken(token);
      }
      const targetUserId = effectiveUserId;
      const canFetchPrivate = Boolean(targetUserId && token);
      try {
        const tasks: Promise<void>[] = [];
        if (canFetchPrivate) {
          tasks.push(fetchUserSettings(targetUserId!).then(data => { if (isMounted && data) setUser(data); }));
          tasks.push(fetchPortfolioSummary(targetUserId!).then(data => { if (isMounted && data) setPortfolio(data); }));
          tasks.push(fetchExecutionLogs(targetUserId!, { limit: '500' }).then(data => {
            if (isMounted && Array.isArray(data)) setLogs(prev => data.length === 0 && prev.length > 0 ? prev : data);
          }));
          if (viewMode === 'live') tasks.push(fetchLiveDashboard(targetUserId!).then(data => { if (isMounted && data) setLiveDashboard(data); }));
        }
        tasks.push(fetchWallets().then(data => { if (isMounted && data.length > 0) setWallets(data); }));
        const results = await Promise.allSettled(tasks);
        if (!isMounted) return;
        if (results.some(result => result.status === 'fulfilled')) {
          setLoadError(null);
          setLastUpdated(new Date());
        } else {
          setLoadError("Unable to reach backend control plane. Retrying automatically...");
        }
      } finally {
        loading = false;
      }
    };

    void loadData();
    const interval = setInterval(loadData, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [accessToken, effectiveUserId, refreshTrigger, viewMode]);

  const toggleSound = () => {
    const next = soundFx.toggleSound();
    setSoundActive(next);
  };

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F0F7FF] dark:bg-[#0F172A] text-[#0F172A] dark:text-white">
        <div className="glass-card p-6 flex flex-col items-center gap-3 rounded-2xl">
          <div className="w-8 h-8 rounded-full border-2 border-[#0284C7] border-t-transparent animate-spin" />
          <span className="text-xs font-mono text-slate-500 dark:text-slate-400">Connecting to Baleen Control Plane...</span>
        </div>
      </div>
    );
  }

  const cachedSnapshots = getCachedPortfolioSnapshots(effectiveUserId, 'all');
  const lastCachedBal = (cachedSnapshots && cachedSnapshots.length > 0) ? cachedSnapshots[cachedSnapshots.length - 1].balance : null;
  const cachedSummary = getCachedPortfolioSummary(effectiveUserId);

  if (!portfolio && !user && !cachedSummary && lastCachedBal === null && loadError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F0F7FF] dark:bg-[#0F172A] p-6 text-[#0F172A] dark:text-white">
        <div className="max-w-md w-full glass-card p-6 rounded-2xl border border-rose-500/30 flex flex-col items-center gap-4 text-center shadow-xl">
          <div className="w-10 h-10 rounded-full bg-rose-500/10 text-rose-500 flex items-center justify-center font-bold text-lg">!</div>
          <h2 className="text-lg font-bold">Portfolio Service Unavailable</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Could not retrieve account balance or financial records. Backend connection failed.
          </p>
          <button
            onClick={() => handleDataRefresh()}
            className="glass-button px-5 py-2.5 rounded-full bg-[#0284C7] text-white font-bold text-xs cursor-pointer hover:opacity-90 transition-opacity"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  // Sandbox calculations
  const activeSummary = portfolio ?? cachedSummary;
  const summaryValuationIncomplete = activeSummary?.valuationStatus === 'INCOMPLETE';
  const sandboxBalance = (activeSummary?.currentBalance !== null && activeSummary?.currentBalance !== undefined)
    ? activeSummary.currentBalance
    : (user?.currentBalance !== null && user?.currentBalance !== undefined)
      ? user.currentBalance
      : (lastCachedBal !== null && lastCachedBal !== undefined)
        ? lastCachedBal
        : (activeSummary?.startingBalance ?? user?.startingBalance ?? 10000.0);
  const sandboxPnl = (activeSummary?.totalPnlUsd !== null && activeSummary?.totalPnlUsd !== undefined)
    ? activeSummary.totalPnlUsd
    : (activeSummary?.knownPnlUsd ?? 0.0);
  const sandboxPnlPct = activeSummary?.totalPnlPct ?? (sandboxBalance && (activeSummary?.startingBalance ?? user?.startingBalance ?? 10000.0) ? ((sandboxBalance - (activeSummary?.startingBalance ?? user?.startingBalance ?? 10000.0)) / (activeSummary?.startingBalance ?? user?.startingBalance ?? 10000.0)) * 100.0 : 0.0);
  const targetSleeveCount = (sandboxBalance ?? 10000) < 250 ? 1 : (sandboxBalance ?? 10000) < 1000 ? 2 : (sandboxBalance ?? 10000) < 3000 ? 4 : (sandboxBalance ?? 10000) < 15000 ? 5 : 10;

  // Live Capital calculations (preserve null/undefined to avoid converting missing state to zero)
  const liveEvidenceVerified = liveDashboard?.execution_evidence === 'authenticated_verified';
  const isLiveConfigured = Boolean(liveDashboard?.is_configured);
  const liveBalance = isLiveConfigured && liveEvidenceVerified ? (liveDashboard?.usdc_balance ?? null) : null;
  const liveNetWorth = isLiveConfigured && liveEvidenceVerified ? (liveDashboard?.portfolio_net_worth ?? null) : null;
  const livePnl = isLiveConfigured && liveEvidenceVerified ? (liveDashboard?.live_pnl ?? null) : null;
  const livePnlPct = (liveBalance !== null && liveBalance > 0 && livePnl !== null) ? (livePnl / liveBalance) * 100.0 : null;

  return (
    <div className="min-h-screen flex flex-col bg-transparent text-slate-950 selection:bg-sky-200 selection:text-slate-950 relative overflow-x-hidden font-sans pb-[calc(2rem+env(safe-area-inset-bottom,0px))]">
      {/* Floating Optical Glass Header */}
      <header className="sticky top-0 z-40 w-full px-2 sm:px-6 lg:px-8 pt-2 sm:pt-3 pb-1">
        <nav className="max-w-7xl mx-auto glass-dock px-3 sm:px-5 py-2 sm:py-2.5 flex items-center justify-between gap-2 sm:gap-4 shadow-lg border border-white/80 dark:border-white/10">

          {/* Left: Brand Logo & Segmented Mode Toggle */}
          <div className="flex items-center gap-2 sm:gap-5 shrink-0 min-w-0">
            <BrandLogo href="/" />

            {/* Top View Toggle: Sandbox vs Live Capital */}
            <div className="flex items-center p-0.5 sm:p-1 rounded-full bg-slate-100/90 border border-slate-200/80 shadow-2xs">
              <button
                onClick={() => setViewMode('sandbox')}
                className={`px-2.5 sm:px-3.5 py-1 sm:py-1.5 rounded-full text-[11px] sm:text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                  viewMode === 'sandbox'
                    ? 'bg-white text-slate-900 shadow-xs border border-slate-200/70 font-extrabold'
                    : 'text-slate-600 hover:text-slate-950'
                }`}
              >
                <span>Sandbox</span>
                <span className="hidden sm:inline"> (Paper)</span>
              </button>
              <button
                onClick={() => setViewMode('live')}
                className={`px-2.5 sm:px-3.5 py-1 sm:py-1.5 rounded-full text-[11px] sm:text-xs font-bold transition-all flex items-center gap-1 sm:gap-1.5 cursor-pointer whitespace-nowrap ${
                  viewMode === 'live'
                    ? 'bg-white text-slate-900 shadow-xs border border-slate-200/70 font-extrabold'
                    : 'text-slate-600 hover:text-slate-950'
                }`}
              >
                <span className={`w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full shrink-0 ${liveDashboard?.is_live_active ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
                <span>Live</span>
                <span className="hidden md:inline"> · Gated</span>
              </button>
            </div>
          </div>

          {/* Center: Search Command Bar */}
          <button
            type="button"
            onClick={() => setCommandPaletteOpen(true)}
            aria-label="Open command palette search (Command + K)"
            className="hidden xl:flex items-center gap-2.5 px-4 py-2 rounded-full bg-slate-50/80 hover:bg-slate-100/90 border border-slate-200 text-xs text-slate-600 w-64 hover:scale-[1.02] active:scale-[0.98] transition-all cursor-pointer shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0284C7]"
          >
            <Search size={14} className="text-[#0284C7]" aria-hidden="true" />
            <span className="text-slate-600 font-medium">Search markets, whales...</span>
            <span className="ml-auto text-[10px] font-mono bg-white px-1.5 py-0.5 rounded text-slate-700 shadow-2xs border border-slate-200">⌘K</span>
          </button>

          {/* Right: Desktop Actions */}
          <div className="hidden md:flex items-center gap-1.5 md:gap-2 shrink-0">
            {/* Search Command Palette */}
            <LiquidOrbButton
              size="sm"
              onClick={() => setCommandPaletteOpen(true)}
              className="xl:hidden"
              aria-label="Open search command palette"
              title="Search (Cmd+K)"
            >
              <Search size={14} aria-hidden="true" className="text-[#0284C7]" />
            </LiquidOrbButton>

            {/* Light / Dark Mode Toggle */}
            <LiquidOrbButton
              size="sm"
              onClick={toggleTheme}
              aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
              title={theme === 'light' ? 'Dark mode' : 'Light mode'}
            >
              {theme === 'light' ? <Moon size={14} aria-hidden="true" className="text-slate-700" /> : <Sun size={14} aria-hidden="true" className="text-amber-500" />}
            </LiquidOrbButton>

            {/* Activity Feed Button */}
            <LiquidOrbButton
              size="sm"
              onClick={() => {
                soundFx.playWhoosh();
                setActivityOpen(true);
              }}
              aria-label="Open activity feed and notifications"
              title="Activity Feed"
            >
              <Bell size={14} aria-hidden="true" className="text-slate-700" />
            </LiquidOrbButton>

            {/* Sound FX Toggle */}
            <LiquidOrbButton
              size="sm"
              active={soundActive}
              onClick={toggleSound}
              aria-label={soundActive ? 'Mute trade signal sound effects' : 'Enable real-time trade signal sound effects'}
              title={soundActive ? 'Mute sound FX' : 'Enable audio FX'}
            >
              {soundActive ? <Volume2 size={14} aria-hidden="true" className="text-sky-600" /> : <VolumeX size={14} aria-hidden="true" className="text-slate-400" />}
            </LiquidOrbButton>

            {session?.user?.isAdmin && (
              <Link
                href="/admin"
                className="text-[10px] sm:text-xs font-bold text-slate-700 hover:text-sky-600 px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full bg-[#f0f7fd] hover:bg-[#e2f0fb] border border-[#d4e5f5] hover:border-[#b9d8f3] transition-all shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0284C7]"
                aria-label="Go to Admin Panel"
              >
                Admin
              </Link>
            )}

            <Link
              href="/settings"
              className="w-8 h-8 sm:w-9 sm:h-9 md:w-10 md:h-10 rounded-full bg-[#f0f7fd] hover:bg-[#e2f0fb] border border-[#d4e5f5] hover:border-[#b9d8f3] text-slate-700 hover:text-sky-600 flex items-center justify-center transition-all shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0284C7]"
              aria-label="Go to User Settings"
            >
              <Settings size={14} aria-hidden="true" className="sm:w-[15px] sm:h-[15px]" />
            </Link>

            <motion.button
              whileHover={{ scale: 1.08 }}
              whileTap={{ scale: 0.94 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}
              onClick={async () => {
                try {
                  await logoutBackend();
                  await signOut({ callbackUrl: '/auth/login' });
                } catch {
                  window.alert('Sign out could not be completed. Please retry when the connection is restored.');
                }
              }}
              className="w-8 h-8 sm:w-9 sm:h-9 md:w-10 md:h-10 rounded-full bg-[#f0f7fd] hover:bg-rose-50 border border-[#d4e5f5] hover:border-rose-300 text-slate-500 hover:text-rose-600 flex items-center justify-center transition-all cursor-pointer shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
              aria-label="Sign out of Baleen"
            >
              <LogOut size={14} aria-hidden="true" className="sm:w-[15px] sm:h-[15px]" />
            </motion.button>
          </div>

          {/* Right: Mobile Hamburger Button */}
          <div className="flex md:hidden items-center gap-1 shrink-0">
            <LiquidOrbButton
              size="sm"
              onClick={() => setMobileMenuOpen(prev => !prev)}
              aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
              title="Menu"
            >
              {mobileMenuOpen ? <X size={16} className="text-slate-800" /> : <Menu size={16} className="text-slate-800" />}
            </LiquidOrbButton>
          </div>
        </nav>

        {/* Mobile Dropdown Menu Sheet */}
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.98 }}
            transition={{ type: 'spring', damping: 25, stiffness: 350 }}
            className="md:hidden max-w-7xl mx-auto mt-2 p-3 bg-white text-slate-950 rounded-2xl shadow-xl border border-slate-200 flex flex-col gap-1.5 z-50"
          >
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                setCommandPaletteOpen(true);
              }}
              className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-slate-700 hover:text-slate-950 transition-colors w-full text-left cursor-pointer"
            >
              <Search size={15} className="text-sky-600 shrink-0" />
              <span className="flex-1">Search Markets &amp; Whales</span>
              <span className="text-[10px] font-mono text-slate-400 bg-white px-1.5 py-0.5 rounded border border-slate-200">⌘K</span>
            </button>

            <button
              onClick={() => {
                setMobileMenuOpen(false);
                soundFx.playWhoosh();
                setActivityOpen(true);
              }}
              className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-slate-700 hover:text-slate-950 transition-colors w-full text-left cursor-pointer"
            >
              <Bell size={15} className="text-sky-600 shrink-0" />
              <span>Activity &amp; Trade Notifications</span>
            </button>

            <button
              onClick={() => {
                toggleSound();
              }}
              className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-slate-700 hover:text-slate-950 transition-colors w-full text-left cursor-pointer"
            >
              {soundActive ? <Volume2 size={15} className="text-sky-600 shrink-0" /> : <VolumeX size={15} className="text-slate-400 shrink-0" />}
              <span className="flex-1">Audio Feedback</span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${soundActive ? 'bg-sky-100 text-sky-800' : 'bg-slate-200 text-slate-600'}`}>
                {soundActive ? 'ON' : 'OFF'}
              </span>
            </button>

            <Link
              href="/settings"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-slate-700 hover:text-slate-950 transition-colors w-full text-left"
            >
              <Settings size={15} className="text-slate-600 shrink-0" />
              <span>Account &amp; API Configuration</span>
            </Link>

            {session?.user?.isAdmin && (
              <Link
                href="/admin"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-sky-50 hover:bg-sky-100 text-xs font-bold text-sky-800 transition-colors w-full text-left"
              >
                <ShieldCheck size={15} className="text-sky-600 shrink-0" />
                <span>Admin Governance</span>
              </Link>
            )}

            <div className="h-px bg-slate-100 my-0.5" />

            <button
              onClick={async () => {
                setMobileMenuOpen(false);
                try {
                  await logoutBackend();
                  await signOut({ callbackUrl: '/auth/login' });
                } catch {
                  window.alert('Sign out could not be completed. Please retry when the connection is restored.');
                }
              }}
              className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-rose-50 hover:bg-rose-100 text-xs font-semibold text-rose-700 transition-colors w-full text-left cursor-pointer"
            >
              <LogOut size={15} className="text-rose-600 shrink-0" />
              <span>Sign Out</span>
            </button>
          </motion.div>
        )}
      </header>

      {/* Main Container */}
      <main className="flex-1 p-3.5 sm:p-6 lg:p-12 max-w-7xl mx-auto w-full flex flex-col gap-6 sm:gap-8 relative z-10">
        {loadError && (
          <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-2.5 text-xs text-amber-800 dark:text-amber-200 flex items-center justify-between">
            <span>Offline Mode · Displaying cached data {lastUpdated ? `(as of ${lastUpdated.toLocaleTimeString()})` : ''}.</span>
            <button onClick={() => handleDataRefresh()} className="underline font-bold cursor-pointer hover:opacity-80">Retry</button>
          </div>
        )}

        <p className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-200">
          Paper trading · Experimental results. Accounting and market data are under validation. Real-money execution is unavailable.
        </p>
        {summaryValuationIncomplete && (
          <p className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs text-amber-900 dark:text-amber-200">
            Valuation incomplete: {activeSummary?.unvaluedTradesCount ?? 0} trade(s) lack sufficient evidence. Totals show Unavailable until valuation is complete.
          </p>
        )}

        {/* VIEW 1: SANDBOX (PAPER TRADING) */}
        {viewMode === 'sandbox' && (
          <>
            {/* Hero Section: Balance & 4-Action Row */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-5 sm:gap-6 pt-1 sm:pt-2">
              <BalanceCounter
                balance={sandboxBalance}
                pnl={sandboxPnl}
                pnlPct={sandboxPnlPct}
                onMirrorClick={() => setIsMirrorOpen(true)}
                onRebalanceClick={() => setIsRebalanceOpen(true)}
                onAnalyticsClick={() => setIsAnalyticsOpen(true)}
                onResetClick={() => setIsResetOpen(true)}
              />

              <div className="flex items-center gap-2.5">
                <div className="glass-card px-3 sm:px-4 py-1.5 sm:py-2 rounded-full flex items-center gap-2 text-[11px] sm:text-xs font-medium text-slate-600 dark:text-slate-300 border border-sky-100/80 dark:border-white/10 shadow-xs">
                  <span>Risk Regime:</span>
                  <span className="font-bold text-[#0F172A] dark:text-white font-mono px-2.5 py-0.5 rounded-full bg-white/90 dark:bg-white/10 shadow-2xs border border-sky-200/50 dark:border-white/10">
                    {user?.riskProfile || 'Balanced'}
                  </span>
                </div>
              </div>
            </div>

            <PaperCopyPanel onConfigure={() => setIsMirrorOpen(true)} />

            {/* Section 1: Line Chart & Analytics Cards */}
            <PortfolioAnalytics
              logs={logs}
              wallets={wallets}
              userId={effectiveUserId}
              startingBalance={portfolio?.startingBalance ?? user?.startingBalance ?? 10000.0}
              currentBalance={sandboxBalance}
              totalFilledTrades={portfolio?.filledTradesCount ?? logs.length}
              topAlphaMarkets={portfolio?.topAlphaMarkets}
              topDrawdownMarkets={portfolio?.topDrawdownMarkets}
              allTimeWinRate={portfolio?.allTimeWinRate}
              allTimeWins={portfolio?.allTimeWins}
              allTimeLosses={portfolio?.allTimeLosses}
              onSelectTrade={setSelectedTrade}
              onResetComplete={handleDataRefresh}
            />

            {/* Section 2: Live Tape & Active Whale Basket */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <LiveTape userId={effectiveUserId} onSelectTrade={setSelectedTrade} />
              </div>
              <div className="lg:col-span-1">
                <WalletLeaderboard userId={effectiveUserId} wallets={wallets} logs={logs} onRefresh={handleDataRefresh} onSelectWallet={setSelectedWallet} targetSleeveCount={targetSleeveCount} />
              </div>
            </div>

            {/* Section 3: Execution Audit & Transactions Feed */}
            <TradeLog
              userId={effectiveUserId}
              logs={logs}
              totalHoldingCount={portfolio?.holdingTradesCount}
              totalClosedCount={portfolio?.closedTradesCount}
              totalFillsCount={portfolio?.filledTradesCount}
              onSelectTrade={setSelectedTrade}
            />
          </>
        )}

        {/* VIEW 2: LIVE CAPITAL (L2 REAL MONEY TRADING) */}
        {viewMode === 'live' && (
          <div className="space-y-8">
            {/* Live Capital Top Status Hero Banner */}
            <div className="glass-card border border-sky-100/80 dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h1 className="text-2xl font-bold tracking-tight text-[#0F172A] dark:text-white flex items-center gap-2.5">
                    Live Capital Portfolio
                  </h1>

                  {/* Status Badge */}
                  <span className={`px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1.5 ${
                    liveDashboard?.is_live_active
                      ? 'bg-emerald-50 dark:bg-[#00D09C]/10 text-emerald-600 dark:text-[#00D09C] border border-emerald-200 dark:border-[#00D09C]/30'
                      : liveDashboard?.is_configured
                      ? 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20'
                      : 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-500/20'
                  }`}>
                    <span className={`w-2 h-2 rounded-full ${
                      liveDashboard?.is_live_active ? 'bg-[#00D09C] animate-ping' : liveDashboard?.is_configured ? 'bg-amber-500' : 'bg-rose-500'
                    }`} />
                    <span>{liveDashboard?.status_badge || 'Live Execution Disabled (Preparation in progress)'}</span>
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Live execution is disabled. Real exchange order routing is inactive pending signing and reconciliation gates.
                </p>
              </div>

              <div className="flex items-center gap-3">
                {!liveDashboard?.is_configured ? (
                  <Link
                    href="/settings"
                    className="glass-button px-5 py-2.5 rounded-full text-white text-xs font-bold transition-all shadow-sm flex items-center gap-1.5"
                  >
                    <Settings size={13} />
                    <span>Configure L2 Keys in Settings</span>
                  </Link>
                ) : (
                  <Link
                    href="/settings"
                    className="glass-button px-4 py-2 rounded-full text-xs font-semibold text-white transition-all flex items-center gap-1.5"
                  >
                    <span>Manage Keys</span>
                    <ExternalLink size={12} />
                  </Link>
                )}
              </div>
            </div>

            {/* Metrics Row: Collateral Balance, Portfolio Net Worth, Realized Live PnL */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
              <div className="glass-card border border-sky-100/80 dark:border-white/10 p-6 rounded-[26px] shadow-sm">
                <div className="text-[11px] text-slate-500 dark:text-slate-400 font-medium mb-1.5 flex items-center gap-1.5">
                  <Coins size={13} className="text-[#0284C7] dark:text-[#38BDF8]" />
                  <span>pUSD L2 Cash Balance (Observed)</span>
                </div>
                <div className="text-3xl font-extrabold font-mono text-[#0F172A] dark:text-white">
                  {liveBalance !== null ? `$${liveBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Unavailable'}
                </div>
                <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1 font-mono">
                  Proxy: {liveDashboard?.polymarket_wallet_address ? `${liveDashboard.polymarket_wallet_address.slice(0, 6)}...${liveDashboard.polymarket_wallet_address.slice(-4)}` : 'Not linked'}
                </div>
              </div>

              <div className="glass-card border border-sky-100/80 dark:border-white/10 p-6 rounded-[26px] shadow-sm">
                <div className="text-[11px] text-slate-500 dark:text-slate-400 font-medium mb-1.5 flex items-center gap-1.5">
                  <TrendingUp size={13} className="text-emerald-500" />
                  <span>Unreconciled Live Equity</span>
                </div>
                <div className="text-3xl font-extrabold font-mono text-emerald-600 dark:text-[#00D09C]">
                  {liveNetWorth !== null ? `$${liveNetWorth.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Unavailable'}
                </div>
                <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                  Open Positions: {liveDashboard?.open_positions_value !== undefined && liveDashboard?.open_positions_value !== null ? `$${liveDashboard.open_positions_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Unavailable'}
                </div>
              </div>

              <div className="glass-card border border-sky-100/80 dark:border-white/10 p-6 rounded-[26px] shadow-sm">
                <div className="text-[11px] text-slate-500 dark:text-slate-400 font-medium mb-1.5 flex items-center gap-1.5">
                  <Zap size={13} className="text-amber-500" />
                  <span>Unreconciled Exchange PnL</span>
                </div>
                <div className={`text-3xl font-extrabold font-mono ${livePnl == null ? 'text-slate-400 dark:text-slate-500' : livePnl >= 0 ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                  {livePnl !== null ? `${livePnl >= 0 ? '+' : ''}$${livePnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Unavailable'}
                </div>
                <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-1 font-mono">
                  {livePnlPct !== null ? `${livePnlPct >= 0 ? '+' : ''}${livePnlPct.toFixed(2)}% on active capital` : 'Reconciliation pending'}
                </div>
              </div>
            </div>

            {/* Active Live Positions */}
            <div className="glass-card border border-sky-100/80 dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-bold text-[#0F172A] dark:text-white flex items-center gap-2">
                    <Activity size={15} className="text-[#0284C7] dark:text-[#38BDF8]" />
                    <span>Active Live Positions ({liveDashboard?.active_positions?.length || 0})</span>
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Open market legs mirrored on Polymarket CLOB.
                  </p>
                </div>
              </div>

              {(!liveDashboard?.active_positions || liveDashboard.active_positions.length === 0) ? (
                <div className="py-12 text-center text-slate-400 dark:text-slate-500 text-xs">
                  No active open live positions at this time.
                </div>
              ) : (
                <div className="overflow-x-auto relative rounded-2xl border border-sky-100/60 dark:border-white/5 scrollbar-thin">
                  <table className="w-full text-left text-xs min-w-[540px]">
                    <thead>
                      <tr className="border-b border-sky-100/80 dark:border-white/10 text-slate-500 dark:text-slate-400">
                        <th className="pb-3 pt-2 pl-3 font-semibold">Market / Question</th>
                        <th className="pb-3 pt-2 font-semibold">Outcome</th>
                        <th className="pb-3 pt-2 font-semibold">Entry Price</th>
                        <th className="pb-3 pt-2 font-semibold">Notional</th>
                        <th className="pb-3 pt-2 pr-3 font-semibold">Source Whale</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-sky-100/50 dark:divide-white/5 font-mono">
                      {liveDashboard.active_positions.map((pos) => (
                        <tr key={pos.id} className="hover:bg-sky-500/[0.04] dark:hover:bg-white/[0.02] transition-colors">
                          <td className="py-3 pl-3 pr-4 font-sans font-medium text-[#0F172A] dark:text-white max-w-xs truncate">
                            {pos.marketQuestion}
                          </td>
                          <td className="py-3">
                            <span className="px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-[#00D09C]/10 text-emerald-700 dark:text-[#00D09C] font-bold text-[11px] border border-emerald-200/60 dark:border-[#00D09C]/20">
                              {pos.outcome}
                            </span>
                          </td>
                          <td className="py-3 text-slate-700 dark:text-slate-300">
                            {pos.entryPrice.toFixed(3)}
                          </td>
                          <td className="py-3 font-bold text-[#0F172A] dark:text-white">
                            ${pos.notionalUsd.toFixed(2)}
                          </td>
                          <td className="py-3 pr-3 text-slate-500 dark:text-slate-400">
                            {pos.sourceWallet.slice(0, 6)}...{pos.sourceWallet.slice(-4)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Live Execution Logs Feed */}
            <div className="glass-card border border-sky-100/80 dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-bold text-[#0F172A] dark:text-white flex items-center gap-2">
                    <ShieldCheck size={15} className="text-[#0284C7] dark:text-[#38BDF8]" />
                    <span>Live CLOB Trade Fills &amp; Settlements (Pipeline Inactive)</span>
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Exchange-confirmed execution logs. Live execution pipeline is currently inactive pending validation gates.
                  </p>
                </div>
              </div>

              {(!liveDashboard?.execution_logs || liveDashboard.execution_logs.length === 0) ? (
                <div className="py-12 text-center text-slate-400 dark:text-slate-500 text-xs">
                  No live exchange trades executed. Live order routing is currently disabled pending signing and reconciliation gates.
                </div>
              ) : (
                <div className="overflow-x-auto relative rounded-2xl border border-sky-100/60 dark:border-white/5 scrollbar-thin">
                  <table className="w-full text-left text-xs min-w-[640px]">
                    <thead>
                      <tr className="border-b border-sky-100/80 dark:border-white/10 text-slate-500 dark:text-slate-400">
                        <th className="pb-3 pt-2 pl-3 font-semibold">Time</th>
                        <th className="pb-3 pt-2 font-semibold">Side</th>
                        <th className="pb-3 pt-2 font-semibold">Market</th>
                        <th className="pb-3 pt-2 font-semibold">Outcome</th>
                        <th className="pb-3 pt-2 font-semibold">Fill Price</th>
                        <th className="pb-3 pt-2 font-semibold">Notional</th>
                        <th className="pb-3 pt-2 font-semibold">Realized PnL</th>
                        <th className="pb-3 pt-2 pr-3 font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-sky-100/50 dark:divide-white/5 font-mono">
                      {liveDashboard.execution_logs.map((l) => (
                        <tr key={l.id} className="hover:bg-sky-500/[0.04] dark:hover:bg-white/[0.02] transition-colors">
                          <td className="py-3 pl-3 text-slate-500 dark:text-slate-400">
                            {new Date(l.timestamp).toLocaleTimeString()}
                          </td>
                          <td className="py-3">
                            <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${
                              l.side === 'BUY' ? 'bg-emerald-50 dark:bg-[#00D09C]/10 text-emerald-700 dark:text-[#00D09C] border border-emerald-200/60 dark:border-[#00D09C]/20' : 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 border border-amber-200/60'
                            }`}>
                              {l.side}
                            </span>
                          </td>
                          <td className="py-3 pr-4 font-sans font-medium text-[#0F172A] dark:text-white max-w-xs truncate">
                            {l.marketQuestion}
                          </td>
                          <td className="py-3 text-slate-700 dark:text-slate-300">
                            {l.outcome}
                          </td>
                          <td className="py-3 text-slate-700 dark:text-slate-300">
                            {l.fillPrice === null ? 'Unavailable' : l.fillPrice.toFixed(3)}
                          </td>
                          <td className="py-3 font-bold text-[#0F172A] dark:text-white">
                            ${l.size.toFixed(2)}
                          </td>
                          <td className="py-3">
                            {l.pnl !== null && l.pnl !== undefined ? (
                              <span className={`font-bold ${l.pnl >= 0 ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                                {l.pnl >= 0 ? '+' : ''}${l.pnl.toFixed(2)}
                              </span>
                            ) : (
                              <span className="text-slate-400 dark:text-slate-500">-</span>
                            )}
                          </td>
                          <td className="py-3 pr-3">
                            <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-white/10 text-slate-700 dark:text-slate-300 text-[10px] border border-sky-100/60 dark:border-white/5">
                              {l.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Quick Command Palette (CMD+K or Navbar click) */}
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        onSelectWallet={setSelectedWallet}
      />

      {/* 1. Mirror Strategy Modal */}
      <MirrorStrategyModal
        isOpen={isMirrorOpen}
        onClose={() => setIsMirrorOpen(false)}
        onSelectWallet={setSelectedWallet}
        targetSleeveCount={targetSleeveCount}
        bankroll={sandboxBalance}
      />

      {/* 2. Rebalance Modal */}
      <RebalanceModal
        isOpen={isRebalanceOpen}
        onClose={() => setIsRebalanceOpen(false)}
        onRebalanceExecute={handleDataRefresh}
      />

      {/* 3. Deep Portfolio Analytics Modal */}
      <DeepAnalyticsModal
        isOpen={isAnalyticsOpen}
        onClose={() => setIsAnalyticsOpen(false)}
        portfolio={portfolio}
        logs={logs}
      />

      {/* 4. Reset Sandbox Modal */}
      <ResetSandboxModal
        isOpen={isResetOpen}
        onClose={() => setIsResetOpen(false)}
        userId={session?.user?.id}
        currentBalance={sandboxBalance}
        onResetComplete={handleDataRefresh}
      />

      {/* Wallet Drawer */}
      <WalletDrawer
        address={selectedWallet}
        onClose={() => setSelectedWallet(null)}
      />

      {/* Trade / Execution Overview Drawer */}
      <TradeDrawer
        trade={selectedTrade}
        onClose={() => setSelectedTrade(null)}
        onSelectWallet={(addr) => {
          setSelectedTrade(null);
          setSelectedWallet(addr);
        }}
      />

      {/* Activity Feed / Notification Panel */}
      <ActivityFeed
        isOpen={activityOpen}
        onClose={() => setActivityOpen(false)}
      />
    </div>
  );
}
