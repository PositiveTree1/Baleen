import fs from 'fs';
import path from 'path';
import { Checkpoint } from './types';

const checkpointFile = () => process.env.LISTENER_CHECKPOINT_FILE || path.join(__dirname, '../checkpoint.json');

export function saveCheckpoint(blockNumber: number): void {
  const CHECKPOINT_FILE = checkpointFile();
  fs.mkdirSync(path.dirname(CHECKPOINT_FILE), { recursive: true });
  const checkpoint: Checkpoint = {
    lastProcessedBlock: blockNumber,
    updatedAt: Date.now(),
  };
  const tmpFile = `${CHECKPOINT_FILE}.tmp.${Date.now()}`;
  try {
    const fd = fs.openSync(tmpFile, 'w');
    try { fs.writeFileSync(fd, JSON.stringify(checkpoint, null, 2)); fs.fsyncSync(fd); }
    finally { fs.closeSync(fd); }
    fs.renameSync(tmpFile, CHECKPOINT_FILE);
  } catch (err) {
    if (fs.existsSync(tmpFile)) {
      try { fs.unlinkSync(tmpFile); } catch {}
    }
    throw err;
  }
}

export function getResumeBlock(): number {
  const CHECKPOINT_FILE = checkpointFile();
  if (fs.existsSync(CHECKPOINT_FILE)) {
    try {
      const data = fs.readFileSync(CHECKPOINT_FILE, 'utf-8');
      const checkpoint: Checkpoint = JSON.parse(data);
      if (!Number.isSafeInteger(checkpoint.lastProcessedBlock) || checkpoint.lastProcessedBlock < 0) {
        throw new Error('Invalid saved source cursor');
      }
      return checkpoint.lastProcessedBlock;
    } catch (err) {
      console.error('Error reading checkpoint file', err);
      throw err; // A damaged cursor must not silently restart at a guessed tip.
    }
  }
  return 0;
}
