'use client';
import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { motion, AnimatePresence } from 'framer-motion';
import { BalanceCounter } from '@/components/dashboard/BalanceCounter';
import { PnLChartWidget } from '@/components/dashboard/PnLChartWidget';
import { ScorecardWidget } from '@/components/dashboard/ScorecardWidget';
import { LiveTape } from '@/components/dashboard/LiveTape';
import { WalletLeaderboard } from '@/components/dashboard/WalletLeaderboard';
import { TradeLog } from '@/components/dashboard/TradeLog';
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
  RotateCcw, 
  LayoutGrid
} from 'lucide-react';
import { signOut } from 'next-auth/react';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { soundFx } from '@/lib/sound';

export type WidgetSize = 'small' | 'medium' | 'full';

export interface WidgetConfig {
  id: string;
  size: WidgetSize;
  height?: 'normal' | 'tall';
}

const DEFAULT_WIDGET_CONFIGS: WidgetConfig[] = [
  { id: 'pnl_chart', size: 'medium', height: 'normal' },
  { id: 'scorecard', size: 'small', height: 'normal' },
  { id: 'live_tape', size: 'medium', height: 'normal' },
  { id: 'whale_leaderboard', size: 'small', height: 'normal' },
  { id: 'positions_table', size: 'full', height: 'normal' },
];

const SIZE_CLASSES: Record<WidgetSize, string> = {
  small: 'col-span-1',
  medium: 'col-span-1 lg:col-span-2',
  full: 'col-span-1 md:col-span-2 lg:col-span-3',
};

