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

  const presets = ['1000', '5000', '10000', '25000'];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password !== form.confirm) {
      return setError('Passwords do not match');
    }
    
    setLoading(true);
    setError('');

    const user = await signUp(form.email, form.password, parseFloat(form.balance));
    
    if (!user) {
      setError('Failed to create account. Email may already be in use.');
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
    <div className="min-h-screen bg-[#090A0F] text-white flex items-center justify-center p-6 selection:bg-white selection:text-black">
      <div className="w-full max-w-md p-8 rounded-3xl bg-zinc-900/40 border border-white/[0.08] shadow-apple backdrop-blur-2xl">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-white mb-1.5">Create Sandbox Account</h1>
          <p className="text-zinc-400 text-xs font-normal">Test automated whale mirroring with paper funds</p>
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
              value={form.email}
              onChange={e => setForm({...form, email: e.target.value})}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-white/30 transition-colors"
              placeholder="you@domain.com"
            />
          </div>
          <div>
            <label className="block text-[11px] text-zinc-400 mb-1.5 font-medium">Password</label>
            <input 
              type="password" 
              required
              value={form.password}
              onChange={e => setForm({...form, password: e.target.value})}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-white/30 transition-colors"
              placeholder="••••••••"
            />
          </div>
          <div>
            <label className="block text-[11px] text-zinc-400 mb-1.5 font-medium">Confirm Password</label>
            <input 
              type="password" 
              required
              value={form.confirm}
              onChange={e => setForm({...form, confirm: e.target.value})}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-white/30 transition-colors"
              placeholder="••••••••"
            />
          </div>
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="block text-[11px] text-zinc-400 font-medium">Starting Sandbox Capital ($)</label>
              <span className="text-[10px] text-zinc-500 font-mono">Virtual</span>
            </div>
            <input 
              type="number" 
              min="100"
              step="100"
              required
              value={form.balance}
              onChange={e => setForm({...form, balance: e.target.value})}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-white/30 transition-colors font-mono mb-2"
            />
            <div className="flex gap-2">
              {presets.map(p => (
                <button
                  type="button"
                  key={p}
                  onClick={() => setForm({...form, balance: p})}
                  className={`text-[11px] font-mono px-2.5 py-1 rounded-lg border transition-all ${
                    form.balance === p 
                      ? 'bg-white text-zinc-950 font-semibold border-white shadow-sm' 
                      : 'bg-white/[0.04] text-zinc-400 border-white/[0.06] hover:text-white'
                  }`}
                >
                  ${parseInt(p).toLocaleString()}
                </button>
              ))}
            </div>
          </div>
          <Button type="submit" className="w-full mt-4 bg-white text-zinc-950 font-semibold" disabled={loading}>
            {loading ? 'Creating Account...' : 'Get Started Free'}
          </Button>
        </form>

        <p className="text-center text-xs text-zinc-500 mt-6">
          Already have an account?{' '}
          <Link href="/auth/login" className="text-white hover:underline font-medium">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}
