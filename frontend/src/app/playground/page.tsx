'use client';
import { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sparkles, Layers, ShieldCheck, TrendingUp, TrendingDown, 
  ArrowRight, Copy, Check, Sliders, Eye, RefreshCw, Zap,
  Compass, Play, BarChart3, Database, ShieldAlert, Cpu
} from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, BarChart, Bar, CartesianGrid, ReferenceLine, Cell } from 'recharts';
import Link from 'next/link';
import { BrandLogo } from '@/components/ui/BrandLogo';

// ==========================================
// 1. RICH SIMULATED MOCK DATA GENERATOR
// ==========================================

const MOCK_SNAPSHOTS_1D = [
  { time: '09:00', date: '26 août', balance: 14850.00, pnl: 4850.00 },
  { time: '10:00', date: '26 août', balance: 14920.50, pnl: 4920.50 },
  { time: '11:00', date: '26 août', balance: 14810.20, pnl: 4810.20 },
  { time: '12:00', date: '26 août', balance: 15120.80, pnl: 5120.80 },
  { time: '13:00', date: '26 août', balance: 15050.40, pnl: 5050.40 },
  { time: '14:00', date: '26 août', balance: 15280.90, pnl: 5280.90 },
  { time: '15:00', date: '26 août', balance: 15210.30, pnl: 5210.30 },
  { time: '16:00', date: '26 août', balance: 15341.32, pnl: 5341.32 },
];

const MOCK_WHALE_WIN_LOSS = [
  { date: '10 août', wonUsd: 1420.50, lostUsd: -240.00, netPnL: 1180.50, dailyPnL: 1180.50, cumulativePnL: 1180.50, tradesCount: 6 },
  { date: '12 août', wonUsd: 2850.00, lostUsd: -620.40, netPnL: 2229.60, dailyPnL: 2229.60, cumulativePnL: 3410.10, tradesCount: 14 },
  { date: '14 août', wonUsd: 410.20, lostUsd: -1850.00, netPnL: -1439.80, dailyPnL: -1439.80, cumulativePnL: 1970.30, tradesCount: 8 },
  { date: '16 août', wonUsd: 3640.80, lostUsd: -410.00, netPnL: 3230.80, dailyPnL: 3230.80, cumulativePnL: 5201.10, tradesCount: 18 },
  { date: '18 août', wonUsd: 520.00, lostUsd: -1640.20, netPnL: -1120.20, dailyPnL: -1120.20, cumulativePnL: 4080.90, tradesCount: 5 },
  { date: '20 août', wonUsd: 4210.00, lostUsd: -320.00, netPnL: 3890.00, dailyPnL: 3890.00, cumulativePnL: 7970.90, tradesCount: 22 },
  { date: '22 août', wonUsd: 5890.40, lostUsd: -890.00, netPnL: 5000.40, dailyPnL: 5000.40, cumulativePnL: 12971.30, tradesCount: 19 },
  { date: '24 août', wonUsd: 310.00, lostUsd: -1420.50, netPnL: -1110.50, dailyPnL: -1110.50, cumulativePnL: 11860.80, tradesCount: 7 },
  { date: '26 août', wonUsd: 3480.52, lostUsd: -0.00, netPnL: 3480.52, dailyPnL: 3480.52, cumulativePnL: 15341.32, tradesCount: 12 },
];

const MOCK_EXECUTIONS = [
  { id: '1', whale: 'hoodr', outcome: 'Yes', market: 'Fed Rate Cut in September 2026', fill: 0.88, live: 0.94, size: 250, pnl: 17.05, pnlPct: 6.82, time: '2m ago', isConsensus: true },
  { id: '2', whale: 'KrackenSruster', outcome: 'No', market: 'US Recession Declared Before Q4', fill: 0.72, live: 0.79, size: 400, pnl: 38.89, pnlPct: 9.72, time: '8m ago', isConsensus: true },
  { id: '3', whale: 'bloodmaster', outcome: 'Yes', market: 'Ethereum Above $4,000 End of Month', fill: 0.44, live: 0.39, size: 180, pnl: -20.45, pnlPct: -11.36, time: '14m ago', isConsensus: false },
  { id: '4', whale: 'iguana7', outcome: 'Yes', market: 'Democratic Control of US Senate 2026', fill: 0.95, live: 0.95, size: 500, pnl: 0.00, pnlPct: 0.00, time: '19m ago', isConsensus: true },
];