const NEXT_SIZE_CYCLE: Record<WidgetSize, WidgetSize> = {
  small: 'medium',
  medium: 'full',
  full: 'small',
};

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

  // Apple-Style Modular Widgets State
  const [widgets, setWidgets] = useState<WidgetConfig[]>(DEFAULT_WIDGET_CONFIGS);
  const [showLayoutMenu, setShowLayoutMenu] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem('baleen_apple_widgets_v4');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setWidgets(parsed);
        }
      }
    } catch {}
  }, []);

  const saveWidgets = (newWidgets: WidgetConfig[]) => {
    setWidgets(newWidgets);
    try {
      localStorage.setItem('baleen_apple_widgets_v4', JSON.stringify(newWidgets));
    } catch {}
  };

  const cycleWidgetSize = (id: string) => {
    const updated = widgets.map(w => {
      if (w.id === id) {
        const next = NEXT_SIZE_CYCLE[w.size] || 'small';
        return { ...w, size: next };
      }
      return w;
    });
    saveWidgets(updated);
  };

  const applyPreset = (preset: 'default' | 'studio' | 'trading') => {
    if (preset === 'default') {
      saveWidgets(DEFAULT_WIDGET_CONFIGS);
    } else if (preset === 'studio') {
      saveWidgets([
        { id: 'pnl_chart', size: 'full', height: 'tall' },
        { id: 'scorecard', size: 'full', height: 'normal' },
        { id: 'live_tape', size: 'medium', height: 'tall' },
        { id: 'whale_leaderboard', size: 'small', height: 'tall' },
        { id: 'positions_table', size: 'full', height: 'normal' },
      ]);
    } else if (preset === 'trading') {
      saveWidgets([
        { id: 'live_tape', size: 'medium', height: 'tall' },
        { id: 'whale_leaderboard', size: 'small', height: 'tall' },
        { id: 'pnl_chart', size: 'medium', height: 'normal' },
        { id: 'scorecard', size: 'small', height: 'normal' },
        { id: 'positions_table', size: 'full', height: 'normal' },
      ]);
    }
    setShowLayoutMenu(false);
  };

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

  const renderWidgetContent = (w: WidgetConfig) => {
    switch (w.id) {
      case 'pnl_chart':
        return (
          <PnLChartWidget
            logs={logs}
            userId={session?.user?.id}
            startingBalance={portfolio?.startingBalance ?? user?.startingBalance ?? 10000.0}
            currentBalance={liveBalance}
            onResetComplete={loadData}
            heightMode={w.height || 'normal'}
            onCycleSize={() => cycleWidgetSize('pnl_chart')}
          />
        );
      case 'scorecard':
        return (
          <ScorecardWidget
            logs={logs}
            totalFilledTrades={portfolio?.filledTradesCount || 5049}
            allTimeWinRate={portfolio?.allTimeWinRate}
            allTimeWins={portfolio?.allTimeWins}
            allTimeLosses={portfolio?.allTimeLosses}
            sizeMode={w.size}
            onCycleSize={() => cycleWidgetSize('scorecard')}
          />
        );
      case 'live_tape':
        return (
          <div className="relative group h-full">
            <LiveTape 
              userId={session?.user?.id} 
              onSelectTrade={setSelectedTrade} 
            />
            <button
              onClick={() => cycleWidgetSize('live_tape')}
              className="absolute bottom-2 right-2 p-1.5 rounded-xl bg-black/[0.03] hover:bg-black/[0.08] text-slate-400 hover:text-slate-800 transition-all opacity-40 group-hover:opacity-100 cursor-nwse-resize z-20"
              title="Click to cycle card width (1/3 → 2/3 → Full)"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 2L2 10M10 6L6 10M10 10H10.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        );
      case 'whale_leaderboard':
        return (
          <div className="relative group h-full">
            <WalletLeaderboard 
              userId={session?.user?.id} 
              onSelectWallet={setSelectedWallet} 
            />
            <button
              onClick={() => cycleWidgetSize('whale_leaderboard')}
              className="absolute bottom-2 right-2 p-1.5 rounded-xl bg-black/[0.03] hover:bg-black/[0.08] text-slate-400 hover:text-slate-800 transition-all opacity-40 group-hover:opacity-100 cursor-nwse-resize z-20"
              title="Click to cycle card width (1/3 → 2/3 → Full)"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 2L2 10M10 6L6 10M10 10H10.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        );
      case 'positions_table':
        return (
          <div className="relative group h-full">
            <TradeLog 
              userId={session?.user?.id} 
              totalHoldingCount={portfolio?.holdingTradesCount}
              totalClosedCount={portfolio?.closedTradesCount}
              totalFillsCount={portfolio?.filledTradesCount}
              onSelectTrade={setSelectedTrade} 
            />
            <button
              onClick={() => cycleWidgetSize('positions_table')}
              className="absolute bottom-2 right-2 p-1.5 rounded-xl bg-black/[0.03] hover:bg-black/[0.08] text-slate-400 hover:text-slate-800 transition-all opacity-40 group-hover:opacity-100 cursor-nwse-resize z-20"
              title="Click to cycle card width (1/3 → 2/3 → Full)"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 2L2 10M10 6L6 10M10 10H10.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        );
      default:
        return null;
    }
  };

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
        {/* Header Section with Balance & Layout Presets */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-6 pb-2">
          <BalanceCounter 
            balance={liveBalance} 
            pnl={livePnl} 
            pnlPct={livePnlPct} 
            onResetClick={() => setIsResetOpen(true)}
          />
          
          <div className="flex items-center gap-2.5 flex-wrap relative">
            {/* Quick Layout Presets Button */}
            <div className="relative">
              <button
                onClick={() => setShowLayoutMenu(!showLayoutMenu)}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-2xl text-xs font-semibold bg-white/80 hover:bg-white text-slate-700 border border-black/[0.08] transition-all cursor-pointer shadow-xs"
                title="Choose dashboard layout preset"
              >
                <LayoutGrid size={13} />
                <span>Layout Presets</span>
              </button>

              {showLayoutMenu && (
                <div className="absolute right-0 top-full mt-2 w-48 bg-white/95 backdrop-blur-2xl rounded-2xl border border-black/[0.08] shadow-2xl p-1.5 z-50 space-y-1">
                  <button
                    onClick={() => applyPreset('default')}
                    className="w-full text-left px-3 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                  >
                    Standard (3-Column)
                  </button>
                  <button
                    onClick={() => applyPreset('studio')}
                    className="w-full text-left px-3 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                  >
                    Studio (Full-Width)
                  </button>
                  <button
                    onClick={() => applyPreset('trading')}
                    className="w-full text-left px-3 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                  >
                    Trading Desk (Tape First)
                  </button>
                </div>
              )}
            </div>

            <div className="bg-white/80 backdrop-blur-md px-3.5 py-2 rounded-2xl flex items-center gap-2.5 border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_1px_3px_rgba(0,0,0,0.02)]">
              <span className="text-xs text-slate-500 font-medium">Risk Regime</span>
              <span className="text-xs font-bold text-slate-900 px-2 py-0.5 rounded-full bg-slate-100 border border-black/[0.06]">
                {user?.riskProfile || 'Balanced'}
              </span>
            </div>
          </div>
        </div>

        {/* Apple-Style Fluid 3-Column Responsive Widget Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {widgets.map((w) => {
            const sizeClass = SIZE_CLASSES[w.size] || 'col-span-1';
            return (
              <motion.div
                key={w.id}
                layout
                transition={{ type: 'spring', damping: 28, stiffness: 320 }}
                className={`${sizeClass} flex flex-col transition-all duration-300 relative`}
              >
                {/* Rendered Widget Tile with Built-in Apple Grabber */}
                <div className="w-full flex-1 h-full">
                  {renderWidgetContent(w)}
                </div>
              </motion.div>
            );
          })}
        </div>
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
