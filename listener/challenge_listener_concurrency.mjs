import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('='.repeat(75));
console.log('LISTENER CONCURRENCY AND CHECKPOINT CRASH TEST HARNESS');
console.log('='.repeat(75));

// 1. QUEUE RACE CONDITION & LOST UPDATE EMPIRICAL PROOF
console.log('\n[CHALLENGE 4] Queue Concurrent Read-Modify-Write Race Condition Test');

const TEST_QUEUE_FILE = path.join(__dirname, 'test_queue.jsonl');

if (fs.existsSync(TEST_QUEUE_FILE)) {
  fs.unlinkSync(TEST_QUEUE_FILE);
}

// Emulate original queue.ts implementation
const processedKeys = new Set();

async function enqueueSignalOrig(signal) {
  const key = `${signal.transactionHash}:${signal.logIndex}`;
  if (processedKeys.has(key)) return;
  processedKeys.add(key);
  const line = JSON.stringify(signal) + '\n';
  await fs.promises.appendFile(TEST_QUEUE_FILE, line, 'utf-8');
}

async function dequeueSignalsOrig(limit) {
  if (!fs.existsSync(TEST_QUEUE_FILE)) return [];
  const content = await fs.promises.readFile(TEST_QUEUE_FILE, 'utf-8');
  const lines = content.trim().split('\n').filter(Boolean);
  const toProcess = lines.slice(0, limit);
  const remaining = lines.slice(limit);
  // Simulated small I/O delay to highlight race window
  await new Promise(r => setTimeout(r, 20));
  await fs.promises.writeFile(TEST_QUEUE_FILE, remaining.join('\n') + (remaining.length > 0 ? '\n' : ''), 'utf-8');
  return toProcess.map(line => JSON.parse(line));
}

async function runQueueRaceTest() {
  for (let i = 1; i <= 5; i++) {
    await enqueueSignalOrig({ transactionHash: `0x${i}`, logIndex: 0, id: i });
  }

  console.log('  Initial state: Queue has 5 signals (IDs 1..5).');

  // Task A dequeues 3 items
  const dequeuePromise = dequeueSignalsOrig(3);

  // While dequeue is processing, Task B enqueues signal 6
  await new Promise(r => setTimeout(r, 5));
  await enqueueSignalOrig({ transactionHash: '0x6', logIndex: 0, id: 6 });
  console.log('  Interleaved: Task B enqueued Signal 6 while Task A was dequeuing.');

  const dequeued = await dequeuePromise;
  console.log(`  Task A dequeued ${dequeued.length} signals:`, dequeued.map(s => s.id));

  // Check remaining file content
  const remainingContent = fs.readFileSync(TEST_QUEUE_FILE, 'utf-8');
  const remainingLines = remainingContent.trim().split('\n').filter(Boolean);
  const remainingIds = remainingLines.map(l => JSON.parse(l).id);
  console.log('  Queue file on disk after concurrent operations:', remainingIds);

  const lostSignal = !remainingIds.includes(6);
  if (lostSignal) {
    console.log('  >>> EMPIRICALLY CONFIRMED BUG: Signal 6 was SILENTLY OVERWRITTEN AND LOST due to non-atomic writeFile! <<<');
  } else {
    console.log('  Signal 6 survived (no race captured).');
  }
}

// 2. UNBOUNDED MEMORY LEAK IN DEDUPLICATION SET
console.log('\n[CHALLENGE 5] In-Memory Set Memory Growth Benchmark');

function testMemoryGrowth() {
  const initialMem = process.memoryUsage().heapUsed;
  const testSet = new Set();
  const COUNT = 250000;
  for (let i = 0; i < COUNT; i++) {
    testSet.add(`0x${i.toString(16).padStart(64, '0')}:${i % 10}`);
  }
  const finalMem = process.memoryUsage().heapUsed;
  const diffMb = ((finalMem - initialMem) / (1024 * 1024)).toFixed(2);
  console.log(`  Added ${COUNT.toLocaleString()} transaction keys to unbounded Set.`);
  console.log(`  Heap memory delta: +${diffMb} MB (no eviction / TTL mechanism).`);
}

// 3. NON-ATOMIC CHECKPOINT CRASH CORRUPTION EMPIRICAL PROOF
console.log('\n[CHALLENGE 6] Checkpoint Non-Atomic Crash & Recovery Test');

const TEST_CHECKPOINT_FILE = path.join(__dirname, 'test_checkpoint.json');

function saveCheckpointOrig(blockNumber) {
  const checkpoint = {
    lastProcessedBlock: blockNumber,
    updatedAt: Date.now(),
  };
  fs.writeFileSync(TEST_CHECKPOINT_FILE, JSON.stringify(checkpoint, null, 2));
}

function saveCheckpointAtomic(blockNumber) {
  const checkpoint = {
    lastProcessedBlock: blockNumber,
    updatedAt: Date.now(),
  };
  const tmpFile = `${TEST_CHECKPOINT_FILE}.tmp`;
  fs.writeFileSync(tmpFile, JSON.stringify(checkpoint, null, 2));
  fs.renameSync(tmpFile, TEST_CHECKPOINT_FILE);
}

function getResumeBlock(file) {
  if (fs.existsSync(file)) {
    try {
      const data = fs.readFileSync(file, 'utf-8');
      const checkpoint = JSON.parse(data);
      return checkpoint.lastProcessedBlock || 0;
    } catch (err) {
      console.error('  [EXPECTED ERROR] getResumeBlock failed to parse:', err.message);
      return 0;
    }
  }
  return 0;
}

async function runCheckpointCrashTest() {
  saveCheckpointOrig(75000000);
  console.log('  Saved normal checkpoint at block 75,000,000 -> Resume block:', getResumeBlock(TEST_CHECKPOINT_FILE));

  // Simulate process kill during write (truncated JSON)
  fs.writeFileSync(TEST_CHECKPOINT_FILE, '{\n  "lastProcessedBlock": 7500010');
  console.log('  Simulated crash mid-write resulting in truncated checkpoint JSON.');
  
  const resumeAfterCrash = getResumeBlock(TEST_CHECKPOINT_FILE);
  console.log('  Resume block returned after corrupted file:', resumeAfterCrash);
  
  if (resumeAfterCrash === 0) {
    console.log('  >>> EMPIRICALLY CONFIRMED BUG: Checkpoint corruption yields Block 0, causing index.ts to discard up to 5,000 blocks! <<<');
  }

  // Demonstrate Atomic Checkpoint Resilience
  saveCheckpointAtomic(75000500);
  console.log('  Atomic checkpoint save at block 75,005,000 -> Resume block:', getResumeBlock(TEST_CHECKPOINT_FILE));

  // Clean up test files
  if (fs.existsSync(TEST_QUEUE_FILE)) fs.unlinkSync(TEST_QUEUE_FILE);
  if (fs.existsSync(TEST_CHECKPOINT_FILE)) fs.unlinkSync(TEST_CHECKPOINT_FILE);
}

async function main() {
  await runQueueRaceTest();
  testMemoryGrowth();
  await runCheckpointCrashTest();
  console.log('\n' + '='.repeat(75));
  console.log('LISTENER EMPIRICAL TESTS COMPLETE');
  console.log('='.repeat(75));
}

main().catch(console.error);
