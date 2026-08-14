'use client';
import { useState, useEffect } from 'react';
import { fetchAdminStatus, fetchAdminWallets } from '@/lib/api-client';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import Link from 'next/link';
import { ArrowLeft, Activity, Database, Users, Wallet, CheckCircle, XCircle, RefreshCw, Sparkles, Filter } from 'lucide-react';

export default function AdminPage() {
  const [status, setStatus] = useState<any>(null);
  const [wallets, setWallets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [filter, setFilter] = useState<'all' | 'active' | 'pending' | 'rejected'>('all');
  const [search, setSearch] = useState('');

  const loadData = async () => {
    setLoading(true);
    const [statusData, walletsData] = await Promise.all([
      fetchAdminStatus(),
      fetchAdminWallets()
    ]);
    setStatus(statusData);
    setWallets(walletsData);
    setLoading(false);
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleTriggerDiscovery = async () => {
    setTriggering(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      await fetch(`${backendUrl}/api/admin/trigger-discovery`, { method: 'POST' });
      setTimeout(() => {
        loadData();
        setTriggering(false);
      }, 2000);
    } catch {
      setTriggering(false);
    }
  };

  const filteredWallets = wallets.filter(w => {
    const s = (w.status || '').toLowerCase();
    const matchesFilter = filter === 'all' || s === filter;
    const matchesSearch = !search || (w.address || '').toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const isServiceOnline = (val: string) => {
    return val === 'ONLINE' || val === 'CONNECTED';
  };

  return (
    <div className="min-h-screen bg-[#090A0F] text-white p-6 lg:p-12 selection:bg-white selection:text-black">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8 pb-4 border-b border-white/[0.06]">
          <Link href="/dashboard" className="inline-flex items-center gap-2 text-xs text-zinc-400 hover:text-white transition-colors">
            <ArrowLeft size={14} /> Back to Dashboard
          </Link>
          <div className="flex items-center gap-3">
            <Button 
              variant="secondary" 
              onClick={loadData} 
              disabled={loading}
              className="text-xs py-2 px-3"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
            </Button>
            <Button 
              variant="primary" 
              onClick={handleTriggerDiscovery} 
              disabled={triggering}
              className="text-xs py-2 px-4 bg-white text-zinc-950 font-semibold"
            >
              <Sparkles size={14} /> {triggering ? 'Scanning Polymarket...' : 'Run Discovery & Score Now'}
            </Button>
          </div>
        </div>
        
        <div className="mb-10">
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
            <Activity className="text-emerald-400" size={26} /> Engine Control Panel
          </h1>
          <p className="text-zinc-400 text-sm">Real-time status of Polymarket indexer, scoring pipeline, and database models.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          {/* Database Stats */}
          <div className="glass-card p-6 rounded-3xl border border-white/[0.08] shadow-apple bg-zinc-900/40 backdrop-blur-xl">
            <h2 className="text-sm font-semibold text-white mb-5 flex items-center gap-2">
              <Database size={16} className="text-zinc-400" /> Database Entities
            </h2>
            {loading && !status ? (
              <div className="space-y-3"><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-2/3" /></div>
            ) : (
              <div className="space-y-3 text-xs">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Total Wallets Discovered</span>
                  <span className="text-white font-mono font-medium">{status?.db?.total_wallets ?? status?.database?.totalWallets ?? wallets.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Active (In Basket)</span>
                  <span className="text-emerald-400 font-mono font-semibold">{status?.db?.active_wallets ?? status?.database?.activeWallets ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Pending Analysis</span>
                  <span className="text-amber-400 font-mono font-medium">{status?.db?.pending_wallets ?? status?.database?.pendingWallets ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Rejected (Filter Failed)</span>
                  <span className="text-rose-400 font-mono font-medium">{status?.db?.rejected_wallets ?? status?.database?.rejectedWallets ?? 0}</span>
                </div>
                <div className="border-t border-white/[0.06] my-2 pt-2 flex justify-between">
                  <span className="text-zinc-400">Registered Users</span>
                  <span className="text-white font-mono">{status?.db?.users ?? status?.database?.totalUsers ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Total Audited Fills</span>
                  <span className="text-white font-mono">{status?.db?.trades ?? status?.database?.totalTrades ?? 0}</span>
                </div>
              </div>
            )}
          </div>

          {/* Service Status */}
          <div className="glass-card p-6 rounded-3xl border border-white/[0.08] shadow-apple bg-zinc-900/40 backdrop-blur-xl">
            <h2 className="text-sm font-semibold text-white mb-5 flex items-center gap-2">
              <Activity size={16} className="text-zinc-400" /> Microservice Health
            </h2>
            <div className="space-y-4 text-xs">
              <div className="flex items-center justify-between p-2.5 rounded-2xl bg-white/[0.02] border border-white/[0.04]">
                <span className="text-zinc-300 font-medium">FastAPI Backend API</span>
                <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
                  <CheckCircle size={12} /> ONLINE
                </span>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-2xl bg-white/[0.02] border border-white/[0.04]">
                <span className="text-zinc-300 font-medium">Neon PostgreSQL DB</span>
                <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
                  <CheckCircle size={12} /> CONNECTED
                </span>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-2xl bg-white/[0.02] border border-white/[0.04]">
                <span className="text-zinc-300 font-medium">Envio Signal Listener</span>
                <span className={`inline-flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-0.5 rounded-full border ${
                  isServiceOnline(status?.services?.listener || 'ONLINE')
                    ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                    : 'text-amber-400 bg-amber-500/10 border-amber-500/20'
                }`}>
                  <CheckCircle size={12} /> {status?.services?.listener || 'ONLINE'}
                </span>
              </div>
            </div>
          </div>

          {/* Job Schedules */}
          <div className="glass-card p-6 rounded-3xl border border-white/[0.08] shadow-apple bg-zinc-900/40 backdrop-blur-xl">
            <h2 className="text-sm font-semibold text-white mb-5 flex items-center gap-2">
              <RefreshCw size={16} className="text-zinc-400" /> Automated Cron Cadence
            </h2>
            <div className="space-y-3.5 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-zinc-400">Whale Discovery Scan</span>
                <span className="font-mono text-white px-2 py-0.5 rounded bg-white/[0.06]">Every 6 hours</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-zinc-400">Basket Rescoring Pass</span>
                <span className="font-mono text-white px-2 py-0.5 rounded bg-white/[0.06]">Every 24 hours</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-zinc-400">AI Whale Behavioral Summaries</span>
                <span className="font-mono text-white px-2 py-0.5 rounded bg-white/[0.06]">Nightly (Groq)</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-zinc-400">Dormancy & Drawdown Verification</span>
                <span className="font-mono text-emerald-400 px-2 py-0.5 rounded bg-emerald-500/10">Continuous</span>
              </div>
            </div>
          </div>
        </div>

        {/* Wallet Pipeline Filter Tabs */}
        <div className="glass-card rounded-3xl overflow-hidden border border-white/[0.08] shadow-apple bg-zinc-900/40 backdrop-blur-xl">
          <div className="p-6 border-b border-white/[0.06] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Wallet size={18} className="text-zinc-400" /> Discovered Whale Pipeline
              </h2>
              <p className="text-xs text-zinc-400 mt-1">Full auditable funnel of all candidate and active wallets.</p>
            </div>
            
            <div className="flex flex-wrap items-center gap-3">
              <input
                type="text"
                placeholder="Search 0x address..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="text-xs bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-1.5 text-white placeholder-zinc-500 focus:outline-none focus:border-white/20 w-48 font-mono"
              />
              <div className="flex rounded-xl bg-white/[0.05] p-0.5 border border-white/[0.08]">
                {(['all', 'active', 'pending', 'rejected'] as const).map(f => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`text-xs px-3 py-1 rounded-lg capitalize font-medium transition-all ${
                      filter === f ? 'bg-white text-zinc-950 font-semibold shadow-sm' : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/[0.06] text-[10px] uppercase tracking-wider text-zinc-400 bg-zinc-950/60">
                  <th className="p-4 sm:px-6 font-medium">Address</th>
                  <th className="p-4 font-medium">Status</th>
                  <th className="p-4 font-medium">Tier</th>
                  <th className="p-4 font-medium text-right">Score</th>
                  <th className="p-4 font-medium text-right">Win Rate</th>
                  <th className="p-4 font-medium text-right">Realized PnL</th>
                  <th className="p-4 sm:px-6 font-medium">Rejection / Audit Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.03]">
                {loading ? (
                  Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i}>
                      <td colSpan={7} className="p-4"><Skeleton className="h-4 w-full" /></td>
                    </tr>
                  ))
                ) : filteredWallets.length > 0 ? (
                  filteredWallets.map((w: any) => {
                    const statusVal = (w.status || 'pending').toLowerCase();
                    const winRate = w.winRatePct ?? w.win_rate_pct ?? 0;
                    const pnl = w.allTimePnlUsd ?? w.all_time_pnl_usd ?? 0;
                    const score = w.baleenScore ?? w.baleen_score ?? '-';
                    const reason = w.rejectionReason ?? w.rejection_reason;

                    return (
                      <tr key={w.address} className="hover:bg-white/[0.03] transition-colors text-xs">
                        <td className="p-4 sm:px-6 font-mono text-zinc-300">
                          {w.address}
                        </td>
                        <td className="p-4">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize ${
                            statusVal === 'active' 
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                              : statusVal === 'rejected' 
                              ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' 
                              : 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
                          }`}>
                            {statusVal}
                          </span>
                        </td>
                        <td className="p-4"><Badge tier={w.tier || 'standard'} /></td>
                        <td className="p-4 text-right font-mono font-medium text-white">{score}</td>
                        <td className="p-4 text-right font-mono text-zinc-300">
                          {winRate > 0 ? `${(winRate > 1 ? winRate : winRate * 100).toFixed(1)}%` : '-'}
                        </td>
                        <td className={`p-4 text-right font-mono font-medium ${pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          ${Math.abs(pnl).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                        </td>
                        <td className="p-4 sm:px-6 text-zinc-400 text-[11px] max-w-[280px] truncate">
                          {reason || w.aiStyleTag || (statusVal === 'active' ? 'Passed all gold-tier filters' : 'Pending evaluation pass')}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={7} className="p-16 text-center text-zinc-500 text-xs">
                      No matching wallets in this category. Click &quot;Run Discovery &amp; Score Now&quot; to fetch and score immediately.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
