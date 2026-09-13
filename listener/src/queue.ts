import fs from 'fs';
import path from 'path';
import { config } from './config';
import { WhaleTradeSignal } from './types';

// Durable across restarts; the lock only coordinates one listener process.
const DEFAULT_QUEUE_FILE = path.join(__dirname, '../queue.jsonl');
let queueOperations: Promise<unknown> = Promise.resolve();
const queueFile = () => process.env.LISTENER_QUEUE_FILE || DEFAULT_QUEUE_FILE;
const tempFile = (file: string) => `${file}.tmp`;
const quarantineFile = (file: string) => `${file}.invalid`;

async function syncFile(file: string, content: string): Promise<void> {
  const handle = await fs.promises.open(file, 'w');
  try { await handle.writeFile(content, 'utf-8'); await handle.sync(); } finally { await handle.close(); }
}

async function appendDurably(file: string, content: string): Promise<void> {
  await fs.promises.mkdir(path.dirname(file), { recursive: true });
  const handle = await fs.promises.open(file, 'a');
  try { await handle.write(content, undefined, 'utf-8'); await handle.sync(); } finally { await handle.close(); }
}

function serialized<T>(operation: () => Promise<T>): Promise<T> {
  const result = queueOperations.then(operation, operation);
  queueOperations = result.then(() => undefined, () => undefined);
  return result;
}

export function getQueueFilePath(): string { return queueFile(); }

function signalIdentityKey(signal: WhaleTradeSignal): string {
  return `${signal.transactionHash.toLowerCase()}:${signal.logIndex}:${signal.walletAddress.toLowerCase()}`;
}

export async function enqueueSignal(signal: WhaleTradeSignal): Promise<void> {
  return serialized(async () => appendDurably(queueFile(), JSON.stringify(signal) + '\n'));
}

export async function postSignalToBackend(signal: WhaleTradeSignal): Promise<boolean> {
  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (config.LISTENER_SERVICE_KEY) {
      headers['X-Service-Key'] = config.LISTENER_SERVICE_KEY;
    }
    const response = await fetch(`${config.BACKEND_URL}/api/signals`, {
      method: 'POST',
      headers,
      body: JSON.stringify(signal),
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      console.error(`[ERROR] Failed to post signal ${signalIdentityKey(signal)} to backend: HTTP ${response.status} ${response.statusText}`);
      return false;
    }
    let body: unknown;
    try { body = await response.json(); } catch { return false; }
    return typeof body === 'object' && body !== null && (body as { accepted?: unknown }).accepted === true;
  } catch (error: any) {
    console.error(`[ERROR] Network error posting signal to backend:`, error?.message || error);
    return false;
  }
}

export async function drainQueue(): Promise<{ delivered: number; remaining: number }> {
  return serialized(async () => {
    const file = queueFile();
    let content: string;
    try { content = await fs.promises.readFile(file, 'utf-8'); } catch { return { delivered: 0, remaining: 0 }; }
    const lines = content.split('\n').filter(Boolean);
    if (lines.length === 0) return { delivered: 0, remaining: 0 };
    const remainingLines: string[] = [];
    const malformedLines: string[] = [];
    let deliveredCount = 0;
    for (const line of lines) {
      let sig: WhaleTradeSignal;
      try { sig = JSON.parse(line) as WhaleTradeSignal; } catch { malformedLines.push(line); continue; }
      if (await postSignalToBackend(sig)) deliveredCount++; else remainingLines.push(line);
    }
    if (malformedLines.length) await appendDurably(quarantineFile(file), malformedLines.join('\n') + '\n');
    await syncFile(tempFile(file), remainingLines.length ? remainingLines.join('\n') + '\n' : '');
    await fs.promises.rename(tempFile(file), file);
    return { delivered: deliveredCount, remaining: remainingLines.length };
  });
}
