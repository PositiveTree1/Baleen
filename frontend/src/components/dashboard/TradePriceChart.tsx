'use client';
import { useEffect, useState } from 'react';
import { fetchTradePriceChart } from '@/lib/api-client';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, ReferenceLine } from 'recharts';
import { Skeleton } from '../ui/Skeleton';
import { TrendingUp, TrendingDown, Clock, Activity, ExternalLink } from 'lucide-react';

interface TradePriceChartProps {
  tradeId: string;
  fillPrice: number;
  currentPrice: number;
  side: string;
}

export function TradePriceChart({ tradeId, fillPrice, currentPrice, side }: TradePriceChartProps) {
  const [data, setData] = useState<{
    history: { timestamp: number; date: string; price: number }[];
    minPrice: number;
    maxPrice: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      const chartData = await fetchTradePriceChart(tradeId);
      if (mounted && chartData) {
        setData(chartData);
      }
      if (mounted) setLoading(false);
    }
    load();
    return () => {
      mounted = false;
    };
  }, [tradeId]);

  const isProfitable = side === 'BUY' ? currentPrice >= fillPrice : currentPrice <= fillPrice;
  const strokeColor = isProfitable ? '#10B981' : '#F43F5E';
  const fillColor = isProfitable ? '#10B981' : '#F43F5E';
  const priceMovePct = fillPrice > 0 ? ((currentPrice - fillPrice) / fillPrice) * 100 * (side === 'BUY' ? 1 : -1) : 0;

  if (loading) {
    return (
      <div className="p-4 rounded-2xl bg-slate-50 border border-black/[0.06] space-y-3">
        <div className="flex justify-between items-center">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 w-16" />
        </div>
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    );
  }

  const history = data?.history || [];
  const minP = Math.max(0.0, Math.min(...history.map(h => h.price), fillPrice, currentPrice) - 0.05);
  const maxP = Math.min(1.0, Math.max(...history.map(h => h.price), fillPrice, currentPrice) + 0.05);

  return (
    <div className="p-4 rounded-2xl bg-slate-50 border border-black/[0.06] space-y-3 shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity size={14} className="text-indigo-600" />
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-700">
            Polymarket CLOB Price Curve
          </span>
        </div>
        <div className="flex items-center gap-1.5 font-mono text-xs font-bold">
          <span className={isProfitable ? 'text-emerald-700' : 'text-rose-700'}>
            {isProfitable ? '+' : ''}{priceMovePct.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Chart Area */}
      <div className="h-44 w-full">
        {history.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
              <defs>
                <linearGradient id={`gradient-${tradeId}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={fillColor} stopOpacity={0.35} />
                  <stop offset="95%" stopColor={fillColor} stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 9, fill: '#94A3B8' }} 
                axisLine={false} 
                tickLine={false} 
                interval="preserveStartEnd"
              />
              <YAxis 
                domain={[minP, maxP]} 
                tick={{ fontSize: 9, fill: '#94A3B8' }} 
                axisLine={false} 
                tickLine={false}
                tickFormatter={(val) => `$${val.toFixed(2)}`}
              />
              <Tooltip 
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const pt = payload[0].payload;
                    return (
                      <div className="bg-slate-950 text-white px-3 py-2 rounded-xl text-xs font-mono shadow-xl border border-white/10">
                        <div className="text-[10px] text-slate-400">{pt.date}</div>
                        <div className="font-bold text-sm text-emerald-400">${pt.price.toFixed(3)}</div>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <ReferenceLine 
                y={fillPrice} 
                stroke="#6366F1" 
                strokeDasharray="3 3" 
                label={{ 
                  value: `Entry: $${fillPrice.toFixed(3)}`, 
                  position: 'right', 
                  fill: '#4F46E5', 
                  fontSize: 9,
                  fontWeight: 'bold'
                }} 
              />
              <Area 
                type="monotone" 
                dataKey="price" 
                stroke={strokeColor} 
                strokeWidth={2}
                fillOpacity={1} 
                fill={`url(#gradient-${tradeId})`} 
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-xs text-slate-400 font-mono">
            Real-time trajectory compiling from Polymarket CLOB...
          </div>
        )}
      </div>

      <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-1 border-t border-black/[0.04]">
        <span>Dashed line: <strong>Whale Entry Fill (${fillPrice.toFixed(3)})</strong></span>
        <span>Latest: <strong>${currentPrice.toFixed(3)}</strong></span>
      </div>
    </div>
  );
}
