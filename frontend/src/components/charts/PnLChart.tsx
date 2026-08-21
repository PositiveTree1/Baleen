'use client';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { formatFrenchDate } from '@/lib/formatters';

interface PnLChartProps {
  data: { date: string; pnl: number }[];
}

export function PnLChart({ data }: PnLChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-white/5 rounded-lg border border-white/5">
        <span className="text-sm text-baleen-muted">No trading history</span>
      </div>
    );
  }

  // Determine if overall is positive or negative for gradient colors
  const latestPnL = data[data.length - 1]?.pnl || 0;
  const isPositive = latestPnL >= 0;
  
  const color = isPositive ? '#10B981' : '#EF4444';

  return (
    <div className="w-full h-full text-xs">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorPnL" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3}/>
              <stop offset="95%" stopColor={color} stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis 
            dataKey="date" 
            stroke="#9CA3AF" 
            tick={{ fill: '#9CA3AF' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(val) => {
              try {
                return formatFrenchDate(val);
              } catch {
                return String(val);
              }
            }}
          />
          <YAxis 
            stroke="#9CA3AF" 
            tick={{ fill: '#9CA3AF' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(val) => `$${val}`}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#161B22', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
            itemStyle={{ color: color }}
            labelStyle={{ color: '#9CA3AF', marginBottom: '4px' }}
            labelFormatter={(val) => {
              try {
                return formatFrenchDate(String(val));
              } catch {
                return String(val);
              }
            }}
            formatter={(value: unknown) => [`$${Number(value).toFixed(2)}`, 'Cumulative P&L']}
          />
          <Area 
            type="stepAfter" 
            dataKey="pnl" 
            stroke={color} 
            fillOpacity={1} 
            fill="url(#colorPnL)" 
            isAnimationActive={true}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
