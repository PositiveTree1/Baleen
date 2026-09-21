'use client';
import { useEffect, useState } from 'react';
import { startAutomaticPaperCopy } from '@/lib/api-client';
import { Modal } from '../ui/Modal';
export interface MirrorStrategyModalProps {
  isOpen: boolean; onClose: () => void; onSelectWallet?: (address: string) => void;
  targetSleeveCount?: number; bankroll?: number;
}
export function MirrorStrategyModal({ isOpen, onClose, bankroll }: MirrorStrategyModalProps) {
  const [cash, setCash] = useState(String(Math.max(20, bankroll ?? 10000)));
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [prevOpen, setPrevOpen] = useState(isOpen);

  if (isOpen !== prevOpen) {
    setPrevOpen(isOpen);
    if (isOpen) {
      setError('');
      setCash(String(Math.max(20, bankroll ?? 10000)));
    }
  }
  async function save() {
    setBusy(true); setError('');
    try {
      await startAutomaticPaperCopy(cash);
      window.dispatchEvent(new Event('paper-copy-updated'));
      onClose();
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not start paper copying'); }
    finally { setBusy(false); }
  }
  return <Modal isOpen={isOpen} onClose={onClose} title="Start automatic paper copying" subtitle="The server selects the roster" maxWidth="max-w-2xl">
    <div className="space-y-4">
      <p className="text-sm">Starting fresh archives your current paper run. Baleen selects the capital-appropriate active roster from fresh eligible research candidates, then divides paper cash equally. Only future fills are copied.</p>
      <label className="block">Starting paper cash ($)<input className="ml-3 rounded-lg border p-2 bg-transparent" type="number" min="20" max="10000000" value={cash} onChange={e => setCash(e.target.value)} /></label>
      <p className="text-sm">Automatic roster · standby snipers remain monitored · paper research only · no real-money approval</p>
      {error && <p role="alert" className="text-red-500">{error}</p>}
      <p className="text-xs text-slate-500">The active roster uses fresh, non-HFT research candidates ranked by recent and all-time verified P&amp;L. If no qualified wallets exist yet, the existing run is kept intact.</p>
      <button disabled={busy || Number(cash) < 20} onClick={save} className="glass-button rounded-xl px-5 py-3 disabled:opacity-40">{busy ? 'Building automatic roster…' : 'Archive current run and start automatic paper copying'}</button>
    </div>
  </Modal>;
}
