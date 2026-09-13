'use client';
import { useMemo } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from 'recharts';
import { formatFrenchDate } from '@/lib/formatters';

interface PnLPoint {
  date: string;
  dailyPnL?: number;
  cumulativePnL: number;
  tradesCount?: number;
}

interface CumulativePnLChartProps {
  data: PnLPoint[];
}

/**
 * Interpolates missing calendar days continuously between min and max date
 * so that flat periods appear as true chronological horizontal lines (matching Polymarket)
 * rather than squishing/stretching arbitrary multi-day gaps.
 */
function interpolateCalendarTimeline(points: PnLPoint[]): PnLPoint[] {
  if (!points || points.length <= 1) return points;

  const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
  const validPoints = points.filter((p) => p && typeof p.date === 'string' && dateRegex.test(p.date));
  if (validPoints.length <= 1) return points;

  const sorted = [...validPoints].sort((a, b) => a.date.localeCompare(b.date));
  const minDateStr = sorted[0].date;
  const maxDateStr = sorted[sorted.length - 1].date;

  const startDate = new Date(minDateStr + 'T00:00:00Z');
  const endDate = new Date(maxDateStr + 'T00:00:00Z');

  const diffDays = Math.round((endDate.getTime() - startDate.getTime()) / 86400000);
  // Cap interpolation to 1,200 calendar days to avoid excessive DOM nodes
  if (diffDays <= 0 || diffDays > 1200) {
    return sorted;
  }

  const pointMap = new Map<string, PnLPoint>();
  for (const pt of sorted) {
    pointMap.set(pt.date, pt);
  }

  const result: PnLPoint[] = [];
  let runningCum = sorted[0].cumulativePnL ?? 0;
  const curr = new Date(startDate);

  while (curr <= endDate) {
    const dStr = curr.toISOString().slice(0, 10);
    if (pointMap.has(dStr)) {
      const existing = pointMap.get(dStr)!;
      runningCum = existing.cumulativePnL ?? runningCum;
      result.push(existing);
    } else {
      result.push({
        date: dStr,
        dailyPnL: 0,
        cumulativePnL: runningCum,
        tradesCount: 0
      });
    }
    curr.setUTCDate(curr.getUTCDate() + 1);
  }

  return result;
}

export function CumulativePnLChart({ data }: CumulativePnLChartProps) {
  const continuousData = useMemo(() => {
    return interpolateCalendarTimeline(data || []);
  }, [data]);

  if (!continuousData || continuousData.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-50 dark:bg-[#12141A] rounded-2xl border border-black/[0.06] dark:border-white/10">
        <span className="text-xs text-slate-400 dark:text-zinc-400 font-medium">No trade history recorded in selected timeframe</span>
      </div>
    );
  }

  const latestVal = continuousData[continuousData.length - 1]?.cumulativePnL ?? 0;
  const isPositive = latestVal >= 0;
  const strokeColor = isPositive ? '#00D09C' : '#FF453A';
  const gradientId = `pnlGradient-${isPositive ? 'pos' : 'neg'}`;
  const glowFilterId = `revolutGlow-${isPositive ? 'pos' : 'neg'}`;

  const formatCurrency = (val: number) => {
    if (Math.abs(val) >= 1000000) return `$${(val / 1000000).toFixed(1)}M`;
    if (Math.abs(val) >= 1000) return `$${(val / 1000).toFixed(0)}k`;
    return `$${val.toFixed(0)}`;
  };

  return (
    <div className="w-full h-full text-xs outline-none focus:outline-none ring-0 focus:ring-0 [&_*]:outline-none select-none">
      <ResponsiveContainer width="100%" height="100%" className="outline-none">
        <AreaChart data={continuousData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }} className="outline-none">
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={strokeColor} stopOpacity={0.28} />
              <stop offset="70%" stopColor={strokeColor} stopOpacity={0.05} />
              <stop offset="100%" stopColor={strokeColor} stopOpacity={0.0} />
            </linearGradient>
            <filter id={glowFilterId} x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor={strokeColor} floodOpacity="0.45" />
            </filter>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
          <XAxis 
            dataKey="date" 
            stroke="#64748B" 
            tick={{ fill: '#8E8F99', fontSize: 10, fontWeight: 500 }}
            tickLine={false}
            axisLine={false}
            minTickGap={28}
            tickFormatter={(val) => {
              if (String(val).startsWith('Day')) return val;
              try {
                return formatFrenchDate(val);
              } catch {
                return String(val);
              }
            }}
          />
          <YAxis 
            stroke="#64748B" 
            tick={{ fill: '#8E8F99', fontSize: 10, fontWeight: 500 }}
            tickLine={false}
            axisLine={false}
            width={46}
            tickFormatter={formatCurrency}
            domain={['auto', 'auto']}
          />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.12)" strokeDasharray="2 2" />
          <Tooltip 
            isAnimationActive={false}
            cursor={{ stroke: 'rgba(255,255,255,0.2)', strokeWidth: 1.5, strokeDasharray: '3 3' }}
            content={({ active, payload, label }) => {
              if (active && payload && payload.length) {
                const pt = payload[0].payload as PnLPoint;
                const cum = pt.cumulativePnL ?? 0;
                const daily = pt.dailyPnL;
                return (
                  <div className="bg-[#0E1015]/95 backdrop-blur-2xl p-3.5 rounded-2xl border border-white/15 shadow-2xl text-white min-w-[170px]">
                    <div className="text-[10px] text-zinc-400 font-medium mb-1 font-mono">{label}</div>
                    <div className="text-sm font-black font-mono text-white flex items-center justify-between">
                      <span className="text-xs text-zinc-400 font-sans font-medium">Cumulative PnL:</span>
                      <span className={cum >= 0 ? 'text-[#00D09C]' : 'text-[#FF453A]'}>
                        {cum >= 0 ? '+' : '-'}${Math.abs(cum).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </div>
                    {daily !== undefined && daily !== 0 && (
                      <div className="text-xs font-semibold font-mono text-zinc-300 flex items-center justify-between mt-1.5 pt-1.5 border-t border-white/10">
                        <span className="text-[11px] text-zinc-400 font-sans font-normal">Daily Gain:</span>
                        <span className={daily >= 0 ? 'text-[#00D09C]' : 'text-[#FF453A]'}>
                          {daily >= 0 ? '+' : '-'}${Math.abs(daily).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                      </div>
                    )}
                  </div>
                );
              }
              return null;
            }}
          />
          <Area 
            type="monotone" 
            dataKey="cumulativePnL" 
            stroke={strokeColor} 
            strokeWidth={2.5}
            fillOpacity={1} 
            fill={`url(#${gradientId})`}
            filter={`url(#${glowFilterId})`}
            dot={false}
            activeDot={{ r: 5, fill: strokeColor, stroke: '#FFFFFF', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
