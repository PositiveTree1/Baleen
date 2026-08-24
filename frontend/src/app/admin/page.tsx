'use client';
import { useState, useEffect } from 'react';
import { fetchAdminStatus, fetchAdminWallets, getCachedAdminStatus, getCachedAdminWallets, reEvaluateWallets, purgeAndRescanWallets, fetchDiscoveryProgress } from '@/lib/api-client';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { BrandLogo } from '@/components/ui/BrandLogo';
import Link from 'next/link';
import { ArrowLeft, Activity, Database, Users, Wallet, CheckCircle, AlertTriangle, RefreshCw, Sparkles, Filter, RotateCw, Trash2, Search, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function AdminPage() {
  const [status, setStatus] = useState<any>(() => getCachedAdminStatus() || null);
  const [wallets, setWallets] = useState<any[]>(() => getCachedAdminWallets() || []);
  const [initialLoading, setInitialLoading] = useState(() => !getCachedAdminStatus());
  const [justRefreshed, setJustRefreshed] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [progress, setProgress] = useState<any>(null);
  const [filter, setFilter] = useState<'all' | 'active' | 'pending' | 'rejected'>('all');
  const [search, setSearch] = useState('');

  const loadData = async (isManual = false) => {
    try {
      const [statusData, walletsData] = await Promise.all([
        fetchAdminStatus(),
        fetchAdminWallets()
      ]);
      setStatus(statusData);
      setWallets(walletsData);
      
      if (statusData?.discovery_state?.status === 'running') {
        setProgress(statusData.discovery_state);
        setEvaluating(true);
      } else if (statusData?.discovery_state?.status === 'completed' && evaluating) {
        setEvaluating(false);
        setProgress(null);
      }
      
      setJustRefreshed(true);
      setTimeout(() => setJustRefreshed(false), 900);
    } catch (e) {
      console.error("Admin refresh error:", e);
    } finally {
      setInitialLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(() => loadData(false), 5000);
    return () => clearInterval(interval);
  }, []);

  const startProgressPolling = () => {
    const pInterval = setInterval(async () => {
      const prog = await fetchDiscoveryProgress();
      if (prog) {
        setProgress(prog);
        if (prog.status === 'completed' || prog.status === 'error' || prog.status === 'interrupted') {
          clearInterval(pInterval);
          setTimeout(() => {
            setEvaluating(false);
            setProgress(null);
            loadData();
          }, 1000);
        }
      }
    }, 800);
  };

  const handleReevaluate = async () => {
    setEvaluating(true);
    try {
      await reEvaluateWallets();
      startProgressPolling();
    } catch {
      setEvaluating(false);
    }
  };

  const handlePurgeAndRescan = async () => {
    if (!confirm("Are you sure you want to PURGE all database records and start scraping Polymarket fresh from scratch?")) {
      return;
    }
    setEvaluating(true);
    try {
      await purgeAndRescanWallets();
      startProgressPolling();
    } catch {
      setEvaluating(false);
    }
  };

  const [wipingAll, setWipingAll] = useState(false);
  const handleHardWipeAll = async () => {
    const confirmation = prompt("⚠️ FACTORY RESET: Type 'RESET' to permanently delete all wallets, execution logs, snapshots, and restore clean $10k sandbox balances:");
    if (confirmation !== 'RESET') {
      if (confirmation !== null) alert("Reset cancelled. You must type 'RESET' exactly.");
      return;
    }
    setWipingAll(true);
    try {
      const { hardWipeAllDatabase } = await import('@/lib/api-client');
      await hardWipeAllDatabase();
      alert("✅ Complete factory reset successful! All database tables wiped.");
      window.location.reload();
    } catch (e) {
      alert("Error executing wipeout: " + String(e));
    } finally {
      setWipingAll(false);
    }
  };

  const handleTriggerDiscovery = async () => {
    setTriggering(true);
    try {
      const backendUrl = (
        process.env.NEXT_PUBLIC_BACKEND_URL || 
        process.env.NEXT_PUBLIC_API_URL || 
        'http://localhost:8000'
      ).replace(/\/$/, '');
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

  const formatUptime = (seconds: number) => {
    if (!seconds) return '0s';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  };

  const formatCronTime = (timestamp: number | null) => {
    if (!timestamp) return 'Waiting for ping...';
    const secondsAgo = Math.floor(Date.now() / 1000 - timestamp);
    if (secondsAgo < 60) return 'Just now';
    return `${Math.floor(secondsAgo / 60)}m ago`;
  };

  const dbType = status?.database?.type || (status?.database?.using_sqlite_fallback ? 'SQLite (Local Failover)' : 'Supabase PostgreSQL');
  const isPostgres = !status?.database?.using_sqlite_fallback && !dbType.includes('SQLite');

  return (
    <div className="min-h-screen bg-[#F8F9FB] text-slate-900 p-6 lg:p-12 selection:bg-slate-900 selection:text-white">
      <div className="max-w-7xl mx-auto">
        {/* Top Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8 pb-4 border-b border-black/[0.06]">
          <div className="flex items-center gap-4">
            <BrandLogo size="sm" subtitle="Admin Console" />
            <span className="text-slate-300">|</span>
            <Link href="/dashboard" className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors">
              <ArrowLeft size={14} /> Back to Dashboard
            </Link>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <Button 
              variant="secondary" 
              onClick={() => loadData(true)} 
              disabled={initialLoading || justRefreshed || wipingAll}
              className="text-xs py-2 px-3 shadow-sm"
            >
              <RefreshCw size={14} className={justRefreshed ? 'animate-spin text-indigo-600' : ''} /> Refresh
            </Button>
            <Button 
              variant="secondary" 
              onClick={handleReevaluate} 
              disabled={evaluating || wipingAll}
              className="text-xs py-2 px-3.5 shadow-sm border-indigo-200 text-indigo-900 bg-indigo-50/50 hover:bg-indigo-100/60 font-semibold"
            >
              <RotateCw size={14} className={evaluating ? 'animate-spin text-indigo-600' : 'text-indigo-600'} /> 
              {evaluating ? 'Evaluating...' : 'Re-evaluate All'}
            </Button>
            <Button 
              variant="danger" 
              onClick={handlePurgeAndRescan} 
              disabled={evaluating || wipingAll}
              className="text-xs py-2 px-3.5 shadow-sm border border-rose-200 text-rose-700 bg-rose-50 hover:bg-rose-100 font-semibold"
            >
              <Trash2 size={14} /> Purge &amp; Rescan
            </Button>
            <Button 
              variant="danger" 
              onClick={handleHardWipeAll} 
              disabled={wipingAll || evaluating}
              className="text-xs py-2 px-3.5 shadow-sm bg-rose-600 hover:bg-rose-700 text-white font-bold"
              title="Completely wipe all database tables and reset system"
            >
              <Trash2 size={14} /> {wipingAll ? 'Wiping...' : 'Factory Reset DB'}
            </Button>
            <Button 
              variant="primary" 
              onClick={handleTriggerDiscovery} 
              disabled={triggering || evaluating || wipingAll}
              className="text-xs py-2 px-4 font-semibold"
            >
              <Sparkles size={14} /> {triggering ? 'Scanning...' : 'Discovery Scan'}
            </Button>
          </div>
        </div>

        {/* Live Discovery Progress Bar */}
        <AnimatePresence>
          {evaluating && progress && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-8 p-5 bg-white border border-indigo-200 rounded-3xl shadow-[0_4px_20px_rgba(99,102,241,0.12)]"
            >
              <div className="flex justify-between items-center mb-2.5">
                <div className="flex items-center gap-2">
                  <RotateCw size={16} className="text-indigo-600 animate-spin" />
                  <span className="text-sm font-bold text-slate-900">
                    {progress.step_description || 'Scraping and auditing Polymarket wallets...'}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-slate-500">
                    {progress.wallets_scanned} scanned • {progress.gold_snipers || 0} Gold Snipers
                  </span>
                  <span className="text-xs font-mono font-bold text-indigo-600 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200">
                    {progress.progress_pct || 0}%
                  </span>
                </div>
              </div>
              <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-indigo-600 rounded-full transition-all duration-300"
                  style={{ width: `${progress.progress_pct || 5}%` }}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        
        <div className="mb-10">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-2 flex items-center gap-3">
            <Activity className="text-slate-900" size={26} /> Engine Control Plane
          </h1>
          <p className="text-slate-600 text-sm">Real-time status of Polymarket indexer, Supabase database models, and scoring workers.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          {/* Database Entities */}
          <div className="p-6 rounded-3xl border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_12px_28px_-4px_rgba(0,0,0,0.05)] bg-white">
            <h2 className="text-sm font-bold text-slate-900 mb-5 flex items-center gap-2">
              <Database size={16} className="text-slate-600" /> Database Entities
            </h2>
            {initialLoading && !status ? (
              <div className="space-y-3"><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-2/3" /></div>
            ) : (
              <div className="space-y-3 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-600 font-medium">Total Wallets Discovered</span>
                  <span className="text-slate-900 font-mono font-bold">{status?.db_stats?.total ?? wallets.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600 font-medium">Active (In Basket)</span>
                  <span className="text-emerald-600 font-mono font-bold">{status?.db_stats?.active ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600 font-medium">Pending Analysis</span>
                  <span className="text-amber-600 font-mono font-bold">{status?.db_stats?.pending ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600 font-medium">Rejected (Failed Rules)</span>
                  <span className="text-rose-600 font-mono font-bold">{status?.db_stats?.rejected ?? 0}</span>
                </div>
                <div className="border-t border-black/[0.06] my-2 pt-2 flex justify-between">
                  <span className="text-slate-600 font-medium">Registered Users</span>
                  <span className="text-slate-900 font-mono font-bold">{status?.database?.totalUsers ?? status?.db?.users ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-600 font-medium">Total Executions Tape</span>
                  <span className="text-slate-900 font-mono font-bold">{status?.database?.totalTrades ?? status?.db?.trades ?? 0}</span>
                </div>
              </div>
            )}
          </div>

          {/* Microservice Health */}
          <div className="p-6 rounded-3xl border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_12px_28px_-4px_rgba(0,0,0,0.05)] bg-white">
            <h2 className="text-sm font-bold text-slate-900 mb-5 flex items-center gap-2">
              <Activity size={16} className="text-slate-600" /> Storage &amp; Infrastructure
            </h2>
            <div className="space-y-3.5 text-xs">
              <div className="flex items-center justify-between p-3 rounded-2xl bg-slate-50 border border-black/[0.04]">
                <span className="text-slate-800 font-semibold">Backend Engine</span>
                <span className="inline-flex items-center gap-1 text-[11px] font-mono font-bold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                  <CheckCircle size={12} /> ONLINE
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-2xl bg-slate-50 border border-black/[0.04]">
                <span className="text-slate-800 font-semibold">Database Engine</span>
                <span className={`inline-flex items-center gap-1 text-[11px] font-mono font-bold px-2.5 py-0.5 rounded-full border ${
                  isPostgres
                    ? 'text-emerald-800 bg-emerald-50 border-emerald-200' 
                    : 'text-amber-800 bg-amber-50 border-amber-200'
                }`}>
                  {isPostgres ? <CheckCircle size={12} /> : <AlertTriangle size={12} />}
                  {isPostgres ? 'Supabase Postgres' : 'SQLite Failover'}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-2xl bg-slate-50 border border-black/[0.04]">
                <span className="text-slate-800 font-semibold">Server Uptime</span>
                <span className="font-mono font-bold text-slate-700 bg-white px-2.5 py-0.5 rounded-full border shadow-sm">
                  {formatUptime(status?.uptime_seconds || 0)}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-2xl bg-slate-50 border border-black/[0.04]">
                <span className="text-slate-800 font-semibold">Keep-Alive Heartbeat</span>
                <span className="font-mono font-bold text-slate-700 bg-white px-2.5 py-0.5 rounded-full border shadow-sm">
                  {formatCronTime(status?.last_cron_ping)}
                </span>
              </div>
            </div>
          </div>

          {/* Job Schedules */}
          <div className="p-6 rounded-3xl border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_12px_28px_-4px_rgba(0,0,0,0.05)] bg-white">
            <h2 className="text-sm font-bold text-slate-900 mb-5 flex items-center gap-2">
              <RefreshCw size={16} className="text-slate-600" /> Continuous Pipeline
            </h2>
            <div className="space-y-3.5 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-600 font-medium">Whale Discovery Scan</span>
                <span className="font-mono text-slate-900 font-bold px-2 py-0.5 rounded bg-slate-100 border border-black/[0.04]">Every 20 minutes</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-600 font-medium">Mark-to-Market Valuation</span>
                <span className="font-mono text-slate-900 font-bold px-2 py-0.5 rounded bg-slate-100 border border-black/[0.04]">Every 25 seconds</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-600 font-medium">AI Behavioral Analysis</span>
                <span className="font-mono text-slate-900 font-bold px-2 py-0.5 rounded bg-slate-100 border border-black/[0.04]">Nightly (Groq Llama-3.1)</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-600 font-medium">Render Idle Keep-Alive</span>
                <span className="font-mono text-emerald-800 font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 border border-emerald-200">5m Ping Cadence</span>
              </div>
            </div>
          </div>
        </div>

        {/* Whale Pipeline Table */}
        <div className={`rounded-3xl overflow-hidden border transition-all duration-700 bg-white ${
          justRefreshed 
            ? 'border-indigo-400/80 shadow-[0_0_24px_rgba(99,102,241,0.16)] ring-1 ring-indigo-300/50' 
            : 'border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_16px_36px_-6px_rgba(0,0,0,0.05)]'
        }`}>
          <div className="p-6 border-b border-black/[0.06] flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50/50">
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Wallet size={18} className="text-slate-700" /> Discovered Whale Pipeline
                </h2>
                {justRefreshed && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-200 animate-pulse">
                    Synced
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-1">Full auditable funnel of all candidate and active wallets.</p>
            </div>
            
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search 0x address..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="text-xs bg-white border border-black/[0.1] rounded-xl pl-8 pr-3 py-2 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-slate-400 shadow-sm w-48 font-mono"
                />
              </div>
              <div className="flex rounded-xl bg-slate-100 p-1 border border-black/[0.06]">
                {(['all', 'active', 'pending', 'rejected'] as const).map(f => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`text-xs px-3 py-1.5 rounded-lg capitalize font-semibold transition-all cursor-pointer ${
                      filter === f ? 'bg-white text-slate-900 shadow-sm border border-black/[0.04]' : 'text-slate-500 hover:text-slate-900'
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
                <tr className="border-b border-black/[0.06] text-[10px] uppercase tracking-wider text-slate-500 bg-slate-50/90 font-semibold">
                  <th className="p-4 sm:px-6 font-semibold">Address</th>
                  <th className="p-4 font-semibold">Status</th>
                  <th className="p-4 font-semibold">Tier</th>
                  <th className="p-4 font-semibold text-right">Score</th>
                  <th className="p-4 font-semibold text-right">Win Rate</th>
                  <th className="p-4 font-semibold text-right">Realized PnL</th>
                  <th className="p-4 sm:px-6 font-semibold">Rejection / Audit Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-black/[0.04]">
                {initialLoading && wallets.length === 0 ? (
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
                      <tr key={w.address} className="hover:bg-slate-50/80 transition-colors text-xs">
                        <td className="p-4 sm:px-6 font-mono text-slate-800 font-semibold">
                          <a 
                            href={`https://polymarket.com/profile/${w.address}`}
                            target="_blank"
                            rel="noreferrer"
                            className="hover:text-indigo-600 transition-colors inline-flex items-center gap-1"
                          >
                            <span>{w.address.slice(0, 8)}...{w.address.slice(-6)}</span>
                            <ExternalLink size={11} className="opacity-40" />
                          </a>
                        </td>
                        <td className="p-4">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold capitalize border shadow-sm ${
                            statusVal === 'active' 
                              ? 'bg-emerald-50 text-emerald-800 border-emerald-200' 
                              : statusVal === 'rejected' 
                              ? 'bg-rose-50 text-rose-800 border-rose-200' 
                              : 'bg-amber-50 text-amber-800 border-amber-200'
                          }`}>
                            {statusVal}
                          </span>
                        </td>
                        <td className="p-4"><Badge tier={w.tier || 'standard'} /></td>
                        <td className="p-4 text-right font-mono font-bold text-slate-900">{score}</td>
                        <td className="p-4 text-right font-mono text-slate-700 font-semibold">
                          {winRate > 0 ? `${(winRate > 1 ? winRate : winRate * 100).toFixed(1)}%` : '-'}
                        </td>
                        <td className={`p-4 text-right font-mono font-bold ${pnl >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                          ${Math.abs(pnl).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                        </td>
                        <td className="p-4 sm:px-6 text-slate-600 text-[11px] max-w-[280px] truncate font-medium">
                          {reason || w.aiStyleTag || (statusVal === 'active' ? 'Passed all gold-tier filters' : 'Pending evaluation pass')}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={7} className="p-16 text-center text-slate-400 text-xs font-medium">
                      No matching wallets in this category. Click &quot;Discovery Scan&quot; above to fetch and score immediately.
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
