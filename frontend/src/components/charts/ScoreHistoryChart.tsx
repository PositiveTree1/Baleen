'use client';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

interface ScoreHistoryChartProps {
  data: { date: string; score: number }[];
}

export function ScoreHistoryChart({ data }: ScoreHistoryChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-zinc-50 rounded-2xl border border-black/[0.06]">
        <span className="text-xs text-zinc-400 font-medium">No score history recorded yet</span>
      </div>
    );
  }

  return (
    <div className="w-full h-full text-xs outline-none focus:outline-none ring-0 focus:ring-0 [&_*]:outline-none select-none">
      <ResponsiveContainer width="100%" height="100%" className="outline-none">
        <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }} className="outline-none">
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
          <XAxis 
            dataKey="date" 
            stroke="#94A3B8" 
            tick={{ fill: '#64748B', fontSize: 10, fontWeight: 500 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(val) => {
              try {
                const d = new Date(val);
                return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
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
            domain={['dataMin - 5', 'dataMax + 5']}
          />
          <Tooltip 
            isAnimationActive={false}
            cursor={{ stroke: '#2563EB', strokeWidth: 1.5, strokeDasharray: '3 3' }}
            contentStyle={{ 
              backgroundColor: '#FFFFFF', 
              border: '1px solid rgba(0,0,0,0.1)', 
              borderRadius: '16px',
              boxShadow: '0 10px 25px -3px rgba(0, 0, 0, 0.08)',
              padding: '8px 12px'
            }}
            itemStyle={{ color: '#0F172A', fontWeight: 600 }}
            labelStyle={{ color: '#64748B', marginBottom: '2px', fontSize: '11px' }}
            labelFormatter={(val: any) => {
              try {
                const d = new Date(String(val));
                return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
              } catch {
                return String(val);
              }
            }}
          />
          <Line 
            type="monotone" 
            dataKey="score" 
            stroke="#2563EB" 
            strokeWidth={2.5}
            dot={{ r: 3, fill: '#2563EB', stroke: '#FFFFFF', strokeWidth: 2 }}
            activeDot={{ r: 5, fill: '#2563EB', stroke: '#FFFFFF', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
