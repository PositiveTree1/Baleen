'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, useMotionValue, useSpring } from 'framer-motion';
import { Activity, Sliders, Layers, Shield, Zap, TrendingUp, CheckCircle, ArrowUpRight } from 'lucide-react';

type MorphMode = 'telemetry' | 'fluid' | 'sleeves';
type KellyRegime = 'conservative' | 'balanced' | 'aggressive';

interface MarketData {
  id: string;
  name: string;
  ticker: string;
  oddsYes: number;
  whaleEntry: number;
  whaleAddress: string;
  conviction: string;
  volume: string;
}

const sampleMarkets: MarketData[] = [
  {
    id: 'm-1',
    name: 'Fed 25bps Rate Cut in Next FOMC',
    ticker: 'FOMC-CUT-25',
    oddsYes: 0.68,
    whaleEntry: 0.58,
    whaleAddress: '0x12a9...3f12',
    conviction: '94.2% Alpha',
    volume: '$1.42M',
  },
  {
    id: 'm-2',
    name: 'Bitcoin Above $100k Before Year-End',
    ticker: 'BTC-100K-EOY',
    oddsYes: 0.74,
    whaleEntry: 0.64,
    whaleAddress: '0x7bf3...910a',
    conviction: '91.8% Alpha',
    volume: '$3.89M',
  },
  {
    id: 'm-3',
    name: 'Ethereum L2 Total Value Exceeds $50B',
    ticker: 'ETH-L2-50B',
    oddsYes: 0.46,
    whaleEntry: 0.38,
    whaleAddress: '0x4981...bb4c',
    conviction: '89.6% Alpha',
    volume: '$840k',
  },
];

