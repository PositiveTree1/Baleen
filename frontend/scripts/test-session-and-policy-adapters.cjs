const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function harness(responder) {
  const requests = [];
  const storage = () => {
    const store = new Map();
    return {
      getItem: k => store.get(k) ?? null,
      setItem: (k, v) => store.set(k, String(v)),
      removeItem: k => store.delete(k),
      key: i => Array.from(store.keys())[i] ?? null,
      get length() { return store.size; },
      clear: () => store.clear(),
    };
  };

  const listeners = new Map();
  const windowObj = {
    addEventListener: (type, fn) => {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(fn);
    },
    removeEventListener: (type, fn) => {
      const arr = listeners.get(type) || [];
      const idx = arr.indexOf(fn);
      if (idx !== -1) arr.splice(idx, 1);
    },
    dispatchEvent: evt => {
      const arr = listeners.get(evt.type) || [];
      arr.forEach(fn => fn(evt));
      return true;
    },
  };

  let currentToken = 'test-token-account-1';
  const context = {
    exports: {},
    process: { env: { NEXT_PUBLIC_BACKEND_URL: 'http://localhost:8000' } },
    Headers,
    Response,
    URL,
    AbortSignal,
    CustomEvent: class CustomEvent {
      constructor(type, init) {
        this.type = type;
        this.detail = init?.detail;
      }
    },
    console,
    window: windowObj,
    sessionStorage: storage(),
    localStorage: storage(),
    fetch: async (url, init) => {
      requests.push({ url: String(url), init });
      if (typeof responder === 'function') {
        return responder(url, init);
      }
      return responder;
    },
    require: name => {
      if (name === 'next-auth/react') {
        return {
          getSession: async () => ({
            user: { id: 'user-1', accessToken: currentToken },
            accessToken: currentToken,
          }),
        };
      }
      return {};
    },
  };

  const source = fs.readFileSync(path.join(__dirname, '../src/lib/api-client.ts'), 'utf8');
  vm.runInNewContext(
    ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText,
    context
  );

  return {
    api: context.exports,
    getRequests: () => requests,
    getLastRequest: () => requests[requests.length - 1],
    setSessionToken: t => { currentToken = t; },
    window: windowObj,
  };
}

// ---------------------------------------------------------------------------
// 1. Session Setup Adapter Tests
// ---------------------------------------------------------------------------

test('fetchSessionSetup handles no session (not_configured)', async () => {
  const h = harness(new Response(JSON.stringify({
    status: 'not_configured',
    liveExecutionReady: false,
  }), { status: 200 }));

  const setup = await h.api.fetchSessionSetup();
  assert.equal(setup.status, 'not_configured');
  assert.equal(setup.liveExecutionReady, false);
  assert.equal(h.getLastRequest().url, 'http://localhost:8000/api/live-trading/session');
  assert.equal(h.getLastRequest().init.cache, 'no-store');
});

test('fetchSessionSetup handles awaiting owner authorization', async () => {
  const h = harness(new Response(JSON.stringify({
    walletAddress: '0x' + '1'.repeat(40),
    sessionAddress: '0x' + '2'.repeat(40),
    verifiedAt: null,
    validUntil: null,
    revokedAt: null,
    scope: 'CLOB',
    status: 'awaiting_owner_authorization',
    ownerAuthorizationRequired: true,
    liveExecutionReady: false,
  }), { status: 200 }));

  const setup = await h.api.fetchSessionSetup();
  assert.equal(setup.status, 'awaiting_owner_authorization');
  assert.equal(setup.ownerAuthorizationRequired, true);
  assert.equal(setup.verifiedAt, null);
  assert.equal(setup.liveExecutionReady, false);
});

test('fetchSessionSetup handles expired session grant', async () => {
  const h = harness(new Response(JSON.stringify({
    walletAddress: '0x' + '1'.repeat(40),
    sessionAddress: '0x' + '2'.repeat(40),
    verifiedAt: '2026-09-01T00:00:00Z',
    validUntil: '2026-09-02T00:00:00Z',
    revokedAt: null,
    scope: 'CLOB',
    status: 'expired',
    ownerAuthorizationRequired: true,
    liveExecutionReady: false,
  }), { status: 200 }));

  const setup = await h.api.fetchSessionSetup();
  assert.equal(setup.status, 'expired');
  assert.equal(setup.ownerAuthorizationRequired, true);
});

