'use client';
import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from 'recharts';
import { DailyPnLPoint } from '@/types';
import { formatFrenchDate } from '@/lib/formatters';

interface DailyWinLossBarChartProps {
  data: DailyPnLPoint[];
}

export function DailyWinLossBarChart({ data }: DailyWinLossBarChartProps) {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];
    return data.filter(pt => pt.dailyChangeKnown !== false).map(pt => {
      const daily = pt.dailyPnL ?? pt.netPnL ?? 0;
      const won = pt.wonUsd != null ? pt.wonUsd : Math.max(0, daily);
      const lost = pt.lostUsd != null ? (pt.lostUsd > 0 ? -pt.lostUsd : pt.lostUsd) : Math.min(0, daily);
      return {
        ...pt,
        wonUsd: won,
        lostUsd: lost,
        netPnL: pt.netPnL ?? daily
      };
    });
  }, [data]);

  if (!data || data.length === 0 || chartData.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-white/[0.03] rounded-2xl border border-white/10">
        <span className="text-xs text-white/50 font-medium">No trade history recorded in selected timeframe</span>
      </div>
    );
  }

  const formatCurrency = (val: number) => {
    const absVal = Math.abs(val);
    if (absVal >= 1000000) return `${val < 0 ? '-' : ''}$${(absVal / 1000000).toFixed(1)}M`;
    if (absVal >= 1000) return `${val < 0 ? '-' : ''}$${(absVal / 1000).toFixed(0)}k`;
    return `${val < 0 ? '-' : ''}$${absVal.toFixed(0)}`;
  };

  const calculatedMaxBar = chartData.length > 80 ? 6 : chartData.length > 40 ? 10 : 18;

  return (
    <div className="w-full h-full text-xs select-none outline-none focus:outline-none ring-0 focus:ring-0 [&_*]:outline-none">
      <ResponsiveContainer width="100%" height="100%" className="outline-none">
        <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }} stackOffset="sign" className="outline-none">
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis 
            dataKey="date" 
            stroke="rgba(255,255,255,0.2)" 
            tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10, fontWeight: 500 }}
            tickLine={false}
            axisLine={false}
            minTickGap={20}
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
            stroke="rgba(255,255,255,0.2)" 
            tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10, fontWeight: 500 }}
            tickLine={false}
            axisLine={false}
            width={46}
            tickFormatter={formatCurrency}
          />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.2)" strokeWidth={1} />
          <Tooltip 
            isAnimationActive={false}
            cursor={{ fill: 'rgba(255, 255, 255, 0.06)' }}
            content={({ active, payload, label }) => {
              if (active && payload && payload.length) {
                const pt = payload[0].payload as DailyPnLPoint;
                const won = pt.wonUsd ?? Math.max(0, pt.dailyPnL);
                const lost = pt.lostUsd ?? (pt.dailyPnL < 0 ? pt.dailyPnL : 0);
                const net = pt.netPnL ?? pt.dailyPnL;
                const trades = pt.tradesCount ?? 1;

                return (
                  <div className="glass-card p-3.5 rounded-2xl border border-white/20 shadow-2xl text-white min-w-[170px] backdrop-blur-2xl">
                    <div className="text-[10px] text-white/50 font-bold uppercase tracking-wider mb-2 flex items-center justify-between">
                      <span>{label}</span>
                      <span className="font-mono text-white/70">{trades} trades</span>
                    </div>

                    <div className="space-y-1.5 font-mono text-xs">
                      <div className="flex items-center justify-between text-[#00D09C] font-bold">
                        <span className="font-sans text-white/60 font-medium">Increase:</span>
                        <span>+${won.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                      </div>
                      <div className="flex items-center justify-between text-[#FF453A] font-bold">
                        <span className="font-sans text-white/60 font-medium">Decrease:</span>
                        <span>-${Math.abs(lost).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                      </div>
                      <div className="pt-1.5 border-t border-white/10 flex items-center justify-between font-extrabold text-sm">
                        <span className="font-sans text-white/80 text-xs font-semibold">Net P&L:</span>
                        <span className={net >= 0 ? 'text-[#00D09C]' : 'text-[#FF453A]'}>
                          {net >= 0 ? '+' : '-'}${Math.abs(net).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              }
              return null;
            }}
          />
          <Bar 
            dataKey="wonUsd" 
            name="P&L increase"
            fill="#00D09C" 
            maxBarSize={calculatedMaxBar}
            radius={[3, 3, 0, 0]}
            isAnimationActive={false}
          />
          <Bar 
            dataKey="lostUsd" 
            name="P&L decrease"
            fill="#FF453A" 
            maxBarSize={calculatedMaxBar}
            radius={[0, 0, 3, 3]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