export default function PlaygroundPage() {
  // Playground interactive states
  const [selectedFont, setSelectedFont] = useState<'outfit' | 'jakarta' | 'cinzel'>('outfit');
  const [glassStyle, setGlassStyle] = useState<'apple-ice' | 'dark-obsidian' | 'liquid-sapphire'>('dark-obsidian');
  const [winLossMode, setWinLossMode] = useState<'discrete' | 'cumulative'>('discrete');
  const [liveTicking, setLiveTicking] = useState(true);
  const [mockBalance, setMockBalance] = useState(15341.32);
  const [headlineText, setHeadlineText] = useState('Mirror the top 1% on Polymarket.');

  // Simulated live ticking
  useEffect(() => {
    if (!liveTicking) return;
    const timer = setInterval(() => {
      setMockBalance((prev) => {
        const delta = (Math.random() - 0.48) * 1.85;
        return Math.round((prev + delta) * 100) / 100;
      });
    }, 2500);
    return () => clearInterval(timer);
  }, [liveTicking]);

  return (
    <div className="min-h-screen bg-[#07090E] text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white relative overflow-x-hidden">
      
      {/* Ambient Caustics & Specular Lighting */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute top-[-10%] left-[20%] w-[800px] h-[800px] bg-gradient-to-br from-indigo-900/20 via-sky-800/10 to-transparent rounded-full blur-3xl opacity-60" />
        <div className="absolute top-[40%] right-[-10%] w-[700px] h-[700px] bg-gradient-to-tl from-slate-800/30 via-indigo-950/20 to-transparent rounded-full blur-3xl opacity-50" />
        <div className="absolute bottom-[-10%] left-[-5%] w-[650px] h-[650px] bg-gradient-to-tr from-cyan-900/15 via-slate-900/30 to-transparent rounded-full blur-3xl opacity-40" />
      </div>

      {/* Top Laboratory Navigation */}
      <header className="sticky top-0 z-50 border-b border-white/[0.08] bg-[#07090E]/80 backdrop-blur-2xl px-6 lg:px-12 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BrandLogo size="md" subtitle="UI Laboratory" />
          <span className="text-white/20">|</span>
          <span className="text-[11px] font-mono font-bold text-cyan-400 bg-cyan-950/60 border border-cyan-500/30 px-2.5 py-0.5 rounded-full">
            LOCAL MOCK SANDBOX
          </span>
        </div>

        <div className="flex items-center gap-3">
          <Link 
            href="/"
            className="text-xs font-semibold text-slate-400 hover:text-white px-3 py-1.5 rounded-xl hover:bg-white/5 transition-colors"
          >
            Landing Page
          </Link>
          <Link 
            href="/dashboard"
            className="text-xs font-semibold text-slate-400 hover:text-white px-3 py-1.5 rounded-xl hover:bg-white/5 transition-colors"
          >
            Live Dashboard
          </Link>
          <Link 
            href="/admin"
            className="text-xs font-semibold text-slate-400 hover:text-white px-3 py-1.5 rounded-xl hover:bg-white/5 transition-colors"
          >
            Admin Control
          </Link>
        </div>
      </header>

      {/* Main Interactive Studio */}
      <main className="flex-1 max-w-7xl mx-auto w-full p-6 lg:p-10 relative z-10 space-y-10">
        
        {/* Lab Control Bar */}
        <div className="p-4 rounded-3xl bg-white/[0.03] border border-white/[0.08] backdrop-blur-xl flex flex-wrap items-center justify-between gap-4 shadow-xl">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
              <Sliders size={14} className="text-indigo-400" /> Active Presets:
            </span>

            {/* Glass Style Toggle */}
            <div className="flex p-1 rounded-2xl bg-black/40 border border-white/[0.08] text-xs font-semibold">
              <button
                onClick={() => setGlassStyle('dark-obsidian')}
                className={`px-3 py-1 rounded-xl transition-all ${
                  glassStyle === 'dark-obsidian' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
                }`}
              >
                Dark Obsidian Silk
              </button>
              <button
                onClick={() => setGlassStyle('liquid-sapphire')}
                className={`px-3 py-1 rounded-xl transition-all ${
                  glassStyle === 'liquid-sapphire' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
                }`}
              >
                Liquid Sapphire
              </button>
              <button
                onClick={() => setGlassStyle('apple-ice')}
                className={`px-3 py-1 rounded-xl transition-all ${
                  glassStyle === 'apple-ice' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
                }`}
              >
                Apple Frost Ice
              </button>
            </div>

            {/* Typography Selector */}
            <div className="flex p-1 rounded-2xl bg-black/40 border border-white/[0.08] text-xs font-semibold">
              <button
                onClick={() => setSelectedFont('outfit')}
                className={`px-3 py-1 rounded-xl transition-all ${
                  selectedFont === 'outfit' ? 'bg-white text-slate-950 font-bold shadow-md' : 'text-slate-400 hover:text-white'
                }`}
              >
                Outfit (Modern Luxury)
              </button>
              <button
                onClick={() => setSelectedFont('jakarta')}
                className={`px-3 py-1 rounded-xl transition-all ${
                  selectedFont === 'jakarta' ? 'bg-white text-slate-950 font-bold shadow-md' : 'text-slate-400 hover:text-white'
                }`}
              >
                Plus Jakarta
              </button>
              <button
                onClick={() => setSelectedFont('cinzel')}
                className={`px-3 py-1 rounded-xl transition-all ${
                  selectedFont === 'cinzel' ? 'bg-white text-slate-950 font-bold shadow-md' : 'text-slate-400 hover:text-white'
                }`}
              >
                Cinzel (Editorial)
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setLiveTicking(!liveTicking)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-mono font-bold transition-all ${
                liveTicking 
                  ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40 shadow-sm' 
                  : 'bg-white/5 text-slate-400 border-white/10'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${liveTicking ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
              {liveTicking ? 'LIVE TICKING: ON' : 'TICKING: PAUSED'}
            </button>
          </div>
        </div>

        {/* SECTION 1: HERO TYPOGRAPHY & BRAND LOGO LAB */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <Eye size={15} className="text-cyan-400" /> Typography &amp; Headline Laboratory
            </h2>
            <span className="text-xs text-slate-500 font-mono">Test headline phrasing and font weight live</span>
          </div>

          <div className="p-8 sm:p-12 rounded-3xl dark-metallic-glass border border-white/[0.12] space-y-6 relative overflow-hidden">
            <div className="space-y-4 max-w-3xl">
              <span className="text-[11px] font-mono font-bold text-cyan-400 tracking-[0.2em] uppercase">
                Headline Font: {selectedFont.toUpperCase()}
              </span>

              <h1 className={`text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white leading-[1.05] ${
                selectedFont === 'outfit' ? 'font-outfit' : selectedFont === 'cinzel' ? 'font-cinzel' : 'font-sans'
              }`}>
                Mirror the top 1% <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-200 to-indigo-300">
                  on Polymarket.
                </span>
              </h1>

              <p className="text-base sm:text-lg text-slate-400 leading-relaxed font-normal max-w-xl">
                Baleen is an institutional copy-trading engine for Polymarket. Discover verified prediction whales and mirror smart money fills with sub-second execution.
              </p>
            </div>

            {/* Quick Live Phrasing Editor */}
            <div className="pt-4 border-t border-white/[0.08] flex flex-col sm:flex-row sm:items-center gap-3">
              <span className="text-xs font-mono text-slate-400">Headline Test:</span>
              <input
                type="text"
                value={headlineText}
                onChange={(e) => setHeadlineText(e.target.value)}
                className="flex-1 bg-black/40 border border-white/15 rounded-xl px-4 py-2 text-xs font-mono text-white focus:outline-none focus:border-indigo-400"
              />
            </div>
          </div>
        </section>

        {/* SECTION 2: DARK METALLIC & LIQUID SAPPHIRE SHOWCASE */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <Layers size={15} className="text-indigo-400" /> Liquid Glass &amp; Dark Metallic Modules
            </h2>
            <span className="text-xs text-slate-500 font-mono">Specular refraction &amp; metallic card styling</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Card 1: Midnight Sapphire Portfolio Card */}
            <div className="lg:col-span-2 p-8 rounded-3xl dark-metallic-glass border border-white/[0.14] space-y-6 relative overflow-hidden">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-mono font-bold text-slate-400 uppercase tracking-wider">Authoritative Capital</span>
                  <div className="text-3xl sm:text-4xl font-extrabold font-mono text-white mt-1">
                    ${mockBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                </div>

                <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-2xl bg-emerald-950/80 border border-emerald-500/30 text-emerald-400 text-xs font-mono font-bold">
                  <TrendingUp size={14} /> +$5,341.32 (+53.41%)
                </div>
              </div>

              {/* Simulated Area Chart */}
              <div className="h-44 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={MOCK_SNAPSHOTS_1D} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="mockPnlGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366F1" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#6366F1" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="time" stroke="#475569" tick={{ fill: '#94A3B8', fontSize: 10 }} tickLine={false} axisLine={false} />
                    <YAxis domain={['dataMin - 100', 'dataMax + 100']} stroke="#475569" tick={{ fill: '#94A3B8', fontSize: 10 }} tickLine={false} axisLine={false} hide />
                    <Tooltip 
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const val = payload[0].value as number;
                          return (
                            <div className="p-2.5 rounded-xl bg-slate-950 border border-white/20 text-xs font-mono text-emerald-400 shadow-xl">
                              ${val.toFixed(2)}
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Area type="monotone" dataKey="balance" stroke="#818CF8" strokeWidth={2.5} fillOpacity={1} fill="url(#mockPnlGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Card 2: Liquid Caustics Engine Spec Card */}
            <div className="p-8 rounded-3xl liquid-glass-dark border border-white/[0.14] space-y-6 flex flex-col justify-between">
              <div className="space-y-4">
                <div className="w-10 h-10 rounded-2xl bg-indigo-500/20 border border-indigo-400/30 flex items-center justify-center text-indigo-300">
                  <Zap size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white tracking-tight">HyperSync Execution</h3>
                  <p className="text-xs text-slate-400 leading-relaxed mt-1">
                    Direct on-chain Polygon contract listener with 240ms copy latency and quadratic slippage protection.
                  </p>
                </div>
              </div>

              <div className="space-y-2 pt-4 border-t border-white/[0.08] font-mono text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>Speed:</span>
                  <span className="text-white font-bold">240ms</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Slippage Cap:</span>
                  <span className="text-emerald-400 font-bold">±1.5%</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Uptime:</span>
                  <span className="text-cyan-400 font-bold">99.98%</span>
                </div>
              </div>
            </div>

          </div>
        </section>

        {/* SECTION 3: WHALE DUAL-COLUMN WIN/LOSS BAR ENGINE */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <BarChart3 size={15} className="text-emerald-400" /> Whale Dual-Column Win/Loss Engine
            </h2>

            <div className="flex p-1 rounded-xl bg-black/40 border border-white/[0.08] text-xs font-semibold">
              <button
                onClick={() => setWinLossMode('discrete')}
                className={`px-3 py-1 rounded-lg transition-all ${
                  winLossMode === 'discrete' ? 'bg-emerald-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
                }`}
              >
                Discrete Daily Bars
              </button>
              <button
                onClick={() => setWinLossMode('cumulative')}
                className={`px-3 py-1 rounded-lg transition-all ${
                  winLossMode === 'cumulative' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
                }`}
              >
                Cumulative Curve
              </button>
            </div>
          </div>

          <div className="p-8 rounded-3xl dark-metallic-glass border border-white/[0.14] space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <span className="text-emerald-400">hoodr</span> Trading Ledger (Authentic Wins &amp; Losses)
                </h3>
                <span className="text-xs text-slate-400 font-mono">
                  Green columns above $0.00 • Red columns below $0.00 • 74.5% Win Rate
                </span>
              </div>
            </div>

            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={MOCK_WHALE_WIN_LOSS} margin={{ top: 10, right: 10, left: 0, bottom: 0 }} stackOffset="sign">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                  <XAxis dataKey="date" stroke="#64748B" tick={{ fill: '#94A3B8', fontSize: 10 }} tickLine={false} axisLine={false} />
                  <YAxis stroke="#64748B" tick={{ fill: '#94A3B8', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} />
                  <ReferenceLine y={0} stroke="rgba(255,255,255,0.25)" strokeWidth={1} />
                  <Tooltip 
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        const pt = payload[0].payload;
                        return (
                          <div className="p-3.5 rounded-2xl bg-slate-950 border border-white/20 shadow-2xl text-xs font-mono space-y-1.5 min-w-[160px]">
                            <div className="text-slate-400 font-bold">{label}</div>
                            <div className="text-emerald-400 font-bold flex justify-between">
                              <span>Won:</span>
                              <span>+${pt.wonUsd.toFixed(2)}</span>
                            </div>
                            <div className="text-rose-400 font-bold flex justify-between">
                              <span>Lost:</span>
                              <span>-${Math.abs(pt.lostUsd).toFixed(2)}</span>
                            </div>
                            <div className="pt-1 border-t border-white/10 text-white font-extrabold flex justify-between">
                              <span>Net:</span>
                              <span className={pt.netPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                                {pt.netPnL >= 0 ? '+' : ''}${pt.netPnL.toFixed(2)}
                              </span>
                            </div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar dataKey="dailyPnL" maxBarSize={28} radius={[4, 4, 4, 4]}>
                    {MOCK_WHALE_WIN_LOSS.map((entry, idx) => (
                      <Cell key={`cell-${idx}`} fill={entry.netPnL >= 0 ? '#10B981' : '#F43F5E'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>

        {/* SECTION 4: SIMULATED EXECUTION TAPE */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-2">
              <Cpu size={15} className="text-cyan-400" /> Simulated Order Execution Tape
            </h2>
            <span className="text-xs text-slate-500 font-mono">Real-time trade auditing preview</span>
          </div>

          <div className="rounded-3xl dark-metallic-glass border border-white/[0.14] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="border-b border-white/[0.08] text-slate-400 font-mono bg-white/[0.02]">
                  <tr>
                    <th className="p-4 pl-6">Whale Target</th>
                    <th className="p-4">Market Question</th>
                    <th className="p-4">Outcome</th>
                    <th className="p-4">Fill Price</th>
                    <th className="p-4">Live Price</th>
                    <th className="p-4">Notional</th>
                    <th className="p-4 pr-6 text-right">Realized PnL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04] font-mono">
                  {MOCK_EXECUTIONS.map((trade) => (
                    <tr key={trade.id} className="hover:bg-white/[0.03] transition-colors">
                      <td className="p-4 pl-6 font-bold text-white flex items-center gap-2">
                        <span>{trade.whale}</span>
                        {trade.isConsensus && (
                          <span className="text-[10px] bg-indigo-950 text-indigo-300 border border-indigo-500/30 px-1.5 py-0.5 rounded">
                            Consensus
                          </span>
                        )}
                      </td>
                      <td className="p-4 text-slate-300 max-w-xs truncate font-sans">{trade.market}</td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded font-bold ${trade.outcome === 'Yes' ? 'bg-emerald-950 text-emerald-400' : 'bg-rose-950 text-rose-400'}`}>
                          {trade.outcome}
                        </span>
                      </td>
                      <td className="p-4 text-slate-400">${trade.fill.toFixed(3)}</td>
                      <td className="p-4 text-slate-200 font-bold">${trade.live.toFixed(3)}</td>
                      <td className="p-4 text-slate-300">${trade.size}</td>
                      <td className={`p-4 pr-6 text-right font-bold ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)} ({trade.pnlPct >= 0 ? '+' : ''}{trade.pnlPct.toFixed(1)}%)
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}
