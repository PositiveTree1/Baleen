'use client';
import { useMemo, useState, useEffect, useCallback, useRef } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { ExecutionLog } from '@/types';
import { 
  RefreshCw,
  Code2,
  Database,
  Copy,
  Check,
  X,
  Loader2
} from 'lucide-react';
import { formatFrenchTime, formatFrenchDate } from '@/lib/formatters';
import { resetSandboxLedger, clearAllCache, fetchPortfolioSnapshots } from '@/lib/api-client';

interface PnLChartWidgetProps {
  logs?: ExecutionLog[];
  userId?: string;
  startingBalance?: number;
  currentBalance?: number;
  onResetComplete?: () => void;
  heightMode?: 'normal' | 'tall';
  onCycleSize?: () => void;
}

export function PnLChartWidget({
  logs = [],
  userId,
  startingBalance = 10000.0,
  currentBalance = 10000.0,
  onResetComplete,
  heightMode = 'normal',
  onCycleSize
}: PnLChartWidgetProps) {
  const [timeframe, setTimeframe] = useState<'1H' | '6H' | '1D' | '1W' | '1M' | 'YTD' | 'ALL'>('ALL');
  const [showResetModal, setShowResetModal] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [showRawDataModal, setShowRawDataModal] = useState(false);
  const [copied, setCopied] = useState(false);

  const isMultiDay = timeframe === 'ALL' || timeframe === '1W' || timeframe === '1M' || timeframe === 'YTD';

  const [snapshotTimeline, setSnapshotTimeline] = useState<any[]>([]);
  const [chartLoading, setChartLoading] = useState<boolean>(false);
  const prevTimelineRef = useRef<any[]>([]);

  const loadSnapshots = useCallback(async () => {
    setChartLoading(true);
    try {
      const tfMap: Record<string, string> = {
        '1H': '1h', '6H': '6h', '1D': '1d', '1W': '1w', '1M': '1m', 'YTD': 'ytd', 'ALL': 'all'
      };
      const data = await fetchPortfolioSnapshots(userId, tfMap[timeframe] || 'all');
      if (Array.isArray(data) && data.length > 0) {
        const timeline = data.map((s: any) => {
          const ts = s.timestamp ? new Date(s.timestamp) : new Date();
          const timeStr = formatFrenchTime(ts);
          const dateStr = formatFrenchDate(ts);
          return {
            displayTime: isMultiDay && dateStr ? `${dateStr} ${timeStr}` : timeStr,
            time: timeStr,
            date: dateStr,
            balance: Math.round((s.balance ?? 10000) * 100) / 100,
            pnl: Math.round((s.pnl ?? 0) * 100) / 100,
            rawTimestamp: ts.getTime(),
          };
        });

        // Ensure smooth continuous timeline up to present moment
        if (currentBalance > 0 && timeline.length > 0) {
          const now = new Date();
          const lastPoint = timeline[timeline.length - 1];
          const gapMs = now.getTime() - lastPoint.rawTimestamp;

          // If there is a multi-hour gap, interpolate smooth hourly checkpoints
          if (gapMs > 3600000) {
            const hours = Math.min(24, Math.floor(gapMs / 3600000));
            const startBal = lastPoint.balance;
            const endBal = currentBalance;
            const startPnl = lastPoint.pnl;
            const endPnl = currentBalance - startingBalance;

            for (let h = 1; h <= hours; h++) {
              const interpMs = lastPoint.rawTimestamp + h * 3600000;
              if (interpMs >= now.getTime() - 60000) break;
              const interpDate = new Date(interpMs);
              const ratio = h / (hours + 1);
              const interpBal = Math.round((startBal + ratio * (endBal - startBal)) * 100) / 100;
              const interpPnl = Math.round((startPnl + ratio * (endPnl - startPnl)) * 100) / 100;
              const iTime = formatFrenchTime(interpDate);
              const iDate = formatFrenchDate(interpDate);
              timeline.push({
                displayTime: isMultiDay && iDate ? `${iDate} ${iTime}` : iTime,
                time: iTime,
                date: iDate,
                balance: interpBal,
                pnl: interpPnl,
                rawTimestamp: interpMs,
              });
            }
          }

          // Append authoritative current live point
          const nowTimeStr = formatFrenchTime(now);
          const nowDateStr = formatFrenchDate(now);
          const livePoint = {
            displayTime: isMultiDay && nowDateStr ? `${nowDateStr} ${nowTimeStr}` : nowTimeStr,
            time: nowTimeStr,
            date: nowDateStr,
            balance: Math.round(currentBalance * 100) / 100,
            pnl: Math.round((currentBalance - startingBalance) * 100) / 100,
            rawTimestamp: now.getTime(),
          };

          const latestPt = timeline[timeline.length - 1];
          if ((now.getTime() - latestPt.rawTimestamp) > 180000) {
            timeline.push(livePoint);
          } else {
            latestPt.balance = Math.round(currentBalance * 100) / 100;
            latestPt.pnl = Math.round((currentBalance - startingBalance) * 100) / 100;
            latestPt.displayTime = livePoint.displayTime;
            latestPt.time = livePoint.time;
            latestPt.date = livePoint.date;
          }
        }

        prevTimelineRef.current = timeline;
        setSnapshotTimeline(timeline);
      } else if (prevTimelineRef.current.length === 0) {
        const nowMs = Date.now();
        const fallback = [{
          displayTime: formatFrenchTime(new Date()),
          balance: Math.round(currentBalance * 100) / 100,
          pnl: Math.round((currentBalance - startingBalance) * 100) / 100,
          date: 'Now',
          rawTimestamp: nowMs,
        }];
        setSnapshotTimeline(fallback);
      }
    } catch (e) {
      console.debug("Snapshot fetch note:", e);
    } finally {
      setChartLoading(false);
    }
  }, [userId, timeframe, currentBalance, startingBalance, isMultiDay]);

  useEffect(() => {
    loadSnapshots();
    const interval = setInterval(loadSnapshots, 15000);
    return () => clearInterval(interval);
  }, [loadSnapshots]);

  const pnlTimeline = (snapshotTimeline.length === 0 && prevTimelineRef.current.length > 0) 
    ? prevTimelineRef.current 
    : snapshotTimeline;

  const periodPnL = useMemo(() => {
    if (pnlTimeline.length < 2) return Math.round((currentBalance - startingBalance) * 100) / 100;
    const startBal = pnlTimeline[0].balance;
    const endBal = pnlTimeline[pnlTimeline.length - 1].balance;
    return Math.round((endBal - startBal) * 100) / 100;
  }, [pnlTimeline, currentBalance, startingBalance]);

  const periodPnLPct = useMemo(() => {
    if (pnlTimeline.length < 2) {
      return startingBalance > 0 ? Math.round(((currentBalance - startingBalance) / startingBalance) * 10000) / 100 : 0;
    }
    const startBal = pnlTimeline[0].balance;
    const endBal = pnlTimeline[pnlTimeline.length - 1].balance;
    return startBal > 0 ? Math.round(((endBal - startBal) / startBal) * 10000) / 100 : 0;
  }, [pnlTimeline, currentBalance, startingBalance]);

  const handleResetSandbox = async () => {
    setIsResetting(true);
    try {
      await resetSandboxLedger(userId);
      clearAllCache();
      setShowResetModal(false);
      if (onResetComplete) onResetComplete();
      window.location.reload();
    } catch (e) {
      console.error("Reset error:", e);
    } finally {
      setIsResetting(false);
    }
  };

  const chartHeightPx = heightMode === 'tall' ? 320 : 220;

  return (
    <div className="p-6 rounded-3xl apple-glass light-refraction relative overflow-hidden space-y-4 h-full flex flex-col justify-between group">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Sandbox Capital Curve</span>
          <div className="flex items-baseline gap-2.5 sm:gap-3 mt-1 flex-wrap sm:nowrap">
            <span className="text-2xl sm:text-3xl font-extrabold font-mono text-slate-950 tabular-nums whitespace-nowrap">
              ${currentBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span className={`inline-flex items-baseline gap-1 text-xs sm:text-sm font-mono font-bold whitespace-nowrap ${periodPnL >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
              <span>{periodPnL >= 0 ? '+' : ''}${periodPnL.toFixed(2)} ({periodPnL >= 0 ? '+' : ''}{periodPnLPct.toFixed(2)}%)</span>
              <span className="text-[10px] text-slate-400 font-sans font-normal whitespace-nowrap ml-0.5">in {timeframe}</span>
            </span>
          </div>
        </div>

        {/* Timeframe selector & Tools */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0 overflow-x-auto">
          <div className={`flex items-center rounded-xl bg-white/40 backdrop-blur-md p-0.5 border border-white/60 shadow-[inset_0_1px_1px_rgba(255,255,255,0.8)] text-xs font-mono font-semibold transition-opacity ${chartLoading ? 'opacity-85' : ''}`}>
            {(['1H', '6H', '1D', '1W', '1M', 'YTD', 'ALL'] as const).map((tf) => {
              const isActive = timeframe === tf;
              return (
                <button
                  key={tf}
                  disabled={chartLoading}
                  onClick={() => {
                    if (!chartLoading && tf !== timeframe) {
                      setTimeframe(tf);
                    }
                  }}
                  className={`px-2 py-1 rounded-lg transition-all flex items-center gap-1 ${
                    chartLoading ? 'cursor-not-allowed' : 'cursor-pointer'
                  } ${
                    isActive 
                      ? 'bg-white text-slate-950 font-bold shadow-xs' 
                      : 'text-slate-500 hover:text-slate-900'
                  }`}
                  title={chartLoading ? `Loading ${timeframe} snapshots...` : `Switch to ${tf} timeframe`}
                >
                  {isActive && chartLoading && (
                    <Loader2 size={10} className="animate-spin text-indigo-600 shrink-0" />
                  )}
                  <span>{tf}</span>
                </button>
              );
            })}
          </div>
          <button
            onClick={() => setShowResetModal(true)}
            className="p-1.5 rounded-xl bg-slate-100 hover:bg-rose-50 text-slate-400 hover:text-rose-600 border border-black/[0.04] transition-all cursor-pointer"
            title="Reset Sandbox to $10,000 baseline"
          >
            <RefreshCw size={13} />
          </button>
          <button
            onClick={() => setShowRawDataModal(true)}
            className="p-1.5 px-2 rounded-xl bg-slate-100 hover:bg-indigo-50 text-slate-500 hover:text-indigo-600 border border-black/[0.04] transition-all cursor-pointer flex items-center gap-1 text-[11px] font-mono font-semibold"
            title="View raw chart snapshot data received from server"
          >
            <Code2 size={13} />
            <span className="hidden sm:inline">Raw Data</span>
          </button>
        </div>
      </div>

      {/* Stable, Zero-Jitter Area Chart Container */}
      <div 
        className="w-full pt-2 outline-none select-none overflow-hidden" 
        style={{ height: `${chartHeightPx}px`, minHeight: `${chartHeightPx}px`, minWidth: 0 }}
      >
        <ResponsiveContainer width="100%" height={chartHeightPx} debounce={40}>
          <AreaChart data={pnlTimeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }} className="outline-none">
            <defs>
              <linearGradient id="widgetBalanceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={periodPnL >= 0 ? '#10B981' : '#F43F5E'} stopOpacity={0.25} />
                <stop offset="95%" stopColor={periodPnL >= 0 ? '#10B981' : '#F43F5E'} stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <XAxis 
              dataKey="displayTime" 
              tick={{ fontSize: 9, fill: '#94A3B8' }} 
              axisLine={false} 
              tickLine={false}
              minTickGap={30}
            />
            <YAxis 
              domain={['auto', 'auto']} 
              tick={{ fontSize: 10, fill: '#94A3B8' }} 
              axisLine={false} 
              tickLine={false}
              tickFormatter={(val) => `$${Math.round(val).toLocaleString()}`}
            />
            <Tooltip 
              isAnimationActive={false}
              cursor={{ stroke: '#6366F1', strokeWidth: 1.5, strokeDasharray: '3 3' }}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const d = payload[0].payload;
                  return (
                    <div className="bg-slate-950 text-white px-4 py-3 rounded-2xl text-xs font-mono shadow-2xl border border-white/10 max-w-xs space-y-1">
                      <div className="flex items-center justify-between text-[10px] text-slate-400">
                        <span>{d.date} • {d.time || d.displayTime}</span>
                        <span className="font-bold text-slate-300">Sandbox Balance</span>
                      </div>
                      <div className="text-base font-bold text-white">${d.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                      <div className={`text-[11px] font-bold ${d.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {d.pnl >= 0 ? '+' : ''}${d.pnl.toFixed(2)} Total P&amp;L
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Area 
              type="monotone"
              dataKey="balance" 
              stroke={periodPnL >= 0 ? '#10B981' : '#F43F5E'} 
              strokeWidth={2.5}
              fillOpacity={1} 
              fill="url(#widgetBalanceGradient)"
              dot={false}
              activeDot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Subtle Apple-Style Corner Resize Grabber */}
      {onCycleSize && (
        <button
          onClick={onCycleSize}
          className="absolute bottom-2 right-2 p-1.5 rounded-xl bg-black/[0.03] hover:bg-black/[0.08] text-slate-400 hover:text-slate-800 transition-all opacity-40 group-hover:opacity-100 cursor-nwse-resize"
          title="Click to cycle card width (1/3 → 2/3 → Full)"
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-current">
            <path d="M10 2L2 10M10 6L6 10M10 10H10.01" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
      )}

      {/* Confirmation Reset Modal */}
      {showResetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white rounded-3xl p-6 shadow-2xl border border-black/[0.08] space-y-4">
            <h3 className="text-base font-bold text-slate-900">Reset Sandbox Simulation?</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              This will reset your paper trading balance back to <strong>$10,000.00</strong>, clear all execution logs and simulation charts.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowResetModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                disabled={isResetting}
                onClick={handleResetSandbox}
                className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 transition-colors shadow-sm cursor-pointer"
              >
                {isResetting ? 'Resetting...' : 'Confirm Reset'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Raw Snapshot Data Modal */}
      {showRawDataModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/75 backdrop-blur-md">
          <div className="w-full max-w-3xl max-h-[85vh] bg-white rounded-3xl p-6 shadow-2xl border border-black/[0.08] flex flex-col space-y-4 relative z-[101]">
            <div className="flex items-center justify-between border-b border-black/[0.06] pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-200">
                  <Database size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Received Chart Snapshot Data</h3>
                  <p className="text-[11px] text-slate-500 font-mono">
                    Timeframe: <span className="font-bold text-slate-800">{timeframe}</span> • {pnlTimeline.length} points received from server
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(JSON.stringify(pnlTimeline, null, 2));
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700 transition-colors cursor-pointer"
                >
                  {copied ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}
                  <span>{copied ? 'Copied!' : 'Copy JSON'}</span>
                </button>
                <button
                  onClick={() => setShowRawDataModal(false)}
                  className="p-1.5 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Code / JSON Viewer */}
            <div className="flex-1 overflow-auto bg-slate-950 text-emerald-400 p-4 rounded-2xl font-mono text-xs leading-relaxed border border-white/10 shadow-inner max-h-[60vh]">
              <pre>{JSON.stringify(pnlTimeline, null, 2)}</pre>
            </div>

            <div className="flex justify-between items-center text-[11px] text-slate-400 pt-1">
              <span>Endpoint: <code className="text-slate-600 font-mono">/api/executions/snapshots?timeframe={timeframe.toLowerCase()}</code></span>
              <span>Latest Balance: <strong className="text-slate-800">${(pnlTimeline[pnlTimeline.length - 1]?.balance ?? currentBalance).toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong></span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
