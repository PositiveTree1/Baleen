'use client';
import React, { useState, useMemo, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sliders, Sparkles, Layers, Eye, RefreshCw, Zap, TrendingUp, TrendingDown, 
  HelpCircle, Copy, Check, ShieldCheck, ChevronDown, ChevronUp, Bell, Volume2, 
  VolumeX, Settings, LogOut, ArrowRight, ExternalLink, Activity, Play, Pause,
  RotateCcw, Droplets, Sun, Moon, Maximize2, Minimize2, Move, Palette, CheckCircle2
} from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, BarChart, Bar, CartesianGrid, ReferenceLine, Cell } from 'recharts';
import Link from 'next/link';
import Image from 'next/image';
import { BrandLogo } from '@/components/ui/BrandLogo';

// ==========================================
// 1. RICH SIMULATED DATA
// ==========================================

const MOCK_HOURLY_TIMELINE = [
  { displayTime: '26 août 09:00', time: '09:00', date: '26 août', balance: 14850.20, pnl: 4850.20 },
  { displayTime: '26 août 10:00', time: '10:00', date: '26 août', balance: 14920.80, pnl: 4920.80 },
  { displayTime: '26 août 11:00', time: '11:00', date: '26 août', balance: 14810.50, pnl: 4810.50 },
  { displayTime: '26 août 12:00', time: '12:00', date: '26 août', balance: 15120.40, pnl: 5120.40 },
  { displayTime: '26 août 13:00', time: '13:00', date: '26 août', balance: 15050.90, pnl: 5050.90 },
  { displayTime: '26 août 14:00', time: '14:00', date: '26 août', balance: 15280.60, pnl: 5280.60 },
  { displayTime: '26 août 15:00', time: '15:00', date: '26 août', balance: 15210.15, pnl: 5210.15 },
  { displayTime: '26 août 16:00', time: '16:00', date: '26 août', balance: 15341.32, pnl: 5341.32 },
];

const MOCK_WHALES = [
  { address: '0x3eae57986be5e0ca435102ffe1f14206ffa2e2ed', name: 'hoodr', winRate: 74.5, pnl: 63056.53, tier: 'standard', score: 88.4, activePositions: 14, avatar: 'https://avatar.vercel.sh/hoodr' },
  { address: '0xd44e974a3edb232aa4aedbdcc59792b76a5f67e2', name: 'KrackenSruster', winRate: 82.1, pnl: 302171.52, tier: 'gold_sniper', score: 94.2, activePositions: 22, avatar: 'https://avatar.vercel.sh/kracken' },
  { address: '0x58f8f1138be2192696378629fc9aa23c7910dc70', name: 'bloodmaster', winRate: 56.7, pnl: 430150.77, tier: 'standard', score: 76.9, activePositions: 31, avatar: 'https://avatar.vercel.sh/blood' },
  { address: '0xdf17f4a8dd01a4cfa6fc3da323a2baee5f8697d1', name: 'iguana7', winRate: 68.2, pnl: 762768.44, tier: 'standard', score: 84.6, activePositions: 19, avatar: 'https://avatar.vercel.sh/iguana' },
  { address: '0x61fefe72aebe7afc69d190bacfad8b561dc70956', name: 'RIPabloEscobar', winRate: 72.0, pnl: 97667.54, tier: 'standard', score: 81.3, activePositions: 8, avatar: 'https://avatar.vercel.sh/pablo' },
];

const MOCK_EXECUTIONS = [
  { id: '1', whale: 'hoodr', outcome: 'Yes', market: 'Fed Rate Cut in September 2026', fill: 0.880, live: 0.940, size: 250, pnl: 17.05, pnlPct: 6.82, time: '2m ago', isConsensus: true, status: 'FILLED' },
  { id: '2', whale: 'KrackenSruster', outcome: 'No', market: 'US Recession Declared Before Q4', fill: 0.720, live: 0.790, size: 400, pnl: 38.89, pnlPct: 9.72, time: '7m ago', isConsensus: true, status: 'FILLED' },
  { id: '3', whale: 'bloodmaster', outcome: 'Yes', market: 'Ethereum Above $4,000 End of Month', fill: 0.440, live: 0.390, size: 180, pnl: -20.45, pnlPct: -11.36, time: '12m ago', isConsensus: false, status: 'FILLED' },
  { id: '4', whale: 'iguana7', outcome: 'Yes', market: 'Democratic Control of US Senate 2026', fill: 0.950, live: 0.950, size: 500, pnl: 0.00, pnlPct: 0.00, time: '18m ago', isConsensus: true, status: 'FILLED' },
  { id: '5', whale: 'RIPabloEscobar', outcome: 'Yes', market: 'SpaceX Starship Orbital Landing Success', fill: 0.610, live: 0.730, size: 320, pnl: 62.95, pnlPct: 19.67, time: '25m ago', isConsensus: true, status: 'FILLED' },
];

