const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function harness(response) {
  let request;
  const storage = () => ({ getItem: () => null, setItem: () => {}, removeItem: () => {}, key: () => null, length: 0 });
  const context = {
    exports: {}, process: { env: {} }, Headers, Response, URL, AbortSignal, console,
    window: {}, sessionStorage: storage(), localStorage: storage(),
    fetch: async (url, init) => { request = { url, init }; return response; },
    require: name => { assert.equal(name, 'next-auth/react'); return { getSession: async () => null }; },
  };
  const source = fs.readFileSync(path.join(__dirname, '../src/lib/api-client.ts'), 'utf8');
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
  } }).outputText, context);
  return { api: context.exports, getRequest: () => request };
}

test('fetchUserSettings preserves valid zero and negative balances', async () => {
  const h = harness(new Response(JSON.stringify({ id: 'u', email: 'a@b.test', startingBalance: 0, currentBalance: -12.5 })));
  const result = await h.api.fetchUserSettings('u');
  assert.equal(result.startingBalance, 0);
  assert.equal(result.currentBalance, -12.5);
});

test('fetchUserSettings rejects successful responses with missing or malformed balances', async () => {
  for (const body of [
    { id: 'u', startingBalance: 100 },
    { id: 'u', currentBalance: 100 },
    { id: 'u', startingBalance: '10000', currentBalance: 10000 },
    { id: 'u', startingBalance: 10000, currentBalance: null },
  ]) {
    const h = harness(new Response(JSON.stringify(body)));
    assert.equal(await h.api.fetchUserSettings('u'), null);
  }
});

test('updateUserSettings preserves backend balances and sends only preference fields', async () => {
  const h = harness(new Response(JSON.stringify({ id: 'u', email: 'a@b.test', sandbox_starting_balance_usd: 2500, sandbox_balance_usd: 0, risk_profile: 'Balanced', daily_digest_opt_in: false })));
  const result = await h.api.updateUserSettings('u', { riskProfile: 'Balanced', dailyDigestOptIn: false });
  assert.equal(result.startingBalance, 2500);
  assert.equal(result.currentBalance, 0);
  assert.deepEqual(JSON.parse(h.getRequest().init.body), { risk_profile: 'Balanced', daily_digest_opt_in: false });
});

test('updateUserSettings rejects malformed successful responses instead of defaulting to 10000', async () => {
  const h = harness(new Response(JSON.stringify({ id: 'u', email: 'a@b.test', risk_profile: 'Balanced' })));
  assert.equal(await h.api.updateUserSettings('u', { riskProfile: 'Balanced' }), null);
});

test('nullable evidence display preserves zero and marks unknown values unavailable', () => {
  const display = value => value === null || value === undefined ? 'Unavailable' : `$${value.toFixed(2)}`;
  assert.equal(display(0), '$0.00');
  assert.equal(display(-1.25), '$-1.25');
  assert.equal(display(null), 'Unavailable');
  assert.equal(display(undefined), 'Unavailable');
});

test('mixed aggregate evidence reports a known-record subtotal and omission count', () => {
  const rows = [{ pnl: 0, feeUsd: 0 }, { pnl: 12.5, feeUsd: null }, { pnl: null, feeUsd: 1.25 }];
  const knownPnl = rows.filter(row => row.pnl !== null && row.pnl !== undefined);
  const knownFees = rows.filter(row => row.feeUsd !== null && row.feeUsd !== undefined);
  assert.equal(knownPnl.reduce((sum, row) => sum + row.pnl, 0), 12.5);
  assert.equal(knownFees.reduce((sum, row) => sum + row.feeUsd, 0), 1.25);
  assert.equal(rows.length - knownPnl.length, 1);
  assert.equal(rows[0].pnl, 0);
});

test('portfolio summary adapter preserves incomplete nullable totals and coverage metadata', async () => {
  const h = harness(new Response(JSON.stringify({
    startingBalance: null, currentBalance: null, totalPnlUsd: null, totalPnlPct: null,
    totalFeesPaidUsd: null, totalNotionalInvested: null, filledTradesCount: 3,
    valuationStatus: 'INCOMPLETE', unvaluedTradesCount: 2, knownPnlUsd: 1.25, knownFeesPaidUsd: 0,
  })));
  const result = await h.api.fetchPortfolioSummary('u');
  assert.equal(result.startingBalance, null);
  assert.equal(result.totalPnlUsd, null);
  assert.equal(result.totalFeesPaidUsd, null);
  assert.equal(result.totalNotionalInvested, null);
  assert.equal(result.valuationStatus, 'INCOMPLETE');
  assert.equal(result.unvaluedTradesCount, 2);
  assert.equal(result.knownFeesPaidUsd, 0);
});