export function LiquidGlassHeroCanvas() {
  const [mode, setMode] = useState<MorphMode>('telemetry');
  const [selectedMarket, setSelectedMarket] = useState<MarketData>(sampleMarkets[0]);
  const [kellyRegime, setKellyRegime] = useState<KellyRegime>('balanced');
  const [interactiveOdds, setInteractiveOdds] = useState<number>(0.68);
  const [tick, setTick] = useState(0);
  const [mouseTilt, setMouseTilt] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  // Drag physics for interactive fluid mode
  const dragX = useMotionValue(0);
  const dragY = useMotionValue(0);
  const springX = useSpring(dragX, { stiffness: 320, damping: 24 });
  const springY = useSpring(dragY, { stiffness: 320, damping: 24 });

  // Floating breathing loop
  useEffect(() => {
    let animId: number;
    const start = performance.now();
    const loop = (now: number) => {
      setTick((now - start) * 0.001);
      animId = requestAnimationFrame(loop);
    };
    animId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animId);
  }, []);

  // Parallax tilt tracking
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    const y = ((e.clientY - rect.top) / rect.height) * 2 - 1;
    setMouseTilt({ x, y });
  };

  const handleMouseLeave = () => {
    setMouseTilt({ x: 0, y: 0 });
  };

  // Autonomous breathing
  const floatY = Math.sin(tick * 1.5) * 4;

  // Interactive dynamic coordinates for fluid mode
  const currentDragX = mode === 'fluid' ? springX.get() : Math.sin(tick * 1.2) * 12;
  const currentDragY = mode === 'fluid' ? springY.get() : Math.cos(tick * 1.5) * 5;

  const c1x = 195 + currentDragX;
  const c1y = 140 + currentDragY;
  const r1 = 64;

  const c2x = 385;
  const c2y = 140;
  const r2 = 78;

  const dx = c2x - c1x;
  const dy = c2y - c1y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const isBonded = dist < 280;

  // Fluid meniscus waist control points
  const midX = (c1x + c2x) / 2;
  const midY = (c1y + c2y) / 2;
  const waistThickness = Math.max(8, 54 - (dist - 190) * 0.38);

  const topC1X = c1x;
  const topC1Y = c1y - r1 + 3;
  const topC2X = c2x - 30;
  const topC2Y = c2y - r2 + 3;
  const topMidY = midY - waistThickness;

  const botC1X = c1x;
  const botC1Y = c1y + r1 - 3;
  const botC2X = c2x - 30;
  const botC2Y = c2y + r2 - 3;
  const botMidY = midY + waistThickness;

  // Dynamic Kelly Fraction sizing math
  const regimeMultiplier = kellyRegime === 'conservative' ? 0.25 : kellyRegime === 'balanced' ? 0.5 : 1.0;
  const p = interactiveOdds;
  const q = 1 - p;
  const b = (1 / selectedMarket.whaleEntry) - 1;
  const rawKelly = Math.max(0, (p * b - q) / b);
  const scaledFraction = Math.min(0.35, rawKelly * regimeMultiplier);
  const simulatedAllocation = Math.round(2000 * (0.4 + scaledFraction * 1.5));
  const expectedValuePct = Math.round(((p / selectedMarket.whaleEntry) - 1) * 100);

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="relative w-full max-w-4xl mx-auto mt-6 sm:mt-10 select-none px-2 sm:px-0"
    >
      {/* Mode Capsule Switcher */}
      <div className="flex items-center justify-center mb-5 sm:mb-6 px-2">
        <div className="glass-dock glass-chromatic-bezel p-1 sm:p-1.5 grid grid-cols-3 w-full max-w-[380px] sm:max-w-md shadow-lg border border-white/90">
          <button
            type="button"
            onClick={() => {
              setMode('telemetry');
              dragX.set(0);
              dragY.set(0);
            }}
            className={`flex items-center justify-center gap-1.5 py-1.5 sm:py-2 px-2.5 rounded-full text-[11px] sm:text-xs font-mono font-bold transition-all text-center ${
              mode === 'telemetry'
                ? 'bg-gradient-to-b from-sky-500 to-sky-600 text-white shadow-md shadow-sky-500/25 scale-[1.02]'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Activity size={13} className={mode === 'telemetry' ? 'text-white' : 'text-sky-600'} />
            <span className="sm:hidden">Console</span>
            <span className="hidden sm:inline">Alpha Console</span>
          </button>

          <button
            type="button"
            onClick={() => setMode('fluid')}
            className={`flex items-center justify-center gap-1.5 py-1.5 sm:py-2 px-2.5 rounded-full text-[11px] sm:text-xs font-mono font-bold transition-all text-center ${
              mode === 'fluid'
                ? 'bg-gradient-to-b from-sky-500 to-sky-600 text-white shadow-md shadow-sky-500/25 scale-[1.02]'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Sliders size={13} className={mode === 'fluid' ? 'text-white' : 'text-cyan-600'} />
            <span className="sm:hidden">Fluid</span>
            <span className="hidden sm:inline">Fluid Meniscus</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setMode('sleeves');
              dragX.set(0);
              dragY.set(0);
            }}
            className={`flex items-center justify-center gap-1.5 py-1.5 sm:py-2 px-2.5 rounded-full text-[11px] sm:text-xs font-mono font-bold transition-all text-center ${
              mode === 'sleeves'
                ? 'bg-gradient-to-b from-sky-500 to-sky-600 text-white shadow-md shadow-sky-500/25 scale-[1.02]'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Layers size={13} className={mode === 'sleeves' ? 'text-white' : 'text-indigo-600'} />
            <span className="sm:hidden">5 Sleeves</span>
            <span className="hidden sm:inline">5 Risk Sleeves</span>
          </button>
        </div>
      </div>

      {/* Main Glass Stage Container */}
      <div className="glass-card glass-chromatic-bezel relative min-h-[420px] sm:min-h-[480px] w-full rounded-[32px] sm:rounded-[36px] overflow-hidden p-4 sm:p-7 flex flex-col justify-between shadow-xl">
        {/* Subtle Perspective Grid */}
        <div
          className="absolute inset-0 pointer-events-none opacity-30"
          style={{
            backgroundImage: `linear-gradient(to right, rgba(2, 132, 199, 0.08) 1px, transparent 1px), linear-gradient(to bottom, rgba(2, 132, 199, 0.08) 1px, transparent 1px)`,
            backgroundSize: '48px 48px',
            transform: `translate3d(${mouseTilt.x * -6}px, ${mouseTilt.y * -6}px, 0)`,
            transition: 'transform 0.4s ease-out',
          }}
        />

        {/* Ambient Arctic Glacier Glow */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div
            className="absolute top-1/4 left-1/4 w-80 h-80 rounded-full bg-sky-200/35 blur-[100px] transition-transform duration-700 ease-out"
            style={{
              transform: `translate3d(${mouseTilt.x * 20}px, ${mouseTilt.y * 15}px, 0)`,
            }}
          />
          <div
            className="absolute bottom-1/4 right-1/4 w-80 h-80 rounded-full bg-cyan-200/30 blur-[100px] transition-transform duration-700 ease-out"
            style={{
              transform: `translate3d(${mouseTilt.x * -20}px, ${mouseTilt.y * -15}px, 0)`,
            }}
          />
        </div>

        {/* MODE 1: INTERACTIVE POLYMARKET ALPHA GLASS TELEMETRY CONSOLE */}
        {mode === 'telemetry' && (
          <motion.div
            style={{ y: floatY }}
            className="relative z-10 w-full flex flex-col gap-4 my-1"
          >
            {/* Top Telemetry Header & Market Switcher */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3 rounded-2xl bg-white/70 backdrop-blur-xl border border-white/90 shadow-sm">
              <div className="flex items-center gap-2.5 flex-wrap">
                <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200/60 text-[10px] sm:text-xs font-mono font-bold text-emerald-700">
                  <span className="size-2 rounded-full bg-emerald-500 animate-ping" />
                  <span>LIVE CLOB</span>
                </span>

                <div className="flex items-center gap-1 bg-sky-50/80 p-1 rounded-xl border border-sky-100">
                  {sampleMarkets.map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => {
                        setSelectedMarket(m);
                        setInteractiveOdds(m.oddsYes);
                      }}
                      className={`px-2.5 py-1 rounded-lg text-[10px] sm:text-xs font-mono font-bold transition-all ${
                        selectedMarket.id === m.id
                          ? 'bg-white text-sky-900 shadow-xs border border-sky-200/60'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      {m.ticker}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-3 text-xs font-mono text-slate-500 self-end sm:self-center">
                <span className="flex items-center gap-1 text-sky-700 font-semibold">
                  <Zap size={13} className="text-sky-500" />
                  <span>Envio: <strong>84ms</strong></span>
                </span>
                <span className="text-slate-300">|</span>
                <span className="text-emerald-700 font-bold">{selectedMarket.conviction}</span>
              </div>
            </div>

            {/* Middle Main Telemetry Stage: Live Probability Curve & Kelly Cockpit */}
            <div className="grid gap-4 lg:grid-cols-[1.3fr_0.9fr] items-stretch">
              {/* Left Column: Live Probability Distribution & Alpha Gap Visualizer */}
              <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-b from-white/90 to-sky-50/60 border border-white/90 shadow-sm flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between font-mono text-xs mb-2">
                    <div className="font-bold text-slate-900 flex items-center gap-1.5">
                      <TrendingUp size={14} className="text-sky-600" />
                      <span>{selectedMarket.name}</span>
                    </div>
                    <span className="text-slate-500 text-[11px]">Vol: {selectedMarket.volume}</span>
                  </div>

                  {/* Interactive SVG Probability Density Curve */}
                  <div className="relative h-36 sm:h-44 w-full mt-2 rounded-xl bg-gradient-to-b from-sky-100/40 via-white/50 to-sky-50/40 p-2 border border-sky-100/70 overflow-hidden">
                    <svg viewBox="0 0 400 140" className="w-full h-full overflow-visible">
                      <defs>
                        <linearGradient id="curveGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#0284C7" stopOpacity="0.3" />
                          <stop offset="100%" stopColor="#0284C7" stopOpacity="0.02" />
                        </linearGradient>
                        <linearGradient id="alphaZone" x1="0" y1="0" x2="1" y2="0">
                          <stop offset="0%" stopColor="#059669" stopOpacity="0.35" />
                          <stop offset="100%" stopColor="#0284C7" stopOpacity="0.25" />
                        </linearGradient>
                      </defs>

                      {/* Horizontal Grid lines */}
                      <line x1="0" y1="30" x2="400" y2="30" stroke="rgba(2, 132, 199, 0.1)" strokeDasharray="3 3" />
                      <line x1="0" y1="70" x2="400" y2="70" stroke="rgba(2, 132, 199, 0.1)" strokeDasharray="3 3" />
                      <line x1="0" y1="110" x2="400" y2="110" stroke="rgba(2, 132, 199, 0.1)" strokeDasharray="3 3" />

                      {/* Whale Entry Reference Line */}
                      {(() => {
                        const whaleX = selectedMarket.whaleEntry * 360 + 20;
                        const marketX = interactiveOdds * 360 + 20;
                        return (
                          <>
                            {/* Alpha Gap Shaded Area */}
                            <rect
                              x={whaleX}
                              y="20"
                              width={Math.max(4, marketX - whaleX)}
                              height="100"
                              fill="url(#alphaZone)"
                              rx="4"
                            />
                            {/* Whale Entry Vertical Marker */}
                            <line x1={whaleX} y1="15" x2={whaleX} y2="125" stroke="#059669" strokeWidth="1.5" strokeDasharray="2 2" />
                            <circle cx={whaleX} cy="55" r="4" fill="#059669" />
                            <text x={whaleX} y="12" fill="#059669" fontSize="9" fontWeight="bold" textAnchor="middle" fontFamily="monospace">
                              Whale ${(selectedMarket.whaleEntry).toFixed(2)}
                            </text>

                            {/* Current Market Odds Vertical Marker */}
                            <line x1={marketX} y1="15" x2={marketX} y2="125" stroke="#0284C7" strokeWidth="2" />
                            <circle cx={marketX} cy="42" r="5" fill="#0284C7" stroke="#ffffff" strokeWidth="2" />
                            <text x={marketX} y="12" fill="#0284C7" fontSize="9" fontWeight="bold" textAnchor="middle" fontFamily="monospace">
                              Market ${(interactiveOdds).toFixed(2)}
                            </text>
                          </>
                        );
                      })()}

                      {/* Smooth Probability Distribution Bell Curve */}
                      <path
                        d="M 20 120 C 80 120, 140 100, 200 60 C 260 20, 320 60, 380 120"
                        fill="url(#curveGradient)"
                        stroke="#0284C7"
                        strokeWidth="2.5"
                      />
                    </svg>

                    {/* Interactive Slider Overlay to Shift Odds */}
                    <div className="absolute bottom-1 inset-x-3 flex items-center justify-between text-[9px] font-mono text-slate-500">
                      <span>Odds: 0.00</span>
                      <span className="font-bold text-sky-800">
                        Alpha Spread: +{Math.round((interactiveOdds - selectedMarket.whaleEntry) * 100)}¢ / contract
                      </span>
                      <span>1.00</span>
                    </div>
                  </div>
                </div>

                {/* Interactive Slider for Odds Testing */}
                <div className="mt-3 flex items-center gap-3 font-mono text-xs">
                  <span className="text-slate-500 text-[11px] shrink-0">Simulate Market Odds:</span>
                  <input
                    type="range"
                    min="0.50"
                    max="0.95"
                    step="0.01"
                    value={interactiveOdds}
                    onChange={(e) => setInteractiveOdds(Number(e.target.value))}
                    className="w-full h-2 rounded-full appearance-none cursor-pointer bg-sky-200 accent-sky-600"
                  />
                  <span className="font-bold text-slate-900 tabular-nums shrink-0">${interactiveOdds.toFixed(2)}</span>
                </div>
              </div>

              {/* Right Column: Kelly Fraction Engine & Isolated Sleeve Sizing */}
              <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-b from-white/90 to-sky-50/60 border border-white/90 shadow-sm flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between font-mono text-xs">
                    <span className="font-bold text-slate-900 flex items-center gap-1.5">
                      <Shield size={14} className="text-emerald-600" />
                      <span>KELLY SIZING ENGINE</span>
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-sky-100 text-sky-800 font-bold text-[10px]">
                      Sleeve A
                    </span>
                  </div>

                  {/* Kelly Regime Toggle */}
                  <div className="mt-3 grid grid-cols-3 gap-1 bg-slate-100/80 p-1 rounded-xl border border-slate-200/60 font-mono text-[10px]">
                    <button
                      type="button"
                      onClick={() => setKellyRegime('conservative')}
                      className={`py-1 rounded-lg font-bold transition-all ${
                        kellyRegime === 'conservative'
                          ? 'bg-white text-slate-900 shadow-xs'
                          : 'text-slate-500 hover:text-slate-800'
                      }`}
                    >
                      0.25x
                    </button>
                    <button
                      type="button"
                      onClick={() => setKellyRegime('balanced')}
                      className={`py-1 rounded-lg font-bold transition-all ${
                        kellyRegime === 'balanced'
                          ? 'bg-white text-sky-700 shadow-xs'
                          : 'text-slate-500 hover:text-slate-800'
                      }`}
                    >
                      0.50x
                    </button>
                    <button
                      type="button"
                      onClick={() => setKellyRegime('aggressive')}
                      className={`py-1 rounded-lg font-bold transition-all ${
                        kellyRegime === 'aggressive'
                          ? 'bg-white text-emerald-700 shadow-xs'
                          : 'text-slate-500 hover:text-slate-800'
                      }`}
                    >
                      1.00x
                    </button>
                  </div>

                  {/* Sizing Outputs */}
                  <div className="mt-4 space-y-2.5 font-mono text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Target Size:</span>
                      <span className="font-black text-slate-900 text-base tabular-nums">
                        ${simulatedAllocation.toLocaleString()}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Expected Value:</span>
                      <span className="font-bold text-emerald-600 tabular-nums">
                        +{expectedValuePct}% EV
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Max CLOB Slippage:</span>
                      <span className="font-semibold text-sky-700 tabular-nums">&lt;0.02%</span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Sleeve Cap Guard:</span>
                      <span className="font-semibold text-slate-800 tabular-nums">$2,000.00</span>
                    </div>
                  </div>
                </div>

                {/* Simulated Order Execution Pill */}
                <div className="mt-4 pt-3 border-t border-sky-100 flex items-center justify-between text-[11px] font-mono">
                  <span className="text-slate-500 flex items-center gap-1">
                    <CheckCircle size={13} className="text-emerald-500" />
                    <span>$1.00 Floor Clamped</span>
                  </span>
                  <span className="text-sky-700 font-bold flex items-center gap-0.5">
                    <span>Simulated Fill</span>
                    <ArrowUpRight size={13} />
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* MODE 2: INTERACTIVE FLUID DRAG & MENISCUS OPTICS */}
        {mode === 'fluid' && (
          <div className="relative w-full max-w-[560px] mx-auto h-[220px] sm:h-[280px] flex items-center justify-between px-2 sm:px-8 overflow-hidden">
            {/* Dynamic SVG Liquid Meniscus Bridge */}
            <svg
              viewBox="0 0 600 280"
              className="absolute inset-0 w-full h-full pointer-events-none overflow-visible filter drop-shadow-[0_12px_24px_rgba(2,132,199,0.15)]"
            >
              <defs>
                <linearGradient id="fluid-glass-surface" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="rgba(255, 255, 255, 0.95)" />
                  <stop offset="40%" stopColor="rgba(224, 242, 254, 0.70)" />
                  <stop offset="100%" stopColor="rgba(186, 230, 253, 0.50)" />
                </linearGradient>

                <linearGradient id="fluid-bridge-chromatic" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#38BDF8" stopOpacity="0.85" />
                  <stop offset="40%" stopColor="#818CF8" stopOpacity="0.85" />
                  <stop offset="70%" stopColor="#059669" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#F472B6" stopOpacity="0.8" />
                </linearGradient>
              </defs>

              {/* Dynamic Meniscus Waist Bridge */}
              {isBonded && (
                <g>
                  <path
                    d={`M ${topC1X} ${topC1Y} Q ${midX} ${topMidY} ${topC2X} ${topC2Y} L ${botC2X} ${botC2Y} Q ${midX} ${botMidY} ${botC1X} ${botC1Y} Z`}
                    fill="url(#fluid-glass-surface)"
                    stroke="rgba(255, 255, 255, 0.9)"
                    strokeWidth="1.5"
                  />
                  <path
                    d={`M ${topC1X} ${topC1Y} Q ${midX} ${topMidY} ${topC2X} ${topC2Y}`}
                    fill="none"
                    stroke="rgba(255, 255, 255, 1)"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                  />
                  <path
                    d={`M ${botC1X} ${botC1Y} Q ${midX} ${botMidY} ${botC2X} ${botC2Y}`}
                    fill="none"
                    stroke="url(#fluid-bridge-chromatic)"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                  />
                </g>
              )}
            </svg>

            {/* Draggable Fluid Glass Droplet */}
            <motion.div
              drag
              dragConstraints={{ left: -40, right: 80, top: -40, bottom: 40 }}
              dragElastic={0.25}
              onDrag={(_, info) => {
                dragX.set(info.offset.x);
                dragY.set(info.offset.y);
              }}
              onDragEnd={() => {
                dragX.set(0);
                dragY.set(0);
              }}
              className="glass-button relative size-24 sm:size-32 rounded-full cursor-grab active:cursor-grabbing flex flex-col items-center justify-center p-2 sm:p-3 shadow-xl z-20 shrink-0 border border-white"
              style={{
                x: springX,
                y: springY,
              }}
            >
              <div className="absolute top-2 inset-x-3 h-4 rounded-full bg-gradient-to-b from-white to-transparent pointer-events-none" />

              <span className="size-2 rounded-full bg-sky-500 animate-ping" />
              <span className="font-mono text-[9px] sm:text-xs font-black text-slate-900 mt-1 tracking-wider">
                DRAG ME
              </span>
              <span className="text-[8px] sm:text-[9px] font-mono text-sky-700 font-bold">
                {isBonded ? 'BONDED' : 'PINCHED'}
              </span>

              <div className="absolute bottom-1.5 inset-x-4 h-1 rounded-full bg-gradient-to-r from-sky-400 via-indigo-300 to-cyan-400 blur-[0.5px] pointer-events-none" />
            </motion.div>

            {/* Base Liquid Glass Sleeve Capsule */}
            <div className="glass-card relative h-28 sm:h-36 w-44 sm:w-64 rounded-[32px] sm:rounded-[40px] flex items-center justify-between px-4 sm:px-7 shadow-lg z-10 shrink-0 border border-white/90">
              <div className="absolute top-2 inset-x-4 h-4 rounded-full bg-gradient-to-b from-white to-transparent pointer-events-none" />

              <div className="font-mono">
                <div className="text-[8px] sm:text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  ISOLATED SLEEVE
                </div>
                <div className="text-sm sm:text-xl font-black text-slate-900 tabular-nums">$2,000.00</div>
                <div className="text-[8px] sm:text-[9px] font-semibold text-emerald-600">Guard: Safe</div>
              </div>

              <div className="flex flex-col items-end gap-1 font-mono">
                <span
                  className={`rounded-full px-2 py-0.5 text-[9px] sm:text-[10px] font-bold border transition-colors ${
                    isBonded
                      ? 'border-emerald-300 bg-emerald-50 text-emerald-700'
                      : 'border-sky-300 bg-sky-50 text-sky-700'
                  }`}
                >
                  {isBonded ? 'Fused' : 'Isolated'}
                </span>
                <span className="text-[8px] text-slate-500">91.4% Win</span>
              </div>

              <div className="absolute bottom-1.5 inset-x-5 h-1 rounded-full bg-gradient-to-r from-cyan-400/60 via-sky-400/70 to-purple-400/60 blur-[0.5px] pointer-events-none" />
            </div>
          </div>
        )}

        {/* MODE 3: 5 ISOLATED RISK SLEEVE DROPLETS */}
        {mode === 'sleeves' && (
          <div className="grid grid-cols-5 gap-2 sm:gap-4 w-full max-w-2xl mx-auto px-1 my-auto">
            {[
              { label: 'Sleeve A', whale: '0x12a9', cap: '$2,000', win: '94.2%', color: '#059669' },
              { label: 'Sleeve B', whale: '0x7bf3', cap: '$2,000', win: '89.6%', color: '#0284C7' },
              { label: 'Sleeve C', whale: '0x4981', cap: '$2,000', win: '91.8%', color: '#7C3AED' },
              { label: 'Sleeve D', whale: '0xce92', cap: '$2,000', win: '92.4%', color: '#059669' },
              { label: 'Sleeve E', whale: '0x38e1', cap: '$2,000', win: '88.9%', color: '#0284C7' },
            ].map((sleeve, idx) => (
              <motion.div
                key={sleeve.label}
                initial={{ scale: 0.8, opacity: 0, y: 16 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: idx * 0.05 }}
                className="glass-card glass-chromatic-bezel group relative flex flex-col items-center justify-between p-2 sm:p-4 rounded-2xl sm:rounded-3xl cursor-pointer hover:scale-105 transition-all shadow-md border border-white/95"
              >
                <div className="absolute top-1 inset-x-2 h-2 rounded-full bg-gradient-to-b from-white to-transparent pointer-events-none opacity-90" />
                <span className="text-[8px] sm:text-[10px] font-mono text-slate-500 font-bold">{sleeve.label}</span>
                <div className="my-1 sm:my-2 size-7 sm:size-10 rounded-full border border-sky-100 bg-sky-50/80 flex items-center justify-center font-mono text-[9px] font-black shadow-inner">
                  <Shield size={13} style={{ color: sleeve.color }} />
                </div>
                <div className="text-center font-mono">
                  <div className="text-[9px] sm:text-xs font-black text-slate-900">{sleeve.cap}</div>
                  <div className="text-[8px] sm:text-[9px] font-bold" style={{ color: sleeve.color }}>
                    {sleeve.win}
                  </div>
                </div>
                <div className="absolute bottom-1 inset-x-2 h-0.5 rounded-full bg-gradient-to-r from-sky-400/40 via-purple-400/40 to-emerald-400/40 opacity-70 pointer-events-none" />
              </motion.div>
            ))}
          </div>
        )}

        {/* Bottom Status Bar */}
        <div className="relative z-20 flex flex-wrap items-center justify-between gap-2 pt-3 mt-3 border-t border-sky-100 font-mono text-xs text-slate-600">
          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-slate-900 font-bold text-[9px] sm:text-[11px]">OPTICAL LIQUID GLASS</span>
            <span className="text-slate-300">|</span>
            <span className="text-[9px] sm:text-[11px] text-slate-600 truncate max-w-[140px] sm:max-w-none">
              {mode === 'telemetry'
                ? 'Polymarket Alpha Glass Telemetry'
                : mode === 'fluid'
                ? 'Surface Tension Meniscus Physics'
                : 'Isolated Mathematical Boundaries'}
            </span>
          </div>

          <div className="flex items-center gap-2 sm:gap-3 text-[9px] sm:text-[11px]">
            <span className="text-slate-500">
              Meniscus:{' '}
              <strong className="text-slate-900 font-bold">
                {mode === 'telemetry' ? 'Active' : isBonded ? 'Bonded' : 'Separated'}
              </strong>
            </span>
            <span className="text-slate-300">·</span>
            <span className="text-slate-500">
              Prism Rim: <strong className="text-emerald-700 font-bold">Active</strong>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
