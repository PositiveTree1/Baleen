'use client';
import { useState, useEffect } from 'react';
import { fetchAdminStatus, fetchAdminWallets } from '@/lib/api-client';
import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import Link from 'next/link';
import { ArrowLeft, Activity, Database, Users, Wallet, CheckCircle, XCircle } from 'lucide-react';

export default function AdminPage() {
  const [status, setStatus] = useState<any>(null);
  const [wallets, setWallets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      const [statusData, walletsData] = await Promise.all([
        fetchAdminStatus(),
        fetchAdminWallets()
      ]);
      setStatus(statusData);
      setWallets(walletsData);
      setLoading(false);
    }
    loadData();
  }, []);

  return (
    <div className="min-h-screen bg-baleen-obsidian p-6">
      <div className="max-w-7xl mx-auto mt-8">
        <Link href="/dashboard" className="inline-flex items-center gap-2 text-baleen-muted hover:text-baleen-white mb-8 transition-colors">
          <ArrowLeft size={16} /> Back to Dashboard
        </Link>
        
        <h1 className="text-3xl font-bold text-baleen-white mb-8 flex items-center gap-3">
          <Activity className="text-baleen-cyan" /> Admin Control Panel
        </h1>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* System Status */}
          <Card className="glass-card">
            <h2 className="text-lg font-semibold text-baleen-white mb-4 flex items-center gap-2">
              <Database size={18} className="text-baleen-muted" /> Database Stats
            </h2>
            {loading ? (
              <div className="space-y-2"><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-2/3" /></div>
            ) : status ? (
              <div className="space-y-3 text-sm">
                <div className="flex justify-between"><span className="text-baleen-muted">Total Wallets</span><span className="text-baleen-white font-mono">{status.db?.total_wallets || 0}</span></div>
                <div className="flex justify-between"><span className="text-baleen-muted">Active (Whales)</span><span className="text-baleen-cyan font-mono">{status.db?.active_wallets || 0}</span></div>
                <div className="flex justify-between"><span className="text-baleen-muted">Pending</span><span className="text-amber-500 font-mono">{status.db?.pending_wallets || 0}</span></div>
                <div className="flex justify-between"><span className="text-baleen-muted">Rejected</span><span className="text-baleen-red font-mono">{status.db?.rejected_wallets || 0}</span></div>
                <div className="border-t border-white/10 my-2 pt-2 flex justify-between"><span className="text-baleen-muted">Users</span><span className="text-baleen-white font-mono">{status.db?.users || 0}</span></div>
                <div className="flex justify-between"><span className="text-baleen-muted">Total Trades</span><span className="text-baleen-white font-mono">{status.db?.trades || 0}</span></div>
              </div>
            ) : <span className="text-baleen-muted text-sm">Unavailable</span>}
          </Card>

          {/* Service Status */}
          <Card className="glass-card">
            <h2 className="text-lg font-semibold text-baleen-white mb-4 flex items-center gap-2">
              <Activity size={18} className="text-baleen-muted" /> Services
            </h2>
            {loading ? (
              <div className="space-y-2"><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-2/3" /></div>
            ) : status ? (
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-2">
                  {status.services?.backend === 'ONLINE' ? <CheckCircle size={14} className="text-baleen-green" /> : <XCircle size={14} className="text-baleen-red" />}
                  <span className="text-baleen-muted">Backend API</span>
                </div>
                <div className="flex items-center gap-2">
                  {status.services?.database === 'ONLINE' ? <CheckCircle size={14} className="text-baleen-green" /> : <XCircle size={14} className="text-baleen-red" />}
                  <span className="text-baleen-muted">Database</span>
                </div>
                <div className="flex items-center gap-2">
                  {status.services?.listener === 'ONLINE' ? <CheckCircle size={14} className="text-baleen-green" /> : <XCircle size={14} className="text-baleen-red" />}
                  <span className="text-baleen-muted">Event Listener</span>
                </div>
              </div>
            ) : <span className="text-baleen-muted text-sm">Unavailable</span>}
          </Card>

          {/* Job Schedule */}
          <Card className="glass-card">
            <h2 className="text-lg font-semibold text-baleen-white mb-4 flex items-center gap-2">
              <Activity size={18} className="text-baleen-muted" /> Schedules
            </h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-baleen-muted">Discovery Job</span><span className="text-baleen-white">Every 6h</span></div>
              <div className="flex justify-between"><span className="text-baleen-muted">Scoring Job</span><span className="text-baleen-white">Every 24h</span></div>
              <div className="flex justify-between"><span className="text-baleen-muted">Analysis Job</span><span className="text-baleen-white">Every 24h</span></div>
            </div>
          </Card>
        </div>

        {/* Wallet Pipeline */}
        <Card className="glass-card overflow-hidden p-0">
          <div className="p-4 border-b border-white/5 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-baleen-white flex items-center gap-2">
              <Wallet size={18} className="text-baleen-muted" /> Wallet Pipeline
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-xs uppercase text-baleen-muted bg-white/5">
                  <th className="p-4 font-medium">Address</th>
                  <th className="p-4 font-medium">Status</th>
                  <th className="p-4 font-medium">Tier</th>
                  <th className="p-4 font-medium">Score</th>
                  <th className="p-4 font-medium">Win Rate</th>
                  <th className="p-4 font-medium">PnL</th>
                  <th className="p-4 font-medium">Rejection Reason</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-white/5">
                      <td colSpan={7} className="p-4"><Skeleton className="h-4 w-full" /></td>
                    </tr>
                  ))
                ) : wallets.length > 0 ? (
                  wallets.map((w: any) => (
                    <tr key={w.address} className="border-b border-white/5 hover:bg-white/5 transition-colors text-sm">
                      <td className="p-4 font-mono text-baleen-white">{(w.address || '').slice(0, 8)}...</td>
                      <td className="p-4">
                        <span className={`px-2 py-1 rounded text-xs ${w.status === 'ACTIVE' ? 'bg-baleen-green/20 text-baleen-green' : w.status === 'REJECTED' ? 'bg-baleen-red/20 text-baleen-red' : 'bg-amber-500/20 text-amber-500'}`}>
                          {w.status}
                        </span>
                      </td>
                      <td className="p-4">{w.tier || '-'}</td>
                      <td className="p-4 font-mono">{w.baleen_score || '-'}</td>
                      <td className="p-4 font-mono">{w.win_rate_pct ? `${w.win_rate_pct}%` : '-'}</td>
                      <td className="p-4 font-mono">${w.all_time_pnl_usd || 0}</td>
                      <td className="p-4 text-baleen-muted text-xs">{w.rejection_reason || '-'}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-baleen-muted">No wallets found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
