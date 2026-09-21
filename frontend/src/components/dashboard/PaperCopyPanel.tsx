'use client';
import { useEffect, useState, useCallback } from 'react';
import { fetchPaperCopy, PaperCopyState } from '@/lib/api-client';

export function PaperCopyPanel({ onConfigure }: { onConfigure: () => void }) {
  const [data, setData] = useState<PaperCopyState | null>(null);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    try { setData(await fetchPaperCopy()); setError(''); }
    catch (e) { setError(e instanceof Error ? e.message : 'Paper account unavailable'); }
  }, []);
  useEffect(() => {
    void refresh();
    const timer = setInterval(refresh, 10000);
    window.addEventListener('paper-copy-updated', refresh);
    return () => { clearInterval(timer); window.removeEventListener('paper-copy-updated', refresh); };
  }, [refresh]);
  const runs = data?.runs ?? [];
  const known = !error && data?.status === 'ACTIVE' && runs.length > 0 && runs.every(r => r.report.valuation.equity != null);
  const equity = known ? runs.reduce((sum, r) => sum + Number(r.report.valuation.equity), 0) : null;
  const pnl = known ? runs.reduce((sum, r) => sum + Number(r.report.valuation.economic_pnl), 0) : null;
  const money = (n: number | null) => n == null ? 'Unavailable' : n.toLocaleString(undefined, { style: 'currency', currency: 'USD' });
  return <section className="glass-card rounded-3xl p-6 space-y-4" aria-label="Server-saved paper copying">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h2 className="text-xl font-bold">Paper copying</h2>
        <p className="text-sm text-slate-500">{data?.status === 'ACTIVE' ? `${runs.length} ${runs.length === 1 ? 'wallet' : 'wallets'} in the ${data.selection_mode === 'automatic' ? 'automatic' : 'saved'} roster` : 'Automatic roster not started'}</p></div>
      <button className="glass-button rounded-xl px-4 py-2" onClick={onConfigure}>Start fresh</button>
    </div>
    {(error || data?.last_error) && <p role="alert" className="text-amber-600">{error || data?.last_error}</p>}
    <div className="flex flex-wrap gap-8"><div>Equity <strong>{money(equity)}</strong></div><div>Net P&amp;L <strong>{money(pnl)}</strong></div>
      <div>Listener <strong>{data?.listener ?? 'Unconfirmed'}</strong></div></div>
    <p className="text-xs text-slate-500">New source fills only. Fixed allocation ratios. The active roster is selected from fresh eligible research candidates; standby snipers remain monitored without an idle sleeve. Paper fills estimate available order-book depth after receipt confirmation; they are not exchange executions.</p>
    {runs.map(r => <div key={r.id} className="border-t border-slate-300/20 pt-3 space-y-2">
      <div className="flex flex-wrap justify-between gap-2"><strong>{r.name || r.wallet}</strong>
        <span className="text-xs">Ratio {Number(r.policy.ratio).toPrecision(4)} · {r.revision} detected decisions</span></div>
      {r.report.valuation.reason && <p className="text-xs text-amber-600">{r.report.valuation.reason}</p>}
      {r.report.events.some(e => e.status === 'unavailable') && <p className="text-amber-600 text-sm">Entries paused after a missed leg. Existing exits remain monitored.</p>}
      {r.report.events.length === 0 && <p className="text-sm text-slate-500">Waiting for a new confirmed source trade.</p>}
      {r.report.events.slice(-8).reverse().map(e => <div key={e.source_id} className="text-xs flex flex-wrap justify-between gap-2">
        <span>{e.status === 'filled' ? 'Paper copied' : e.status === 'settled' ? 'Paper settled' : 'Not copied'} · {e.quantity} shares</span><span>{e.reason || `Fee $${e.fee_usd}`}</span>
      </div>)}
    </div>)}
    <div className="border-t border-slate-300/20 pt-4 space-y-2" aria-label="Standby sniper wallets">
      <div><h3 className="font-bold">Standby sniper wallets</h3><p className="text-xs text-slate-500">Intermittent, non-HFT candidates monitored by the listener. They have no idle paper sleeve.</p></div>
      {(data?.standby_snipers ?? []).length === 0 ? <p className="text-sm text-slate-500">No fresh standby candidates yet.</p> :
        data!.standby_snipers!.map(s => <div key={s.address} className="text-xs flex flex-wrap justify-between gap-2 rounded-lg border border-slate-300/20 p-2">
          <span><strong>{s.name || s.pseudonym || s.address}</strong><span className="block text-slate-500">{s.address}</span></span>
          <span className="text-right">{Number(s.fills_per_day_30d).toFixed(1)} fills/day · ${Number(s.all_time_pnl_usd).toLocaleString()} P&amp;L<span className="block text-slate-500">{s.reasons.join(', ')}</span></span>
        </div>)}
    </div>
    <div className="border-t border-slate-300/20 pt-4 space-y-2" aria-label="Standby sniper allocation decisions">
      <div><h3 className="font-bold">Sniper allocation decisions</h3><p className="text-xs text-slate-500">Only free cash moves from the lowest current-P&amp;L active sleeve; open positions are never closed to fund a sniper.</p></div>
      {(data?.sniper_allocations ?? []).length === 0 ? <p className="text-sm text-slate-500">No standby sniper trade has required an allocation yet.</p> :
        data!.sniper_allocations!.map(a => <div key={a.source_event_id} className="text-xs rounded-lg border border-slate-300/20 p-2 flex flex-wrap justify-between gap-2">
          <span><strong>{a.status === 'ALLOCATED' ? 'Allocated' : 'Not allocated'}</strong> · {a.source_wallet}<span className="block text-slate-500">{a.reason}</span></span>
          <span>{a.allocated_cash_usd == null ? 'No cash moved' : `$${Number(a.allocated_cash_usd).toLocaleString()} paper cash`}<span className="block text-slate-500">{new Date(a.created_at).toLocaleString()}</span></span>
        </div>)}
    </div>
    <div className="border-t border-slate-300/20 pt-4 space-y-2" aria-label="Automatic roster rotation history">
      <div><h3 className="font-bold">Automatic roster rotation</h3><p className="text-xs text-slate-500">Fresh evaluation can promote a stronger eligible wallet. Retired wallets keep only exit monitoring until copied positions close.</p></div>
      {(data?.roster_rotations ?? []).length === 0 ? <p className="text-sm text-slate-500">No roster rotation has been needed yet.</p> :
        data!.roster_rotations!.map((rotation, index) => <div key={`${rotation.created_at}-${index}`} className="text-xs rounded-lg border border-slate-300/20 p-2">
          <strong>{rotation.promoted.length} promoted · {rotation.retired.length} retired</strong><span className="ml-2 text-slate-500">{new Date(rotation.created_at).toLocaleString()}</span>
          {rotation.promoted.map(p => <span key={p.wallet} className="block">Promoted {p.wallet} from {p.replaced_wallet} with ${Number(p.cash || 0).toLocaleString()} free paper cash</span>)}
          {rotation.skipped.map(s => <span key={s.wallet} className="block text-amber-600">Skipped {s.wallet}: {s.reason}</span>)}
        </div>)}
    </div>
  </section>;
}
