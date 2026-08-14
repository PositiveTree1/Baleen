'use client';
import { useState } from 'react';
import { signIn } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import Link from 'next/link';
import { guestLogin } from '@/lib/api-client';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const res = await signIn('credentials', {
      email,
      password,
      redirect: false,
    });

    if (res?.error) {
      setError('Invalid email or password');
      setLoading(false);
    } else {
      router.push('/dashboard');
      router.refresh();
    }
  };

  const handleGuestLogin = async () => {
    setLoading(true);
    setError('');
    const guest = await guestLogin();
    if (!guest) {
      setError('Failed to create guest session');
      setLoading(false);
      return;
    }
    const res = await signIn('credentials', {
      email: guest.email,
      password: guest.password,
      redirect: false,
    });
    if (res?.error) {
      setError('Guest login failed');
      setLoading(false);
    } else {
      router.push('/dashboard');
      router.refresh();
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FB] text-slate-900 flex items-center justify-center p-6 selection:bg-slate-900 selection:text-white">
      <div className="w-full max-w-md p-8 rounded-3xl bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_4px_16px_rgba(0,0,0,0.04),0_24px_48px_-12px_rgba(0,0,0,0.08)]">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 mb-1.5">Sign in to Baleen</h1>
          <p className="text-slate-500 text-xs font-normal">Access your automated whale-index dashboard</p>
        </div>

        {error && (
          <div className="mb-5 p-3 rounded-2xl bg-rose-50 border border-rose-200 text-rose-700 text-xs text-center font-semibold shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 mb-6">
          <div>
            <label className="block text-[11px] text-slate-600 mb-1.5 font-semibold">Email Address</label>
            <input 
              type="email" 
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full bg-slate-50 border border-black/[0.08] rounded-xl px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-slate-500 transition-colors shadow-[inset_0_1px_2px_rgba(0,0,0,0.03)]"
              placeholder="you@domain.com"
            />
          </div>
          <div>
            <label className="block text-[11px] text-slate-600 mb-1.5 font-semibold">Password</label>
            <input 
              type="password" 
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-slate-50 border border-black/[0.08] rounded-xl px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-slate-500 transition-colors shadow-[inset_0_1px_2px_rgba(0,0,0,0.03)]"
              placeholder="••••••••"
            />
          </div>
          <Button type="submit" className="w-full mt-3 font-semibold" disabled={loading}>
            {loading ? 'Authenticating...' : 'Sign In'}
          </Button>
        </form>

        <div className="relative flex items-center py-4">
          <div className="flex-grow border-t border-black/[0.06]"></div>
          <span className="flex-shrink-0 mx-4 text-[10px] uppercase font-mono text-slate-400 font-bold">Fast Access</span>
          <div className="flex-grow border-t border-black/[0.06]"></div>
        </div>

        <Button 
          variant="secondary" 
          className="w-full mb-3 text-xs font-semibold shadow-sm"
          onClick={handleGuestLogin}
          disabled={loading}
        >
          Explore as Guest (Instant Demo)
        </Button>

        <p className="text-center text-xs text-slate-500 mt-6">
          Don&apos;t have an account?{' '}
          <Link href="/auth/signup" className="text-slate-900 hover:underline font-bold">
            Create Free Sandbox
          </Link>
        </p>
      </div>
    </div>
  );
}
