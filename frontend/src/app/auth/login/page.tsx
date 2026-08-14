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
    <div className="min-h-screen bg-[#090A0F] text-white flex items-center justify-center p-6 selection:bg-white selection:text-black">
      <div className="w-full max-w-md p-8 rounded-3xl bg-zinc-900/40 border border-white/[0.08] shadow-apple backdrop-blur-2xl">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-white mb-1.5">Sign in to Baleen</h1>
          <p className="text-zinc-400 text-xs font-normal">Access your automated whale-index dashboard</p>
        </div>

        {error && (
          <div className="mb-5 p-3 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs text-center font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 mb-6">
          <div>
            <label className="block text-[11px] text-zinc-400 mb-1.5 font-medium">Email Address</label>
            <input 
              type="email" 
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-white/30 transition-colors"
              placeholder="you@domain.com"
            />
          </div>
          <div>
            <label className="block text-[11px] text-zinc-400 mb-1.5 font-medium">Password</label>
            <input 
              type="password" 
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-white/30 transition-colors"
              placeholder="••••••••"
            />
          </div>
          <Button type="submit" className="w-full mt-3 bg-white text-zinc-950 font-semibold" disabled={loading}>
            {loading ? 'Authenticating...' : 'Sign In'}
          </Button>
        </form>

        <div className="relative flex items-center py-4">
          <div className="flex-grow border-t border-white/[0.06]"></div>
          <span className="flex-shrink-0 mx-4 text-[10px] uppercase font-mono text-zinc-500">Fast Access</span>
          <div className="flex-grow border-t border-white/[0.06]"></div>
        </div>

        <Button 
          variant="secondary" 
          className="w-full mb-3 text-xs"
          onClick={handleGuestLogin}
          disabled={loading}
        >
          Explore as Guest (Instant Demo)
        </Button>

        <p className="text-center text-xs text-zinc-500 mt-6">
          Don&apos;t have an account?{' '}
          <Link href="/auth/signup" className="text-white hover:underline font-medium">
            Create Free Sandbox
          </Link>
        </p>
      </div>
    </div>
  );
}
