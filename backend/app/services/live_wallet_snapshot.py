"""Complete wallet token discovery and exact confirmed balances for onboarding.

Uses the configured archive RPC's standard eth_getLogs completeness contract.
Unsupported/truncated/malformed responses fail closed; no data API value is
substituted for an on-chain balance. Contract addresses reviewed 2026-09-13.
"""
from datetime import datetime
from decimal import Decimal
import re
from eth_abi import decode, encode
from eth_utils import keccak
from app.services.settlement_receipts import hex_number, SettlementEvidenceError, SettlementPending

COLLATERAL = '0xc011a7e12a19f7b1f670d46f03b03f3342e82dfb'
CTF = '0x4d97dcd97ec945f40cf65f87097ace5ea0476045'
POSITION_MANAGER = '0x006f54f7f9a22e0000cc2ab60031000000ae9fef'
TOKEN_CONTRACTS = (CTF, POSITION_MANAGER)
SINGLE = '0x'+keccak(text='TransferSingle(address,address,address,uint256,uint256)').hex()
BATCH = '0x'+keccak(text='TransferBatch(address,address,address,uint256[],uint256[])').hex()


class LiveWalletSnapshot:
    def __init__(self, rpc):
        self.rpc = rpc

    async def _logs(self, query, start, end):
        result = await self.rpc.rpc('eth_getLogs', [{**query, 'fromBlock':hex(start), 'toBlock':hex(end)}])
        if not isinstance(result, list):
            raise SettlementEvidenceError('Wallet transfer coverage unavailable')
        # Split full pages instead of accepting a commonly truncated response.
        if len(result) >= 1000:
            if start == end:
                raise SettlementEvidenceError('Single-block wallet log coverage exceeds safe limit')
            midpoint = (start+end)//2
            return await self._logs(query, start, midpoint) + await self._logs(query, midpoint+1, end)
        return result

    async def _call_uint(self, contract, signature, types, args, block):
        payload = '0x'+(keccak(text=signature)[:4]+encode(types, args)).hex()
        result = await self.rpc.rpc('eth_call', [{'to':contract, 'data':payload}, block])
        if not isinstance(result, str) or not re.fullmatch(r'0x[0-9a-fA-F]{64}', result):
            raise SettlementEvidenceError('Invalid wallet balance response')
        return int(result, 16)

    async def read(self, wallet):
        if not re.fullmatch(r'0x[0-9a-fA-F]{40}', wallet):
            raise SettlementEvidenceError('Invalid wallet address')
        if hex_number(await self.rpc.rpc('eth_chainId', [])) != 137:
            raise SettlementEvidenceError('Wallet snapshot chain mismatch')
        head = hex_number(await self.rpc.rpc('eth_blockNumber', []))
        height = head-128
        if height < 0:
            raise SettlementEvidenceError('Confirmed wallet block unavailable')
        block = await self.rpc.rpc('eth_getBlockByNumber', [hex(height), False])
        if (not isinstance(block, dict) or hex_number(block.get('number')) != height
                or not re.fullmatch(r'0x[0-9a-fA-F]{64}', str(block.get('hash')))):
            raise SettlementEvidenceError('Wallet snapshot block unavailable')
        wallet_topic = '0x'+'0'*24+wallet.lower()[2:]
        # Scan from genesis: counterfactual addresses can receive tokens before
        # wallet deployment. Use both directions and both ERC-1155 event types.
        universe, identities = set(), {}
        for topics in ([ [SINGLE,BATCH], None, wallet_topic ], [[SINGLE,BATCH], None, None, wallet_topic]):
            logs = await self._logs({'address':list(TOKEN_CONTRACTS), 'topics':topics}, 0, head)
            query_seen = set()
            for log in logs:
                ts = log.get('topics', [])
                contract = str(log.get('address', '')).lower()
                if (contract not in TOKEN_CONTRACTS or len(ts) != 4 or ts[0] not in (SINGLE,BATCH)
                        or any(not re.fullmatch(r'0x[0-9a-fA-F]{64}', str(t)) for t in ts)
                        or wallet_topic not in (str(ts[2]).lower(), str(ts[3]).lower()) or log.get('removed') is True
                        or not re.fullmatch(r'0x[0-9a-fA-F]{64}', str(log.get('transactionHash', '')))
                        or not re.fullmatch(r'0x[0-9a-fA-F]{64}', str(log.get('blockHash', '')))
                        or not 0 <= hex_number(log.get('blockNumber')) <= head):
                    raise SettlementEvidenceError('Wallet log identity mismatch')
                identity = (log['transactionHash'].lower(), hex_number(log.get('logIndex')))
                if identity in query_seen:
                    raise SettlementEvidenceError('Wallet query repeated a transfer log')
                query_seen.add(identity)
                if identity in identities:
                    if identities[identity] != log:
                        raise SettlementEvidenceError('Conflicting wallet transfer log')
                    continue  # A self-transfer appears in both direction queries.
                identities[identity] = log
                try:
                    data = bytes.fromhex(log['data'].removeprefix('0x'))
                    if ts[0] == SINGLE:
                        if len(data) != 64:
                            raise ValueError('Malformed single transfer')
                        token, _ = decode(['uint256','uint256'], data)
                        ids = [token]
                    else:
                        ids, amounts = decode(['uint256[]','uint256[]'], data)
                        if len(ids) != len(amounts) or encode(['uint256[]','uint256[]'], [ids,amounts]) != data:
                            raise ValueError('Malformed batch transfer')
                except Exception as exc:
                    raise SettlementEvidenceError('Malformed wallet transfer amounts') from exc
                universe.update((contract, str(token)) for token in ids)
        code = await self.rpc.rpc('eth_getCode', [wallet, hex(height)])
        if not isinstance(code, str) or not re.fullmatch(r'0x[0-9a-fA-F]+', code) or code == '0x0':
            raise SettlementEvidenceError('Confirmed Deposit Wallet deployment unavailable')
        if await self._call_uint(COLLATERAL, 'decimals()', [], [], hex(height)) != 6:
            raise SettlementEvidenceError('Unexpected collateral precision')
        cash = await self._call_uint(COLLATERAL, 'balanceOf(address)', ['address'], [wallet], hex(height))
        latest_cash = await self._call_uint(COLLATERAL, 'balanceOf(address)', ['address'], [wallet], 'latest')
        if cash != latest_cash:
            raise SettlementPending('Recent wallet funding or spending is not yet confirmed')
        balances = {}
        for contract, token in sorted(universe):
            qty = await self._call_uint(contract, 'balanceOf(address,uint256)', ['address','uint256'], [wallet,int(token)], hex(height))
            latest = await self._call_uint(contract, 'balanceOf(address,uint256)', ['address','uint256'], [wallet,int(token)], 'latest')
            if qty != latest:
                raise SettlementPending('Recent wallet inventory changes are not yet confirmed')
            balances[contract+':'+token] = str(Decimal(qty)/1000000)
        canonical = await self.rpc.rpc('eth_getBlockByNumber', [hex(height), False])
        if not isinstance(canonical, dict) or canonical.get('hash') != block['hash']:
            raise SettlementEvidenceError('Wallet snapshot block changed')
        return {'block_number':height, 'block_hash':block['hash'],
            'block_time':datetime.utcfromtimestamp(hex_number(block.get('timestamp'))),
            'cash':Decimal(cash)/1000000, 'balances':balances}
