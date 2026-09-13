const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

// Render the actual component into a minimal element tree, then exercise its
// submit handler. Only framework and HTTP boundaries are stubbed.
async function submit(signupResult, loginResult, throws = false) {
  const state = [{ email: 'fixture@example.test', password: 'test-password', confirm: 'test-password', balance: '10000' }, '', false];
  const navigations = [];
  let cursor = 0;
  let logins = 0;
  const element = (type, props) => ({ type, props });
  const context = { exports: {}, console, require: name => {
    if (name === 'react') return { useState: () => {
      const index = cursor++;
      return [state[index], value => { state[index] = value; }];
    } };
    if (name === 'react/jsx-runtime') return { jsx: element, jsxs: element };
    if (name === 'next/navigation') return { useRouter: () => ({ push: url => navigations.push(url), refresh() {} }) };
    if (name === 'next-auth/react') return { signIn: async () => { logins++; return loginResult; } };
    if (name === '@/lib/api-client') return { signUp: async () => { if (throws) throw Error('network'); return signupResult; } };
    if (name === '@/context/ThemeContext') return { useTheme: () => ({ theme: 'light', toggleTheme() {} }) };
    return {};
  } };
  const source = fs.readFileSync(path.join(__dirname, '../src/app/auth/signup/page.tsx'), 'utf8');
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022,
  } }).outputText, context);
  const tree = context.exports.default();
  function findForm(node) {
    if (!node || typeof node !== 'object') return;
    if (node.type === 'form') return node;
    for (const child of [node.props?.children].flat(Infinity)) {
      const match = findForm(child);
      if (match) return match;
    }
  }
  await findForm(tree).props.onSubmit({ preventDefault() {} });
  return { state, navigations, logins };
}

test('failed signup stays on form and does not try login', async () => {
  const r = await submit(null, { ok: true });
  assert.equal(r.logins, 0);
  assert.deepEqual(r.navigations, []);
  assert.match(r.state[1], /Could not create/);
  assert.equal(r.state[2], false);
});
test('failed post-signup login shows an error without dashboard navigation', async () => {
  const r = await submit({ id: 'fixture' }, { ok: false });
  assert.deepEqual(r.navigations, []);
  assert.match(r.state[1], /sign in failed/);
  assert.equal(r.state[2], false);
});
test('successful signup and login navigate to dashboard', async () => {
  const r = await submit({ id: 'fixture' }, { ok: true });
  assert.deepEqual(r.navigations, ['/dashboard']);
  assert.equal(r.state[1], '');
});
test('network failure stays on form and releases loading state', async () => {
  const r = await submit(null, null, true);
  assert.deepEqual(r.navigations, []);
  assert.match(r.state[1], /Could not complete signup/);
  assert.equal(r.state[2], false);
});
