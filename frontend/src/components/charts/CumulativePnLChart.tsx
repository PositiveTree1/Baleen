'use client';
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

export function CumulativePnLChart({ data }: CumulativePnLChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-50 dark:bg-[#1C1D22] rounded-2xl border border-black/[0.06] dark:border-white/10">
        <span className="text-xs text-slate-400 dark:text-zinc-400 font-medium">No trade history recorded in selected timeframe</span>
      </div>
    );
  }

  const latestVal = data[data.length - 1]?.cumulativePnL ?? 0;
  const isPositive = latestVal >= 0;
  const strokeColor = isPositive ? '#10B981' : '#F43F5E';
  const gradientId = `pnlGradient-${isPositive ? 'pos' : 'neg'}`;

  const formatCurrency = (val: number) => {
    if (Math.abs(val) >= 1000000) return `$${(val / 1000000).toFixed(1)}M`;
    if (Math.abs(val) >= 1000) return `$${(val / 1000).toFixed(0)}k`;
    return `$${val.toFixed(0)}`;
  };

  return (
    <div className="w-full h-full text-xs outline-none focus:outline-none ring-0 focus:ring-0 [&_*]:outline-none select-none">
      <ResponsiveContainer width="100%" height="100%" className="outline-none">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }} className="outline-none">
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={strokeColor} stopOpacity={0.25} />
              <stop offset="95%" stopColor={strokeColor} stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.05)" vertical={false} />
          <XAxis 
            dataKey="date" 
            stroke="#94A3B8" 
            tick={{ fill: '#64748B', fontSize: 10, fontWeight: 500 }}
            tickLine={false}
            axisLine={false}
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
            stroke="#94A3B8" 
            tick={{ fill: '#64748B', fontSize: 10, fontWeight: 500 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={formatCurrency}
            domain={['auto', 'auto']}
          />
          <ReferenceLine y={0} stroke="rgba(0,0,0,0.12)" strokeDasharray="2 2" />
          <Tooltip 
            isAnimationActive={false}
            cursor={{ stroke: '#6366F1', strokeWidth: 1.5, strokeDasharray: '3 3' }}
            content={({ active, payload, label }) => {
              if (active && payload && payload.length) {
                const pt = payload[0].payload as PnLPoint;
                const cum = pt.cumulativePnL ?? 0;
                const daily = pt.dailyPnL;
                return (
                  <div className="bg-white/95 dark:bg-[#1C1D22]/95 backdrop-blur-xl p-3 rounded-2xl border border-black/[0.08] dark:border-white/10 shadow-xl text-slate-900 dark:text-white min-w-[150px]">
                    <div className="text-[10px] text-slate-400 dark:text-[#8E8F99] font-medium mb-1">{label}</div>
                    <div className="text-sm font-bold font-mono text-slate-950 dark:text-white flex items-center justify-between">
                      <span className="text-xs text-slate-500 dark:text-[#8E8F99] font-sans font-medium">Cumulative PnL:</span>
                      <span className={cum >= 0 ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}>
                        {cum >= 0 ? '+' : '-'}${Math.abs(cum).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </div>
                    {daily !== undefined && (
                      <div className="text-xs font-semibold font-mono text-slate-600 dark:text-slate-300 flex items-center justify-between mt-1 pt-1 border-t border-black/[0.04] dark:border-white/10">
                        <span className="text-[11px] text-slate-400 dark:text-[#8E8F99] font-sans font-normal">Daily Gain:</span>
                        <span className={daily >= 0 ? 'text-emerald-600 dark:text-[#00D09C]' : 'text-rose-600 dark:text-[#FF453A]'}>
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
            dot={false}
            activeDot={{ r: 5, fill: strokeColor, stroke: '#FFFFFF', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
