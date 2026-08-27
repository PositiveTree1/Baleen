'use client';
import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { fetchUserSettings, updateUserSettings, fetchPortfolioSummary } from '@/lib/api-client';
import { User, PortfolioSummary } from '@/types';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { ResetSandboxModal } from '@/components/dashboard/ResetSandboxModal';
import { ArrowLeft, Save, Moon, Sun } from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import Link from 'next/link';

export default function SettingsPage() {
  const { data: session } = useSession();
  const { theme, toggleTheme } = useTheme();
  const [user, setUser] = useState<User | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [isResetOpen, setIsResetOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [riskProfile, setRiskProfile] = useState<'Conservative' | 'Balanced' | 'Aggressive'>('Balanced');
  const [dailyDigest, setDailyDigest] = useState(true);

  const loadUserData = () => {
    if (session?.user?.id) {
      Promise.all([
        fetchUserSettings(session.user.id),
        fetchPortfolioSummary(session.user.id)
      ]).then(([userData, portfolioData]) => {
        if (userData) {
          setUser(userData);
          setRiskProfile(userData.riskProfile as any || 'Balanced');
          setDailyDigest(userData.dailyDigestOptIn);
        }
        if (portfolioData) {
          setPortfolio(portfolioData);
        }
      });
    }
  };

  useEffect(() => {
    loadUserData();
  }, [session]);

  async function handleSave() {
    if (!session?.user?.id) return;
    setSaving(true);
    setSavedSuccess(false);
    const updated = await updateUserSettings(session.user.id, {
      riskProfile,
      dailyDigestOptIn: dailyDigest
    });
    if (updated) {
      setUser(updated);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    }
    setSaving(false);
  }

  const profiles = [
    { id: 'Conservative', desc: 'Lower position sizing (5% max), strictest slippage tolerances. Prioritizes capital preservation.' },
    { id: 'Balanced', desc: 'Standard dynamic sizing (10% max) scaled by active basket count and whale risk conviction.' },
    { id: 'Aggressive', desc: 'Higher leverage allocation (20% max), looser slippage window. Maximizes upside volatility.' }
  ] as const;

  return (
    <div className="min-h-screen bg-[#F8F9FB] dark:bg-[#000000] text-slate-900 dark:text-white p-6 lg:p-12 selection:bg-[#00D09C] selection:text-black transition-colors duration-150">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <BrandLogo size="sm" subtitle="Settings" />
            <span className="text-slate-300 dark:text-slate-700">|</span>
            <Link href="/dashboard" className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 dark:text-[#8E8F99] hover:text-slate-950 dark:hover:text-white transition-colors">
              <ArrowLeft size={14} /> Back to Dashboard
            </Link>
          </div>

          <button
            onClick={toggleTheme}
            className="w-9 h-9 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-white flex items-center justify-center transition-all cursor-pointer shadow-2xs"
            title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
          >
            {theme === 'light' ? <Moon size={15} /> : <Sun size={15} className="text-amber-400" />}
          </button>
        </div>
        
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950 dark:text-white mb-2">Engine Settings</h1>
          <p className="text-slate-600 dark:text-[#8E8F99] text-sm">Manage your paper trading balance, execution risk regime, and digest alerts.</p>
        </div>

        <div className="space-y-6">
          {/* Account Status Card */}
          <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-950 dark:text-white">Sandbox Capital Allocation</h2>
              <button
                type="button"
                onClick={() => setIsResetOpen(true)}
                className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 bg-indigo-50 dark:bg-indigo-500/10 px-3.5 py-1.5 rounded-full border border-indigo-200 dark:border-indigo-500/20 transition-colors cursor-pointer"
              >
                Reset Sandbox Amount
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5">
                <div className="text-[11px] text-slate-500 dark:text-[#8E8F99] font-medium mb-1">Starting Allocation</div>
                <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white">
                  ${(user?.startingBalance ?? 10000).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.04] dark:border-white/5">
                <div className="text-[11px] text-slate-500 dark:text-[#8E8F99] font-medium mb-1">Current Mark-to-Market</div>
                <div className="text-2xl font-bold font-mono text-emerald-600 dark:text-[#00D09C]">
                  ${(portfolio?.currentBalance ?? user?.currentBalance ?? 10000).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
            </div>
          </div>

          {/* Risk Profile Selector */}
          <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm space-y-4">
            <div>
              <h2 className="text-sm font-bold text-slate-950 dark:text-white mb-1">Risk Regime</h2>
              <p className="text-xs text-slate-500 dark:text-[#8E8F99]">Controls maximum capital committed per mirrored trade event.</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {profiles.map(p => {
                const isSelected = riskProfile === p.id;
                return (
                  <div 
                    key={p.id}
                    onClick={() => setRiskProfile(p.id)}
                    className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                      isSelected 
                        ? 'border-indigo-600 dark:border-[#00D09C] bg-indigo-50/50 dark:bg-[#00D09C]/10 shadow-sm' 
                        : 'border-black/[0.06] dark:border-white/5 bg-slate-50 dark:bg-[#1C1D22] hover:border-black/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-slate-900 dark:text-white">{p.id}</span>
                      <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${isSelected ? 'border-indigo-600 dark:border-[#00D09C] bg-indigo-600 dark:bg-[#00D09C]' : 'border-slate-300 dark:border-slate-600'}`}>
                        {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white dark:bg-black" />}
                      </div>
                    </div>
                    <p className="text-[11px] text-slate-600 dark:text-[#8E8F99] leading-relaxed">{p.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Daily Digest Toggle */}
          <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-950 dark:text-white">Daily Digest Alerts</h2>
              <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-0.5">Receive daily performance digest summaries of all copy-trade executions.</p>
            </div>
            <button
              onClick={() => setDailyDigest(!dailyDigest)}
              className={`w-12 h-6 rounded-full p-0.5 transition-colors cursor-pointer ${dailyDigest ? 'bg-[#00D09C]' : 'bg-slate-300 dark:bg-[#2C2D35]'}`}
            >
              <div className={`w-5 h-5 rounded-full bg-white dark:bg-black shadow-xs transform transition-transform ${dailyDigest ? 'translate-x-6' : 'translate-x-0'}`} />
            </button>
          </div>

          {/* Save Button */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-8 py-3.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black hover:bg-slate-800 dark:hover:bg-slate-200 text-xs font-bold transition-all shadow-md active:scale-[0.98] cursor-pointer disabled:opacity-50"
            >
              <Save size={14} />
              <span>{saving ? 'Saving...' : savedSuccess ? '✓ Settings Saved' : 'Save Preferences'}</span>
            </button>
          </div>
        </div>

        <ResetSandboxModal
          isOpen={isResetOpen}
          onClose={() => setIsResetOpen(false)}
          userId={session?.user?.id}
          currentBalance={portfolio?.currentBalance ?? user?.currentBalance ?? 10000}
          onResetComplete={loadUserData}
        />
      </div>
    </div>
  );
}
