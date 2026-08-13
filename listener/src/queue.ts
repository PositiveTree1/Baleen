import fs from 'fs';
import path from 'path';
import { config } from './config';
import { WhaleTradeSignal } from './types';

const QUEUE_FILE = path.join(__dirname, '../queue.jsonl');
const processedKeys = new Set<string>();

export async function enqueueSignal(signal: WhaleTradeSignal): Promise<void> {
  const key = `${signal.transactionHash}:${signal.logIndex}`;
  if (processedKeys.has(key)) {
    return;
  }
  
  processedKeys.add(key);
  const line = JSON.stringify(signal) + '\n';
  await fs.promises.appendFile(QUEUE_FILE, line, 'utf-8');
}

export async function dequeueSignals(limit: number): Promise<WhaleTradeSignal[]> {
  if (!fs.existsSync(QUEUE_FILE)) {
    return [];
  }
  
  const content = await fs.promises.readFile(QUEUE_FILE, 'utf-8');
  const lines = content.trim().split('\n').filter(Boolean);
  
  const toProcess = lines.slice(0, limit);
  const remaining = lines.slice(limit);
  
  await fs.promises.writeFile(QUEUE_FILE, remaining.join('\n') + (remaining.length > 0 ? '\n' : ''), 'utf-8');
  return toProcess.map(line => JSON.parse(line));
}

export async function postSignalToBackend(signal: WhaleTradeSignal): Promise<void> {
  try {
    const response = await fetch(`${config.BACKEND_URL}/api/signals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(signal),
    });
    
    if (!response.ok) {
      console.error('Failed to post signal to backend', response.statusText);
    }
  } catch (error) {
    console.error('Error posting signal to backend', error);
  }
}
