'use client';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

interface ScoreHistoryChartProps {
  data: { date: string; score: number }[];
}

export function ScoreHistoryChart({ data }: ScoreHistoryChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-white/5 rounded-lg border border-white/5">
        <span className="text-sm text-baleen-muted">No history yet</span>
      </div>
    );
  }

  return (
    <div className="w-full h-full text-xs">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis 
            dataKey="date" 
            stroke="#9CA3AF" 
            tick={{ fill: '#9CA3AF' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(val) => new Date(val).toLocaleDateString([], { month: 'short', day: 'numeric' })}
          />
          <YAxis 
            stroke="#9CA3AF" 
            tick={{ fill: '#9CA3AF' }}
            tickLine={false}
            axisLine={false}
            domain={['dataMin - 10', 'dataMax + 10']}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#161B22', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
            itemStyle={{ color: '#00F2FE' }}
            labelStyle={{ color: '#9CA3AF', marginBottom: '4px' }}
            labelFormatter={(val) => new Date(String(val)).toLocaleDateString()}
          />
          <Line 
            type="monotone" 
            dataKey="score" 
            stroke="#00F2FE" 
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#00F2FE', stroke: '#161B22', strokeWidth: 2 }}
            isAnimationActive={true}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
