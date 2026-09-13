const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

// Exercise the actual client module with browser/session/network boundaries mocked.
function harness() {
  let session = { user: { accessToken: 'account-a' } };
  let network = async () => new Response('[]');
  const events = [];
  const storage = () => {
    const values = new Map();
    return { getItem: k => values.get(k) ?? null, setItem: (k, v) => values.set(k, v),
      removeItem: k => values.delete(k), key: i => [...values.keys()][i], get length() { return values.size; } };
  };
  const context = { exports: {}, process: { env: {} }, Headers, Response, URL, AbortSignal, console,
    sessionStorage: storage(), localStorage: storage(),
    window: { dispatchEvent: event => events.push(event.type) },
    CustomEvent: class { constructor(type) { this.type = type; } },
    fetch: (...args) => network(...args),
    require: name => {
      assert.equal(name, 'next-auth/react');
      return { getSession: async () => session };
    } };
  const source = fs.readFileSync(path.join(__dirname, '../src/lib/api-client.ts'), 'utf8');
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
  } }).outputText, context);
  return { api: context.exports, context, events,
    setSession: value => { session = value; }, setNetwork: value => { network = value; } };
}

test('signed session supplies bearer, legacy browser token is removed', async () => {
  const h = harness();
  h.context.localStorage.setItem('baleen_auth_token', 'previous-account');
  h.setNetwork(async (_, init) => {
    assert.equal(init.headers.get('Authorization'), 'Bearer account-a');
    return new Response('[]');
  });
  await h.api.fetchWithAuth('http://localhost/test');
  assert.equal(h.context.localStorage.getItem('baleen_auth_token'), null);
  assert.equal(h.context.sessionStorage.getItem('baleen_auth_token'), null);
});

test('logout revokes the current signed-session token, not stale memory', async () => {
  const h = harness();
  h.api.setAuthToken('previous-account');
  h.setNetwork(async (url, init) => {
    assert.ok(url.endsWith('/api/auth/logout'));
    assert.equal(init.headers.Authorization, 'Bearer account-a');
    return new Response('{}');
  });
  await h.api.logoutBackend();
  assert.equal(h.api.getAuthToken(), null);
});

test('failed revocation is reported instead of silently claiming logout', async () => {
  const h = harness();
  h.api.setAuthToken('account-a');
  h.setNetwork(async () => new Response(null, { status: 503 }));
  await assert.rejects(h.api.logoutBackend(), /Sign out could not be completed/);
  assert.equal(h.api.getAuthToken(), 'account-a');
});

test('logout removes authority even if in-memory bearer still exists', async () => {
  const h = harness();
  h.api.setAuthToken('old-account');
  h.setSession(null);
  h.setNetwork(async (_, init) => {
    assert.equal(init.headers.has('Authorization'), false);
    return new Response(null, { status: 401 });
  });
  await h.api.fetchWithAuth('http://localhost/test');
  assert.equal(h.api.getAuthToken(), null);
  assert.deepEqual(h.events, ['baleen:session-expired']);
});

test('successful empty executions replace cached rows', async () => {
  const h = harness();
  h.setNetwork(async () => new Response(JSON.stringify([{ id: 'trade-a', side: 'BUY', status: 'FILLED' }])));
  assert.equal((await h.api.fetchExecutionLogs('user-a')).length, 1);
  h.setNetwork(async () => new Response('[]'));
  assert.equal((await h.api.fetchExecutionLogs('user-a')).length, 0);
  assert.equal(h.api.getCachedExecutionLogs('user-a').length, 0);
});

test('account switch clears caches and discards a late previous-account response', async () => {
  const h = harness();
  let complete;
  let started;
  const began = new Promise(resolve => { started = resolve; });
  h.setNetwork(() => new Promise(resolve => { complete = resolve; started(); }));
  const pending = h.api.fetchWithAuth('http://localhost/previous-account');
  await began;
  h.setSession({ user: { accessToken: 'account-b' } });
  h.setNetwork(async () => new Response('[]'));
  await h.api.fetchWithAuth('http://localhost/current-account');
  complete(new Response('private previous-account data'));
  assert.equal((await pending).status, 409);
  assert.equal(h.api.getAuthToken(), 'account-b');
});
