'use client';
import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { fetchUserSettings, updateUserSettings } from '@/lib/api-client';
import { User } from '@/types';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ArrowLeft, Save } from 'lucide-react';
import Link from 'next/link';

export default function SettingsPage() {
  const { data: session } = useSession();
  const [user, setUser] = useState<User | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [riskProfile, setRiskProfile] = useState<'Conservative' | 'Balanced' | 'Aggressive'>('Balanced');
  const [dailyDigest, setDailyDigest] = useState(true);

  useEffect(() => {
    if (session?.user?.id) {
      fetchUserSettings(session.user.id).then(data => {
        if (data) {
          setUser(data);
          setRiskProfile(data.riskProfile as any || 'Balanced');
          setDailyDigest(data.dailyDigestOptIn);
        }
      });
    }
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
    <div className="min-h-screen bg-[#F8F9FB] text-slate-900 p-6 lg:p-12 selection:bg-slate-900 selection:text-white">
      <div className="max-w-3xl mx-auto">
        <Link href="/dashboard" className="inline-flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-slate-900 mb-8 transition-colors">
          <ArrowLeft size={14} /> Back to Dashboard
        </Link>
        
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-2">Engine Settings</h1>
        <p className="text-slate-600 text-sm mb-8">Manage your paper trading balance, execution risk regime, and digest alerts.</p>

        <div className="space-y-6">
          {/* Account Status Card */}
          <div className="p-6 rounded-3xl border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_12px_28px_-4px_rgba(0,0,0,0.05)] bg-white">
            <h2 className="text-sm font-bold text-slate-900 mb-4">Sandbox Capital Allocation</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-2xl bg-slate-50 border border-black/[0.06] shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
                <div className="text-[11px] text-slate-500 font-medium mb-1">Starting Allocation</div>
                <div className="text-2xl font-bold font-mono text-slate-800">
                  ${(user?.startingBalance ?? 10000).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 border border-black/[0.06] shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
                <div className="text-[11px] text-slate-500 font-medium mb-1">Current Mark-to-Market</div>
                <div className="text-2xl font-bold font-mono text-emerald-600">
                  ${(user?.currentBalance ?? 10000).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              </div>
            </div>
          </div>

          {/* Risk Profile Selector */}
          <div className="p-6 rounded-3xl border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_12px_28px_-4px_rgba(0,0,0,0.05)] bg-white">
            <h2 className="text-sm font-bold text-slate-900 mb-1">Risk Regime</h2>
            <p className="text-xs text-slate-500 mb-4">Controls maximum capital committed per mirrored trade event.</p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {profiles.map(p => {
                const isSelected = riskProfile === p.id;
                return (
                  <div 
                    key={p.id}
                    onClick={() => setRiskProfile(p.id)}
                    className={`p-4 rounded-2xl border cursor-pointer transition-all duration-150 ${
                      isSelected 
                        ? 'border-slate-900 bg-slate-50 shadow-sm' 
                        : 'border-black/[0.06] bg-white hover:border-black/[0.12] hover:bg-slate-50/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-xs font-bold ${isSelected ? 'text-slate-900' : 'text-slate-600'}`}>
                        {p.id}
                      </span>
                      {isSelected && <span className="w-2 h-2 rounded-full bg-emerald-500" />}
                    </div>
                    <div className="text-[11px] text-slate-500 leading-relaxed font-medium">
                      {p.desc}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Preferences */}
          <div className="p-6 rounded-3xl border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_2px_8px_rgba(0,0,0,0.03),0_12px_28px_-4px_rgba(0,0,0,0.05)] bg-white">
            <h2 className="text-sm font-bold text-slate-900 mb-4">Digest &amp; Notification Preferences</h2>
            <label className="flex items-center justify-between cursor-pointer group p-3 rounded-2xl hover:bg-slate-50 transition-colors">
              <div>
                <div className="text-xs font-bold text-slate-900">Daily Performance Digest</div>
                <div className="text-[11px] text-slate-500 font-medium">Receive a daily summary email of mirrored whale trades and realized P&L.</div>
              </div>
              <div className="relative">
                <input 
                  type="checkbox" 
                  className="sr-only" 
                  checked={dailyDigest}
                  onChange={(e) => setDailyDigest(e.target.checked)}
                />
                <div className={`w-11 h-6 rounded-full transition-colors ${dailyDigest ? 'bg-slate-900' : 'bg-slate-200'}`} />
                <div className={`absolute left-0.5 top-0.5 w-5 h-5 rounded-full transition-transform ${dailyDigest ? 'translate-x-5 bg-white' : 'translate-x-0 bg-white shadow-sm'}`} />
              </div>
            </label>
          </div>

          <div className="flex items-center justify-between pt-2">
            {savedSuccess ? (
              <span className="text-xs font-bold text-emerald-600 flex items-center gap-1.5">
                ✓ Settings saved successfully.
              </span>
            ) : <span />}
            <Button 
              onClick={handleSave} 
              disabled={saving} 
              className="bg-slate-900 text-white px-6 py-2.5 font-semibold shadow-sm"
            >
              <Save size={15} /> {saving ? 'Saving Changes...' : 'Save Settings'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
