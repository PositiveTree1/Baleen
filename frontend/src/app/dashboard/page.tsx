'use client';
import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { BalanceCounter } from '@/components/dashboard/BalanceCounter';
import { LiveTape } from '@/components/dashboard/LiveTape';
import { WalletLeaderboard } from '@/components/dashboard/WalletLeaderboard';
import { TradeLog } from '@/components/dashboard/TradeLog';
import { WalletDrawer } from '@/components/dashboard/WalletDrawer';
import { fetchUserSettings } from '@/lib/api-client';
import { User } from '@/types';
import Image from 'next/image';
import Link from 'next/link';
import { Settings, LogOut } from 'lucide-react';
import { signOut } from 'next-auth/react';

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const [selectedWallet, setSelectedWallet] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (session?.user?.id) {
      fetchUserSettings(session.user.id).then(data => {
        if (data) setUser(data);
      });
    }
  }, [session]);

  if (status === 'loading') {
    return <div className="min-h-screen flex items-center justify-center text-baleen-muted">Loading Engine...</div>;
  }

  return (
    <div className="min-h-screen flex flex-col bg-baleen-obsidian">
      {/* Top Navigation */}
      <nav className="flex items-center justify-between p-4 px-6 border-b border-white/5 bg-baleen-charcoal/50 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <Image src="/logo.png" alt="Baleen Logo" width={24} height={24} className="w-6 h-6 object-contain" />
          <span className="font-bold text-lg tracking-tight text-baleen-white">Baleen Control</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs text-baleen-muted mr-4">
            <div className="w-2 h-2 rounded-full bg-baleen-green animate-pulse" />
            <span>Engine Active</span>
          </div>
          <Link href="/admin" className="text-baleen-muted hover:text-baleen-white transition-colors text-xs uppercase tracking-wider font-semibold">
            Admin
          </Link>
          <Link href="/settings" className="text-baleen-muted hover:text-baleen-white transition-colors">
            <Settings size={20} />
          </Link>
          <button onClick={() => signOut()} className="text-baleen-muted hover:text-baleen-red transition-colors">
            <LogOut size={20} />
          </button>
        </div>
      </nav>

      <main className="flex-1 p-6 max-w-7xl mx-auto w-full flex flex-col gap-6">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
          <BalanceCounter balance={user?.currentBalance ?? null} />
          
          <div className="glass-card px-4 py-2 rounded-lg flex items-center gap-3 border border-white/5">
            <span className="text-xs text-baleen-muted uppercase tracking-wider">Risk Profile</span>
            <span className="text-sm font-medium text-baleen-cyan">{user?.riskProfile || 'Loading...'}</span>
          </div>
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <LiveTape />
          </div>
          <div className="lg:col-span-1">
            <WalletLeaderboard onSelectWallet={setSelectedWallet} />
          </div>
        </div>

        {/* Trade Log */}
        <TradeLog userId={session?.user?.id} />
      </main>

      {/* Drawer */}
      <WalletDrawer 
        address={selectedWallet} 
        onClose={() => setSelectedWallet(null)} 
      />
    </div>
  );
}
