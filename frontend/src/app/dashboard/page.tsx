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
      <div className="min-h-screen flex items-center justify-center bg-[#F8F9FB] text-slate-500 text-sm">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-slate-900 animate-ping" />
          <span className="font-medium">Initializing Baleen Engine...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FB] text-slate-900 selection:bg-slate-900 selection:text-white">
      {/* Top Navigation */}
      <nav className="flex items-center justify-between py-4 px-6 lg:px-12 border-b border-black/[0.06] bg-white/80 backdrop-blur-2xl sticky top-0 z-40 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
        <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
          <Image src="/logo.png" alt="Baleen Logo" width={26} height={26} className="w-6.5 h-6.5 object-contain" />
          <span className="font-bold text-base tracking-tight text-slate-900">Baleen Control</span>
        </Link>
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span>Engine Active</span>
          </div>
          <Link href="/admin" className="text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors px-3 py-1.5 rounded-xl hover:bg-black/5">
            Admin
          </Link>
          <Link href="/settings" className="p-2 text-slate-600 hover:text-slate-900 hover:bg-black/5 rounded-xl transition-colors">
            <Settings size={18} />
          </Link>
          <button onClick={() => signOut()} className="p-2 text-slate-600 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-colors cursor-pointer">
            <LogOut size={18} />
          </button>
        </div>
      </nav>

      <main className="flex-1 p-6 lg:p-12 max-w-7xl mx-auto w-full flex flex-col gap-8">
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-6 pb-2">
          <BalanceCounter balance={user?.currentBalance ?? null} />
          
          <div className="flex items-center gap-3">
            <div className="bg-white px-4 py-2.5 rounded-2xl flex items-center gap-3 border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_1px_3px_rgba(0,0,0,0.04)]">
              <span className="text-xs text-slate-500 font-medium">Risk Regime</span>
              <span className="text-xs font-bold text-slate-900 px-2.5 py-0.5 rounded-full bg-slate-100 border border-black/[0.06]">
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
