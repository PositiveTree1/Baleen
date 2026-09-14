'use client';
import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { fetchAdminStatus, fetchAdminWallets, getCachedAdminStatus, getCachedAdminWallets, reEvaluateWallets, purgeAndRescanWallets, fetchDiscoveryProgress, setAuthToken, fetchWithAuth, AdminStatus, AdminWallet, DiscoveryProgress } from '@/lib/api-client';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { BrandLogo } from '@/components/ui/BrandLogo';
import Link from 'next/link';
import { ArrowLeft, Activity, Database, Users, Wallet, CheckCircle, AlertTriangle, RefreshCw, Sparkles, Filter, RotateCw, Trash2, Search, ExternalLink, Sun, Moon, Lock } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { motion, AnimatePresence } from 'framer-motion';

export default function AdminPage() {
  const { data: session, status: sessionStatus } = useSession();
  const [status, setStatus] = useState<AdminStatus | null>(() => getCachedAdminStatus() || null);
  const [wallets, setWallets] = useState<AdminWallet[]>(() => getCachedAdminWallets() || []);
  const [initialLoading, setInitialLoading] = useState(() => !getCachedAdminStatus());
  const [justRefreshed, setJustRefreshed] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [progress, setProgress] = useState<DiscoveryProgress | null>(null);
  const [filter, setFilter] = useState<'all' | 'active' | 'pending' | 'rejected'>('all');
  const { theme, toggleTheme } = useTheme();
  const [wipingAll, setWipingAll] = useState(false);
  const [search, setSearch] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [referenceNow, setReferenceNow] = useState(0);

  useEffect(() => {
    const token = session?.user?.accessToken || (session as { accessToken?: string })?.accessToken;
    if (token) {
      setAuthToken(token);
    }

    if (sessionStatus !== 'authenticated' || !session?.user?.isAdmin) {
      return;
    }
    let isMounted = true;

    const runLoad = async () => {
      try {
        const [statusData, walletsData] = await Promise.all([
          fetchAdminStatus(),
          fetchAdminWallets()
        ]);
        if (!isMounted) return;
        setReferenceNow(Date.now());
        setStatus(statusData);
        setWallets(walletsData);

        if (statusData?.discovery_state?.status === 'running') {
          setProgress(statusData.discovery_state);
          setEvaluating(true);
        } else if (statusData?.discovery_state?.status === 'completed') {
          setEvaluating(false);
          setProgress(null);
        }
      } catch (e) {
        console.error("Admin refresh error:", e);
      } finally {
        if (isMounted) setInitialLoading(false);
      }
    };

    void runLoad();
    const interval = setInterval(runLoad, 5000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [refreshKey, sessionStatus, session]);

  const handleManualRefresh = () => {
    setRefreshKey(k => k + 1);
    setJustRefreshed(true);
    setTimeout(() => setJustRefreshed(false), 900);
  };

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
            setRefreshKey(k => k + 1);
          }, 1200);
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
    if (!window.confirm("Purge all active/rejected wallets and re-scan top leaderboard?")) return;
    setEvaluating(true);
    try {
      await purgeAndRescanWallets();
      startProgressPolling();
    } catch {
      setEvaluating(false);
    }
  };

  const handleHardWipeAll = async () => {
    const conf = window.prompt("Type 'RESET' to completely wipe all database tables, reset portfolios to $10k, and restart engine discovery:");
    if (conf !== 'RESET') return;

    setWipingAll(true);
    try {
      const backendUrl = (
        process.env.NEXT_PUBLIC_API_URL ||
        'http://localhost:8000'
      ).replace(/\/$/, '');
      const res = await fetchWithAuth(`${backendUrl}/api/admin/hard-wipe-all`, { method: 'POST' });
      if (res.ok) {
        alert("Database successfully wiped and reset to clean genesis state!");
        window.location.reload();
      } else {
        alert("Wipe failed: check backend logs.");
      }
    } catch (e) {
      alert(`Wipe error: ${e}`);
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
      await fetchWithAuth(`${backendUrl}/api/admin/trigger-discovery`, { method: 'POST' });
      setTimeout(() => {
        setRefreshKey(k => k + 1);
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

  const formatCronTime = (timestamp: number | null, currentTs: number) => {
    if (!timestamp || !currentTs) return 'Waiting for ping...';
    const secondsAgo = Math.floor(currentTs / 1000 - timestamp);
    if (secondsAgo < 60) return 'Just now';
    return `${Math.floor(secondsAgo / 60)}m ago`;
  };

  const dbType = status?.database?.type || (status?.database?.using_sqlite_fallback ? 'SQLite (Local Failover)' : 'Supabase PostgreSQL');
  const isPostgres = !status?.database?.using_sqlite_fallback && !dbType.includes('SQLite');

  if (sessionStatus === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center text-white relative z-10">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-[#00D09C] border-t-transparent animate-spin" />
          <span className="text-xs font-mono text-white/60">Verifying administrator credentials...</span>
        </div>
      </div>
    );
  }

  if (sessionStatus === 'unauthenticated') {
    return (
      <div className="min-h-screen text-white flex flex-col items-center justify-center p-6 relative z-10">
        <div className="glass-card w-full max-w-md p-8 rounded-[32px] text-center space-y-4 text-white shadow-2xl">
          <div className="w-12 h-12 mx-auto rounded-2xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-300">
            <Lock size={24} />
          </div>
          <h2 className="text-lg font-bold">Authentication Required</h2>
          <p className="text-xs text-white/60">
            The Baleen Control Plane is restricted. Please sign in with administrator credentials.
          </p>
          <Link
            href="/auth/login"
            className="inline-block w-full py-3 rounded-full glass-button text-white text-xs font-bold transition-all cursor-pointer shadow-md"
          >
            Sign In
          </Link>
        </div>
      </div>
    );
  }

  if (!session?.user?.isAdmin) {
    return (
      <div className="min-h-screen text-white flex flex-col items-center justify-center p-6 relative z-10">
        <div className="glass-card w-full max-w-md p-8 rounded-[32px] text-center space-y-4 text-white shadow-2xl">
          <div className="w-12 h-12 mx-auto rounded-2xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-300">
            <AlertTriangle size={24} />
          </div>
          <h2 className="text-lg font-bold">Access Denied</h2>
          <p className="text-xs text-white/60">
            Your account ({session?.user?.email || 'authenticated user'}) does not have administrator privileges.
          </p>
          <Link
            href="/dashboard"
            className="inline-block w-full py-3 rounded-full glass-button text-white text-xs font-bold transition-all cursor-pointer shadow-md"
          >
            Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen text-white p-6 lg:p-12 selection:bg-[#00D09C] selection:text-black relative z-10">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Top Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-white/10">
          <div className="flex items-center gap-4">
            <BrandLogo size="sm" />
            <span className="text-white/20">|</span>
            <Link href="/dashboard" className="inline-flex items-center gap-1.5 text-xs font-semibold text-white/60 hover:text-white transition-colors">
              <ArrowLeft size={14} /> Back to Dashboard
            </Link>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={toggleTheme}
              className="w-9 h-9 rounded-full ctrl-btn text-white flex items-center justify-center transition-all cursor-pointer shadow-xs mr-1"
              title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
            >
              {theme === 'light' ? <Moon size={15} /> : <Sun size={15} className="text-amber-400" />}
            </button>
            <button
              onClick={handleManualRefresh}
              disabled={initialLoading || justRefreshed || wipingAll}
              className="ctrl-btn text-xs py-2 px-3 text-white rounded-full flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <RefreshCw size={14} className={justRefreshed ? 'animate-spin text-[#00D09C]' : ''} /> Refresh
            </button>
            <button
              onClick={handleReevaluate}
              disabled={evaluating || wipingAll}
              className="ctrl-btn text-xs py-2 px-3.5 text-indigo-300 rounded-full flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <RotateCw size={14} className={evaluating ? 'animate-spin text-indigo-400' : 'text-indigo-400'} />
              {evaluating ? 'Evaluating...' : 'Re-evaluate All'}
            </button>
            <button
              onClick={handlePurgeAndRescan}
              disabled={evaluating || wipingAll}
              className="ctrl-btn text-xs py-2 px-3.5 text-rose-300 rounded-full flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <Trash2 size={14} /> Purge &amp; Rescan
            </button>
            <button
              onClick={handleHardWipeAll}
              disabled={wipingAll || evaluating}
              className="ctrl-btn text-xs py-2 px-3.5 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 rounded-full font-bold flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              title="Completely wipe all database tables and reset system"
            >
              <Trash2 size={14} /> {wipingAll ? 'Wiping...' : 'Factory Reset DB'}
            </button>
            <button
              onClick={handleTriggerDiscovery}
              disabled={triggering || evaluating || wipingAll}
              className="glass-button text-xs py-2 px-4 font-semibold text-white rounded-full flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <Sparkles size={14} /> {triggering ? 'Scanning...' : 'Discovery Scan'}
            </button>
          </div>
        </div>

        {/* Live Discovery Progress Bar */}
        <AnimatePresence>
          {evaluating && progress && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="glass-card p-5 rounded-3xl text-white shadow-xl"
            >
              <div className="flex justify-between items-center mb-2.5">
                <div className="flex items-center gap-2">
                  <RotateCw size={16} className="text-indigo-400 animate-spin" />
                  <span className="text-sm font-bold text-white">
                    {progress.step_description || 'Scraping and auditing Polymarket wallets...'}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-white/60">
                    {progress.wallets_scanned} scanned • {progress.gold_snipers || 0} Gold Snipers
                  </span>
                  <span className="text-xs font-mono font-bold text-indigo-300 bg-indigo-500/20 px-2.5 py-0.5 rounded-full border border-indigo-500/30">
                    {progress.progress_pct || 0}%
                  </span>
                </div>
              </div>
              <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-indigo-500 rounded-full transition-all duration-300"
                  style={{ width: `${progress.progress_pct || 5}%` }}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
            <Activity className="text-white" size={26} /> Engine Control Plane
          </h1>
          <p className="text-white/60 text-sm">Real-time status of Polymarket indexer, Supabase database models, and scoring workers.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Database Entities */}
          <div className="glass-card p-6 rounded-3xl space-y-4 text-white">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Database size={16} className="text-white/70" /> Database Entities
            </h2>
            {initialLoading && !status ? (
              <div className="space-y-3"><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-2/3" /></div>
            ) : (
              <div className="space-y-3 text-xs">
                <div className="flex justify-between">
                  <span className="text-white/60 font-medium">Total Wallets Discovered</span>
                  <span className="text-white font-mono font-bold">{status?.db_stats?.total ?? wallets.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/60 font-medium">Active (In Basket)</span>
                  <span className="text-[#00D09C] font-mono font-bold">{status?.db_stats?.active ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/60 font-medium">Pending Analysis</span>
                  <span className="text-amber-300 font-mono font-bold">{status?.db_stats?.pending ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/60 font-medium">Rejected (Failed Rules)</span>
                  <span className="text-rose-400 font-mono font-bold">{status?.db_stats?.rejected ?? 0}</span>
                </div>
                <div className="border-t border-white/10 my-2 pt-2 flex justify-between">
                  <span className="text-white/60 font-medium">Registered Users</span>
                  <span className="text-white font-mono font-bold">{status?.database?.totalUsers ?? status?.db?.users ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/60 font-medium">Total Executions Tape</span>
                  <span className="text-white font-mono font-bold">{status?.database?.totalTrades ?? status?.db?.trades ?? 0}</span>
                </div>
              </div>
            )}
          </div>

          {/* Microservice Health */}
          <div className="glass-card p-6 rounded-3xl space-y-4 text-white">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Activity size={16} className="text-white/70" /> Storage &amp; Infrastructure
            </h2>
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between p-3 rounded-2xl bg-white/[0.04] border border-white/10">
                <span className="text-white/80 font-semibold">Backend Engine</span>
                <span className="inline-flex items-center gap-1 text-[11px] font-mono font-bold text-[#00D09C] bg-[#00D09C]/15 px-2.5 py-0.5 rounded-full border border-[#00D09C]/30">
                  <CheckCircle size={12} /> ONLINE
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-2xl bg-white/[0.04] border border-white/10">
                <span className="text-white/80 font-semibold">Database Engine</span>
                <span className={`inline-flex items-center gap-1 text-[11px] font-mono font-bold px-2.5 py-0.5 rounded-full border ${
                  isPostgres
                    ? 'text-[#00D09C] bg-[#00D09C]/15 border-[#00D09C]/30'
                    : 'text-amber-300 bg-amber-500/15 border-amber-500/30'
                }`}>
                  {isPostgres ? <CheckCircle size={12} /> : <AlertTriangle size={12} />}
                  {isPostgres ? 'Supabase Postgres' : 'SQLite Failover'}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-2xl bg-white/[0.04] border border-white/10">
                <span className="text-white/80 font-semibold">Server Uptime</span>
                <span className="font-mono font-bold text-white bg-white/10 px-2.5 py-0.5 rounded-full border border-white/15">
                  {formatUptime(status?.uptime_seconds || 0)}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-2xl bg-white/[0.04] border border-white/10">
                <span className="text-white/80 font-semibold">Keep-Alive Heartbeat</span>
                <span className="font-mono font-bold text-white bg-white/10 px-2.5 py-0.5 rounded-full border border-white/15">
                  {formatCronTime(status?.last_cron_ping ?? null, referenceNow)}
                </span>
              </div>
            </div>
          </div>

          {/* Discovery & Re-evaluation Audit */}
          <div className="glass-card p-6 rounded-3xl space-y-4 text-white">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <RefreshCw size={16} className="text-white/70" /> Discovery &amp; Scoring Audit
            </h2>
            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-white/60 font-medium">Last Discovery Scan</span>
                <span className="font-mono text-white font-bold">
                  {status?.audit?.last_discovery_at ? new Date(status.audit.last_discovery_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' }) : 'Continuous'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-white/60 font-medium">Last Re-evaluation</span>
                <span className="font-mono text-white font-bold">
                  {status?.audit?.last_scoring_at ? new Date(status.audit.last_scoring_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' }) : 'Active'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-white/60 font-medium">Active Basket Composition</span>
                <span className="font-mono text-[#00D09C] font-bold">
                  {status?.audit?.gold_snipers || 0} Gold • {status?.audit?.standard_whales || 0} Standard
                </span>
              </div>
              <div className="border-t border-white/10 pt-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-white/40 block mb-1.5">Top Rejection Reasons</span>
                <div className="space-y-1">
                  {(status?.audit?.rejection_breakdown || []).slice(0, 3).map((r: { reason: string; count: number }, idx: number) => (
                    <div key={idx} className="flex justify-between text-[11px]">
                      <span className="text-white/60 truncate max-w-[170px]">{r.reason}</span>
                      <span className="font-mono font-bold text-rose-400">{r.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Whale Pipeline Table */}
        <div className="glass-card rounded-3xl overflow-hidden text-white shadow-2xl">
          <div className="p-6 border-b border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white/[0.02]">
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Wallet size={18} className="text-white/70" /> Discovered Whale Pipeline
                </h2>
                {justRefreshed && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-[#00D09C] bg-[#00D09C]/15 px-2 py-0.5 rounded-full border border-[#00D09C]/30 animate-pulse">
                    Synced
                  </span>
                )}
              </div>
              <p className="text-xs text-white/60 mt-1">Full auditable funnel of all candidate and active wallets.</p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
                <input
                  type="text"
                  placeholder="Search 0x address..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="text-xs bg-white/[0.06] border border-white/15 rounded-xl pl-8 pr-3 py-2 text-white placeholder-white/30 focus:outline-none focus:border-[#00D09C] shadow-sm w-48 font-mono"
                />
              </div>
              <div className="flex rounded-xl bg-white/[0.06] p-1 border border-white/10">
                {(['all', 'active', 'pending', 'rejected'] as const).map(f => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`text-xs px-3 py-1.5 rounded-lg capitalize font-semibold transition-all cursor-pointer ${
                      filter === f ? 'bg-white/20 text-white shadow-xs' : 'text-white/60 hover:text-white'
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
                <tr className="border-b border-white/10 text-[10px] uppercase tracking-wider text-white/50 bg-white/[0.02] font-semibold">
                  <th className="p-4 sm:px-6 font-semibold">Address</th>
                  <th className="p-4 font-semibold">Status</th>
                  <th className="p-4 font-semibold">Tier</th>
                  <th className="p-4 font-semibold text-right">Score</th>
                  <th className="p-4 font-semibold text-right">Win Rate</th>
                  <th className="p-4 font-semibold text-right">Realized PnL</th>
                  <th className="p-4 sm:px-6 font-semibold">Rejection / Audit Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {initialLoading && wallets.length === 0 ? (
                  Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i}>
                      <td colSpan={7} className="p-4"><Skeleton className="h-4 w-full" /></td>
                    </tr>
                  ))
                ) : filteredWallets.length > 0 ? (
                  filteredWallets.map((w: AdminWallet) => {
                    const statusVal = (w.status || 'pending').toLowerCase();
                    const winRate = w.winRatePct ?? w.win_rate_pct ?? 0;
                    const pnl = w.allTimePnlUsd ?? w.all_time_pnl_usd ?? 0;
                    const score = w.baleenScore ?? w.baleen_score ?? '-';
                    const reason = w.rejectionReason ?? w.rejection_reason;

                    return (
                      <tr key={w.address} className="hover:bg-white/[0.04] transition-colors text-xs">
                        <td className="p-4 sm:px-6 font-mono text-white font-semibold">
                          <a
                            href={`https://polymarket.com/profile/${w.address}`}
                            target="_blank"
                            rel="noreferrer"
                            className="hover:text-[#00D09C] transition-colors inline-flex items-center gap-1"
                          >
                            <span>{w.address.slice(0, 8)}...{w.address.slice(-6)}</span>
                            <ExternalLink size={11} className="opacity-40" />
                          </a>
                        </td>
                        <td className="p-4">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold capitalize border ${
                            statusVal === 'active'
                              ? 'bg-[#00D09C]/15 text-[#00D09C] border-[#00D09C]/30'
                              : statusVal === 'rejected'
                              ? 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                              : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                          }`}>
                            {statusVal}
                          </span>
                        </td>
                        <td className="p-4"><Badge tier={w.tier || 'standard'} /></td>
                        <td className="p-4 text-right font-mono font-bold text-white">{score}</td>
                        <td className="p-4 text-right font-mono text-white/80 font-semibold">
                          {winRate > 0 ? `${(winRate > 1 ? winRate : winRate * 100).toFixed(1)}%` : '-'}
                        </td>
                        <td className={`p-4 text-right font-mono font-bold ${pnl >= 0 ? 'text-[#00D09C]' : 'text-rose-400'}`}>
                          ${Math.abs(pnl).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                        </td>
                        <td className="p-4 sm:px-6 text-white/60 text-[11px] max-w-[280px] truncate font-medium">
                          {reason || w.aiStyleTag || (statusVal === 'active' ? 'Passed all gold-tier filters' : 'Pending evaluation pass')}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={7} className="p-16 text-center text-white/50 text-xs font-medium">
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
