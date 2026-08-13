import { createHyperSyncClient, buildQuery } from '../src/hypersync';
import { getResumeBlock, saveCheckpoint } from '../src/checkpoint';
import fs from 'fs';
import path from 'path';

describe('HyperSync and Checkpoint Tests', () => {
  const CHECKPOINT_FILE = path.join(__dirname, '../checkpoint.json');

  beforeAll(() => {
    if (fs.existsSync(CHECKPOINT_FILE)) {
      fs.unlinkSync(CHECKPOINT_FILE);
    }
  });

  it('should build a valid query', () => {
    const query = buildQuery(1000);
    expect(query.fromBlock).toBe(1000);
    expect(query.logs.length).toBe(1);
    expect(query.logs[0].topics[0][0]).toBeDefined();
    expect(query.fieldSelection.log).toContain('blockNumber');
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
});
