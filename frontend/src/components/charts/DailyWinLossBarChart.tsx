'use client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine, Cell } from 'recharts';
import { DailyPnLPoint } from '@/types';

interface DailyWinLossBarChartProps {
  data: DailyPnLPoint[];
}

export function DailyWinLossBarChart({ data }: DailyWinLossBarChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-50 rounded-2xl border border-black/[0.06]">
        <span className="text-xs text-slate-400 font-medium">No trade volume history recorded yet</span>
      </div>
    );
  }

  const formatCurrency = (val: number) => {
    const absVal = Math.abs(val);
    if (absVal >= 1000000) return `${val < 0 ? '-' : ''}$${(absVal / 1000000).toFixed(1)}M`;
    if (absVal >= 1000) return `${val < 0 ? '-' : ''}$${(absVal / 1000).toFixed(0)}k`;
    return `${val < 0 ? '-' : ''}$${absVal.toFixed(0)}`;
  };

  return (
    <div className="w-full h-full text-xs select-none">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }} stackOffset="sign">
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
                return new Date(val).toLocaleDateString([], { month: 'short', day: 'numeric' });
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
          />
          <ReferenceLine y={0} stroke="rgba(0,0,0,0.18)" strokeWidth={1} />
          <Tooltip 
            content={({ active, payload, label }) => {
              if (active && payload && payload.length) {
                const pt = payload[0].payload as DailyPnLPoint;
                const won = pt.wonUsd ?? Math.max(0, pt.dailyPnL);
                const lost = pt.lostUsd ?? (pt.dailyPnL < 0 ? pt.dailyPnL : 0);
                const net = pt.netPnL ?? pt.dailyPnL;
                const trades = pt.tradesCount ?? 1;

                return (
                  <div className="bg-white/95 backdrop-blur-xl p-3.5 rounded-2xl border border-black/[0.08] shadow-xl text-slate-900 min-w-[170px]">
                    <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2 flex items-center justify-between">
                      <span>{label}</span>
                      <span className="font-mono text-slate-500">{trades} trades</span>
                    </div>

                    <div className="space-y-1.5 font-mono text-xs">
                      <div className="flex items-center justify-between text-emerald-600 font-bold">
                        <span className="font-sans text-slate-500 font-medium">Won:</span>
                        <span>+${won.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                      </div>
                      <div className="flex items-center justify-between text-rose-600 font-bold">
                        <span className="font-sans text-slate-500 font-medium">Lost:</span>
                        <span>-${Math.abs(lost).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                      </div>
                      <div className="pt-1.5 border-t border-black/[0.06] flex items-center justify-between font-extrabold text-sm">
                        <span className="font-sans text-slate-700 text-xs font-semibold">Net P&L:</span>
                        <span className={net >= 0 ? 'text-emerald-600' : 'text-rose-600'}>
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
          {/* Green Winning Column on Top with Rounded Upper Corners */}
          <Bar 
            dataKey="wonUsd" 
            maxBarSize={28}
            shape={(props: any) => {
              const { x, y, width, height } = props;
              if (!height || height <= 0) return null;
              const r = Math.min(4, height / 2);
              return (
                <path
                  d={`M ${x},${y + r}
                      Q ${x},${y} ${x + r},${y}
                      L ${x + width - r},${y}
                      Q ${x + width},${y} ${x + width},${y + r}
                      L ${x + width},${y + height}
                      L ${x},${y + height}
                      Z`}
                  fill="#10B981"
                />
              );
            }}
          />
          {/* Red Losing Column on Bottom with Rounded Bottom Outer Corners */}
          <Bar 
            dataKey="lostUsd" 
            maxBarSize={28}
            shape={(props: any) => {
              const { x, y, width, height } = props;
              if (!height || height <= 0) return null;
              const r = Math.min(4, height / 2);
              return (
                <path
                  d={`M ${x},${y}
                      L ${x + width},${y}
                      L ${x + width},${y + height - r}
                      Q ${x + width},${y + height} ${x + width - r},${y + height}
                      L ${x + r},${y + height}
                      Q ${x},${y + height} ${x},${y + height - r}
                      Z`}
                  fill="#F43F5E"
                />
              );
            }}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
