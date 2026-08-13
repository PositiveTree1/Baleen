import fs from 'fs';
import path from 'path';
import { Checkpoint } from './types';

const CHECKPOINT_FILE = path.join(__dirname, '../checkpoint.json');

export function saveCheckpoint(blockNumber: number): void {
  const checkpoint: Checkpoint = {
    lastProcessedBlock: blockNumber,
    updatedAt: Date.now(),
  };
  fs.writeFileSync(CHECKPOINT_FILE, JSON.stringify(checkpoint, null, 2));
}

export function getResumeBlock(): number {
  if (fs.existsSync(CHECKPOINT_FILE)) {
    try {
      const data = fs.readFileSync(CHECKPOINT_FILE, 'utf-8');
      const checkpoint: Checkpoint = JSON.parse(data);
      return checkpoint.lastProcessedBlock || 0;
    } catch (err) {
      console.error('Error reading checkpoint file', err);
      return 0;
    }
  }
  return 0;
}
