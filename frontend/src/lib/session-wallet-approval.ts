/** Fixed-purpose owner approval. Invoke only from an explicit user button click. */
export interface WalletProvider {
  request(args: { method: string; params?: unknown[] }): Promise<unknown>;
}

export interface SessionOperation {
  id: string;
  kind: 'AUTHORIZE' | 'REVOKE';
  state: string;
  ownerAddress: string;
  walletAddress: string;
  sessionAddress: string;
  deadline: number;
  validUntil: number | null;
  scopes: string[];
  transactionId: string | null;
  transactionHash: string | null;
  liveExecutionReady: false;
  typedData: {
    domain: { name: string; version: string; chainId: number; verifyingContract: string };
    types: Record<string, { name: string; type: string }[]>;
    primaryType: string;
    message: { wallet: string; nonce: string; deadline: string;
      calls: { target: string; value: string; data: string }[] };
  } | null;
}

const address = (value: unknown): value is string => typeof value === 'string' && /^0x[0-9a-f]{40}$/i.test(value);
const fields = (pairs: string[]) => pairs.map(pair => { const [name, type] = pair.split(':'); return { name, type }; });
const TYPES = {
  EIP712Domain: fields(['name:string', 'version:string', 'chainId:uint256', 'verifyingContract:address']),
  Batch: fields(['wallet:address', 'nonce:uint256', 'deadline:uint256', 'calls:Call[]']),
  Call: fields(['target:address', 'value:uint256', 'data:bytes']),
};

export function validateSessionOperation(operation: SessionOperation, now = Math.floor(Date.now()/1000)): void {
  const typed = operation.typedData;
  if (operation.state !== 'PREPARED' || !typed || !address(operation.ownerAddress)
      || !address(operation.walletAddress) || !address(operation.sessionAddress)
      || !Number.isSafeInteger(operation.deadline) || operation.deadline <= now+30 || operation.deadline > now+300
      || typed.domain.name !== 'DepositWallet' || typed.domain.version !== '1' || typed.domain.chainId !== 137
      || typed.domain.verifyingContract.toLowerCase() !== operation.walletAddress.toLowerCase()
      || Object.keys(typed.domain).sort().join() !== 'chainId,name,verifyingContract,version'
      || typed.primaryType !== 'Batch' || typed.message.wallet.toLowerCase() !== operation.walletAddress.toLowerCase()
      || typed.message.deadline !== String(operation.deadline) || !/^\d+$/.test(typed.message.nonce)
      || BigInt(typed.message.nonce) >= BigInt('0x1'+'0'.repeat(64)) || typed.message.calls.length !== 1
      || Object.keys(typed.message).sort().join() !== 'calls,deadline,nonce,wallet'
      || Object.keys(typed.types).sort().join() !== 'Batch,Call,EIP712Domain') {
    throw new Error('Wallet approval request is expired or does not match this session.');
  }
  for (const name of Object.keys(TYPES) as (keyof typeof TYPES)[]) {
    if (JSON.stringify(typed.types[name]) !== JSON.stringify(TYPES[name])) throw new Error('Unexpected wallet approval types.');
  }
  const call = typed.message.calls[0];
  let data: string;
  if (operation.kind === 'AUTHORIZE') {
    if (JSON.stringify(operation.scopes) !== '["CLOB"]' || operation.validUntil === null
        || !Number.isSafeInteger(operation.validUntil) || operation.validUntil < now+4315*3600-300
        || operation.validUntil > now+4315*3600+10) throw new Error('Unexpected session scope or expiry.');
    data = '0x24017fae' + operation.sessionAddress.slice(2).toLowerCase().padStart(64, '0')
      + BigInt(operation.validUntil).toString(16).padStart(64, '0');
  } else if (operation.kind === 'REVOKE' && operation.validUntil === null && operation.scopes.length === 0) {
    data = '0xe63f952f' + operation.sessionAddress.slice(2).toLowerCase().padStart(64, '0');
  } else {
    throw new Error('Unsupported wallet approval operation.');
  }
  if (call.target.toLowerCase() !== operation.walletAddress.toLowerCase() || call.value !== '0'
      || call.data.toLowerCase() !== data || Object.keys(call).sort().join() !== 'data,target,value') {
    throw new Error('Wallet approval must contain only the displayed session operation.');
  }
}

export async function signSessionOperation(operation: SessionOperation, provider: WalletProvider): Promise<string> {
  validateSessionOperation(operation);
  if (await provider.request({ method:'eth_chainId' }) !== '0x89') throw new Error('Select Polygon in your owner wallet first.');
  const accounts = await provider.request({ method:'eth_requestAccounts' });
  if (!Array.isArray(accounts) || !accounts.some(a => address(a) && a.toLowerCase() === operation.ownerAddress.toLowerCase())) {
    throw new Error('Connect the Deposit Wallet owner shown in this request.');
  }
  validateSessionOperation(operation); // The wallet picker may remain open past the deadline.
  const signature = await provider.request({ method:'eth_signTypedData_v4',
    params:[operation.ownerAddress, JSON.stringify(operation.typedData)] });
  if (typeof signature !== 'string' || !/^0x[0-9a-f]{130}$/i.test(signature)) throw new Error('Wallet did not return a supported owner signature.');
  return signature;
}
