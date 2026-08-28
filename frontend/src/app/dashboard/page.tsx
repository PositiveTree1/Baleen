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
import { fetchUserSettings, fetchPortfolioSummary, fetchExecutionLogs, getCachedExecutionLogs, getCachedPortfolioSummary } from '@/lib/api-client';
import { User, ExecutionLog, PortfolioSummary } from '@/types';
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
  Moon
} from 'lucide-react';
import { signOut } from 'next-auth/react';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { soundFx } from '@/lib/sound';

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const { theme, toggleTheme } = useTheme();
  const [selectedWallet, setSelectedWallet] = useState<string | null>(null);
  const [selectedTrade, setSelectedTrade] = useState<ExecutionLog | null>(null);
  
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
    try {
      const [userData, portfolioData, logsData] = await Promise.all([
        session?.user?.id ? fetchUserSettings(session.user.id) : null,
        fetchPortfolioSummary(session?.user?.id),
        fetchExecutionLogs(session?.user?.id, { limit: '100' })
      ]);
      if (userData) setUser(userData);
      if (portfolioData) setPortfolio(portfolioData);
      if (Array.isArray(logsData)) setLogs(logsData);
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

  const liveBalance = portfolio?.currentBalance ?? user?.currentBalance ?? 10000.0;
  const livePnl = portfolio?.totalPnlUsd ?? 0.0;
  const livePnlPct = portfolio?.totalPnlPct ?? 0.0;

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FB] dark:bg-[#000000] text-slate-900 dark:text-white selection:bg-[#00D09C] selection:text-black relative overflow-x-hidden font-sans transition-colors duration-150">
      
      {/* Top Bar Navigation (Clean Baleen Brand) */}
      <nav className="flex items-center justify-between py-4 px-6 lg:px-12 border-b border-black/[0.06] dark:border-white/[0.08] bg-white/80 dark:bg-[#000000]/90 backdrop-blur-2xl sticky top-0 z-40">
        
        {/* Left: Baleen Brand Logo */}
        <div className="flex items-center gap-3">
          <BrandLogo href="/" />
        </div>

        {/* Center: Search Command Bar (Clickable) */}
        <div 
          onClick={() => setCommandPaletteOpen(true)}
          className="hidden md:flex items-center gap-2 px-4 py-2 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 text-xs text-[#8E8F99] w-64 hover:border-black/20 dark:hover:border-white/20 transition-all cursor-pointer shadow-2xs"
        >
          <Search size={14} className="text-[#8E8F99]" />
          <span className="text-slate-600 dark:text-[#8E8F99]">Search markets, whales...</span>
          <span className="ml-auto text-[10px] font-mono bg-white dark:bg-[#2C2D35] px-1.5 py-0.5 rounded text-slate-700 dark:text-white shadow-2xs">⌘K</span>
        </div>

        {/* Right: Circular Icon Actions */}
        <div className="flex items-center gap-2.5">
          {/* Light / Dark Mode Toggle */}
          <button
            onClick={toggleTheme}
            className="w-10 h-10 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-white flex items-center justify-center transition-all cursor-pointer shadow-2xs"
            title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
          >
            {theme === 'light' ? <Moon size={16} /> : <Sun size={16} className="text-amber-400" />}
          </button>

          <button
            onClick={() => setActivityOpen(true)}
            className="w-10 h-10 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-white flex items-center justify-center transition-all cursor-pointer shadow-2xs"
            title="Activity Feed & Notifications"
          >
            <Bell size={16} />
          </button>

          <button
            onClick={toggleSound}
            className={`w-10 h-10 rounded-full border transition-all cursor-pointer flex items-center justify-center ${
              soundActive 
                ? 'bg-[#00D09C]/10 text-[#00D09C] border-[#00D09C]/30' 
                : 'bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-[#8E8F99]'
            }`}
            title={soundActive ? 'Mute Trade Signal Chimes' : 'Enable Real-time Sound Chimes'}
          >
            {soundActive ? <Volume2 size={16} /> : <VolumeX size={16} />}
          </button>

          <Link href="/admin" className="text-xs font-bold text-slate-900 dark:text-white px-3.5 py-2 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 transition-all">
            Admin
          </Link>
          
          <Link href="/settings" className="w-10 h-10 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-white flex items-center justify-center transition-all">
            <Settings size={16} />
          </Link>
          
          <button onClick={() => signOut()} className="w-10 h-10 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-rose-50 dark:hover:bg-rose-950/60 border border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-[#8E8F99] hover:text-[#FF453A] flex items-center justify-center transition-all cursor-pointer">
            <LogOut size={16} />
          </button>
        </div>
      </nav>

      {/* Main Container */}
      <main className="flex-1 p-4 sm:p-6 lg:p-12 max-w-7xl mx-auto w-full flex flex-col gap-8 relative z-10">
        
        {/* Hero Section: Balance & 4-Action Row (Fully Functional) */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-6 pt-2">
          <BalanceCounter 
            balance={liveBalance} 
            pnl={livePnl} 
            pnlPct={livePnlPct} 
            onMirrorClick={() => setIsMirrorOpen(true)}
            onRebalanceClick={() => setIsRebalanceOpen(true)}
            onAnalyticsClick={() => setIsAnalyticsOpen(true)}
            onResetClick={() => setIsResetOpen(true)}
          />

          <div className="flex items-center gap-2.5">
            <div className="revolut-card-sub bg-[#F1F3F5] dark:bg-[#1C1D22] px-4 py-2 rounded-full flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-[#8E8F99] border border-black/[0.04] dark:border-white/5 shadow-2xs">
              <span>Risk Regime:</span>
              <span className="font-bold text-slate-900 dark:text-white font-mono px-2 py-0.5 rounded-full bg-white dark:bg-[#2C2D35] shadow-2xs">
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
          currentBalance={liveBalance}
          totalFilledTrades={portfolio?.filledTradesCount || 5049}
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
        currentBalance={liveBalance}
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
