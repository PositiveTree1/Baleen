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
    <div className="min-h-screen bg-baleen-obsidian flex items-center justify-center p-4">
      <Card variant="elevated" className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-baleen-white mb-2">Initialize Engine</h1>
          <p className="text-baleen-muted text-sm">Sign in to your Baleen dashboard.</p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded bg-baleen-red/10 border border-baleen-red/20 text-baleen-red text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 mb-6">
          <div>
            <label className="block text-xs text-baleen-muted mb-1 uppercase tracking-wider">Email</label>
            <input 
              type="email" 
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-baleen-white focus:outline-none focus:border-baleen-cyan transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs text-baleen-muted mb-1 uppercase tracking-wider">Password</label>
            <input 
              type="password" 
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-baleen-white focus:outline-none focus:border-baleen-cyan transition-colors"
            />
          </div>
          <Button type="submit" className="w-full mt-2" disabled={loading}>
            {loading ? 'Authenticating...' : 'Sign In'}
          </Button>
        </form>

        <div className="relative flex items-center py-4">
          <div className="flex-grow border-t border-white/10"></div>
          <span className="flex-shrink-0 mx-4 text-xs text-baleen-muted">OR</span>
          <div className="flex-grow border-t border-white/10"></div>
        </div>

        <Button 
          variant="secondary" 
          className="w-full mb-4"
          onClick={handleGuestLogin}
          disabled={loading}
        >
          Continue as Guest
        </Button>

        <Button 
          variant="secondary" 
          className="w-full mb-6"
          disabled={!process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID}
          onClick={() => signIn('google', { callbackUrl: '/dashboard' })}
        >
          {process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ? 'Sign in with Google' : 'Google Auth Disabled'}
        </Button>

        <p className="text-center text-sm text-baleen-muted">
          New to Baleen?{' '}
          <Link href="/auth/signup" className="text-baleen-cyan hover:underline">
            Request Access
          </Link>
        </p>
      </Card>
    </div>
  );
}
