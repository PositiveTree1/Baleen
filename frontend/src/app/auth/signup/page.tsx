'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { signIn } from 'next-auth/react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import Link from 'next/link';
import { signUp } from '@/lib/api-client';

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: '', password: '', confirm: '', balance: '10000' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password !== form.confirm) {
      return setError('Passwords do not match');
    }
    
    setLoading(true);
    setError('');

    const user = await signUp(form.email, form.password, parseFloat(form.balance));
    
    if (!user) {
      setError('Failed to create account. Email may be in use.');
      setLoading(false);
      return;
    }

    // Auto sign in
    const res = await signIn('credentials', {
      email: form.email,
      password: form.password,
      redirect: false,
    });

    if (res?.ok) {
      router.push('/dashboard');
      router.refresh();
    } else {
      router.push('/auth/login');
    }
  };

  return (
    <div className="min-h-screen bg-baleen-obsidian flex items-center justify-center p-4">
      <Card variant="elevated" className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-baleen-white mb-2">Deploy Engine</h1>
          <p className="text-baleen-muted text-sm">Create your non-custodial copy-trading account.</p>
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
              value={form.email}
              onChange={e => setForm({...form, email: e.target.value})}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-baleen-white focus:outline-none focus:border-baleen-cyan transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs text-baleen-muted mb-1 uppercase tracking-wider">Password</label>
            <input 
              type="password" 
              required
              value={form.password}
              onChange={e => setForm({...form, password: e.target.value})}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-baleen-white focus:outline-none focus:border-baleen-cyan transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs text-baleen-muted mb-1 uppercase tracking-wider">Confirm Password</label>
            <input 
              type="password" 
              required
              value={form.confirm}
              onChange={e => setForm({...form, confirm: e.target.value})}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-baleen-white focus:outline-none focus:border-baleen-cyan transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs text-baleen-muted mb-1 uppercase tracking-wider">Paper Sandbox Balance ($)</label>
            <input 
              type="number" 
              min="100"
              step="100"
              required
              value={form.balance}
              onChange={e => setForm({...form, balance: e.target.value})}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-baleen-white focus:outline-none focus:border-baleen-cyan transition-colors"
            />
          </div>
          <Button type="submit" className="w-full mt-2" disabled={loading}>
            {loading ? 'Deploying...' : 'Sign Up'}
          </Button>
        </form>

        <p className="text-center text-sm text-baleen-muted">
          Already have an account?{' '}
          <Link href="/auth/login" className="text-baleen-cyan hover:underline">
            Sign In
          </Link>
        </p>
      </Card>
    </div>
  );
}