const MOCK_DUAL_BARS = [
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

export default function PlaygroundPage() {
  // ==========================================
  // 2. INTERACTIVE LIQUID GLASS CONTROLS STATE
  // ==========================================
  const [glassOpacity, setGlassOpacity] = useState(0.55); // 0.1 to 0.95
  const [glassBlur, setGlassBlur] = useState(24); // 0 to 60px
  const [glassSaturation, setGlassSaturation] = useState(190); // 100 to 250%
  const [lightReflection, setLightReflection] = useState(0.85); // 0.0 to 1.0 (Specular water light sheen)
  const [glassBorderOpacity, setGlassBorderOpacity] = useState(0.85); // 0.1 to 1.0
  const [glassRadius, setGlassRadius] = useState(28); // 12 to 40px
  const [waterRipples, setWaterRipples] = useState(true);
  const [specularAngle, setSpecularAngle] = useState(135); // 0 to 360 deg
  const [fontFamily, setFontFamily] = useState<'outfit' | 'jakarta' | 'cinzel' | 'inter'>('outfit');
  const [timeframe, setTimeframe] = useState<'1H' | '1D' | '1W' | '1M' | 'ALL'>('1D');
  const [dualChartMode, setDualChartMode] = useState<'discrete' | 'cumulative'>('discrete');
  const [selectedWhale, setSelectedWhale] = useState<any | null>(null);

  // Live simulation states
  const [liveBalance, setLiveBalance] = useState(15341.32);
  const [isTicking, setIsTicking] = useState(true);
  const [hudMinimized, setHudMinimized] = useState(false);
  const [tab, setTab] = useState<'holding' | 'closed' | 'all'>('holding');

  // Live Balance Ticker
  useEffect(() => {
    if (!isTicking) return;
    const interval = setInterval(() => {
      setLiveBalance((prev) => {
        const delta = (Math.random() - 0.48) * 2.15;
        return Math.round((prev + delta) * 100) / 100;
      });
    }, 2400);
    return () => clearInterval(interval);
  }, [isTicking]);

  // Preset Configurations
  const applyPreset = (preset: 'visionos' | 'pure-water' | 'frosted-ice' | 'prism' | 'default') => {
    switch (preset) {
      case 'visionos':
        setGlassOpacity(0.38);
        setGlassBlur(32);
        setGlassSaturation(210);
        setLightReflection(0.95);
        setGlassBorderOpacity(0.9);
        setGlassRadius(32);
        setSpecularAngle(135);
        setWaterRipples(true);
        break;
      case 'pure-water':
        setGlassOpacity(0.18);
        setGlassBlur(16);
        setGlassSaturation(160);
        setLightReflection(0.98);
        setGlassBorderOpacity(0.95);
        setGlassRadius(28);
        setSpecularAngle(120);
        setWaterRipples(true);
        break;
      case 'frosted-ice':
        setGlassOpacity(0.78);
        setGlassBlur(40);
        setGlassSaturation(180);
        setLightReflection(0.65);
        setGlassBorderOpacity(0.8);
        setGlassRadius(24);
        setSpecularAngle(145);
        setWaterRipples(false);
        break;
      case 'prism':
        setGlassOpacity(0.45);
        setGlassBlur(28);
        setGlassSaturation(240);
        setLightReflection(1.0);
        setGlassBorderOpacity(1.0);
        setGlassRadius(30);
        setSpecularAngle(160);
        setWaterRipples(true);
        break;
      case 'default':
        setGlassOpacity(0.55);
        setGlassBlur(24);
        setGlassSaturation(190);
        setLightReflection(0.85);
        setGlassBorderOpacity(0.85);
        setGlassRadius(28);
        setSpecularAngle(135);
        setWaterRipples(true);
        break;
    }
  };

  // Dynamic Liquid Glass Style Object
  const liquidGlassStyle: React.CSSProperties = {
    background: `linear-gradient(${specularAngle}deg, rgba(255, 255, 255, ${glassOpacity}) 0%, rgba(255, 255, 255, ${glassOpacity * 0.4}) 35%, rgba(255, 255, 255, ${glassOpacity * 0.15}) 60%, rgba(255, 255, 255, ${glassOpacity * 0.65}) 100%)`,
    backdropFilter: `blur(${glassBlur}px) saturate(${glassSaturation}%)`,
    WebkitBackdropFilter: `blur(${glassBlur}px) saturate(${glassSaturation}%)`,
    borderRadius: `${glassRadius}px`,
    border: `1px solid rgba(255, 255, 255, ${glassBorderOpacity})`,
    boxShadow: `
      inset 0 1.5px 1.5px 0 rgba(255, 255, 255, ${lightReflection}),
      inset 0 -1px 1px 0 rgba(0, 0, 0, 0.03),
      0 8px 32px 0 rgba(31, 38, 135, 0.06),
      0 2px 8px -2px rgba(15, 23, 42, 0.03)
    `,
  };

  const activeFontClass = 
    fontFamily === 'outfit' ? 'font-outfit' : 
    fontFamily === 'cinzel' ? 'font-cinzel' : 
    fontFamily === 'inter' ? 'font-sans' : 'font-sans';

  return (
    <div className={`min-h-screen bg-[#F8F9FB] text-slate-900 selection:bg-slate-900 selection:text-white relative overflow-x-hidden ${activeFontClass}`}>
      
      {/* ========================================================= */}
      {/* AMBIENT CAUSTICS & WATER SPECULAR BACKGROUND */}
      {/* ========================================================= */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        {waterRipples && (
          <>
            <motion.div 
              animate={{ 
                scale: [1, 1.15, 1],
                x: [0, 20, 0],
                y: [0, -25, 0],
              }}
              transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }}
              className="absolute -top-32 right-1/4 w-[750px] h-[750px] bg-gradient-to-br from-indigo-200/45 via-sky-100/35 to-transparent rounded-full blur-3xl opacity-75" 
            />
            <motion.div 
              animate={{ 
                scale: [1, 1.2, 1],
                x: [0, -30, 0],
                y: [0, 30, 0],
              }}
              transition={{ duration: 18, repeat: Infinity, ease: 'easeInOut' }}
              className="absolute top-1/3 -left-32 w-[650px] h-[650px] bg-gradient-to-tr from-cyan-200/40 via-sky-100/30 to-transparent rounded-full blur-3xl opacity-65" 
            />
            <motion.div 
              animate={{ 
                scale: [1, 1.1, 1],
                x: [0, 25, 0],
              }}
              transition={{ duration: 16, repeat: Infinity, ease: 'easeInOut' }}
              className="absolute bottom-10 right-10 w-[700px] h-[700px] bg-gradient-to-tl from-indigo-200/30 via-slate-200/40 to-transparent rounded-full blur-3xl opacity-70" 
            />
          </>
        )}
      </div>

      {/* ========================================================= */}
      {/* TOP NAVIGATION (EXACT SANDBOX PAGE HEADER) */}
      {/* ========================================================= */}
      <nav 
        style={liquidGlassStyle}
        className="mx-4 sm:mx-8 lg:mx-12 mt-4 px-6 lg:px-8 py-3.5 flex items-center justify-between sticky top-3 z-40 transition-all duration-300"
      >
        <div className="flex items-center gap-3">
          <BrandLogo href="/" subtitle="UI Lab Sandbox" />
          <span className="text-[10px] font-mono font-bold text-indigo-700 bg-indigo-100/80 border border-indigo-200 px-2.5 py-0.5 rounded-full shadow-xs">
            LIVE PREVIEW
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setHudMinimized(!hudMinimized)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 text-white hover:bg-slate-800 text-xs font-bold transition-all shadow-sm cursor-pointer"
          >
            <Sliders size={13} />
            <span>{hudMinimized ? 'Show Glass Controls' : 'Hide Controls'}</span>
          </button>

          <Link href="/dashboard" className="text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors px-3 py-1.5 rounded-xl hover:bg-black/5">
            Exit to Dashboard
          </Link>
        </div>
      </nav>

      {/* ========================================================= */}
      {/* MAIN SANDBOX PAGE LAYOUT */}
      {/* ========================================================= */}
      <main className="flex-1 p-4 sm:p-6 lg:p-12 max-w-7xl mx-auto w-full flex flex-col gap-6 relative z-10 pb-36">
        
        {/* Header Section: Balance & Real-time Equity */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-6 pb-2">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 font-mono">
                Authoritative Capital
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            </div>

            <div className="flex flex-wrap items-baseline gap-3">
              <div className="text-4xl sm:text-5xl lg:text-6xl font-extrabold font-mono tracking-tight text-slate-950">
                ${liveBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>

              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-2xl bg-emerald-50 border border-emerald-200/80 text-emerald-700 text-xs font-mono font-bold shadow-xs">
                <TrendingUp size={13} />
                <span>+${(liveBalance - 10000).toLocaleString(undefined, { minimumFractionDigits: 2 })} (+{(((liveBalance - 10000) / 10000) * 100).toFixed(2)}%)</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <div 
              style={liquidGlassStyle}
              className="px-4 py-2 flex items-center gap-2.5 text-xs font-medium text-slate-600"
            >
              <span>Simulation Mode:</span>
              <span className="font-bold text-slate-950 font-mono px-2 py-0.5 rounded-full bg-slate-100 border border-black/[0.06]">
                $10,000 Sandbox
              </span>
            </div>
          </div>
        </div>

        {/* SECTION 1: PORTFOLIO PNL GRAPH CARD (APPLIED WITH LIQUID GLASS) */}
        <section 
          style={liquidGlassStyle} 
          className="p-6 sm:p-8 space-y-6 relative overflow-hidden transition-all duration-300 group"
        >
          {/* Subtle Water Reflection Shimmer Sheen */}
          <div 
            className="absolute inset-0 pointer-events-none opacity-60 mix-blend-overlay z-0"
            style={{
              background: `linear-gradient(${specularAngle}deg, rgba(255,255,255,${lightReflection * 0.8}) 0%, transparent 40%, rgba(255,255,255,${lightReflection * 0.4}) 80%, transparent 100%)`
            }}
          />

          <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-black/[0.04] pb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
                <Activity size={18} className="text-indigo-600" />
                Portfolio Capital Curve &amp; Mark-to-Market
              </h3>
              <p className="text-xs text-slate-500 font-mono mt-0.5">
                Authentic 100% database snapshots • Live Clob mark-to-market valuation
              </p>
            </div>

            {/* Timeframe Buttons */}
            <div className="flex rounded-2xl bg-slate-200/60 p-1 border border-black/[0.04] text-xs font-bold">
              {(['1H', '1D', '1W', '1M', 'ALL'] as const).map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-3 py-1 rounded-xl transition-all ${
                    timeframe === tf ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* Area Chart with Monotone Bezier Spline */}
          <div className="relative z-10 h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MOCK_HOURLY_TIMELINE} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="pnlLiquidGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366F1" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#6366F1" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.04)" vertical={false} />
                <XAxis dataKey="time" stroke="#94A3B8" tick={{ fill: '#64748B', fontSize: 10, fontWeight: 600 }} tickLine={false} axisLine={false} />
                <YAxis domain={['dataMin - 100', 'dataMax + 100']} stroke="#94A3B8" tick={{ fill: '#64748B', fontSize: 10, fontWeight: 600 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v.toLocaleString()}`} />
                <Tooltip 
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const pt = payload[0].payload;
                      return (
                        <div 
                          style={liquidGlassStyle}
                          className="p-3 shadow-xl text-xs font-mono text-slate-900 border border-white/90 space-y-1 min-w-[140px]"
                        >
                          <div className="text-slate-500 font-bold">{pt.displayTime || label}</div>
                          <div className="text-sm font-extrabold text-indigo-600">${pt.balance.toFixed(2)}</div>
                          <div className="text-emerald-600 font-bold">+${pt.pnl.toFixed(2)}</div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Area 
                  type="monotone" 
                  dataKey="balance" 
                  stroke="#4F46E5" 
                  strokeWidth={3} 
                  fillOpacity={1} 
                  fill="url(#pnlLiquidGrad)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* SECTION 2: DISCOVERED WHALE INDEX BASKET & SCOREBOARD */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Whale Leaderboard Card */}
          <div 
            style={liquidGlassStyle}
            className="lg:col-span-2 p-6 sm:p-8 space-y-5 relative overflow-hidden"
          >
            <div className="flex items-center justify-between border-b border-black/[0.04] pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
                  <ShieldCheck size={18} className="text-indigo-600" />
                  Top Verified Whale Indexers
                </h3>
                <span className="text-xs text-slate-500 font-mono">Click any whale to inspect dual-column win/loss curve</span>
              </div>
              <span className="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-2.5 py-1 rounded-full">
                {MOCK_WHALES.length} Active
              </span>
            </div>

            <div className="space-y-2.5">
              {MOCK_WHALES.map((whale, idx) => (
                <div
                  key={whale.address}
                  onClick={() => setSelectedWhale(whale)}
                  className="p-3.5 rounded-2xl bg-white/60 hover:bg-white/95 border border-white/80 hover:border-indigo-200 transition-all duration-200 cursor-pointer flex items-center justify-between shadow-xs hover:shadow-md"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono font-bold text-slate-400 w-4">{idx + 1}</span>
                    <div className="w-8 h-8 rounded-full bg-slate-200 overflow-hidden relative border">
                      <Image src={whale.avatar} alt={whale.name} fill className="object-cover" />
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold text-slate-900">{whale.name}</span>
                        {whale.tier === 'gold_sniper' && (
                          <span className="text-[10px] bg-amber-50 text-amber-700 border border-amber-200 px-1.5 py-0.2 rounded-full font-bold">
                            Gold Sniper
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-slate-500 font-mono">{whale.activePositions} positions open</span>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-xs font-mono font-bold text-emerald-600">+${whale.pnl.toLocaleString()}</div>
                    <div className="text-[11px] text-slate-500 font-mono">{whale.winRate}% Win Rate</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Dual-Column Whale Inspector */}
          <div 
            style={liquidGlassStyle}
            className="p-6 sm:p-8 space-y-4 flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between border-b border-black/[0.04] pb-3 mb-3">
                <h3 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-1.5">
                  <BarChart3 size={16} className="text-emerald-600" />
                  Whale Win/Loss Engine
                </h3>
                <div className="flex rounded-xl bg-slate-200/60 p-0.5 text-[10px] font-bold">
                  <button
                    onClick={() => setDualChartMode('discrete')}
                    className={`px-2 py-0.5 rounded-lg ${dualChartMode === 'discrete' ? 'bg-white shadow-xs text-slate-900' : 'text-slate-500'}`}
                  >
                    Bars
                  </button>
                  <button
                    onClick={() => setDualChartMode('cumulative')}
                    className={`px-2 py-0.5 rounded-lg ${dualChartMode === 'cumulative' ? 'bg-white shadow-xs text-slate-900' : 'text-slate-500'}`}
                  >
                    Curve
                  </button>
                </div>
              </div>

              <span className="text-xs font-mono text-slate-500 block mb-3">
                Target: <strong>{selectedWhale ? selectedWhale.name : 'hoodr'}</strong> (74.5% Win Rate)
              </span>

              {/* Dual-Column Chart */}
              <div className="h-44 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={MOCK_DUAL_BARS} margin={{ top: 5, right: 5, left: -15, bottom: 0 }} stackOffset="sign">
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.05)" vertical={false} />
                    <XAxis dataKey="date" stroke="#94A3B8" tick={{ fill: '#64748B', fontSize: 9 }} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94A3B8" tick={{ fill: '#64748B', fontSize: 9 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v}`} />
                    <ReferenceLine y={0} stroke="rgba(0,0,0,0.2)" strokeWidth={1} />
                    <Tooltip 
                      content={({ active, payload, label }) => {
                        if (active && payload && payload.length) {
                          const pt = payload[0].payload;
                          return (
                            <div className="p-2.5 rounded-xl bg-white/95 backdrop-blur-md border border-black/[0.08] shadow-lg text-xs font-mono space-y-1">
                              <div className="font-bold text-slate-800">{label}</div>
                              <div className="text-emerald-600 font-bold">Won: +${pt.wonUsd}</div>
                              <div className="text-rose-600 font-bold">Lost: -${Math.abs(pt.lostUsd)}</div>
                              <div className="border-t pt-1 font-extrabold text-slate-950">Net: ${pt.netPnL}</div>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Bar dataKey="dailyPnL" maxBarSize={20} radius={[3, 3, 3, 3]}>
                      {MOCK_DUAL_BARS.map((entry, idx) => (
                        <Cell key={`bar-${idx}`} fill={entry.netPnL >= 0 ? '#10B981' : '#F43F5E'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="pt-3 border-t border-black/[0.04] text-[11px] text-slate-500 font-mono flex justify-between">
              <span>Green: Gains above $0</span>
              <span>Red: Losses below $0</span>
            </div>
          </div>

        </div>

        {/* SECTION 3: EXECUTION AUDIT & POSITIONS CENTER */}
        <section 
          style={liquidGlassStyle}
          className="p-6 sm:p-8 space-y-4"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-black/[0.04] pb-3">
            <div>
              <h3 className="text-base font-bold text-slate-900 tracking-tight">Execution Audit &amp; Positions Center</h3>
              <p className="text-xs text-slate-500 font-mono">Real-time mark-to-market positions and quadratic taker fees</p>
            </div>

            <div className="flex rounded-xl bg-slate-200/60 p-0.5 text-xs font-semibold">
              <button
                onClick={() => setTab('holding')}
                className={`px-3 py-1 rounded-lg ${tab === 'holding' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500'}`}
              >
                Holding ({MOCK_EXECUTIONS.length})
              </button>
              <button
                onClick={() => setTab('closed')}
                className={`px-3 py-1 rounded-lg ${tab === 'closed' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500'}`}
              >
                Closed / Resolved
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="border-b border-black/[0.04] text-slate-400 font-mono">
                <tr>
                  <th className="pb-3 pl-2">Whale Source</th>
                  <th className="pb-3">Market Question</th>
                  <th className="pb-3">Outcome</th>
                  <th className="pb-3">Fill Price</th>
                  <th className="pb-3">Live Price</th>
                  <th className="pb-3">Notional</th>
                  <th className="pb-3 pr-2 text-right">Realized PnL</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-black/[0.04] font-mono">
                {MOCK_EXECUTIONS.map((trade) => (
                  <tr key={trade.id} className="hover:bg-white/60 transition-colors">
                    <td className="py-3.5 pl-2 font-bold text-slate-900 flex items-center gap-1.5">
                      <span>{trade.whale}</span>
                      {trade.isConsensus && (
                        <span className="text-[10px] bg-indigo-50 text-indigo-700 border border-indigo-200 px-1.5 py-0.2 rounded font-sans font-bold">
                          Consensus
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 text-slate-700 max-w-xs truncate font-sans">{trade.market}</td>
                    <td className="py-3.5">
                      <span className={`px-2 py-0.5 rounded font-bold ${trade.outcome === 'Yes' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'}`}>
                        {trade.outcome}
                      </span>
                    </td>
                    <td className="py-3.5 text-slate-500">${trade.fill.toFixed(3)}</td>
                    <td className="py-3.5 text-slate-950 font-bold">${trade.live.toFixed(3)}</td>
                    <td className="py-3.5 text-slate-700">${trade.size}</td>
                    <td className={`py-3.5 pr-2 text-right font-bold ${trade.pnl >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)} ({trade.pnlPct >= 0 ? '+' : ''}{trade.pnlPct.toFixed(1)}%)
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

      </main>

      {/* ========================================================= */}
      {/* FLOATING APPLE LIQUID GLASS CONTROL CENTER (HUD INSPECTOR) */}
      {/* ========================================================= */}
      <div className="fixed bottom-6 right-6 z-50 max-w-sm sm:max-w-md w-full px-4 sm:px-0">
        <div 
          style={{
            background: 'rgba(15, 23, 42, 0.88)',
            backdropFilter: 'blur(36px) saturate(200%)',
            WebkitBackdropFilter: 'blur(36px) saturate(200%)',
            borderRadius: '28px',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            boxShadow: '0 20px 50px -10px rgba(0, 0, 0, 0.5), inset 0 1px 1px rgba(255, 255, 255, 0.4)'
          }}
          className="text-white p-5 space-y-4 shadow-2xl transition-all duration-300"
        >
          {/* HUD Header */}
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-400/30">
                <Sliders size={14} />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white uppercase tracking-wider">Liquid Glass Studio</h4>
                <p className="text-[10px] text-slate-400 font-mono">Live dynamic shader variables</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => applyPreset('default')}
                className="p-1.5 rounded-xl bg-white/5 hover:bg-white/15 text-slate-400 hover:text-white transition-colors"
                title="Reset to default"
              >
                <RotateCcw size={13} />
              </button>
              <button
                onClick={() => setHudMinimized(!hudMinimized)}
                className="p-1.5 rounded-xl bg-white/5 hover:bg-white/15 text-slate-400 hover:text-white transition-colors"
              >
                {hudMinimized ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
              </button>
            </div>
          </div>

          {/* HUD Expanded Sliders Body */}
          <AnimatePresence>
            {!hudMinimized && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-4 overflow-hidden"
              >
                {/* One-Click Presets */}
                <div className="space-y-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
                    Instant Presets
                  </span>
                  <div className="grid grid-cols-3 gap-1.5 text-[11px] font-semibold font-mono">
                    <button
                      onClick={() => applyPreset('visionos')}
                      className="p-2 rounded-xl bg-indigo-950/80 hover:bg-indigo-900 border border-indigo-500/40 text-indigo-200 transition-all text-center"
                    >
                      🌊 VisionOS
                    </button>
                    <button
                      onClick={() => applyPreset('pure-water')}
                      className="p-2 rounded-xl bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-500/40 text-cyan-200 transition-all text-center"
                    >
                      💧 Pure Water
                    </button>
                    <button
                      onClick={() => applyPreset('frosted-ice')}
                      className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 border border-white/20 text-slate-200 transition-all text-center"
                    >
                      🧊 Frost Ice
                    </button>
                  </div>
                </div>

                {/* Slider 1: Transparency / Opacity */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-slate-400">Water Clarity (Opacity)</span>
                    <span className="text-indigo-400 font-bold">{Math.round(glassOpacity * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0.1"
                    max="0.95"
                    step="0.02"
                    value={glassOpacity}
                    onChange={(e) => setGlassOpacity(parseFloat(e.target.value))}
                    className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                  />
                </div>

                {/* Slider 2: Backdrop Blur */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-slate-400">Backdrop Blur Depth</span>
                    <span className="text-indigo-400 font-bold">{glassBlur}px</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="60"
                    step="2"
                    value={glassBlur}
                    onChange={(e) => setGlassBlur(parseInt(e.target.value))}
                    className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                  />
                </div>

                {/* Slider 3: Specular Light Reflection */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-slate-400">Specular Water Sheen</span>
                    <span className="text-indigo-400 font-bold">{Math.round(lightReflection * 100)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={lightReflection}
                    onChange={(e) => setLightReflection(parseFloat(e.target.value))}
                    className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                  />
                </div>

                {/* Slider 4: Corner Radius */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-slate-400">Apple Curvature (Radius)</span>
                    <span className="text-indigo-400 font-bold">{glassRadius}px</span>
                  </div>
                  <input
                    type="range"
                    min="12"
                    max="40"
                    step="2"
                    value={glassRadius}
                    onChange={(e) => setGlassRadius(parseInt(e.target.value))}
                    className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                  />
                </div>

                {/* Font Selector */}
                <div className="space-y-1.5 pt-2 border-t border-white/10">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono">
                    Global Typography
                  </span>
                  <div className="grid grid-cols-3 gap-1.5 text-xs font-semibold">
                    <button
                      onClick={() => setFontFamily('outfit')}
                      className={`p-1.5 rounded-xl transition-all ${
                        fontFamily === 'outfit' ? 'bg-white text-slate-950 font-bold' : 'bg-white/5 text-slate-400 hover:text-white'
                      }`}
                    >
                      Outfit
                    </button>
                    <button
                      onClick={() => setFontFamily('jakarta')}
                      className={`p-1.5 rounded-xl transition-all ${
                        fontFamily === 'jakarta' ? 'bg-white text-slate-950 font-bold' : 'bg-white/5 text-slate-400 hover:text-white'
                      }`}
                    >
                      Jakarta
                    </button>
                    <button
                      onClick={() => setFontFamily('cinzel')}
                      className={`p-1.5 rounded-xl transition-all ${
                        fontFamily === 'cinzel' ? 'bg-white text-slate-950 font-bold' : 'bg-white/5 text-slate-400 hover:text-white'
                      }`}
                    >
                      Cinzel
                    </button>
                  </div>
                </div>

                {/* Toggle: Water Caustic Animation */}
                <div className="pt-2 border-t border-white/10 flex items-center justify-between text-xs font-mono">
                  <span className="text-slate-300">Ambient Caustics Ripple</span>
                  <button
                    onClick={() => setWaterRipples(!waterRipples)}
                    className={`px-2.5 py-1 rounded-lg font-bold ${
                      waterRipples ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40' : 'bg-white/5 text-slate-500'
                    }`}
                  >
                    {waterRipples ? 'ACTIVE' : 'OFF'}
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

    </div>
  );
}
