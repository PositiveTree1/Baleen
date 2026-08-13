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
  const [riskProfile, setRiskProfile] = useState<'Conservative' | 'Balanced' | 'Aggressive'>('Balanced');
  const [dailyDigest, setDailyDigest] = useState(true);

  useEffect(() => {
    if (session?.user?.id) {
      fetchUserSettings(session.user.id).then(data => {
        if (data) {
          setUser(data);
          setRiskProfile(data.riskProfile);
          setDailyDigest(data.dailyDigestOptIn);
        }
      });
    }
  }, [session]);

  async function handleSave() {
    if (!session?.user?.id) return;
    setSaving(true);
    const updated = await updateUserSettings(session.user.id, {
      riskProfile,
      dailyDigestOptIn: dailyDigest
    });
    if (updated) {
      setUser(updated);
    }
    setSaving(false);
  }

  const profiles = [
    { id: 'Conservative', desc: 'Lower position sizing, stricter slippage limits. Prioritizes capital preservation.' },
    { id: 'Balanced', desc: 'Standard position sizing matching whale conviction. Balanced risk/reward.' },
    { id: 'Aggressive', desc: 'Higher leverage, looser slippage. Captures maximum upside with higher volatility.' }
  ] as const;

  return (
    <div className="min-h-screen bg-baleen-obsidian p-6">
      <div className="max-w-3xl mx-auto mt-8">
        <Link href="/dashboard" className="inline-flex items-center gap-2 text-baleen-muted hover:text-baleen-white mb-8 transition-colors">
          <ArrowLeft size={16} /> Back to Dashboard
        </Link>
        
        <h1 className="text-3xl font-bold text-baleen-white mb-8">Engine Settings</h1>

        <div className="space-y-8">
          {/* Read-only balances */}
          <Card>
            <h2 className="text-lg font-semibold text-baleen-white mb-4">Account Status</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-white/5 rounded-lg border border-white/5">
                <div className="text-xs text-baleen-muted mb-1">Starting Balance</div>
                <div className="text-xl font-mono text-baleen-white">
                  ${user?.startingBalance.toLocaleString(undefined, { minimumFractionDigits: 2 }) || '0.00'}
                </div>
              </div>
              <div className="p-4 bg-white/5 rounded-lg border border-white/5">
                <div className="text-xs text-baleen-muted mb-1">Current Balance</div>
                <div className="text-xl font-mono text-baleen-white">
                  ${user?.currentBalance.toLocaleString(undefined, { minimumFractionDigits: 2 }) || '0.00'}
                </div>
              </div>
            </div>
          </Card>

          {/* Risk Profile */}
          <Card>
            <h2 className="text-lg font-semibold text-baleen-white mb-4">Risk Profile</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {profiles.map(p => (
                <div 
                  key={p.id}
                  onClick={() => setRiskProfile(p.id)}
                  className={`p-4 rounded-lg border cursor-pointer transition-all ${
                    riskProfile === p.id 
                      ? 'border-baleen-cyan bg-baleen-cyan/10' 
                      : 'border-white/10 hover:border-white/30 bg-white/5'
                  }`}
                >
                  <div className={`font-semibold mb-2 ${riskProfile === p.id ? 'text-baleen-cyan' : 'text-baleen-white'}`}>
                    {p.id}
                  </div>
                  <div className="text-xs text-baleen-muted leading-relaxed">
                    {p.desc}
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Preferences */}
          <Card>
            <h2 className="text-lg font-semibold text-baleen-white mb-4">Preferences</h2>
            <label className="flex items-center gap-4 cursor-pointer group">
              <div className="relative">
                <input 
                  type="checkbox" 
                  className="sr-only" 
                  checked={dailyDigest}
                  onChange={(e) => setDailyDigest(e.target.checked)}
                />
                <div className={`w-10 h-6 rounded-full transition-colors ${dailyDigest ? 'bg-baleen-cyan' : 'bg-white/10'}`}></div>
                <div className={`absolute left-1 top-1 w-4 h-4 rounded-full bg-white transition-transform ${dailyDigest ? 'translate-x-4' : 'translate-x-0'}`}></div>
              </div>
              <div>
                <div className="font-medium text-baleen-white">Daily Digest Opt-in</div>
                <div className="text-xs text-baleen-muted">Receive a daily email summary of mirrored trades and P&L.</div>
              </div>
            </label>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSave} disabled={saving} className="flex items-center gap-2">
              <Save size={16} /> {saving ? 'Saving...' : 'Save Settings'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
