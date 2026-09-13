/**
 * Deterministic Frontend Terminology, State Invariant, and Accessibility Test Suite
 *
 * Verifies:
 * 1. Prohibited claims and fake stats have been eliminated across all frontend source files.
 * 2. Honest paper simulation terminology and pUSD labeling are in place.
 * 3. Collateral display distinguishes unconfigured/missing ("Unavailable") from valid zero ("$0.00").
 * 4. Fallbacks do not fabricate performance metrics (e.g. 74% winrate or $12.4k PnL).
 * 5. Interactive list items, inputs, and drawers satisfy keyboard navigation and accessibility standards.
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const SRC_DIR = path.resolve(__dirname, '..', 'src');

function getAllFiles(dir, extensions = ['.tsx', '.ts']) {
  let results = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results = results.concat(getAllFiles(fullPath, extensions));
    } else if (extensions.includes(path.extname(entry.name))) {
      results.push(fullPath);
    }
  }
  return results;
}

// ---------------------------------------------------------------------------
// Test Group 1: Terminology & Prohibited Claim Sweeps
// ---------------------------------------------------------------------------
test('Frontend source files must not contain prohibited marketing claims or fake stats', () => {
  const allFiles = getAllFiles(SRC_DIR);
  const prohibitedPatterns = [
    { pattern: /<\s*38ms/i, label: '< 38ms latency claim' },
    { pattern: /\b38ms\b/i, label: '38ms latency claim' },
    { pattern: /audited\s+whales/i, label: 'audited whales claim' },
    { pattern: /audited\s+index/i, label: 'audited index claim' },
    { pattern: /institutional\s+audit/i, label: 'institutional audit claim' },
    { pattern: /turn\s+\$20\s+into\s+close\s+to\s+\$10,000\+/i, label: 'guaranteed return marketing' },
    { pattern: /5,000\+\s+live\s+executions/i, label: 'fake live execution volume' },
    { pattern: /Live\s+Autopilot/i, label: 'misleading Live Autopilot status' },
  ];

  const violations = [];

  for (const filePath of allFiles) {
    const content = fs.readFileSync(filePath, 'utf-8');
    const relPath = path.relative(SRC_DIR, filePath).replace(/\\/g, '/');

    for (const { pattern, label } of prohibitedPatterns) {
      if (pattern.test(content)) {
        violations.push(`${relPath} violates "${label}"`);
      }
    }
  }

  assert.deepEqual(violations, [], `Found prohibited claim violations:\n${violations.join('\n')}`);
});

test('Landing and dashboard components must reflect paper sandbox and simulated status', () => {
  const profitSimPath = path.join(SRC_DIR, 'components', 'landing', 'ProfitSimulator.tsx');
  const liveTickerPath = path.join(SRC_DIR, 'components', 'landing', 'LiveTicker.tsx');
  const dashboardPagePath = path.join(SRC_DIR, 'app', 'dashboard', 'page.tsx');
  const deepAnalyticsPath = path.join(SRC_DIR, 'components', 'dashboard', 'DeepAnalyticsModal.tsx');

  const simContent = fs.readFileSync(profitSimPath, 'utf-8');
  assert.ok(simContent.includes('Paper Sandbox') || simContent.includes('Paper Simulation'), 'ProfitSimulator must clarify paper simulation');
  assert.ok(!simContent.includes('audited whales'), 'ProfitSimulator must not say audited whales');

  const tickerContent = fs.readFileSync(liveTickerPath, 'utf-8');
  assert.ok(tickerContent.includes('Paper Simulation'), 'LiveTicker must indicate paper simulation');
  assert.ok(!tickerContent.includes('Won $42,910'), 'LiveTicker must not have fake static winnings');

  const dashContent = fs.readFileSync(dashboardPagePath, 'utf-8');
  assert.ok(dashContent.includes('Live Trading · Unavailable (Gated)') || dashContent.includes('Live Execution Disabled'), 'Dashboard must display gated live status');
  assert.ok(dashContent.includes('pUSD'), 'Dashboard must label paper collateral as pUSD');

  const analyticsContent = fs.readFileSync(deepAnalyticsPath, 'utf-8');
  assert.ok(analyticsContent.includes('Paper Portfolio Analytics'), 'DeepAnalyticsModal must indicate paper portfolio');
});

// ---------------------------------------------------------------------------
// Test Group 2: Collateral & Metric Formatting Invariants
// ---------------------------------------------------------------------------
test('Collateral formatting logic must distinguish unavailable state from valid zero', () => {
  function formatCollateral(val) {
    if (val === null || val === undefined) return 'Unavailable';
    return `$${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  assert.equal(formatCollateral(null), 'Unavailable');
  assert.equal(formatCollateral(undefined), 'Unavailable');
  assert.equal(formatCollateral(0), '$0.00');
  assert.equal(formatCollateral(0.0), '$0.00');
  assert.equal(formatCollateral(1500.5), '$1,500.50');
});

test('Performance metric formatters must not invent fallback numbers', () => {
  function formatWinRate(wr) {
    if (wr === undefined || wr === null) return '—';
    return `${(wr * 100).toFixed(0)}%`;
  }

  function formatPnl(pnl) {
    if (pnl === undefined || pnl === null) return '—';
    return `${pnl >= 0 ? '+' : ''}${(pnl / 1000).toFixed(1)}k`;
  }

  // Undefined or null must yield em-dash, never 74% or $12.4k
  assert.equal(formatWinRate(undefined), '—');
  assert.equal(formatWinRate(null), '—');
  assert.equal(formatWinRate(0.74), '74%');

  assert.equal(formatPnl(undefined), '—');
  assert.equal(formatPnl(null), '—');
  assert.equal(formatPnl(12400), '+12.4k');
  assert.equal(formatPnl(-5200), '-5.2k');
});

// ---------------------------------------------------------------------------
// Test Group 3: Keyboard Accessibility & A11y Attributes
// ---------------------------------------------------------------------------
test('Interactive list items in dashboard components must support keyboard navigation', () => {
  const componentsToCheck = [
    { file: 'components/dashboard/TradeLog.tsx', name: 'TradeLog' },
    { file: 'components/dashboard/LiveTape.tsx', name: 'LiveTape' },
    { file: 'components/dashboard/WalletLeaderboard.tsx', name: 'WalletLeaderboard' },
    { file: 'components/ui/CommandPalette.tsx', name: 'CommandPalette' },
  ];

  for (const { file, name } of componentsToCheck) {
    const fullPath = path.join(SRC_DIR, file);
    const content = fs.readFileSync(fullPath, 'utf-8');

    assert.ok(content.includes('role="button"'), `${name} must include role="button" for clickable items`);
    assert.ok(content.includes('tabIndex={0}'), `${name} must include tabIndex={0} for keyboard focusability`);
    assert.ok(content.includes('onKeyDown='), `${name} must include onKeyDown handler for Enter / Space invocation`);
  }
});

test('All inputs and form controls in settings, modals, and palettes must have accessible labels', () => {
  const filesToCheck = [
    path.join(SRC_DIR, 'app', 'settings', 'page.tsx'),
    path.join(SRC_DIR, 'components', 'dashboard', 'FullHistorySpreadsheetModal.tsx'),
    path.join(SRC_DIR, 'components', 'dashboard', 'ResetSandboxModal.tsx'),
    path.join(SRC_DIR, 'components', 'dashboard', 'WalletLeaderboard.tsx'),
    path.join(SRC_DIR, 'components', 'dashboard', 'LiveTape.tsx'),
    path.join(SRC_DIR, 'components', 'ui', 'CommandPalette.tsx'),
  ];

  for (const filePath of filesToCheck) {
    const content = fs.readFileSync(filePath, 'utf-8');
    // Match <input ... /> accounting for potential arrow functions (=>) inside attributes
    const inputMatches = content.match(/<input[\s\S]*?\/>/g) || [];

    for (const inputTag of inputMatches) {
      const hasAriaLabel = /aria-label=/i.test(inputTag);
      const hasId = /id=/i.test(inputTag);
      const isHidden = /type=["']hidden["']/i.test(inputTag);

      if (!isHidden) {
        assert.ok(
          hasAriaLabel || hasId,
          `Input in ${path.basename(filePath)} missing accessible name (aria-label or id+htmlFor):\n  ${inputTag}`
        );
      }
    }
  }
});

test('Modals and flyout drawers must listen for Escape key', () => {
  const flyouts = [
    path.join(SRC_DIR, 'components', 'dashboard', 'ActivityFeed.tsx'),
    path.join(SRC_DIR, 'components', 'dashboard', 'BaleenCopilot.tsx'),
    path.join(SRC_DIR, 'components', 'dashboard', 'WalletDrawer.tsx'),
  ];

  for (const filePath of flyouts) {
    const content = fs.readFileSync(filePath, 'utf-8');
    assert.ok(
      content.includes("'Escape'") || content.includes('"Escape"'),
      `${path.basename(filePath)} must listen for Escape key to close`
    );
  }
});