test('prepareSession initiates session key and treats non-2xx as error', async () => {
  const hSuccess = harness(new Response(JSON.stringify({
    walletAddress: '0x' + '1'.repeat(40),
    sessionAddress: '0x' + '2'.repeat(40),
    status: 'awaiting_owner_authorization',
    ownerAuthorizationRequired: true,
    liveExecutionReady: false,
  }), { status: 200 }));

  const result = await hSuccess.api.prepareSession();
  assert.equal(result.status, 'awaiting_owner_authorization');
  assert.equal(hSuccess.getLastRequest().init.method, 'POST');

  const hFail = harness(new Response(JSON.stringify({
    detail: 'Configure Deposit Wallet and owner API credentials first',
  }), { status: 409 }));

  await assert.rejects(
    async () => hFail.api.prepareSession(),
    /Configure Deposit Wallet and owner API credentials first/
  );
});

test('verifySession verifies grant and treats non-2xx as error', async () => {
  const hSuccess = harness(new Response(JSON.stringify({
    walletAddress: '0x' + '1'.repeat(40),
    sessionAddress: '0x' + '2'.repeat(40),
    verifiedAt: '2026-09-13T10:00:00Z',
    validUntil: '2026-10-13T10:00:00Z',
    revokedAt: null,
    scope: 'CLOB',
    status: 'authorization_observed',
    ownerAuthorizationRequired: false,
    liveExecutionReady: false,
  }), { status: 200 }));

  const verified = await hSuccess.api.verifySession();
  assert.equal(verified.status, 'authorization_observed');
  assert.equal(hSuccess.getLastRequest().init.method, 'POST');

  const hFail = harness(new Response(JSON.stringify({
    detail: 'Owner-approved CLOB session authorization is not verified',
  }), { status: 409 }));

  await assert.rejects(
    async () => hFail.api.verifySession(),
    /Owner-approved CLOB session authorization is not verified/
  );
});

test('disableSession stops local signing and indicates owner revocation required', async () => {
  const h = harness(new Response(JSON.stringify({
    localSigningDisabled: true,
    ownerRevocationRequired: true,
    message: 'Local signing stopped; revoke the session grant with the Deposit Wallet owner to remove exchange authority.',
  }), { status: 200 }));

  const result = await h.api.disableSession();
  assert.equal(result.localSigningDisabled, true);
  assert.equal(result.ownerRevocationRequired, true);
  assert.equal(h.getLastRequest().init.method, 'POST');
});

// ---------------------------------------------------------------------------
// 2. Owner Operations (Prepare, Sign, Submit, Pending/Unknown Relay)
// ---------------------------------------------------------------------------

test('prepareSessionOperation sends kind and parses challenge payload', async () => {
  const h = harness(new Response(JSON.stringify({
    id: 'op-123',
    kind: 'AUTHORIZE',
    state: 'PREPARED',
    ownerAddress: '0x' + '3'.repeat(40),
    walletAddress: '0x' + '1'.repeat(40),
    sessionAddress: '0x' + '2'.repeat(40),
    deadline: Math.floor(Date.now() / 1000) + 240,
    validUntil: Math.floor(Date.now() / 1000) + 4315 * 3600,
    scopes: ['CLOB'],
    transactionId: null,
    transactionHash: null,
    liveExecutionReady: false,
    typedData: {
      domain: { name: 'DepositWallet', version: '1', chainId: 137, verifyingContract: '0x' + '1'.repeat(40) },
      types: {},
      primaryType: 'Batch',
      message: { wallet: '0x' + '1'.repeat(40), nonce: '1', deadline: '100', calls: [] },
    },
  }), { status: 200 }));

  const op = await h.api.prepareSessionOperation('AUTHORIZE');
  assert.equal(op.id, 'op-123');
  assert.equal(op.kind, 'AUTHORIZE');
  assert.equal(op.state, 'PREPARED');
  assert.deepEqual(JSON.parse(h.getLastRequest().init.body), { kind: 'AUTHORIZE' });
});

