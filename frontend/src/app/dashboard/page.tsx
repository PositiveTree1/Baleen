'use client';
import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
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
  fetchLiveDashboard
} from '@/lib/api-client';
import { User, ExecutionLog, PortfolioSummary, LiveTradingDashboard } from '@/types';
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
  Zap
} from 'lucide-react';
import { signOut } from 'next-auth/react';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { soundFx } from '@/lib/sound';

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const { theme, toggleTheme } = useTheme();
  const [selectedWallet, setSelectedWallet] = useState<string | null>(null);
  const [selectedTrade, setSelectedTrade] = useState<ExecutionLog | null>(null);
  
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
  const [soundActive, setSoundActive] = useState(false);
  const [logs, setLogs] = useState<ExecutionLog[]>(() => getCachedExecutionLogs(session?.user?.id) || []);
  const [user, setUser] = useState<User | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(() => getCachedPortfolioSummary(session?.user?.id) || null);

  const loadData = async () => {
    if (typeof document !== 'undefined' && document.hidden) return;
    try {
      const [userData, portfolioData, logsData, liveData] = await Promise.all([
        session?.user?.id ? fetchUserSettings(session.user.id) : null,
        fetchPortfolioSummary(session?.user?.id),
        fetchExecutionLogs(session?.user?.id, { limit: '500' }),
        fetchLiveDashboard(session?.user?.id)
      ]);
      if (userData) setUser(userData);
      if (portfolioData) setPortfolio(portfolioData);
      if (Array.isArray(logsData)) setLogs(logsData);
      if (liveData) setLiveDashboard(liveData);
    } catch (err) {
      console.debug("Dashboard polling note:", err);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 6000);
    return () => clearInterval(interval);
  }, [session]);

  const toggleSound = () => {
    const next = soundFx.toggleSound();
    setSoundActive(next);
  };

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F8F9FB] dark:bg-[#000000] text-slate-900 dark:text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-[#00D09C] border-t-transparent animate-spin" />
          <span className="text-xs font-mono text-[#8E8F99]">Connecting to Baleen Control Plane...</span>
        </div>
      </div>
    );
  }

  const cachedSnapshots = getCachedPortfolioSnapshots(session?.user?.id, 'all');
  const lastCachedBal = (cachedSnapshots && cachedSnapshots.length > 0) ? cachedSnapshots[cachedSnapshots.length - 1].balance : null;
  const lastCachedPnl = (cachedSnapshots && cachedSnapshots.length > 0) ? cachedSnapshots[cachedSnapshots.length - 1].pnl : null;
  const cachedSummary = getCachedPortfolioSummary(session?.user?.id);

  // Sandbox calculations
  const sandboxBalance = portfolio?.currentBalance ?? user?.currentBalance ?? cachedSummary?.currentBalance ?? lastCachedBal ?? 10000.0;
  const sandboxPnl = portfolio?.totalPnlUsd ?? cachedSummary?.totalPnlUsd ?? lastCachedPnl ?? 0.0;
  const sandboxPnlPct = portfolio?.totalPnlPct ?? cachedSummary?.totalPnlPct ?? (sandboxBalance > 10000.0 ? ((sandboxBalance - 10000.0) / 10000.0) * 100.0 : 0.0);

  // Live Capital calculations
  const liveBalance = liveDashboard?.usdc_balance ?? 0.0;
  const liveNetWorth = liveDashboard?.portfolio_net_worth ?? liveBalance;
  const livePnl = liveDashboard?.live_pnl ?? 0.0;
  const livePnlPct = liveBalance > 0 ? (livePnl / liveBalance) * 100.0 : 0.0;

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FB] dark:bg-[#000000] text-slate-900 dark:text-white selection:bg-[#00D09C] selection:text-black relative overflow-x-hidden font-sans transition-colors duration-150">
      
      {/* Top Bar Navigation */}
      <nav className="flex items-center justify-between py-3 px-3.5 sm:px-6 lg:px-12 border-b border-black/[0.06] dark:border-white/[0.08] bg-white/80 dark:bg-[#000000]/90 backdrop-blur-2xl sticky top-0 z-40">
        
        {/* Left: Baleen Brand Logo & Mode Segmented Toggle */}
        <div className="flex items-center gap-4 sm:gap-6 shrink-0">
          <BrandLogo href="/" />
          
          {/* Top View Toggle: Sandbox vs Live Capital */}
          <div className="flex items-center p-1 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 shadow-2xs">
            <button
              onClick={() => setViewMode('sandbox')}
              className={`px-3 sm:px-4 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                viewMode === 'sandbox'
                  ? 'bg-white dark:bg-black text-slate-950 dark:text-white shadow-xs'
                  : 'text-slate-500 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              Sandbox (Paper Trading)
            </button>
            <button
              onClick={() => setViewMode('live')}
              className={`px-3 sm:px-4 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                viewMode === 'live'
                  ? 'bg-[#00D09C] text-black shadow-xs font-extrabold'
                  : 'text-slate-500 dark:text-[#8E8F99] hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${liveDashboard?.is_live_active ? 'bg-black animate-pulse' : 'bg-amber-500'}`} />
              <span>Live Capital (L2 Real Money)</span>
            </button>
          </div>
        </div>

        {/* Center: Search Command Bar */}
        <div 
          onClick={() => setCommandPaletteOpen(true)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setCommandPaletteOpen(true);
            }
          }}
          role="button"
          tabIndex={0}
          aria-label="Open command palette search (Command + K)"
          className="hidden xl:flex items-center gap-2 px-4 py-2 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 text-xs text-[#8E8F99] w-64 hover:border-black/20 dark:hover:border-white/20 transition-all cursor-pointer shadow-2xs focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C]"
        >
          <Search size={14} className="text-[#8E8F99]" aria-hidden="true" />
          <span className="text-slate-600 dark:text-[#8E8F99]">Search markets, whales...</span>
          <span className="ml-auto text-[10px] font-mono bg-white dark:bg-[#2C2D35] px-1.5 py-0.5 rounded text-slate-700 dark:text-white shadow-2xs">⌘K</span>
        </div>

        {/* Right: Circular Icon Actions */}
        <div className="flex items-center gap-1 sm:gap-2 lg:gap-2.5 shrink-0">
          {/* Light / Dark Mode Toggle */}
          <button
            onClick={toggleTheme}
            className="w-8 h-8 sm:w-9 sm:h-9 md:w-10 md:h-10 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-white flex items-center justify-center transition-all cursor-pointer shadow-2xs shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C]"
            aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          >
            {theme === 'light' ? <Moon size={14} aria-hidden="true" className="sm:w-[15px] sm:h-[15px]" /> : <Sun size={14} aria-hidden="true" className="text-amber-400 sm:w-[15px] sm:h-[15px]" />}
          </button>

          <button
            onClick={() => setActivityOpen(true)}
            className="w-8 h-8 sm:w-9 sm:h-9 md:w-10 md:h-10 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-white flex items-center justify-center transition-all cursor-pointer shadow-2xs shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C]"
            aria-label="Open activity feed and notifications"
          >
            <Bell size={14} aria-hidden="true" className="sm:w-[15px] sm:h-[15px]" />
          </button>

          <button
            onClick={toggleSound}
            className={`w-8 h-8 sm:w-9 sm:h-9 md:w-10 md:h-10 rounded-full border transition-all cursor-pointer flex items-center justify-center shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] ${
              soundActive 
                ? 'bg-[#00D09C]/10 text-[#00D09C] border-[#00D09C]/30' 
                : 'bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-[#8E8F99]'
            }`}
            aria-label={soundActive ? 'Mute trade signal sound effects' : 'Enable real-time trade signal sound effects'}
          >
            {soundActive ? <Volume2 size={14} aria-hidden="true" className="sm:w-[15px] sm:h-[15px]" /> : <VolumeX size={14} aria-hidden="true" className="sm:w-[15px] sm:h-[15px]" />}
          </button>

          <Link 
            href="/admin" 
            className="text-[10px] sm:text-xs font-bold text-slate-900 dark:text-white px-2 sm:px-3 py-1 sm:py-1.5 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 transition-all shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C]"
            aria-label="Go to Admin Panel"
          >
            Admin
          </Link>
          
          <Link 
            href="/settings" 
            className="w-8 h-8 sm:w-9 sm:h-9 md:w-10 md:h-10 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-white flex items-center justify-center transition-all shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C]"
            aria-label="Go to User Settings"
          >
            <Settings size={14} aria-hidden="true" className="sm:w-[15px] sm:h-[15px]" />
          </Link>
          
          <button 
            onClick={() => signOut()} 
            className="w-8 h-8 sm:w-9 sm:h-9 md:w-10 md:h-10 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-rose-50 dark:hover:bg-rose-950/60 border border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-[#8E8F99] hover:text-[#FF453A] flex items-center justify-center transition-all cursor-pointer shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
            aria-label="Sign out of Baleen"
          >
            <LogOut size={14} aria-hidden="true" className="sm:w-[15px] sm:h-[15px]" />
          </button>
        </div>
      </nav>

      {/* Main Container */}
      <main className="flex-1 p-3.5 sm:p-6 lg:p-12 max-w-7xl mx-auto w-full flex flex-col gap-6 sm:gap-8 relative z-10">
        
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
                <div className="revolut-card-sub bg-[#F1F3F5] dark:bg-[#1C1D22] px-3 sm:px-4 py-1.5 sm:py-2 rounded-full flex items-center gap-2 text-[11px] sm:text-xs font-medium text-slate-600 dark:text-[#8E8F99] border border-black/[0.04] dark:border-white/5 shadow-2xs">
                  <span>Risk Regime:</span>
                  <span className="font-bold text-slate-950 dark:text-white font-mono px-2 py-0.5 rounded-full bg-white dark:bg-[#2C2D35] shadow-2xs">
                    {user?.riskProfile || 'Balanced'}
                  </span>
                </div>
              </div>
            </div>

            {/* Section 1: Line Chart & Analytics Cards */}
            <PortfolioAnalytics
              logs={logs}
              userId={session?.user?.id}
              startingBalance={portfolio?.startingBalance ?? user?.startingBalance ?? 10000.0}
              currentBalance={sandboxBalance}
              totalFilledTrades={portfolio?.filledTradesCount ?? logs.length}
              topAlphaMarkets={portfolio?.topAlphaMarkets}
              topDrawdownMarkets={portfolio?.topDrawdownMarkets}
              allTimeWinRate={portfolio?.allTimeWinRate}
              allTimeWins={portfolio?.allTimeWins}
              allTimeLosses={portfolio?.allTimeLosses}
              onSelectTrade={setSelectedTrade}
              onResetComplete={loadData}
            />

            {/* Section 2: Live Tape & Active Whale Basket */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <LiveTape userId={session?.user?.id} onSelectTrade={setSelectedTrade} />
              </div>
              <div className="lg:col-span-1">
                <WalletLeaderboard userId={session?.user?.id} onSelectWallet={setSelectedWallet} />
              </div>
            </div>

            {/* Section 3: Execution Audit & Transactions Feed */}
            <TradeLog 
              userId={session?.user?.id} 
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
            <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h1 className="text-2xl font-bold tracking-tight text-slate-950 dark:text-white flex items-center gap-2.5">
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
                    <span>{liveDashboard?.status_badge || 'Credentials Required'}</span>
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-[#8E8F99]">
                  Real-time L2 execution directly against Polymarket CLOB. Pure Proportional Sleeve Sizing active.
                </p>
              </div>

              <div className="flex items-center gap-3">
                {!liveDashboard?.is_configured ? (
                  <Link
                    href="/settings"
                    className="px-5 py-2.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black hover:bg-slate-800 dark:hover:bg-slate-200 text-xs font-bold transition-all shadow-sm flex items-center gap-1.5"
                  >
                    <Settings size={13} />
                    <span>Configure L2 Keys in Settings</span>
                  </Link>
                ) : (
                  <Link
                    href="/settings"
                    className="px-4 py-2 rounded-full bg-slate-100 dark:bg-[#1C1D22] hover:bg-slate-200 dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-xs font-semibold text-slate-700 dark:text-white transition-all flex items-center gap-1.5"
                  >
                    <span>Manage Keys</span>
                    <ExternalLink size={12} />
                  </Link>
                )}
              </div>
            </div>

            {/* Metrics Row: USDC Balance, Portfolio Net Worth, Realized Live PnL */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
              <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 rounded-[24px] shadow-sm">
                <div className="text-[11px] text-slate-500 dark:text-[#8E8F99] font-medium mb-1.5 flex items-center gap-1.5">
                  <Coins size={13} />
                  <span>Real USDC L2 Cash Balance</span>
                </div>
                <div className="text-3xl font-extrabold font-mono text-slate-950 dark:text-white">
                  ${liveBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
                <div className="text-[10px] text-slate-400 dark:text-[#8E8F99] mt-1 font-mono">
                  Proxy: {liveDashboard?.polymarket_wallet_address ? `${liveDashboard.polymarket_wallet_address.slice(0, 6)}...${liveDashboard.polymarket_wallet_address.slice(-4)}` : 'Not linked'}
                </div>
              </div>

              <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 rounded-[24px] shadow-sm">
                <div className="text-[11px] text-slate-500 dark:text-[#8E8F99] font-medium mb-1.5 flex items-center gap-1.5">
                  <TrendingUp size={13} />
                  <span>Portfolio Net Worth (Cash + Open Legs)</span>
                </div>
                <div className="text-3xl font-extrabold font-mono text-emerald-600 dark:text-[#00D09C]">
                  ${liveNetWorth.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
                <div className="text-[10px] text-slate-400 dark:text-[#8E8F99] mt-1">
                  Open Positions Value: ${((liveDashboard?.open_positions_value) || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>

              <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 rounded-[24px] shadow-sm">
                <div className="text-[11px] text-slate-500 dark:text-[#8E8F99] font-medium mb-1.5 flex items-center gap-1.5">
                  <Zap size={13} />
                  <span>Realized Live PnL</span>
                </div>
                <div className={`text-3xl font-extrabold font-mono ${livePnl >= 0 ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}`}>
                  {livePnl >= 0 ? '+' : ''}${livePnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
                <div className="text-[10px] text-slate-400 dark:text-[#8E8F99] mt-1 font-mono">
                  {livePnlPct >= 0 ? '+' : ''}{livePnlPct.toFixed(2)}% on active capital
                </div>
              </div>
            </div>

            {/* Active Live Positions */}
            <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-bold text-slate-950 dark:text-white flex items-center gap-2">
                    <Activity size={15} className="text-[#00D09C]" />
                    <span>Active Live Positions ({liveDashboard?.active_positions?.length || 0})</span>
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-0.5">
                    Open market legs mirrored on Polymarket CLOB.
                  </p>
                </div>
              </div>

              {(!liveDashboard?.active_positions || liveDashboard.active_positions.length === 0) ? (
                <div className="py-12 text-center text-slate-400 dark:text-[#8E8F99] text-xs">
                  No active open live positions at this time.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-black/[0.06] dark:border-white/5 text-slate-500 dark:text-[#8E8F99]">
                        <th className="pb-3 font-semibold">Market / Question</th>
                        <th className="pb-3 font-semibold">Outcome</th>
                        <th className="pb-3 font-semibold">Entry Price</th>
                        <th className="pb-3 font-semibold">Notional</th>
                        <th className="pb-3 font-semibold">Source Whale</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-black/[0.04] dark:divide-white/5 font-mono">
                      {liveDashboard.active_positions.map((pos) => (
                        <tr key={pos.id} className="hover:bg-slate-50 dark:hover:bg-white/[0.02]">
                          <td className="py-3 pr-4 font-sans font-medium text-slate-900 dark:text-white max-w-xs truncate">
                            {pos.marketQuestion}
                          </td>
                          <td className="py-3">
                            <span className="px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-[#00D09C]/10 text-[#00D09C] font-bold text-[11px]">
                              {pos.outcome}
                            </span>
                          </td>
                          <td className="py-3 text-slate-700 dark:text-slate-300">
                            {pos.entryPrice.toFixed(3)}
                          </td>
                          <td className="py-3 font-bold text-slate-900 dark:text-white">
                            ${pos.notionalUsd.toFixed(2)}
                          </td>
                          <td className="py-3 text-slate-500 dark:text-[#8E8F99]">
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
            <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-bold text-slate-950 dark:text-white flex items-center gap-2">
                    <ShieldCheck size={15} className="text-[#00D09C]" />
                    <span>Live CLOB Trade Fills &amp; Settlements ({liveDashboard?.execution_logs?.length || 0})</span>
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-0.5">
                    Authentic non-sandbox trade logs executed through Layer 2.
                  </p>
                </div>
              </div>

              {(!liveDashboard?.execution_logs || liveDashboard.execution_logs.length === 0) ? (
                <div className="py-12 text-center text-slate-400 dark:text-[#8E8F99] text-xs">
                  No live real-money trades executed yet. Once whale signals trigger, they will be logged here with authentic CLOB settlement hashes.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-black/[0.06] dark:border-white/5 text-slate-500 dark:text-[#8E8F99]">
                        <th className="pb-3 font-semibold">Time</th>
                        <th className="pb-3 font-semibold">Side</th>
                        <th className="pb-3 font-semibold">Market</th>
                        <th className="pb-3 font-semibold">Outcome</th>
                        <th className="pb-3 font-semibold">Fill Price</th>
                        <th className="pb-3 font-semibold">Notional</th>
                        <th className="pb-3 font-semibold">Realized PnL</th>
                        <th className="pb-3 font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-black/[0.04] dark:divide-white/5 font-mono">
                      {liveDashboard.execution_logs.map((l) => (
                        <tr key={l.id} className="hover:bg-slate-50 dark:hover:bg-white/[0.02]">
                          <td className="py-3 text-slate-500 dark:text-[#8E8F99]">
                            {new Date(l.timestamp).toLocaleTimeString()}
                          </td>
                          <td className="py-3">
                            <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${
                              l.side === 'BUY' ? 'bg-emerald-50 dark:bg-[#00D09C]/10 text-[#00D09C]' : 'bg-amber-50 dark:bg-amber-500/10 text-amber-500'
                            }`}>
                              {l.side}
                            </span>
                          </td>
                          <td className="py-3 pr-4 font-sans font-medium text-slate-900 dark:text-white max-w-xs truncate">
                            {l.marketQuestion}
                          </td>
                          <td className="py-3 text-slate-700 dark:text-slate-300">
                            {l.outcome}
                          </td>
                          <td className="py-3 text-slate-700 dark:text-slate-300">
                            {l.fillPrice.toFixed(3)}
                          </td>
                          <td className="py-3 font-bold text-slate-900 dark:text-white">
                            ${l.size.toFixed(2)}
                          </td>
                          <td className="py-3">
                            {l.pnl !== null && l.pnl !== undefined ? (
                              <span className={`font-bold ${l.pnl >= 0 ? 'text-[#00D09C]' : 'text-[#FF453A]'}`}>
                                {l.pnl >= 0 ? '+' : ''}${l.pnl.toFixed(2)}
                              </span>
                            ) : (
                              <span className="text-slate-400 dark:text-slate-600">-</span>
                            )}
                          </td>
                          <td className="py-3">
                            <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-[#1C1D22] text-slate-700 dark:text-slate-300 text-[10px]">
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
      />

      {/* 2. Rebalance Modal */}
      <RebalanceModal
        isOpen={isRebalanceOpen}
        onClose={() => setIsRebalanceOpen(false)}
        onRebalanceExecute={loadData}
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
        onResetComplete={loadData}
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
