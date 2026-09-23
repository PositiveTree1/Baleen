import { createHyperSyncClient, buildQuery, canAdvanceCursor } from '../src/hypersync';
import { getResumeBlock, saveCheckpoint } from '../src/checkpoint';
import fs from 'fs';
import path from 'path';
import os from 'os';

describe('HyperSync and Checkpoint Tests', () => {
  const CHECKPOINT_FILE = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'baleen-checkpoint-test-')), 'checkpoint.json');

  beforeAll(() => {
    process.env.LISTENER_CHECKPOINT_FILE = CHECKPOINT_FILE;
    if (fs.existsSync(CHECKPOINT_FILE)) {
      fs.unlinkSync(CHECKPOINT_FILE);
    }
  });
  afterAll(() => { delete process.env.LISTENER_CHECKPOINT_FILE; });

  it('should build a valid query', () => {
    const query = buildQuery(1000);
    expect(query.fromBlock).toBe(1000);
    expect(query.logs.length).toBe(1);
    expect(query.logs[0].topics[0][0]).toBeDefined();
    expect(query.fieldSelection.log).toContain('BlockNumber');
  });

  it('should save and resume checkpoint', () => {
    expect(getResumeBlock()).toBe(0);
    
    saveCheckpoint(12345);
    expect(getResumeBlock()).toBe(12345);
    
    saveCheckpoint(54321);
    expect(getResumeBlock()).toBe(54321);
  });

  it('should create client', () => {
    const client = createHyperSyncClient();
    expect(client).toBeDefined();
  });

  it('accepts HyperSync’s first-unread cursor after an inclusive query', () => {
    expect(canAdvanceCursor(501, 400, 500)).toBe(true);
    expect(canAdvanceCursor(502, 400, 500)).toBe(false);
    expect(canAdvanceCursor(400, 400, 500)).toBe(false);
  });
});
