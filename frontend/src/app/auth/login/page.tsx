'use client';
import { useState, Suspense } from 'react';
import { signIn } from 'next-auth/react';
import { useRouter, useSearchParams } from 'next/navigation';
import { BrandLogo } from '@/components/ui/BrandLogo';
import { useTheme } from '@/context/ThemeContext';
import { Sun, Moon, Sparkles, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { guestLogin, setAuthToken } from '@/lib/api-client';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { theme, toggleTheme } = useTheme();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [guestStatus, setGuestStatus] = useState<'idle' | 'provisioning' | 'launching'>('idle');

  const displayedError = error || (searchParams.get('reason') === 'session-expired'
    ? 'Your session expired. Please sign in again to view your portfolio.' : '');

  const isGuestBusy = guestStatus !== 'idle';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await signIn('credentials', {
        email,
        password,
        redirect: false,
      });

      if (res?.error) {
        setError('Invalid email or password');
        setLoading(false);
      } else {
        window.location.href = '/dashboard';
      }
    } catch {
      setError('An unexpected error occurred during sign in');
      setLoading(false);
    }
  };

  const handleGuestLogin = async () => {
    setGuestStatus('provisioning');
    setError('');

    try {
      // 1. Fast path: Client retrieves isolated credentials directly from backend
      const guestCreds = await guestLogin();
      if (guestCreds && guestCreds.email && guestCreds.password) {
        if (guestCreds.access_token) {
          setAuthToken(guestCreds.access_token);
        }
        setGuestStatus('launching');

        // Authorize with NextAuth using pre-provisioned guest credentials
        // Use a 3-second safeguard race so serverless cold starts never freeze the UI
        try {
          await Promise.race([
            signIn('credentials', {
              email: guestCreds.email,
              password: guestCreds.password,
              guestToken: guestCreds.access_token || '',
              guestId: guestCreds.id || '',
              isGuest: 'true',
              redirect: false,
            }),
            new Promise((resolve) => setTimeout(resolve, 3000))
          ]);
        } catch (authErr) {
          console.debug("NextAuth fast-path note:", authErr);
        }

        // Hard navigate so Next.js hydrates the authenticated session cleanly
        window.location.href = '/dashboard';
        return;
      }

      // 2. Direct server-side fallback
      setGuestStatus('launching');
      try {
        await Promise.race([
          signIn('credentials', {
            isGuest: 'true',
            redirect: false,
          }),
          new Promise((resolve) => setTimeout(resolve, 4000))
        ]);
      } catch (authErr) {
        console.debug("Fallback auth note:", authErr);
      }

      window.location.href = '/dashboard';
    } catch (err) {
      console.error("Guest login exception:", err);
      setError('An error occurred provisioning guest session');
      setGuestStatus('idle');
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FB] dark:bg-[#000000] text-slate-900 dark:text-white flex flex-col items-center justify-center p-6 selection:bg-[#00D09C] selection:text-black transition-colors duration-150 relative">
      {/* Top right theme toggle */}
      <div className="absolute top-6 right-6">
        <button
          onClick={toggleTheme}
          className="w-10 h-10 rounded-full bg-white dark:bg-[#16171B] hover:bg-slate-100 dark:hover:bg-[#24262E] border border-black/[0.08] dark:border-white/10 text-slate-700 dark:text-white flex items-center justify-center transition-all cursor-pointer shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C]"
          aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
        >
          {theme === 'light' ? <Moon size={16} aria-hidden="true" /> : <Sun size={16} aria-hidden="true" className="text-amber-400" />}
        </button>
      </div>

      {/* Responsive Guest Session Transition Overlay */}
      {isGuestBusy && (
        <div className="fixed inset-0 z-50 bg-[#F8F9FB]/95 dark:bg-[#000000]/95 backdrop-blur-sm flex flex-col items-center justify-center p-6 transition-all duration-300">
          <div className="flex flex-col items-center max-w-sm text-center space-y-4">
            <div className="relative flex items-center justify-center">
              <div className="w-12 h-12 rounded-full border-2 border-[#00D09C] border-t-transparent animate-spin" />
              <Sparkles size={16} className="text-amber-400 absolute" />
            </div>
            <div className="space-y-1.5">
              <h2 className="text-base font-bold text-slate-950 dark:text-white tracking-tight">
                {guestStatus === 'provisioning' ? 'Provisioning Isolated Sandbox…' : 'Entering Dashboard…'}
              </h2>
              <p className="text-xs text-slate-500 dark:text-[#8E8F99]">
                Allocating $10,000 pUSD paper trading capital & connecting live whale streams.
              </p>
            </div>
            <button
              onClick={() => { window.location.href = '/dashboard'; }}
              className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 hover:text-[#00D09C] dark:hover:text-[#00D09C] underline transition-colors cursor-pointer"
            >
              Taking longer than expected? Click here to enter dashboard →
            </button>
          </div>
        </div>
      )}

      <div className="w-full max-w-md p-8 sm:p-9 rounded-[28px] bg-white dark:bg-[#16171B] border border-black/[0.08] dark:border-white/10 shadow-xl space-y-6">
        <div className="text-center flex flex-col items-center">
          <div className="mb-4">
            <BrandLogo size="lg" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-950 dark:text-white mb-1">Sign in to Baleen</h1>
          <p className="text-slate-500 dark:text-[#8E8F99] text-xs">Access your automated whale-index dashboard</p>
        </div>

        {displayedError && (
          <div className="p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 text-rose-700 dark:text-rose-400 text-xs text-center font-semibold" role="alert">
            {displayedError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="login-email" className="block text-[11px] text-slate-600 dark:text-[#8E8F99] mb-1.5 font-bold">Email Address</label>
            <input 
              id="login-email"
              type="email" 
              name="email"
              autoComplete="email"
              spellCheck={false}
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 rounded-2xl px-4 py-3 text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] transition-colors"
              placeholder="you@domain.com"
            />
          </div>
          <div>
            <label htmlFor="login-password" className="block text-[11px] text-slate-600 dark:text-[#8E8F99] mb-1.5 font-bold">Password</label>
            <input 
              id="login-password"
              type="password" 
              name="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-slate-50 dark:bg-[#1C1D22] border border-black/[0.08] dark:border-white/10 rounded-2xl px-4 py-3 text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] transition-colors"
              placeholder="••••••••"
            />
          </div>
          <button 
            type="submit" 
            className="w-full py-3.5 mt-2 rounded-full bg-slate-950 dark:bg-white text-white dark:text-black text-xs font-bold hover:bg-slate-800 dark:hover:bg-slate-200 transition-all shadow-md cursor-pointer disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] active:scale-[0.98]"
            disabled={loading || isGuestBusy}
          >
            {loading ? 'Authenticating…' : 'Sign In'}
          </button>
        </form>

        <div className="relative flex items-center py-1">
          <div className="flex-grow border-t border-black/[0.06] dark:border-white/10"></div>
          <span className="flex-shrink-0 mx-3 text-[10px] uppercase font-mono text-slate-400 dark:text-[#8E8F99] font-bold">or</span>
          <div className="flex-grow border-t border-black/[0.06] dark:border-white/10"></div>
        </div>

        <button 
          type="button"
          className="w-full py-3.5 rounded-full bg-[#F1F3F5] dark:bg-[#1C1D22] hover:bg-[#E2E6EA] dark:hover:bg-[#2C2D35] border border-black/[0.08] dark:border-white/10 text-slate-900 dark:text-white text-xs font-bold transition-all shadow-xs cursor-pointer flex items-center justify-center gap-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] active:scale-[0.98] disabled:opacity-50"
          onClick={handleGuestLogin}
          disabled={loading || isGuestBusy}
        >
          {isGuestBusy ? (
            <Loader2 size={14} className="animate-spin text-[#00D09C]" aria-hidden="true" />
          ) : (
            <Sparkles size={14} className="text-amber-500" aria-hidden="true" />
          )}
          <span>{isGuestBusy ? 'Opening Dashboard…' : 'Explore as Guest (Instant Demo)'}</span>
        </button>

        <p className="text-center text-xs text-slate-500 dark:text-[#8E8F99] pt-2">
          Don&apos;t have an account?{' '}
          <Link href="/auth/signup" className="text-slate-950 dark:text-white hover:underline font-bold focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00D09C] rounded-md px-1 py-0.5">
            Create Free Sandbox
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return <Suspense fallback={<p role="status">Loading sign in…</p>}><LoginForm /></Suspense>;
}
