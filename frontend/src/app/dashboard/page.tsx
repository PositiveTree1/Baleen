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
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#090A0F] text-zinc-400 text-sm">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-white animate-ping" />
          <span>Initializing Baleen Engine...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#090A0F] text-white selection:bg-white selection:text-black">
      {/* Top Navigation */}
      <nav className="flex items-center justify-between py-4 px-6 lg:px-12 border-b border-white/[0.06] bg-[#090A0F]/80 backdrop-blur-2xl sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <Image src="/logo.png" alt="Baleen Logo" width={26} height={26} className="w-6.5 h-6.5 object-contain" />
          <span className="font-semibold text-base tracking-tight text-white">Baleen Control</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Engine Active</span>
          </div>
          <Link href="/admin" className="text-xs font-medium text-zinc-400 hover:text-white transition-colors px-3 py-1.5 rounded-lg hover:bg-white/[0.06]">
            Admin
          </Link>
          <Link href="/settings" className="p-2 text-zinc-400 hover:text-white hover:bg-white/[0.06] rounded-xl transition-colors">
            <Settings size={18} />
          </Link>
          <button onClick={() => signOut()} className="p-2 text-zinc-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-xl transition-colors cursor-pointer">
            <LogOut size={18} />
          </button>
        </div>
      </nav>

      <main className="flex-1 p-6 lg:p-12 max-w-7xl mx-auto w-full flex flex-col gap-8">
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-6 pb-2">
          <BalanceCounter balance={user?.currentBalance ?? null} />
          
          <div className="flex items-center gap-3">
            <div className="glass-card px-4 py-2.5 rounded-2xl flex items-center gap-3 border border-white/[0.08] shadow-apple-sm">
              <span className="text-xs text-zinc-500 font-medium">Risk Regime</span>
              <span className="text-xs font-semibold text-white px-2.5 py-0.5 rounded-full bg-white/[0.08] border border-white/[0.08]">
                {user?.riskProfile || 'Balanced'}
              </span>
            </div>
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
