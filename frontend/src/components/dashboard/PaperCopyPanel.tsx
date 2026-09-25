'use client';
import { useEffect, useRef, useState } from 'react';
import { fetchPaperCopy, fetchPaperCopyResearch, PaperCopyState, PaperResearchState } from '@/lib/api-client';

export function PaperCopyPanel({ onConfigure }: { onConfigure: () => void }) {
  const [data, setData] = useState<PaperCopyState | null>(null);
  const [research, setResearch] = useState<PaperResearchState | null>(null);
  const [error, setError] = useState('');
  const [connecting, setConnecting] = useState(true);
  const hasLoadedPaperState = useRef(false);
  useEffect(() => {
    let active = true;
    const fetchLatest = async () => {
      // The paper account is the only state needed to make this panel useful.
      // Load the larger research registry after it so a slow registry query
      // cannot turn a healthy paper account into an apparent fetch failure.
      try {
        const res = await fetchPaperCopy();
        if (!active) return;
        setData(res);
        setError('');
        setConnecting(false);
        hasLoadedPaperState.current = true;
      } catch (e) {
        // On a first visit, the backend may still be restoring its worker
        // state. Keep retrying without presenting that short startup window
        // as an account failure.
        if (active && hasLoadedPaperState.current) setError(e instanceof Error ? e.message : 'Paper account unavailable');
      }
      try {
        const registry = await fetchPaperCopyResearch();
        if (active) setResearch(registry);
      } catch {
        // Registry data is supplementary and retries with the next refresh.
      }
    };
    void fetchLatest();
    const timer = setInterval(fetchLatest, 5000);
    window.addEventListener('paper-copy-updated', fetchLatest);
    return () => { active = false; clearInterval(timer); window.removeEventListener('paper-copy-updated', fetchLatest); };
  }, []);
  const runs = data?.runs ?? [];
  const activeRuns = runs.filter(r => (r.role ?? 'active') === 'active');
  const retiredRuns = runs.filter(r => (r.role ?? 'active') === 'retired');
  const known = !error && data?.status === 'ACTIVE' && activeRuns.length > 0 && activeRuns.every(r => r.report.valuation.equity != null);
  const equity = known ? activeRuns.reduce((sum, r) => sum + Number(r.report.valuation.equity), 0) : null;
  const pnl = known ? activeRuns.reduce((sum, r) => sum + Number(r.report.valuation.economic_pnl), 0) : null;
  const money = (n: number | null) => n == null ? 'Unavailable' : n.toLocaleString(undefined, { style: 'currency', currency: 'USD' });
  const moneyText = (n: string) => Number(n).toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
  return <section className="glass-card rounded-[28px] p-5 sm:p-6 space-y-4 border border-sky-100/80" aria-label="Automatic paper strategy">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h2 className="text-xl font-bold">Automatic paper strategy</h2>
        <p className="text-sm text-slate-500">{data?.status === 'ACTIVE' ? `${activeRuns.length} ${activeRuns.length === 1 ? 'wallet' : 'wallets'} in the ${data.selection_mode === 'automatic' ? 'automatic' : 'saved'} roster${retiredRuns.length ? ` · ${retiredRuns.length} retired source${retiredRuns.length === 1 ? '' : 's'} exit-monitoring only` : ''}` : 'Automatic roster not started'}</p></div>
      <button className="glass-button rounded-xl px-4 py-2" onClick={onConfigure}>Start fresh</button>
    </div>
    {connecting && !data && <p className="text-sm text-slate-500">Connecting to paper strategy…</p>}
    {(error || data?.last_error) && <p role="alert" className="text-amber-600">{error || data?.last_error}</p>}
    <div className="flex flex-wrap gap-8"><div>Equity <strong>{money(equity)}</strong></div><div>Net P&amp;L <strong>{money(pnl)}</strong></div>
      <div>Listener <strong>{data?.listener ?? 'Unconfirmed'}</strong></div></div>
    {runs.length === 0 && data?.discovery && <div className="rounded-xl border border-slate-300/20 p-3 text-sm" aria-label="Automatic roster discovery progress">
      <strong>Discovery {data.discovery.status || 'idle'}</strong>{typeof data.discovery.progress_pct === 'number' && <span> · {data.discovery.progress_pct}%</span>}
      <p className="text-xs text-slate-500 mt-1">{data.discovery.error_message || data.discovery.step_description || 'Waiting to evaluate the retained wallet registry.'}</p>
      {typeof data.discovery.wallets_scanned === 'number' && <p className="text-xs text-slate-500">{data.discovery.wallets_scanned} wallets scanned in this pass.</p>}
    </div>}
    {data?.roster_status && <p className="text-xs text-slate-500" aria-label="Automatic roster evidence counts">
      Eligibility: <strong>{data.roster_status.active_eligible}</strong> active candidates · <strong>{data.roster_status.standby}</strong> standby snipers · <strong>{data.roster_status.needs_data}</strong> awaiting coverage · <strong>{data.roster_status.excluded}</strong> excluded · <strong>{data.roster_status.stale}</strong> awaiting refresh{data.roster_status.legacy_retained > 0 ? ` · ${data.roster_status.legacy_retained.toLocaleString()} preserved legacy identities (not queued)` : ''}
    </p>}
    {runs.length === 0 && <p className="text-xs text-slate-500">Net P&amp;L becomes available after an active paper sleeve receives a confirmed source fill and a current order-book valuation.</p>}
    <p className="text-xs text-slate-500">New source fills only. Available paper capital is divided equally across however many wallets actually qualify; unused target slots do not reserve cash. Standby snipers remain monitored without an idle sleeve.</p>
    {activeRuns.map(r => <div key={r.id} className="border-t border-slate-300/20 pt-3 space-y-2">
      <div className="flex flex-wrap justify-between gap-2"><strong>{r.name || r.wallet}</strong>
        <span className="text-xs">Ratio {Number(r.policy.ratio).toPrecision(4)} · {r.revision} detected decisions</span></div>
      {r.report.valuation.reason && <p className="text-xs text-amber-600">{r.report.valuation.reason}</p>}
      {r.report.events.some(e => e.status === 'unavailable') && <p className="text-amber-600 text-sm">Entries paused after a missed leg. Existing exits remain monitored.</p>}
      {r.report.events.length === 0 && <p className="text-sm text-slate-500">Waiting for a new confirmed source trade.</p>}
      {r.report.events.slice(-8).reverse().map(e => <div key={e.source_id} className="text-xs flex flex-wrap justify-between gap-2">
        <span>{e.status === 'filled' ? 'Paper copied' : e.status === 'settled' ? 'Paper settled' : 'Not copied'} · {e.quantity} shares</span><span>{e.reason || `Fee $${e.fee_usd}`}</span>
      </div>)}
    </div>)}
    {retiredRuns.length > 0 && <div className="border-t border-slate-300/20 pt-4 space-y-2" aria-label="Retired paper-copy sources">
      <div><h3 className="font-bold">Retired sources</h3><p className="text-xs text-slate-500">These wallets are no longer followed for new entries. They remain only to process exits for an already-copied position.</p></div>
      {retiredRuns.map(r => <p key={r.id} className="text-xs rounded-lg border border-slate-300/20 p-2"><strong>{r.name || r.wallet}</strong> · {r.revision} recorded decisions · {r.report.events.length ? 'exit monitoring retained' : 'no copied inventory'}</p>)}
    </div>}
    <div className="border-t border-slate-300/20 pt-4 space-y-2" aria-label="Standby sniper wallets">
      <div><h3 className="font-bold">Standby sniper wallets</h3><p className="text-xs text-slate-500">Intermittent, non-HFT candidates monitored by the listener. They have no idle paper sleeve.</p></div>
      {(data?.standby_snipers ?? []).length === 0 ? <p className="text-sm text-slate-500">No fresh standby candidates yet.</p> :
        data!.standby_snipers!.map(s => <div key={s.address} className="text-xs flex flex-wrap justify-between gap-2 rounded-lg border border-slate-300/20 p-2">
          <span><strong>{s.name || s.pseudonym || s.address}</strong><span className="block text-slate-500">{s.address}</span></span>
          <span className="text-right">{Number(s.fills_per_day_30d).toFixed(1)} fills/day · ${Number(s.all_time_pnl_usd).toLocaleString()} economic P&amp;L<span className="block text-slate-500">${Number(s.realized_pnl_usd).toLocaleString()} realized · {s.closed_position_win_rate_pct == null ? 'Closed win rate pending' : `${s.closed_position_win_rate_pct.toFixed(1)}% closed win rate`} · {s.reasons.join(', ')}</span></span>
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
    <details className="border-t border-slate-300/20 pt-4" aria-label="Wallet research registry">
      <summary className="cursor-pointer font-bold">Wallet research registry {research ? `(${research.registry.displayed} of ${research.registry.total})` : ''}</summary>
      <p className="mt-2 text-xs text-slate-500">Every currently admitted or evaluated wallet is shown with the latest automatic decision. {research && research.registry.legacy_retained > 0 ? `${research.registry.legacy_retained.toLocaleString()} legacy identities are preserved outside the active research queue until independently re-admitted through the current $50k gate.` : ''} This is read-only research; active sleeves are still selected only from fresh eligible candidates.</p>
      <div className="mt-3 space-y-2">
        {(research?.registry.wallets ?? []).map(w => <div key={w.address} className="rounded-lg border border-slate-300/20 p-3 text-xs">
          <div className="flex flex-wrap justify-between gap-2"><strong>{w.name || w.pseudonym || w.address}</strong><span>{w.classification.replace('_', ' ')}{w.is_hft ? ' · HFT excluded' : ''}</span></div>
          <span className="block text-slate-500 break-all">{w.address}</span>
          <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-1 sm:grid-cols-4"><span>Economic {moneyText(w.all_time_pnl_usd)}</span><span>Realized {moneyText(w.realized_pnl_usd)}</span><span>30d {moneyText(w.recent_pnl_30d)}</span><span>{Number(w.fills_per_day_30d).toFixed(1)} fills/day</span></div>
          <p className="mt-1 text-slate-500">{w.reasons.join(', ')} · Coverage: {w.trade_coverage_complete ? 'complete' : (w.trade_coverage_reason || 'awaiting')} · {w.observed_at ? new Date(w.observed_at).toLocaleString() : 'not yet observed'}</p>
        </div>)}
        {research && research.registry.wallets.length === 0 && <p className="text-sm text-slate-500">No wallet evidence has been collected yet.</p>}
      </div>
    </details>
    <div className="border-t border-slate-300/20 pt-4 space-y-3" aria-label="Discovery funnel statistics">
      <div><h3 className="font-bold">Discovery funnel</h3><p className="text-xs text-slate-500">Addresses are discovered first, checked against the $50,000 P&amp;L gate, then deeply audited. Rejected low-P&amp;L addresses are never promoted into the research roster.</p></div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        <div className="rounded-xl bg-slate-50 border border-slate-200 p-3"><span className="block text-slate-500">Found this scan</span><strong>{data?.discovery?.addresses_found ?? 0}</strong></div>
        <div className="rounded-xl bg-slate-50 border border-slate-200 p-3"><span className="block text-slate-500">P&amp;L checked</span><strong>{data?.discovery?.pnl_checked ?? 0}</strong> / {data?.discovery?.pnl_queue_total ?? 0}</div>
        <div className="rounded-xl bg-slate-50 border border-slate-200 p-3"><span className="block text-slate-500">Below $50k</span><strong>{data?.discovery?.pnl_rejected_below_50k ?? 0}</strong></div>
        <div className="rounded-xl bg-slate-50 border border-slate-200 p-3"><span className="block text-slate-500">Admitted / audited</span><strong>{data?.discovery?.pnl_admitted ?? 0}</strong> / {data?.discovery?.evidence_audited ?? 0}</div>
      </div>
    </div>
  </section>;
}
