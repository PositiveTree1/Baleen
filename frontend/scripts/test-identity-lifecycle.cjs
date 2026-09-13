const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function createHarness() {
  let session = { user: { accessToken: 'token-active-session', id: 'user-alpha' } };
  let networkCalls = [];
  let networkHandler = async (url, init) => {
    networkCalls.push({ url, init });
    return new Response(JSON.stringify({ status: 'ok' }), { status: 200 });
  };
  const events = [];
  const storage = () => {
    const values = new Map();
    return {
      getItem: k => values.get(k) ?? null,
      setItem: (k, v) => values.set(k, v),
      removeItem: k => values.delete(k),
      key: i => [...values.keys()][i],
      get length() { return values.size; },
      clear: () => values.clear()
    };
  };

  const context = {
    exports: {},
    process: { env: { NEXT_PUBLIC_BACKEND_URL: 'http://localhost:8000' } },
    Headers,
    Response,
    AbortSignal,
    URL,
    console,
    sessionStorage: storage(),
    localStorage: storage(),
    window: {
      dispatchEvent: event => events.push(event.type)
    },
    CustomEvent: class { constructor(type) { this.type = type; } },
    fetch: (...args) => networkHandler(...args),
    require: name => {
      assert.equal(name, 'next-auth/react');
      return { getSession: async () => session };
    }
  };

  const source = fs.readFileSync(path.join(__dirname, '../src/lib/api-client.ts'), 'utf8');
  vm.runInNewContext(
    ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
    }).outputText,
    context
  );

  return {
    api: context.exports,
    context,
    events,
    getNetworkCalls: () => networkCalls,
    setSession: val => { session = val; },
    setNetworkHandler: fn => { networkHandler = fn; }
  };
}

test('Identity Lifecycle Journey 1: Signup & Returning User Login', async () => {
  const h = createHarness();
  
  // Set session as newly authenticated
  h.setSession({ user: { accessToken: 'token-new-user', id: 'new-user-id' } });
  
  // Request sends Bearer token
  h.setNetworkHandler(async (url, init) => {
    assert.equal(init.headers.get('Authorization'), 'Bearer token-new-user');
    return new Response(JSON.stringify({ id: 'new-user-id', email: 'new@baleen.ai' }));
  });

  const res = await h.api.fetchWithAuth('http://localhost:8000/api/me');
  assert.equal(res.status, 200);
  assert.equal(h.api.getAuthToken(), 'token-new-user');
});

test('Identity Lifecycle Journey 2: Logout Backend Revocation', async () => {
  const h = createHarness();
  let logoutCalled = false;
  
  h.setSession({ user: { accessToken: 'token-to-revoke', id: 'user-id' } });
  await h.api.fetchWithAuth('http://localhost:8000/api/me');
  assert.equal(h.api.getAuthToken(), 'token-to-revoke');

  h.setNetworkHandler(async (url, init) => {
    if (url.includes('/api/auth/logout')) {
      assert.equal(init.method, 'POST');
      assert.equal(init.headers['Authorization'], 'Bearer token-to-revoke');
      logoutCalled = true;
      return new Response(JSON.stringify({ status: 'ok' }));
    }
    return new Response('[]');
  });

  await h.api.logoutBackend();
  assert.equal(logoutCalled, true);
  assert.equal(h.api.getAuthToken(), null);
});

test('Identity Lifecycle Journey 3: 401 Session Expiry Trigger', async () => {
  const h = createHarness();
  h.setSession({ user: { accessToken: 'expired-token', id: 'user-id' } });
  
  h.setNetworkHandler(async () => {
    return new Response(JSON.stringify({ detail: 'Token has been revoked.' }), { status: 401 });
  });

  const res = await h.api.fetchWithAuth('http://localhost:8000/api/me');
  assert.equal(res.status, 401);
  assert.equal(h.api.getAuthToken(), null);
  assert.ok(h.events.includes('baleen:session-expired'));
});

test('Identity Lifecycle Journey 4: Cross-tab & Multi-Account Isolation', async () => {
  const h = createHarness();
  
  // Tab 1 User A
  h.setSession({ user: { accessToken: 'token-user-a', id: 'user-a' } });
  h.setNetworkHandler(async (url, init) => {
    return new Response(JSON.stringify([{ id: 'trade-a' }]));
  });
  const logsA = await h.api.fetchExecutionLogs('user-a');
  assert.equal(logsA.length, 1);

  // Tab switches to User B
  h.setSession({ user: { accessToken: 'token-user-b', id: 'user-b' } });
  h.setNetworkHandler(async (url, init) => {
    assert.equal(init.headers.get('Authorization'), 'Bearer token-user-b');
    return new Response(JSON.stringify([]));
  });

  // Fetching logs for User B receives User B's data, caches cleared
  const logsB = await h.api.fetchExecutionLogs('user-b');
  assert.equal(logsB.length, 0);
  assert.equal(h.api.getAuthToken(), 'token-user-b');
});

test('Identity Lifecycle Journey 5: No Persistent Plaintext Tokens in Browser Storage', async () => {
  const h = createHarness();
  h.context.localStorage.setItem('baleen_auth_token', 'rogue_token');
  h.context.sessionStorage.setItem('baleen_auth_token', 'rogue_token');
  
  h.setSession({ user: { accessToken: 'session-token' } });
  await h.api.fetchWithAuth('http://localhost:8000/api/me');

  // Both storage mechanisms must be purged
  assert.equal(h.context.localStorage.getItem('baleen_auth_token'), null);
  assert.equal(h.context.sessionStorage.getItem('baleen_auth_token'), null);
});
