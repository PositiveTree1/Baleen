import copy
from decimal import Decimal
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from eth_abi import encode
from app.services.settlement_receipts import PolygonSettlementReader, SettlementEvidenceError, TOPIC, V1_TOPIC, V1_EXCHANGES

TX, BLOCK, ORDER = '0x'+'a'*64, '0x'+'b'*64, '0x'+'c'*64
WALLET = '0x'+'1'*40
EXCHANGE = '0xe111180000d2663c0091e4f400237545b87b996b'


@pytest.mark.asyncio
@pytest.mark.parametrize('side', ['BUY', 'SELL'])
async def test_legacy_source_exchange_receipt_matches_listener(side):
    receipt = fixture_receipt()
    contract = sorted(V1_EXCHANGES)[0]
    receipt['logs'][0]['address'] = contract
    receipt['logs'][0]['topics'][0] = V1_TOPIC
    values = [0, 111, 10000000, 20000000, 0] if side == 'BUY' else [111, 0, 20000000, 10000000, 0]
    receipt['logs'][0]['data'] = '0x'+encode(['uint256']*5, values).hex()
    source = SimpleNamespace(tx_hash=TX, block_number=100, block_hash=BLOCK, block_time=datetime.utcfromtimestamp(1000),
        log_index=0, emitting_contract=contract, source_wallet_address=WALLET, side=side, token_id='111', shares=20., price=.5)
    reader = PolygonSettlementReader(None)
    reader.receipt = AsyncMock(return_value=(receipt, {'timestamp':hex(1000)}))
    assert (await reader.source(source))['quantity'] == 20
    receipt['logs'][0]['topics'][0] = TOPIC
    with pytest.raises(SettlementEvidenceError): await reader.source(source)


def fixture_receipt(side=0, cash=10000000, qty=20000000, fee=250000):
    making, taking = (cash, qty) if side == 0 else (qty, cash)
    return {'transactionHash': TX, 'blockHash': BLOCK, 'blockNumber': '0x64', 'status': '0x1', 'logs': [{
        'address': EXCHANGE, 'topics': [TOPIC, ORDER, '0x'+'0'*24+WALLET[2:], '0x'+'0'*64],
        'logIndex': '0x0', 'data': '0x'+encode(['uint8','uint256','uint256','uint256','uint256','bytes32','bytes32'],
            [side, 111, making, taking, fee, bytes(32), bytes(32)]).hex()}]}


@pytest.mark.asyncio
@pytest.mark.parametrize('side', ['BUY', 'SELL'])
async def test_receipt_fee_is_exact_collateral_for_both_sides(side):
    receipt = fixture_receipt(0 if side == 'BUY' else 1)
    responses = {'eth_chainId': '0x89', 'eth_getTransactionReceipt': receipt,
                 'eth_blockNumber': '0x100', 'eth_getBlockByNumber': {'number': '0x64', 'hash': BLOCK}}
    import json
    def handler(request):
        body = json.loads(request.content)
        return httpx.Response(200, json={'jsonrpc': '2.0', 'id': 1, 'result': responses[body['method']]})
    async with httpx.AsyncClient(base_url='https://rpc.test', transport=httpx.MockTransport(handler)) as client:
        fill = await PolygonSettlementReader(client).fill(TX,
            SimpleNamespace(signed_order_hash=ORDER, token_id='111', side=side), WALLET)
    assert fill['quantity'] == 20 and fill['cash_amount'] == 10 and fill['fee'] == Decimal('.25')


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['chain', 'reorg', 'unconfirmed', 'failed', 'missing_order', 'duplicate', 'wrong_wallet', 'token'])
async def test_invalid_chain_evidence_never_returns_a_fill(fault):
    receipt = fixture_receipt()
    responses = {'eth_chainId': '0x89', 'eth_getTransactionReceipt': receipt,
                 'eth_blockNumber': '0x100', 'eth_getBlockByNumber': {'number':'0x64', 'hash':BLOCK}}
    if fault == 'chain': responses['eth_chainId'] = '0x1'
    if fault == 'reorg': responses['eth_getBlockByNumber']['hash'] = TX
    if fault == 'unconfirmed': responses['eth_blockNumber'] = '0x65'
    if fault == 'failed': receipt['status'] = '0x0'
    if fault == 'missing_order': receipt['logs'] = []
    if fault == 'duplicate': receipt['logs'].append(copy.deepcopy(receipt['logs'][0]))
    if fault == 'wrong_wallet': receipt['logs'][0]['topics'][2] = '0x'+'0'*64
    reader = PolygonSettlementReader(None)
    reader.rpc = AsyncMock(side_effect=lambda method, params: responses[method])
    with pytest.raises(SettlementEvidenceError):
        await reader.fill(TX, SimpleNamespace(signed_order_hash=ORDER, token_id='112' if fault == 'token' else '111', side='BUY'), WALLET)


@pytest.mark.asyncio
@pytest.mark.parametrize('maker', [True, False])
@pytest.mark.parametrize('fault', [None, 'quantity', 'price', 'side', 'block', 'time', 'log', 'wallet'])
async def test_source_receipt_proves_participant_and_exact_amounts(maker, fault):
    receipt = fixture_receipt()
    if not maker:
        receipt['logs'][0]['topics'][2], receipt['logs'][0]['topics'][3] = (
            receipt['logs'][0]['topics'][3], receipt['logs'][0]['topics'][2])
    source = SimpleNamespace(tx_hash=TX, block_number=100, block_hash=BLOCK, block_time=datetime.utcfromtimestamp(1000),
        log_index=0, emitting_contract=EXCHANGE, source_wallet_address=WALLET, side='BUY' if maker else 'SELL',
        token_id='111', shares=20., price=.5)
    if fault == 'quantity': source.shares = 21
    if fault == 'price': source.price = .6
    if fault == 'side': source.side = 'SELL' if maker else 'BUY'
    if fault == 'block': source.block_number = 101
    if fault == 'time': source.block_time = datetime.utcfromtimestamp(999)
    if fault == 'log': source.log_index = 1
    if fault == 'wallet': source.source_wallet_address = '0x'+'2'*40
    reader = PolygonSettlementReader(None)
    reader.receipt = AsyncMock(return_value=(receipt, {'timestamp':hex(1000)}))
    if fault or not maker:
        with pytest.raises(SettlementEvidenceError):
            await reader.source(source)
    else:
        proof = await reader.source(source)
        assert proof == {'quantity':Decimal(20), 'cash_amount':Decimal(10), 'price':Decimal('.5')}
