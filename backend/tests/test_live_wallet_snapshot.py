from decimal import Decimal
from unittest.mock import AsyncMock
import pytest
from eth_abi import encode, decode
from eth_utils import keccak
from app.services.live_wallet_snapshot import LiveWalletSnapshot, COLLATERAL, CTF, SINGLE
from app.services.settlement_receipts import SettlementEvidenceError

WALLET, HASH = '0x'+'1'*40, '0x'+'a'*64


def fixture(fault=None):
    log = {'address':CTF, 'topics':[SINGLE,'0x'+'0'*64,'0x'+'0'*64,'0x'+'0'*24+WALLET[2:]],
        'data':'0x'+encode(['uint256','uint256'], [111, 20000000]).hex(),
        'blockNumber':'0x1', 'blockHash':HASH, 'transactionHash':HASH, 'logIndex':'0x0'}
    blocks = 0
    async def call(method, params):
        nonlocal blocks
        if method == 'eth_chainId': return '0x1' if fault == 'chain' else '0x89'
        if method == 'eth_blockNumber': return hex(300)
        if method == 'eth_getBlockByNumber':
            blocks += 1
            return {'number':hex(172), 'hash':'0x'+'b'*64 if fault == 'reorg' and blocks > 1 else HASH, 'timestamp':hex(1000)}
        if method == 'eth_getLogs':
            assert params[0]['fromBlock'] == '0x0'  # Includes prefunded, undeployed wallet addresses.
            if fault == 'logs': return {'unexpected':'shape'}
            if len(params[0]['topics']) == 3: return []
            if fault == 'contract': log['address'] = WALLET
            if fault == 'malformed': log['data'] = '0x00'
            return [log]
        if method == 'eth_getCode': return '0x' if fault == 'undeployed' else '0x6000'
        if method == 'eth_call':
            if params[0]['data'] == '0x'+keccak(text='decimals()')[:4].hex():
                value = 18 if fault == 'decimals' else 6
            elif params[0]['to'] == COLLATERAL:
                value = 137654321 + (1 if fault == 'unconfirmed_cash' and params[1] == 'latest' else 0)
            else:
                value = 0 if fault != 'unconfirmed_token' or params[1] != 'latest' else 1
            return hex(value) if fault == 'short_balance' else '0x'+encode(['uint256'], [value]).hex()
        raise AssertionError(method)
    rpc = AsyncMock()
    rpc.rpc.side_effect = call
    return LiveWalletSnapshot(rpc)


@pytest.mark.asyncio
async def test_exact_funding_and_all_historical_token_balances_are_observed():
    result = await fixture().read(WALLET)
    assert result['cash'] == Decimal('137.654321')
    assert result['balances'] == {CTF+':111':'0'}
    assert result['block_number'] == 172 and result['block_hash'] == HASH


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['chain','reorg','logs','contract','malformed','undeployed','decimals',
                                  'unconfirmed_cash','unconfirmed_token','short_balance'])
async def test_incomplete_or_conflicting_wallet_evidence_cannot_initialize(fault):
    with pytest.raises(SettlementEvidenceError):
        await fixture(fault).read(WALLET)


@pytest.mark.asyncio
async def test_full_rpc_log_page_is_split_not_treated_as_complete():
    rpc = AsyncMock()
    rpc.rpc.side_effect = [[{}]*1000, [{'block':'left'}], [{'block':'right'}]]
    reader = LiveWalletSnapshot(rpc)
    assert await reader._logs({}, 0, 3) == [{'block':'left'}, {'block':'right'}]
    assert rpc.rpc.call_args_list[1].args[1][0]['toBlock'] == '0x1'
    assert rpc.rpc.call_args_list[2].args[1][0]['fromBlock'] == '0x2'
