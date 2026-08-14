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
    <div className="min-h-screen bg-[#F8F9FB] text-slate-900 flex items-center justify-center p-6 selection:bg-slate-900 selection:text-white">
      <div className="w-full max-w-md p-8 rounded-3xl bg-white border border-black/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,1),0_4px_16px_rgba(0,0,0,0.04),0_24px_48px_-12px_rgba(0,0,0,0.08)]">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 mb-1.5">Create Sandbox Account</h1>
          <p className="text-slate-500 text-xs font-normal">Test automated whale mirroring with paper funds</p>
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
              value={form.email}
              onChange={e => setForm({...form, email: e.target.value})}
              className="w-full bg-slate-50 border border-black/[0.08] rounded-xl px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-slate-500 transition-colors shadow-[inset_0_1px_2px_rgba(0,0,0,0.03)]"
              placeholder="you@domain.com"
            />
          </div>
          <div>
            <label className="block text-[11px] text-slate-600 mb-1.5 font-semibold">Password</label>
            <input 
              type="password" 
              required
              value={form.password}
              onChange={e => setForm({...form, password: e.target.value})}
              className="w-full bg-slate-50 border border-black/[0.08] rounded-xl px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-slate-500 transition-colors shadow-[inset_0_1px_2px_rgba(0,0,0,0.03)]"
              placeholder="••••••••"
            />
          </div>
          <div>
            <label className="block text-[11px] text-slate-600 mb-1.5 font-semibold">Confirm Password</label>
            <input 
              type="password" 
              required
              value={form.confirm}
              onChange={e => setForm({...form, confirm: e.target.value})}
              className="w-full bg-slate-50 border border-black/[0.08] rounded-xl px-3.5 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-slate-500 transition-colors shadow-[inset_0_1px_2px_rgba(0,0,0,0.03)]"
              placeholder="••••••••"
            />
          </div>
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="block text-[11px] text-slate-600 font-semibold">Starting Sandbox Capital ($)</label>
              <span className="text-[10px] text-slate-400 font-mono font-bold">Virtual</span>
            </div>
            <input 
              type="number" 
              min="100"
              step="100"
              required
              value={form.balance}
              onChange={e => setForm({...form, balance: e.target.value})}
              className="w-full bg-slate-50 border border-black/[0.08] rounded-xl px-3.5 py-2.5 text-sm text-slate-900 focus:outline-none focus:border-slate-500 transition-colors font-mono mb-2 shadow-[inset_0_1px_2px_rgba(0,0,0,0.03)] font-bold"
            />
            <div className="flex gap-2">
              {presets.map(p => (
                <button
                  type="button"
                  key={p}
                  onClick={() => setForm({...form, balance: p})}
                  className={`text-[11px] font-mono px-3 py-1 rounded-xl border transition-all ${
                    form.balance === p 
                      ? 'bg-slate-900 text-white font-bold border-slate-900 shadow-sm' 
                      : 'bg-slate-100 text-slate-600 border-black/[0.06] hover:bg-slate-200/70 font-semibold'
                  }`}
                >
                  ${parseInt(p).toLocaleString()}
                </button>
              ))}
            </div>
          </div>
          <Button type="submit" className="w-full mt-4 font-semibold" disabled={loading}>
            {loading ? 'Creating Account...' : 'Get Started Free'}
          </Button>
        </form>

        <p className="text-center text-xs text-slate-500 mt-6">
          Already have an account?{' '}
          <Link href="/auth/login" className="text-slate-900 hover:underline font-bold">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}
