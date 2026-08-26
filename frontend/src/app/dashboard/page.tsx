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
  Bell
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
      <div className="min-h-screen flex items-center justify-center bg-[#F8F9FB]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-slate-900 border-t-transparent animate-spin" />
          <span className="text-xs font-mono text-slate-400">Synchronizing Control Plane...</span>
        </div>
      </div>
    );
  }

  const liveBalance = portfolio?.currentBalance ?? user?.currentBalance ?? 10000.0;
  const livePnl = portfolio?.totalPnlUsd ?? 0.0;
  const livePnlPct = portfolio?.totalPnlPct ?? 0.0;

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FB] text-slate-900 selection:bg-slate-900 selection:text-white relative overflow-x-hidden">
      {/* Ambient Liquid Specular Background */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute -top-32 right-1/4 w-[650px] h-[650px] bg-gradient-to-br from-indigo-100/35 via-sky-50/25 to-transparent rounded-full blur-3xl opacity-60" />
        <div className="absolute top-1/3 -left-32 w-[550px] h-[550px] bg-gradient-to-tr from-slate-200/40 via-zinc-100/30 to-transparent rounded-full blur-3xl opacity-50" />
        <div className="absolute bottom-10 right-10 w-[600px] h-[600px] bg-gradient-to-tl from-indigo-100/25 via-slate-100/35 to-transparent rounded-full blur-3xl opacity-60" />
      </div>

      {/* Top Navigation */}
      <nav className="flex items-center justify-between py-4 px-6 lg:px-12 border-b border-black/[0.06] bg-white/70 backdrop-blur-2xl sticky top-0 z-40 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
        <BrandLogo href="/" subtitle="Control Plane" />
        <div className="flex items-center gap-3">
          <button
            onClick={() => setActivityOpen(true)}
            className="p-2 rounded-xl border border-black/[0.06] bg-white hover:bg-indigo-50 text-slate-500 hover:text-indigo-600 transition-colors cursor-pointer relative"
            title="Activity Feed & Notifications"
          >
            <Bell size={16} />
          </button>

          <button
            onClick={toggleSound}
            className={`p-2 rounded-xl border transition-colors cursor-pointer ${
              soundActive 
                ? 'bg-indigo-50 text-indigo-700 border-indigo-200 shadow-sm' 
                : 'text-slate-500 hover:text-slate-900 border-black/[0.06] bg-white hover:bg-slate-50'
            }`}
            title={soundActive ? 'Mute Trade Signal Chimes' : 'Enable Real-time Sound Chimes'}
          >
            {soundActive ? <Volume2 size={16} /> : <VolumeX size={16} />}
          </button>

          <Link href="/admin" className="text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors px-3 py-1.5 rounded-xl hover:bg-black/5">
            Admin
          </Link>
          <Link href="/settings" className="p-2 text-slate-600 hover:text-slate-900 hover:bg-black/5 rounded-xl transition-colors">
            <Settings size={18} />
          </Link>
          <button onClick={() => signOut()} className="p-2 text-slate-600 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-colors cursor-pointer">
            <LogOut size={18} />
          </button>
        </div>
      </nav>

      <main className="flex-1 p-6 lg:p-12 max-w-7xl mx-auto w-full flex flex-col gap-6 relative z-10">
        {/* Header Section with Balance */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-6 pb-2">
          <BalanceCounter 
            balance={liveBalance} 
            pnl={livePnl} 
            pnlPct={livePnlPct} 
            onResetClick={() => setIsResetOpen(true)}
          />
          
          <div className="flex items-center gap-2.5 flex-wrap">
            <div className="bg-white/80 backdrop-blur-md px-3.5 py-2 rounded-2xl flex items-center gap-2.5 border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_1px_3px_rgba(0,0,0,0.02)]">
              <span className="text-xs text-slate-500 font-medium">Risk Regime</span>
              <span className="text-xs font-bold text-slate-900 px-2 py-0.5 rounded-full bg-slate-100 border border-black/[0.06]">
                {user?.riskProfile || 'Balanced'}
              </span>
            </div>
          </div>
        </div>

        {/* Section 1: Portfolio Capital Curve & Performance Scorecard */}
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

        {/* Section 3: Positions & Execution Audit Log */}
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
