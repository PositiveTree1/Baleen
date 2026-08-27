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
import { ActivityFeed } from '@/components/dashboard/ActivityFeed';
import { CommandPalette } from '@/components/ui/CommandPalette';
import { fetchUserSettings, fetchPortfolioSummary, fetchExecutionLogs, getCachedExecutionLogs, getCachedPortfolioSummary } from '@/lib/api-client';
import { User, ExecutionLog, PortfolioSummary } from '@/types';
import Link from 'next/link';
import { 
  Settings, 
  LogOut, 
  Volume2, 
  VolumeX, 
  Bell,
  Search,
  Sliders,
  ShieldCheck
} from 'lucide-react';
import { signOut } from 'next-auth/react';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { soundFx } from '@/lib/sound';

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const [selectedWallet, setSelectedWallet] = useState<string | null>(null);
  const [selectedTrade, setSelectedTrade] = useState<ExecutionLog | null>(null);
  const [isResetOpen, setIsResetOpen] = useState(false);
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
      <div className="min-h-screen flex items-center justify-center bg-[#000000] text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-[#00D09C] border-t-transparent animate-spin" />
          <span className="text-xs font-mono text-[#8E8F99]">Connecting to Revolut Control Plane...</span>
        </div>
      </div>
    );
  }

  const liveBalance = portfolio?.currentBalance ?? user?.currentBalance ?? 10000.0;
  const livePnl = portfolio?.totalPnlUsd ?? 0.0;
  const livePnlPct = portfolio?.totalPnlPct ?? 0.0;
  const userInitial = session?.user?.name ? session.user.name.slice(0, 2).toUpperCase() : 'BL';

  return (
    <div className="min-h-screen flex flex-col bg-[#000000] text-white selection:bg-[#00D09C] selection:text-black relative overflow-x-hidden font-sans">
      
      {/* Revolut Top Bar Navigation */}
      <nav className="flex items-center justify-between py-4 px-6 lg:px-12 border-b border-white/[0.08] bg-[#000000]/90 backdrop-blur-2xl sticky top-0 z-40">
        
        {/* Left: User Avatar Circle & Brand Logo */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-[#FF7A00] text-black font-bold flex items-center justify-center text-sm shadow-md">
            {userInitial}
          </div>
          <BrandLogo href="/" subtitle="Revolut Control" />
        </div>

        {/* Center: Search Command Bar (Revolut pill style) */}
        <div className="hidden md:flex items-center gap-2 px-4 py-2 rounded-full bg-[#1C1D22] border border-white/5 text-xs text-[#8E8F99] w-64 hover:border-white/15 transition-all cursor-pointer">
          <Search size={14} className="text-[#8E8F99]" />
          <span>Search markets, whales...</span>
          <span className="ml-auto text-[10px] font-mono bg-[#2C2D35] px-1.5 py-0.5 rounded text-white">⌘K</span>
        </div>

        {/* Right: Circular Icon Actions */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setActivityOpen(true)}
            className="w-10 h-10 rounded-full bg-[#1C1D22] hover:bg-[#2C2D35] border border-white/10 text-white flex items-center justify-center transition-all cursor-pointer"
            title="Activity Feed & Notifications"
          >
            <Bell size={16} />
          </button>

          <button
            onClick={toggleSound}
            className={`w-10 h-10 rounded-full border transition-all cursor-pointer flex items-center justify-center ${
              soundActive 
                ? 'bg-[#00D09C]/10 text-[#00D09C] border-[#00D09C]/30' 
                : 'bg-[#1C1D22] hover:bg-[#2C2D35] border-white/10 text-[#8E8F99]'
            }`}
            title={soundActive ? 'Mute Trade Signal Chimes' : 'Enable Real-time Sound Chimes'}
          >
            {soundActive ? <Volume2 size={16} /> : <VolumeX size={16} />}
          </button>

          <Link href="/admin" className="text-xs font-bold text-white px-3.5 py-2 rounded-full bg-[#1C1D22] hover:bg-[#2C2D35] border border-white/10 transition-all">
            Admin
          </Link>
          
          <Link href="/settings" className="w-10 h-10 rounded-full bg-[#1C1D22] hover:bg-[#2C2D35] border border-white/10 text-white flex items-center justify-center transition-all">
            <Settings size={16} />
          </Link>
          
          <button onClick={() => signOut()} className="w-10 h-10 rounded-full bg-[#1C1D22] hover:bg-rose-950/60 border border-white/10 text-[#8E8F99] hover:text-[#FF453A] flex items-center justify-center transition-all cursor-pointer">
            <LogOut size={16} />
          </button>
        </div>
      </nav>

      {/* Main Revolut Container */}
      <main className="flex-1 p-4 sm:p-6 lg:p-12 max-w-7xl mx-auto w-full flex flex-col gap-8 relative z-10">
        
        {/* Hero Section: Revolut Balance & 4-Action Row */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-6 pt-2">
          <BalanceCounter 
            balance={liveBalance} 
            pnl={livePnl} 
            pnlPct={livePnlPct} 
            onResetClick={() => setIsResetOpen(true)}
            onAnalyticsClick={() => {
              window.scrollTo({ top: 350, behavior: 'smooth' });
            }}
            onMirrorClick={() => {
              window.scrollTo({ top: 900, behavior: 'smooth' });
            }}
          />

          <div className="flex items-center gap-2.5">
            <div className="revolut-card-sub bg-[#1C1D22] px-4 py-2 rounded-full flex items-center gap-2 text-xs font-medium text-[#8E8F99] border border-white/5">
              <span>Risk Regime:</span>
              <span className="font-bold text-white font-mono px-2 py-0.5 rounded-full bg-[#2C2D35]">
                {user?.riskProfile || 'Balanced'}
              </span>
            </div>
          </div>
        </div>

        {/* Section 1: Revolut Dark Line Chart & Analytics Cards */}
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

        {/* Section 3: Revolut Execution Audit & Transactions Feed */}
        <TradeLog 
          userId={session?.user?.id} 
          totalHoldingCount={portfolio?.holdingTradesCount}
          totalClosedCount={portfolio?.closedTradesCount}
          totalFillsCount={portfolio?.filledTradesCount}
          onSelectTrade={setSelectedTrade} 
        />
      </main>

      {/* Quick Command Palette (CMD+K) */}
      <CommandPalette onSelectWallet={setSelectedWallet} />

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

      {/* Reset Sandbox Modal */}
      <ResetSandboxModal
        isOpen={isResetOpen}
        onClose={() => setIsResetOpen(false)}
        userId={session?.user?.id}
        currentBalance={liveBalance}
        onResetComplete={loadData}
      />

      {/* Activity Feed / Notification Panel */}
      <ActivityFeed
        isOpen={activityOpen}
        onClose={() => setActivityOpen(false)}
      />
    </div>
  );
}
