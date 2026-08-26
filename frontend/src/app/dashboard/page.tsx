'use client';
import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { motion, Reorder, AnimatePresence } from 'framer-motion';
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
  GripVertical, 
  Maximize2, 
  Minimize2, 
  SlidersHorizontal, 
  RotateCcw, 
  ArrowUp, 
  ArrowDown, 
  Sparkles,
  LayoutGrid,
  Check
} from 'lucide-react';
import { signOut } from 'next-auth/react';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { soundFx } from '@/lib/sound';

export type WidgetSize = 'small' | 'medium' | 'full';

export interface WidgetConfig {
  id: string;
  size: WidgetSize;
  height?: 'normal' | 'tall';
  visible?: boolean;
}

const DEFAULT_WIDGET_CONFIGS: WidgetConfig[] = [
  { id: 'pnl_chart', size: 'medium', height: 'normal', visible: true },
  { id: 'scorecard', size: 'small', height: 'normal', visible: true },
  { id: 'live_tape', size: 'medium', height: 'normal', visible: true },
  { id: 'whale_leaderboard', size: 'small', height: 'normal', visible: true },
  { id: 'positions_table', size: 'full', height: 'normal', visible: true },
];

const WIDGET_TITLES: Record<string, string> = {
  pnl_chart: 'Capital Curve & Performance Chart',
  scorecard: 'Execution Scorecard & Win Rate',
  live_tape: 'Live Execution Tape',
  whale_leaderboard: 'Active Whale Leaderboard',
  positions_table: 'Positions & Execution Audit',
};

const SIZE_LABELS: Record<WidgetSize, string> = {
  small: '1/3 Width',
  medium: '2/3 Width',
  full: 'Full Width',
};

