'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { signIn } from 'next-auth/react';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { useTheme } from '@/context/ThemeContext';
import { Sun, Moon } from 'lucide-react';
import Link from 'next/link';
import { signUp } from '@/lib/api-client';

export default function SignupPage() {
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();
  const [form, setForm] = useState({ email: '', password: '', confirm: '', balance: '10000' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const presets = ['1000', '5000', '10000', '25000'];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password !== form.confirm) {
      return setError('Passwords do not match');
    }
    
    setLoading(true);
    setError('');

    try {
      const account = await signUp(form.email, form.password, parseFloat(form.balance));
      if (!account) {
        setError('Could not create this account. Check your details, or sign in if you already have an account.');
        return;
      }
      
      const res = await signIn('credentials', {
        email: form.email,
        password: form.password,
        redirect: false,
      });

      if (res?.ok) {
        router.push('/dashboard');
        router.refresh();
      } else {
        setError('Your account was created, but sign in failed. Please use the sign-in page.');
      }
    } catch {
      setError('Could not complete signup. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen text-white flex flex-col items-center justify-center p-6 selection:bg-[#00D09C] selection:text-black relative z-10">
      {/* Top right theme toggle */}
      <div className="absolute top-6 right-6">
        <button
          onClick={toggleTheme}
          className="w-10 h-10 rounded-full ctrl-btn text-white flex items-center justify-center transition-all cursor-pointer shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C]"
          aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
        >
          {theme === 'light' ? <Moon size={16} aria-hidden="true" /> : <Sun size={16} aria-hidden="true" className="text-amber-400" />}
        </button>
      </div>

      <div className="glass-card w-full max-w-md p-8 sm:p-9 rounded-[32px] space-y-6 text-white shadow-2xl">
        <div className="text-center flex flex-col items-center">
          <div className="mb-4">
            <BrandLogo size="lg" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white mb-1">Create Sandbox Account</h1>
          <p className="text-white/60 text-xs">Test automated whale mirroring with paper funds</p>
        </div>

        {error && (
          <div className="p-3.5 rounded-2xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs text-center font-semibold" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="signup-email" className="block text-[11px] text-white/70 mb-1.5 font-bold">Email Address</label>
            <input 
              id="signup-email"
              type="email" 
              name="email"
              autoComplete="email"
              spellCheck={false}
              required
              value={form.email}
              onChange={e => setForm({ ...form, email: e.target.value })}
              className="w-full bg-white/[0.06] border border-white/15 rounded-2xl px-4 py-3 text-sm text-white placeholder-white/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] transition-colors"
              placeholder="you@domain.com"
            />
          </div>
          <div>
            <label htmlFor="signup-password" className="block text-[11px] text-white/70 mb-1.5 font-bold">Password</label>
            <input 
              id="signup-password"
              type="password" 
              name="password"
              autoComplete="new-password"
              required
              value={form.password}
              onChange={e => setForm({ ...form, password: e.target.value })}
              className="w-full bg-white/[0.06] border border-white/15 rounded-2xl px-4 py-3 text-sm text-white placeholder-white/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] transition-colors"
              placeholder="••••••••"
            />
          </div>
          <div>
            <label htmlFor="signup-confirm" className="block text-[11px] text-white/70 mb-1.5 font-bold">Confirm Password</label>
            <input 
              id="signup-confirm"
              type="password" 
              name="confirmPassword"
              autoComplete="new-password"
              required
              value={form.confirm}
              onChange={e => setForm({ ...form, confirm: e.target.value })}
              className="w-full bg-white/[0.06] border border-white/15 rounded-2xl px-4 py-3 text-sm text-white placeholder-white/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] transition-colors"
              placeholder="••••••••"
            />
          </div>

          <div>
            <label className="block text-[11px] text-white/70 mb-1.5 font-bold">Starting Paper Balance (USD)</label>
            <div className="grid grid-cols-4 gap-2 mb-2">
              {presets.map(p => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setForm({ ...form, balance: p })}
                  className={`py-2 text-xs font-bold rounded-xl border transition-all cursor-pointer font-mono tabular-nums focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] ${
                    form.balance === p 
                      ? 'bg-[#00D09C] text-black border-[#00D09C] shadow-[0_0_12px_rgba(0,208,156,0.25)]' 
                      : 'bg-white/[0.04] text-white/70 border-white/10 hover:border-white/20'
                  }`}
                >
                  ${parseInt(p).toLocaleString()}
                </button>
              ))}
            </div>
          </div>

          <button 
            type="submit" 
            className="w-full py-3.5 mt-3 rounded-full glass-button text-white text-xs font-bold transition-all shadow-md cursor-pointer disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] active:scale-[0.98]"
            disabled={loading}
          >
            {loading ? 'Creating Sandbox…' : 'Open Sandbox Account'}
          </button>
        </form>

        <p className="text-center text-xs text-white/60 pt-2">
          Already have an account?{' '}
          <Link href="/auth/login" className="text-white hover:underline font-bold focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] rounded-md px-1 py-0.5">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}