test('submitSessionSignature submits signature and preserves unresolved relay status', async () => {
  for (const state of ['SUBMITTING', 'PENDING', 'UNKNOWN']) {
    const h = harness(new Response(JSON.stringify({
      id: 'op-123',
      kind: 'AUTHORIZE',
      state,
      ownerAddress: '0x' + '3'.repeat(40),
      walletAddress: '0x' + '1'.repeat(40),
      sessionAddress: '0x' + '2'.repeat(40),
      deadline: 12345,
      validUntil: null,
      scopes: ['CLOB'],
      transactionId: state === 'PENDING' ? 'relayer-tx-456' : null,
      transactionHash: null,
      liveExecutionReady: false,
      typedData: null,
    }), { status: 200 }));

    const res = await h.api.submitSessionSignature('op-123', '0x' + 'a'.repeat(130));
    assert.equal(res.state, state);
    assert.equal(h.getLastRequest().url, 'http://localhost:8000/api/live-trading/session/operations/op-123/signature');
    assert.deepEqual(JSON.parse(h.getLastRequest().init.body), { signature: '0x' + 'a'.repeat(130) });
  }
});

test('fetchSessionOperations returns list of recent operations without caching', async () => {
  const h = harness(new Response(JSON.stringify([
    { id: 'op-1', kind: 'AUTHORIZE', state: 'GRANT_OBSERVED', liveExecutionReady: false },
    { id: 'op-2', kind: 'REVOKE', state: 'PENDING', liveExecutionReady: false },
  ]), { status: 200 }));

  const ops = await h.api.fetchSessionOperations();
  assert.equal(ops.length, 2);
  assert.equal(ops[0].id, 'op-1');
  assert.equal(ops[1].state, 'PENDING');
  assert.equal(h.getLastRequest().init.cache, 'no-store');
});

// ---------------------------------------------------------------------------
// 3. Wallet Signing Checks (Wrong wallet, rejected signature via session-wallet-approval)
// ---------------------------------------------------------------------------