const SIZE_CLASSES: Record<WidgetSize, string> = {
  small: 'col-span-1',
  medium: 'col-span-1 lg:col-span-2',
  full: 'col-span-1 md:col-span-2 lg:col-span-3',
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
  const [isCustomizing, setIsCustomizing] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem('baleen_apple_widgets_v3');
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
      localStorage.setItem('baleen_apple_widgets_v3', JSON.stringify(newWidgets));
    } catch {}
  };

  const setWidgetSize = (id: string, size: WidgetSize) => {
    const updated = widgets.map(w => w.id === id ? { ...w, size } : w);
    saveWidgets(updated);
  };

  const toggleWidgetHeight = (id: string) => {
    const updated = widgets.map(w => {
      if (w.id === id) {
        const nextHeight: 'normal' | 'tall' = w.height === 'tall' ? 'normal' : 'tall';
        return { ...w, height: nextHeight };
      }
      return w;
    });
    saveWidgets(updated);
  };

  const moveWidget = (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= widgets.length) return;
    const updated = [...widgets];
    const [moved] = updated.splice(index, 1);
    updated.splice(newIndex, 0, moved);
    saveWidgets(updated);
  };

  const applyPreset = (preset: 'default' | 'studio' | 'trading') => {
    if (preset === 'default') {
      saveWidgets(DEFAULT_WIDGET_CONFIGS);
    } else if (preset === 'studio') {
      saveWidgets([
        { id: 'pnl_chart', size: 'full', height: 'tall', visible: true },
        { id: 'scorecard', size: 'small', height: 'normal', visible: true },
        { id: 'whale_leaderboard', size: 'medium', height: 'normal', visible: true },
        { id: 'live_tape', size: 'full', height: 'tall', visible: true },
        { id: 'positions_table', size: 'full', height: 'normal', visible: true },
      ]);
    } else if (preset === 'trading') {
      saveWidgets([
        { id: 'live_tape', size: 'medium', height: 'tall', visible: true },
        { id: 'whale_leaderboard', size: 'small', height: 'tall', visible: true },
        { id: 'pnl_chart', size: 'medium', height: 'normal', visible: true },
        { id: 'scorecard', size: 'small', height: 'normal', visible: true },
        { id: 'positions_table', size: 'full', height: 'normal', visible: true },
      ]);
    }
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
          />
        );
      case 'live_tape':
        return (
          <LiveTape 
            userId={session?.user?.id} 
            onSelectTrade={setSelectedTrade} 
          />
        );
      case 'whale_leaderboard':
        return (
          <WalletLeaderboard 
            userId={session?.user?.id} 
            onSelectWallet={setSelectedWallet} 
          />
        );
      case 'positions_table':
        return (
          <TradeLog 
            userId={session?.user?.id} 
            totalHoldingCount={portfolio?.holdingTradesCount}
            totalClosedCount={portfolio?.closedTradesCount}
            totalFillsCount={portfolio?.filledTradesCount}
            onSelectTrade={setSelectedTrade} 
          />
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
        {/* Header Section with Balance & Apple Widget Customizer Bar */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-6 pb-2">
          <BalanceCounter 
            balance={liveBalance} 
            pnl={livePnl} 
            pnlPct={livePnlPct} 
            onResetClick={() => setIsResetOpen(true)}
          />
          
          <div className="flex items-center gap-2.5 flex-wrap">
            {/* Apple / Revolut Widget Customizer Toggle */}
            <button
              onClick={() => setIsCustomizing(!isCustomizing)}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-2xl text-xs font-semibold border transition-all cursor-pointer shadow-xs ${
                isCustomizing
                  ? 'bg-slate-950 text-white border-slate-900 shadow-md ring-2 ring-indigo-500/30'
                  : 'bg-white/80 hover:bg-white text-slate-700 border-black/[0.08]'
              }`}
              title="Customize, resize and reorder widgets"
            >
              <LayoutGrid size={13} />
              <span>{isCustomizing ? 'Done Editing' : 'Customize Widgets'}</span>
            </button>

            {isCustomizing && (
              <div className="flex items-center gap-1.5 bg-white/90 backdrop-blur-md p-1 rounded-2xl border border-black/[0.08] shadow-sm">
                <button
                  onClick={() => applyPreset('default')}
                  className="px-2.5 py-1 rounded-xl text-[11px] font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
                  title="Default 3-Column Balance Layout"
                >
                  Standard
                </button>
                <button
                  onClick={() => applyPreset('studio')}
                  className="px-2.5 py-1 rounded-xl text-[11px] font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
                  title="Full-Width Pro Analytics Layout"
                >
                  Full Width
                </button>
                <button
                  onClick={() => applyPreset('trading')}
                  className="px-2.5 py-1 rounded-xl text-[11px] font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
                  title="Live Tape & Scalp Priority Layout"
                >
                  Live Scalp
                </button>
                <button
                  onClick={() => applyPreset('default')}
                  className="p-1 rounded-xl text-slate-400 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
                  title="Reset to Default"
                >
                  <RotateCcw size={12} />
                </button>
              </div>
            )}

            <div className="bg-white/80 backdrop-blur-md px-3.5 py-2 rounded-2xl flex items-center gap-2.5 border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_1px_3px_rgba(0,0,0,0.02)]">
              <span className="text-xs text-slate-500 font-medium">Risk Regime</span>
              <span className="text-xs font-bold text-slate-900 px-2 py-0.5 rounded-full bg-slate-100 border border-black/[0.06]">
                {user?.riskProfile || 'Balanced'}
              </span>
            </div>
          </div>
        </div>

        {/* Apple-Style Responsive 3-Column Widget Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {widgets.map((w, index) => {
            const sizeClass = SIZE_CLASSES[w.size] || 'col-span-1';
            return (
              <motion.div
                key={w.id}
                layout
                transition={{ type: 'spring', damping: 26, stiffness: 260 }}
                className={`${sizeClass} flex flex-col transition-all duration-300 relative ${
                  isCustomizing ? 'ring-2 ring-indigo-400/60 ring-dashed rounded-3xl p-1 bg-indigo-50/25 shadow-lg' : ''
                }`}
              >
                {/* Individual Widget Customizer Toolbar (Visible when Customizing) */}
                {isCustomizing && (
                  <div className="flex items-center justify-between px-3.5 py-2 mb-2 bg-white/95 backdrop-blur-md rounded-2xl border border-black/[0.08] shadow-sm select-none">
                    <div className="flex items-center gap-2 text-slate-800">
                      <span className="text-[11px] font-mono font-bold tracking-tight">{WIDGET_TITLES[w.id] || w.id}</span>
                    </div>

                    {/* Granular Size & Position Switcher */}
                    <div className="flex items-center gap-2">
                      {/* Size Selector: 1/3, 2/3, Full */}
                      <div className="flex rounded-xl bg-slate-100 p-0.5 border border-black/[0.04] text-[10px] font-mono font-bold">
                        {(['small', 'medium', 'full'] as WidgetSize[]).map((s) => (
                          <button
                            key={s}
                            onClick={() => setWidgetSize(w.id, s)}
                            className={`px-2 py-0.5 rounded-lg transition-all cursor-pointer ${
                              w.size === s
                                ? 'bg-slate-950 text-white shadow-xs'
                                : 'text-slate-500 hover:text-slate-900'
                            }`}
                            title={`Resize to ${SIZE_LABELS[s]}`}
                          >
                            {s === 'small' ? '1/3' : s === 'medium' ? '2/3' : 'Full'}
                          </button>
                        ))}
                      </div>

                      {/* Height Toggle (For chart & tape) */}
                      {(w.id === 'pnl_chart' || w.id === 'live_tape') && (
                        <button
                          onClick={() => toggleWidgetHeight(w.id)}
                          className={`px-2 py-0.5 rounded-xl border text-[10px] font-mono font-bold transition-all cursor-pointer ${
                            w.height === 'tall'
                              ? 'bg-indigo-600 text-white border-indigo-600'
                              : 'bg-white text-slate-600 border-black/[0.08] hover:bg-slate-50'
                          }`}
                          title={w.height === 'tall' ? 'Switch to Standard Height' : 'Switch to Tall Height'}
                        >
                          {w.height === 'tall' ? 'Tall' : 'Normal'}
                        </button>
                      )}

                      {/* Move Order Buttons */}
                      <div className="flex items-center gap-0.5 border-l border-black/[0.06] pl-1.5">
                        <button
                          onClick={() => moveWidget(index, 'up')}
                          disabled={index === 0}
                          className="p-1 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 disabled:opacity-30 cursor-pointer"
                          title="Move Earlier"
                        >
                          <ArrowUp size={12} />
                        </button>
                        <button
                          onClick={() => moveWidget(index, 'down')}
                          disabled={index === widgets.length - 1}
                          className="p-1 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 disabled:opacity-30 cursor-pointer"
                          title="Move Later"
                        >
                          <ArrowDown size={12} />
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Rendered Widget Tile */}
                <div className="w-full flex-1">
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
