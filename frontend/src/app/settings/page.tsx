'use client';
import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { 
  fetchUserSettings, 
  updateUserSettings, 
  fetchPortfolioSummary,
  saveLiveCredentials,
  fetchLiveCredentials,
  testLiveConnection,
  toggleLiveTrading
} from '@/lib/api-client';
import { User, PortfolioSummary, TestConnectionResult } from '@/types';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { ResetSandboxModal } from '@/components/dashboard/ResetSandboxModal';
import { 
  ArrowLeft, 
  Save, 
  Moon, 
  Sun, 
  Key, 
  ShieldCheck, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  Lock,
  ExternalLink,
  Zap
} from 'lucide-react';
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

  // L2 Live Trading Credentials State
  const [proxyAddress, setProxyAddress] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [passphrase, setPassphrase] = useState('');
  const [isConfigured, setIsConfigured] = useState(false);
  const [isLiveActive, setIsLiveActive] = useState(false);
  const [liveBalanceUsdc, setLiveBalanceUsdc] = useState<number>(0);
  const [lastVerifiedAt, setLastVerifiedAt] = useState<string | null>(null);
  const [savingCredentials, setSavingCredentials] = useState(false);
  const [credentialsSavedSuccess, setCredentialsSavedSuccess] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<TestConnectionResult | null>(null);
  const [credentialError, setCredentialError] = useState<string | null>(null);
  const [showLiveConfirmModal, setShowLiveConfirmModal] = useState(false);

  const loadUserData = () => {
    if (session?.user?.id) {
      Promise.all([
        fetchUserSettings(session.user.id),
        fetchPortfolioSummary(session.user.id),
        fetchLiveCredentials(session.user.id)
      ]).then(([userData, portfolioData, liveCreds]) => {
        if (userData) {
          setUser(userData);
          setRiskProfile(userData.riskProfile as any || 'Balanced');
          setDailyDigest(userData.dailyDigestOptIn);
        }
        if (portfolioData) {
          setPortfolio(portfolioData);
        }
        if (liveCreds) {
          setIsConfigured(liveCreds.is_configured);
          setIsLiveActive(liveCreds.is_live_active);
          setLiveBalanceUsdc(liveCreds.live_balance_usdc || 0);
          setLastVerifiedAt(liveCreds.last_verified_at);
          if (liveCreds.polymarket_wallet_address) {
            setProxyAddress(liveCreds.polymarket_wallet_address);
          }
          if (liveCreds.clob_api_key_masked) {
            setApiKey(liveCreds.clob_api_key_masked);
          }
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

  async function handleSaveCredentials() {
    if (!proxyAddress.trim() || !apiKey.trim() || !apiSecret.trim() || !passphrase.trim()) {
      setCredentialError("All four fields (Proxy Address, CLOB API Key, Secret, and Passphrase) are required.");
      return;
    }
    setSavingCredentials(true);
    setCredentialError(null);
    setCredentialsSavedSuccess(false);
    try {
      const res = await saveLiveCredentials({
        userId: session?.user?.id,
        polymarketWalletAddress: proxyAddress.trim(),
        clobApiKey: apiKey.trim(),
        clobApiSecret: apiSecret.trim(),
        clobApiPassphrase: passphrase.trim()
      });
      if (res) {
        setIsConfigured(res.is_configured);
        setIsLiveActive(res.is_live_active);
        setCredentialsSavedSuccess(true);
        setTimeout(() => setCredentialsSavedSuccess(false), 4000);
      }
    } catch (err: any) {
      setCredentialError(err.message || "Failed to save live trading credentials.");
    } finally {
      setSavingCredentials(false);
    }
  }

  async function handleTestConnection() {
    setTestingConnection(true);
    setCredentialError(null);
    setTestResult(null);
    try {
      const res = await testLiveConnection({
        userId: session?.user?.id,
        polymarketWalletAddress: proxyAddress.trim() || undefined,
        clobApiKey: apiKey.trim() || undefined,
        clobApiSecret: apiSecret.trim() || undefined,
        clobApiPassphrase: passphrase.trim() || undefined
      });
      setTestResult(res);
      if (res.balance_usdc !== undefined) {
        setLiveBalanceUsdc(res.balance_usdc);
      }
      if (res.verified_at) {
        setLastVerifiedAt(res.verified_at);
      }
    } catch (err: any) {
      setCredentialError(err.message || "Connection test failed. Please verify your CLOB keys and Proxy Address.");
    } finally {
      setTestingConnection(false);
    }
  }

  async function handleToggleLiveTrading(targetState: boolean) {
    if (targetState && !isConfigured) {
      setCredentialError("Please enter and save valid Polymarket CLOB credentials before enabling live trading.");
      return;
    }
    if (targetState) {
      setShowLiveConfirmModal(true);
      return;
    }
    await executeToggle(false);
  }

  async function executeToggle(enabled: boolean) {
    try {
      const res = await toggleLiveTrading(enabled, session?.user?.id);
      setIsLiveActive(res.is_live_active);
      setShowLiveConfirmModal(false);
    } catch (err: any) {
      setCredentialError(err.message || "Failed to toggle live trading.");
    }
  }

  const profiles = [
    { id: 'Conservative', desc: 'Lower position sizing (5% max), strictest slippage tolerances. Prioritizes capital preservation.' },
    { id: 'Balanced', desc: 'Pure proportional sleeve sizing scaled dynamically by whale position fractions.' },
    { id: 'Aggressive', desc: 'Higher leverage allocation, looser slippage window. Maximizes upside volatility.' }
  ] as const;

  return (
    <div className="min-h-screen bg-[#F8F9FB] dark:bg-[#000000] text-slate-900 dark:text-white p-6 lg:p-12 selection:bg-[#00D09C] selection:text-black transition-colors duration-150">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <BrandLogo size="sm" />
            <span className="text-slate-300 dark:text-slate-700">|</span>
            <Link href="/dashboard" className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 dark:text-[#8E8F99] hover:text-slate-950 dark:hover:text-white transition-colors">
              <ArrowLeft size={14} /> Back to Dashboard
            </Link>
          </div>

          <button
            onClick={toggleTheme}
            className="w-9 h-9 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-white flex items-center justify-center transition-all cursor-pointer shadow-2xs"
            aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          >
            {theme === 'light' ? <Moon size={15} /> : <Sun size={15} className="text-amber-400" />}
          </button>
        </div>
        
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-950 dark:text-white mb-2">Engine Settings</h1>
          <p className="text-slate-600 dark:text-[#8E8F99] text-sm">Manage your paper trading balance, execution risk regime, and L2 live trading credentials.</p>
        </div>

        <div className="space-y-6">
          {/* L2 API Key & Live Trading Credentials Card */}
          <div className="revolut-card bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 p-6 sm:p-8 rounded-[28px] shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-black/[0.06] dark:border-white/5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                  <Key size={18} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-950 dark:text-white flex items-center gap-2">
                    Polymarket CLOB L2 Credentials
                    {isConfigured && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-[#00D09C]/10 text-emerald-600 dark:text-[#00D09C] border border-emerald-200 dark:border-[#00D09C]/20 font-mono">
                        Configured
                      </span>
                    )}
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-[#8E8F99] mt-0.5">
                    Connect your Polymarket Layer 2 CLOB API keys for automated non-custodial copy trading.
                  </p>
                </div>
              </div>

              {/* Master Live Trading Toggle */}
              <div className="flex items-center gap-3 self-end sm:self-auto">
                <div className="text-right">
                  <div className="text-[11px] font-bold text-slate-900 dark:text-white">
                    {isLiveActive ? 'Live Execution Active' : 'Live Execution Paused'}
                  </div>
                  <div className="text-[10px] text-slate-500 dark:text-[#8E8F99]">
                    {isLiveActive ? 'Mirroring to CLOB' : 'Paper Sandbox Only'}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleToggleLiveTrading(!isLiveActive)}
                  className={`w-12 h-6 rounded-full p-0.5 transition-colors cursor-pointer ${
                    isLiveActive ? 'bg-[#00D09C]' : 'bg-slate-300 dark:bg-[#2C2D35]'
                  }`}
                  aria-label="Toggle Live Trading Execution"
                >
                  <div className={`w-5 h-5 rounded-full bg-white dark:bg-black shadow-xs transform transition-transform ${isLiveActive ? 'translate-x-6' : 'translate-x-0'}`} />
                </button>
              </div>
            </div>

            {/* Error or Alert Banner */}
            {credentialError && (
              <div className="p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-xs text-rose-700 dark:text-rose-400 flex items-start gap-2.5">
                <AlertTriangle size={15} className="shrink-0 mt-0.5" />
                <span>{credentialError}</span>
              </div>
            )}

            {/* Success Feedback Banner */}
            {credentialsSavedSuccess && (
              <div className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-[#00D09C]/10 border border-emerald-200 dark:border-[#00D09C]/20 text-xs text-emerald-700 dark:text-[#00D09C] flex items-center gap-2.5">
                <CheckCircle2 size={15} />
                <span>L2 credentials securely saved! You can now test the connection and fetch your live USDC balance.</span>
              </div>
            )}

            {/* Test Connection Result Box */}
            {testResult && (
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.06] dark:border-white/5 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-white">
                    <ShieldCheck size={16} className="text-[#00D09C]" />
                    <span>Connection Verified</span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500 dark:text-[#8E8F99]">
                    {new Date(testResult.verified_at).toLocaleTimeString()}
                  </span>
                </div>
                <div className="flex items-center justify-between pt-1">
                  <span className="text-xs text-slate-500 dark:text-[#8E8F99]">Verified USDC Balance:</span>
                  <span className="text-lg font-bold font-mono text-[#00D09C]">
                    ${testResult.balance_usdc.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USDC
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-[#8E8F99]">{testResult.status_message}</p>
              </div>
            )}

            {/* Inputs Grid */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                  Polymarket Proxy Wallet Address (0x...)
                </label>
                <input
                  type="text"
                  placeholder="0x1234...abcd"
                  value={proxyAddress}
                  onChange={(e) => setProxyAddress(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                />
                <p className="text-[10px] text-slate-500 dark:text-[#8E8F99] mt-1">
                  Your deposit proxy wallet shown in Polymarket Profile &gt; Deposit &gt; Copy Address.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    CLOB API Key
                  </label>
                  <input
                    type="text"
                    placeholder="API Key"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    CLOB API Secret
                  </label>
                  <input
                    type="password"
                    placeholder="••••••••••••••••"
                    value={apiSecret}
                    onChange={(e) => setApiSecret(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-[#8E8F99] mb-1.5">
                    CLOB Passphrase
                  </label>
                  <input
                    type="password"
                    placeholder="••••••••"
                    value={passphrase}
                    onChange={(e) => setPassphrase(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 text-xs font-mono text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#00D09C]"
                  />
                </div>
              </div>
            </div>

            {/* Action Buttons Row */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
              <div className="text-[11px] text-slate-500 dark:text-[#8E8F99] flex items-center gap-1.5">
                <Lock size={12} />
                <span>Credentials are encrypted and never exposed in cleartext.</span>
              </div>

              <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testingConnection || (!proxyAddress && !isConfigured)}
                  className="px-4 py-2.5 rounded-full bg-slate-100 dark:bg-[#1C1D22] hover:bg-slate-200 dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-xs font-bold text-slate-800 dark:text-white transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  <RefreshCw size={13} className={testingConnection ? 'animate-spin' : ''} />
                  <span>{testingConnection ? 'Pinging CLOB...' : 'Test Connection & Fetch L2 Balance'}</span>
                </button>

                <button
                  type="button"
                  onClick={handleSaveCredentials}
                  disabled={savingCredentials}
                  className="px-5 py-2.5 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black hover:bg-slate-800 dark:hover:bg-slate-200 text-xs font-bold transition-all shadow-sm flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  <Save size={13} />
                  <span>{savingCredentials ? 'Saving...' : 'Save Credentials'}</span>
                </button>
              </div>
            </div>
          </div>

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

        {/* Live Trading Activation Warning Modal */}
        {showLiveConfirmModal && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white dark:bg-[#16171B] border border-black/10 dark:border-white/10 p-6 sm:p-8 rounded-[28px] max-w-md w-full shadow-2xl space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 flex items-center justify-center text-amber-600 dark:text-amber-400">
                <AlertTriangle size={24} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-950 dark:text-white">Enable Real Money Live Trading?</h3>
                <p className="text-xs text-slate-600 dark:text-[#8E8F99] mt-2 leading-relaxed">
                  You are about to activate real Polymarket CLOB trade execution. Real USDC from proxy wallet <span className="font-mono text-slate-900 dark:text-white font-bold">{proxyAddress.slice(0, 8)}...</span> will be committed to mirror whale signals according to Pure Proportional Sleeve Sizing.
                </p>
              </div>
              <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 text-[11px] text-amber-800 dark:text-amber-300">
                ⚠️ Make sure you have tested your API connection and verified your USDC balance before proceeding.
              </div>
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowLiveConfirmModal(false)}
                  className="px-5 py-2.5 rounded-full border border-black/10 dark:border-white/10 text-xs font-semibold text-slate-700 dark:text-white hover:bg-slate-100 dark:hover:bg-[#1C1D22] transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => executeToggle(true)}
                  className="px-6 py-2.5 rounded-full bg-[#00D09C] hover:bg-[#00b084] text-black text-xs font-bold transition-all shadow-md cursor-pointer"
                >
                  Confirm & Enable Live Trading
                </button>
              </div>
            </div>
          </div>
        )}

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
