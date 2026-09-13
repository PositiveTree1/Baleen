const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require('typescript');
const source = fs.readFileSync(require('node:path').join(__dirname, '../src/lib/session-wallet-approval.ts'), 'utf8');
const exportsObject = {};
vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { target:ts.ScriptTarget.ES2020, module:ts.ModuleKind.CommonJS } }).outputText,
  { exports:exportsObject });
const { validateSessionOperation, signSessionOperation } = exportsObject;
const fields = pairs => pairs.map(p => { const [name,type] = p.split(':'); return {name,type}; });
function fixture() {
  const now = Math.floor(Date.now()/1000), wallet = '0x'+'1'.repeat(40), session = '0x'+'2'.repeat(40);
  return { id:'fixture', kind:'AUTHORIZE', state:'PREPARED', ownerAddress:'0x'+'3'.repeat(40),
    walletAddress:wallet, sessionAddress:session, deadline:now+240, validUntil:now+4315*3600, scopes:['CLOB'],
    typedData:{ domain:{name:'DepositWallet',version:'1',chainId:137,verifyingContract:wallet}, primaryType:'Batch',
      types:{ EIP712Domain:fields(['name:string','version:string','chainId:uint256','verifyingContract:address']),
        Batch:fields(['wallet:address','nonce:uint256','deadline:uint256','calls:Call[]']),
        Call:fields(['target:address','value:uint256','data:bytes']) },
      message:{ wallet, nonce:String(2n**200n), deadline:String(now+240), calls:[{target:wallet,value:'0',
        data:'0x24017fae'+session.slice(2).padStart(64,'0')+BigInt(now+4315*3600).toString(16).padStart(64,'0')}] } } };
}
(async () => {
  validateSessionOperation(fixture());
  for (const mutate of [o => o.typedData.message.calls[0].value='1', o => o.scopes=['ALL'],
    o => o.typedData.domain.chainId=1, o => o.typedData.message.calls.push(o.typedData.message.calls[0]),
    o => o.typedData.message.calls[0].data='0x', o => o.deadline=1,
    o => o.sessionAddress='0x'+'4'.repeat(40), o => o.typedData.types.Call[0].type='bytes32']) {
    const operation = fixture(); mutate(operation); assert.throws(() => validateSessionOperation(operation));
  }
  let requested = [];
  const operation = fixture();
  const provider = { request:async request => { requested.push(request.method);
    if(request.method==='eth_chainId') return '0x89';
    if(request.method==='eth_requestAccounts') return [operation.ownerAddress];
    assert.equal(request.params[0], operation.ownerAddress);
    assert.equal(JSON.parse(request.params[1]).message.nonce, String(2n**200n));
    return '0x'+'1'.repeat(130);
  } };
  assert.equal(await signSessionOperation(operation, provider), '0x'+'1'.repeat(130));
  assert.deepEqual(requested,['eth_chainId','eth_requestAccounts','eth_signTypedData_v4']);
  requested=[];
  await assert.rejects(signSessionOperation(fixture(), {request:async r => { requested.push(r.method); return '0x1'; }}));
  assert.deepEqual(requested,['eth_chainId']);
  console.log('11 wallet approval checks passed (mock provider; no real wallet signing).');
})().catch(error => { console.error(error); process.exitCode=1; });