test('wallet list adapter preserves unknown statistics and valid zero', async () => {
  const h = harness(new Response(JSON.stringify([
    { address: '0xunknown', tier: 'standard', win_rate_pct: null, all_time_pnl_usd: null, avg_trades_per_day: null, baleen_score: null, max_drawdown_pct: null, total_trades_analyzed: null, avg_hold_hours: null, median_inter_trade_gap_hours: 0 },
    { address: '0xzero', tier: 'standard', win_rate_pct: 0, all_time_pnl_usd: 0, avg_trades_per_day: 0, baleen_score: 0, max_drawdown_pct: 0, total_trades_analyzed: 0, avg_hold_hours: null, median_inter_trade_gap_hours: 0 },
  ])));
  const [unknown, zero] = await h.api.fetchWallets();
  assert.equal(unknown.winRate, null);
  assert.equal(unknown.pnl, null);
  assert.equal(unknown.tradesPerDay, null);
  assert.equal(unknown.score, null);
  assert.equal(unknown.medianInterTradeGapHours, 0);
  assert.equal(zero.winRate, 0);
  assert.equal(zero.pnl, 0);
  assert.equal(zero.tradesPerDay, 0);
  assert.equal(zero.score, 0);
  assert.equal(zero.medianInterTradeGapHours, 0);
});

test('wallet detail adapter preserves unknown statistics and keeps trade gap separate from hold time', async () => {
  const h = harness(new Response(JSON.stringify({
    wallet: { address: '0xunknown', tier: 'standard', win_rate_pct: null, all_time_pnl_usd: null, avg_trades_per_day: null, baleen_score: null, max_drawdown_pct: null, total_trades_analyzed: null, avg_hold_hours: null, median_inter_trade_gap_hours: 0 },
    score_history: [], daily_pnl_history: [], recent_trades: [],
  })));
  const result = await h.api.fetchWallet('0xunknown');
  assert.equal(result.winRate, null);
  assert.equal(result.pnl, null);
  assert.equal(result.tradesPerDay, null);
  assert.equal(result.score, null);
  assert.equal(result.maxDrawdown, null);
  assert.equal(result.totalTradesAnalyzed, null);
  assert.equal(result.avgHoldHours, null);
  assert.equal(result.medianInterTradeGapHours, 0);
});

test('live execution state fetch is uncached and preserves decimal strings and cancellation timestamp', async () => {
  const h = harness(new Response(JSON.stringify({
    status: 'available', liveExecutionReady: false,
    cash: '12.340001', reservedCash: '0.000001', availableCash: '12.34',
    reconciledAt: '2026-09-12T10:11:12+00:00',
    reconciliation: { status: 'consistent', detail: 'Matched', finishedAt: null },
    orders: [{ id: 'order-1', tokenId: 'token-1', side: 'BUY', state: 'PREPARED', quantity: '2.0001', filledQuantity: '0', limitPrice: '0.37001', cancelRequestedAt: '2026-09-12T10:12:00+00:00' }],
  })));
  const result = await h.api.fetchLiveExecutionState();
  assert.equal(h.getRequest().url.endsWith('/api/live-trading/execution-state'), true);
  assert.equal(h.getRequest().init.cache, 'no-store');
  assert.equal(result.cash, '12.340001');
  assert.equal(result.reservedCash, '0.000001');
  assert.equal(result.orders[0].quantity, '2.0001');
  assert.equal(result.orders[0].filledQuantity, '0');
  assert.equal(result.orders[0].cancelRequestedAt, '2026-09-12T10:12:00+00:00');
  assert.equal(result.liveExecutionReady, false);
});

test('order cancellation stays pending only until the order reaches a terminal state', () => {
  const h = harness(new Response('{}'));
  const label = h.api.getLiveOrderStateLabel;
  assert.equal(label({ state: 'PREPARED', cancelRequestedAt: '2026-09-12T10:12:00+00:00' }), 'Pending cancellation');
  assert.equal(label({ state: 'SUBMITTING', cancelRequestedAt: '2026-09-12T10:12:00+00:00' }), 'Pending cancellation');
  for (const state of ['CANCELLED', 'FILLED', 'VOID']) {
    assert.equal(label({ state, cancelRequestedAt: '2026-09-12T10:12:00+00:00' }), state);
  }
  assert.equal(label({ state: 'ACKNOWLEDGED', cancelRequestedAt: null }), 'ACKNOWLEDGED');
  assert.equal(label({ state: null, cancelRequestedAt: null }), 'Unavailable');
});