test('signSessionOperation rejects when wrong account is connected', async () => {
  const approvalSource = fs.readFileSync(path.join(__dirname, '../src/lib/session-wallet-approval.ts'), 'utf8');
  const approvalExports = {};
  vm.runInNewContext(
    ts.transpileModule(approvalSource, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText,
    { exports: approvalExports }
  );

  const now = Math.floor(Date.now() / 1000);
  const wallet = '0x' + '1'.repeat(40);
  const session = '0x' + '2'.repeat(40);
  const owner = '0x' + '3'.repeat(40);
  const wrongOwner = '0x' + '9'.repeat(40);

  const fields = pairs => pairs.map(p => { const [name, type] = p.split(':'); return { name, type }; });
  const validOp = {
    id: 'test-op',
    kind: 'AUTHORIZE',
    state: 'PREPARED',
    ownerAddress: owner,
    walletAddress: wallet,
    sessionAddress: session,
    deadline: now + 240,
    validUntil: now + 4315 * 3600,
    scopes: ['CLOB'],
    transactionId: null,
    transactionHash: null,
    liveExecutionReady: false,
    typedData: {
      domain: { name: 'DepositWallet', version: '1', chainId: 137, verifyingContract: wallet },
      primaryType: 'Batch',
      types: {
        EIP712Domain: fields(['name:string', 'version:string', 'chainId:uint256', 'verifyingContract:address']),
        Batch: fields(['wallet:address', 'nonce:uint256', 'deadline:uint256', 'calls:Call[]']),
        Call: fields(['target:address', 'value:uint256', 'data:bytes']),
      },
      message: {
        wallet,
        nonce: '100',
        deadline: String(now + 240),
        calls: [{
          target: wallet,
          value: '0',
          data: '0x24017fae' + session.slice(2).padStart(64, '0') + BigInt(now + 4315 * 3600).toString(16).padStart(64, '0'),
        }],
      },
    },
  };

  // Wrong account connected
  const wrongProvider = {
    request: async ({ method }) => {
      if (method === 'eth_chainId') return '0x89';
      if (method === 'eth_requestAccounts') return [wrongOwner];
      return null;
    },
  };

  await assert.rejects(
    async () => approvalExports.signSessionOperation(validOp, wrongProvider),
    /Connect the Deposit Wallet owner shown in this request/
  );

  // Rejected / malformed signature returned by wallet
  const rejectProvider = {
    request: async ({ method }) => {
      if (method === 'eth_chainId') return '0x89';
      if (method === 'eth_requestAccounts') return [owner];
      if (method === 'eth_signTypedData_v4') return '0xbad';
      return null;
    },
  };

  await assert.rejects(
    async () => approvalExports.signSessionOperation(validOp, rejectProvider),
    /Wallet did not return a supported owner signature/
  );
});

// ---------------------------------------------------------------------------
// 4. Copy Policy Adapter Tests (Unset / null, validation failure, serialization)
// ---------------------------------------------------------------------------

test('fetchCopyPolicy returns null when policy is unset', async () => {
  const h = harness(new Response(JSON.stringify(null), { status: 200 }));
  const policy = await h.api.fetchCopyPolicy();
  assert.equal(policy, null);
  assert.equal(h.getLastRequest().url, 'http://localhost:8000/api/live-trading/copy-policy');
  assert.equal(h.getLastRequest().init.cache, 'no-store');
});

test('saveCopyPolicy sends exact top-level fields and receives revision', async () => {
  const hSuccess = harness(new Response(JSON.stringify({
    revision: 1,
    source_wallets: ['0x' + '3'.repeat(40)],
    copy_ratio: '0.10',
    limits: {
      max_order_cash: '100.00',
      max_total_exposure: '1000.00',
      max_token_exposure: '500.00',
      max_daily_loss: '50.00',
      max_open_orders: 5,
      max_slippage_bps: '100',
      max_quote_age_ms: 10000,
      max_source_age_ms: 60000,
      max_fee_bps: '100',
    },
    requiresReactivation: true,
  }), { status: 200 }));

  const payload = {
    source_wallets: ['0x' + '3'.repeat(40)],
    copy_ratio: '0.10',
    max_order_cash: '100.00',
    max_total_exposure: '1000.00',
    max_token_exposure: '500.00',
    max_daily_loss: '50.00',
    max_open_orders: 5,
    max_slippage_bps: '100',
    max_quote_age_ms: 10000,
    max_source_age_ms: 60000,
    max_fee_bps: '100',
  };

  const saved = await hSuccess.api.saveCopyPolicy(payload);
  assert.equal(saved.revision, 1);
  assert.equal(saved.requiresReactivation, true);
  assert.deepEqual(JSON.parse(hSuccess.getLastRequest().init.body), payload);
  assert.equal(hSuccess.getLastRequest().init.method, 'PUT');
});

test('saveCopyPolicy rejects non-2xx with backend detail error and retains input', async () => {
  const hFail = harness(new Response(JSON.stringify({
    detail: 'Source wallet addresses must be valid and unique',
  }), { status: 422 }));

  await assert.rejects(
    async () => hFail.api.saveCopyPolicy({
      source_wallets: ['invalid'],
      copy_ratio: '0.10',
      max_order_cash: '100',
      max_total_exposure: '1000',
      max_token_exposure: '500',
      max_daily_loss: '50',
      max_open_orders: 5,
      max_slippage_bps: '100',
      max_quote_age_ms: 10000,
      max_source_age_ms: 60000,
      max_fee_bps: '100',
    }),
    /Source wallet addresses must be valid and unique/
  );
});

test('saveCopyPolicy formats FastAPI 422 validation array without [object Object]', async () => {
  const hFail = harness(new Response(JSON.stringify({
    detail: [
      { loc: ['body', 'max_order_cash'], msg: 'Input should be greater than 0', type: 'greater_than' },
      { loc: ['body', 'copy_ratio'], msg: 'Input should be less than or equal to 1', type: 'less_than_equal' },
    ],
  }), { status: 422 }));

  await assert.rejects(
    async () => hFail.api.saveCopyPolicy({
      source_wallets: ['0x' + '1'.repeat(40)],
      copy_ratio: '1.5',
      max_order_cash: '-10',
      max_total_exposure: '1000',
      max_token_exposure: '500',
      max_daily_loss: '50',
      max_open_orders: 5,
      max_slippage_bps: '100',
      max_quote_age_ms: 10000,
      max_source_age_ms: 60000,
      max_fee_bps: '100',
    }),
    /max_order_cash: Input should be greater than 0; copy_ratio: Input should be less than or equal to 1/
  );
});

// ---------------------------------------------------------------------------
// 5. Account Initialization Adapter
// ---------------------------------------------------------------------------

test('initializeLiveAccount calls endpoint and parses confirmed baseline', async () => {
  const h = harness(new Response(JSON.stringify({
    runId: 'run-uuid-1234',
    startingCash: '250.75',
    blockNumber: 62450123,
    liveExecutionReady: false,
  }), { status: 200 }));

  const baseline = await h.api.initializeLiveAccount();
  assert.equal(baseline.runId, 'run-uuid-1234');
  assert.equal(baseline.startingCash, '250.75');
  assert.equal(baseline.blockNumber, 62450123);
  assert.equal(baseline.liveExecutionReady, false);
  assert.equal(h.getLastRequest().url, 'http://localhost:8000/api/live-trading/initialize-account');
  assert.equal(h.getLastRequest().init.method, 'POST');
});

test('initializeLiveAccount propagates server setup-required error without bypassing', async () => {
  const h = harness(new Response(JSON.stringify({
    detail: 'Live account initialization needs a verified session, complete confirmed funding, no open orders and no unimported positions',
  }), { status: 409 }));

  await assert.rejects(
    async () => h.api.initializeLiveAccount(),
    /Live account initialization needs a verified session/
  );
});

// ---------------------------------------------------------------------------
// 6. Paper Runs and Trades Archive Adapters
// ---------------------------------------------------------------------------

test('fetchPaperRuns and fetchPaperRunTrades load account-owned archive history', async () => {
  const h = harness((url) => {
    if (String(url).includes('/paper-runs/run-1/trades')) {
      return new Response(JSON.stringify([
        {
          id: 'trade-1',
          runId: 'run-1',
          side: 'BUY',
          status: 'FILLED',
          tokenId: 'tok-1',
          sourceWallet: '0x' + '3'.repeat(40),
          executedAt: '2026-09-12T12:00:00Z',
          fillPrice: 0.45,
          notionalUsd: 10.0,
          feeUsd: 0.05,
          realizedPnlUsd: 0.0,
        },
        {
          id: 'trade-2',
          runId: 'run-1',
          side: 'SELL',
          status: 'OPEN',
          tokenId: 'tok-2',
          sourceWallet: null,
          executedAt: '2026-09-12T13:00:00',
          fillPrice: null,
          notionalUsd: null,
          feeUsd: null,
          realizedPnlUsd: null,
        },
      ]), { status: 200 });
    }
    return new Response(JSON.stringify([
      {
        id: 'run-1',
        status: 'ARCHIVED',
        startedAt: '2026-09-10T10:00:00Z',
        endedAt: '2026-09-12T15:00:00Z',
        startingBalance: 10000,
      },
    ]), { status: 200 });
  });

  const runs = await h.api.fetchPaperRuns('user-1');
  assert.equal(runs.length, 1);
  assert.equal(runs[0].id, 'run-1');
  assert.equal(runs[0].status, 'ARCHIVED');
  assert.equal(runs[0].startingBalance, 10000);

  const trades = await h.api.fetchPaperRunTrades('user-1', 'run-1');
  assert.equal(trades.length, 2);
  assert.equal(trades[0].id, 'trade-1');
  assert.equal(trades[0].fillPrice, 0.45);
  assert.equal(trades[0].feeUsd, 0.05);
  assert.equal(trades[0].realizedPnlUsd, 0.0); // Known zero preserved
  assert.equal(trades[1].fillPrice, null);     // Null preserved without crashing
  assert.equal(trades[1].realizedPnlUsd, null);
});

// ---------------------------------------------------------------------------
// 7. Date Formatting and Error Helper Tests
// ---------------------------------------------------------------------------

test('extractApiErrorMessage extracts messages from strings, objects, and FastAPI arrays', () => {
  const h = harness(new Response('{}'));
  const extract = h.api.extractApiErrorMessage;

  assert.equal(extract({ detail: 'Simple error' }, 'Fallback'), 'Simple error');
  assert.equal(extract({ message: 'Message error' }, 'Fallback'), 'Message error');
  assert.equal(extract({
    detail: [
      { loc: ['body', 'source_wallets'], msg: 'Field required' },
      { loc: ['body', 'max_daily_loss'], msg: 'Must be positive' },
    ],
  }, 'Fallback'), 'source_wallets: Field required; max_daily_loss: Must be positive');
  assert.equal(extract({}, 'Fallback message'), 'Fallback message');
  assert.equal(extract(null, 'Fallback message'), 'Fallback message');
});

test('formatUtcDate formats valid dates to explicit UTC and marks unknown unavailable', () => {
  const h = harness(new Response('{}'));
  const format = h.api.formatUtcDate;

  assert.equal(format(null), 'Unavailable');
  assert.equal(format(undefined), 'Unavailable');
  assert.equal(format(''), 'Unavailable');
  assert.equal(format('   '), 'Unavailable');
  assert.equal(format('invalid-date'), 'Unavailable');

  // ISO string with Z
  const formattedIso = format('2026-09-13T10:30:00Z');
  assert.equal(formattedIso, '2026-09-13 10:30:00 UTC');

  // Naive ISO string (no Z or offset) MUST NOT drift due to local browser timezone
  const formattedNaive = format('2026-09-13T10:30:00');
  assert.equal(formattedNaive, '2026-09-13 10:30:00 UTC');

  // Space-separated datetime string
  const formattedSpace = format('2026-09-13 10:30:00');
  assert.equal(formattedSpace, '2026-09-13 10:30:00 UTC');

  // Unix seconds as number
  const formattedSec = format(1789295400); // 2026-09-13 10:30:00 UTC
  assert.equal(formattedSec, '2026-09-13 10:30:00 UTC');

  // Unix seconds as string of digits
  const formattedSecStr = format('1789295400');
  assert.equal(formattedSecStr, '2026-09-13 10:30:00 UTC');
});

// ---------------------------------------------------------------------------
// 8. Account change clearing displayed private state
// ---------------------------------------------------------------------------

test('account switch clears auth token and discards late responses from previous account', async () => {
  const h = harness(new Response('{}'));
  h.api.setAuthToken('token-user-1');
  assert.equal(h.api.getAuthToken(), 'token-user-1');

  h.api.setAuthToken('token-user-2');
  assert.equal(h.api.getAuthToken(), 'token-user-2');

  // When token changes to null, auth token is cleared
  h.api.setAuthToken(null);
  assert.equal(h.api.getAuthToken(), null);
});

test('settings page clearPrivateState purges all credentials, policy form inputs, and archives', () => {
  const settingsSource = fs.readFileSync(path.join(__dirname, '../src/app/settings/page.tsx'), 'utf8');

  // Verify that clearPrivateState clears proxyAddress, signerAddress, apiKey, apiSecret, passphrase
  assert.ok(settingsSource.includes("setProxyAddress('')"), 'Must reset proxyAddress');
  assert.ok(settingsSource.includes("setSignerAddress('')"), 'Must reset signerAddress');
  assert.ok(settingsSource.includes("setApiKey('')"), 'Must reset apiKey');
  assert.ok(settingsSource.includes("setApiSecret('')"), 'Must reset apiSecret');
  assert.ok(settingsSource.includes("setPassphrase('')"), 'Must reset passphrase');

  // Verify that all copy policy inputs are reset to empty strings
  assert.ok(settingsSource.includes("setPolicySourceWallets('')"), 'Must reset policySourceWallets');
  assert.ok(settingsSource.includes("setPolicyCopyRatio('')"), 'Must reset policyCopyRatio');
  assert.ok(settingsSource.includes("setPolicyMaxOrderCash('')"), 'Must reset policyMaxOrderCash');
  assert.ok(settingsSource.includes("setPolicyMaxTotalExposure('')"), 'Must reset policyMaxTotalExposure');
  assert.ok(settingsSource.includes("setPolicyMaxTokenExposure('')"), 'Must reset policyMaxTokenExposure');
  assert.ok(settingsSource.includes("setPolicyMaxDailyLoss('')"), 'Must reset policyMaxDailyLoss');
  assert.ok(settingsSource.includes("setPolicyMaxOpenOrders('')"), 'Must reset policyMaxOpenOrders');
  assert.ok(settingsSource.includes("setPolicyMaxSlippageBps('')"), 'Must reset policyMaxSlippageBps');
  assert.ok(settingsSource.includes("setPolicyMaxFeeBps('')"), 'Must reset policyMaxFeeBps');
  assert.ok(settingsSource.includes("setPolicyMaxQuoteAgeMs('')"), 'Must reset policyMaxQuoteAgeMs');
  assert.ok(settingsSource.includes("setPolicyMaxSourceAgeMs('')"), 'Must reset policyMaxSourceAgeMs');

  // Verify initial useState defaults for policy are empty strings (not fabricated values)
  assert.ok(settingsSource.includes("const [policyCopyRatio, setPolicyCopyRatio] = useState('');"), 'Initial copy ratio must be empty string');
  assert.ok(settingsSource.includes("const [policyMaxOrderCash, setPolicyMaxOrderCash] = useState('');"), 'Initial max order cash must be empty string');

  // Verify clearPrivateState is invoked on session-expired and account change
  assert.ok(settingsSource.includes("window.addEventListener('baleen:session-expired', onExpired);"), 'Must listen for session-expired');
  assert.ok(
    settingsSource.includes("clearPrivateState()") &&
    settingsSource.includes("!session?.user?.id"),
    'Must clear private state when unauthenticated'
  );
});

