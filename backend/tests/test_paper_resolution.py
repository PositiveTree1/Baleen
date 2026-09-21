from unittest.mock import AsyncMock
import pytest
from app.services.paper_resolution import resolution_evidence
from app.research.proportional_replay import replay
from tests.test_independent_ledger_and_replay import leg


@pytest.mark.asyncio
@pytest.mark.parametrize('numerators,payout', [([1,0], '1'), ([0,1], '0'), ([1,1], '0.5')])
async def test_confirmed_payout_supports_wins_losses_and_void(numerators, payout, monkeypatch):
    cid = '0x'+'a'*64
    block = {'number': hex(100), 'hash': '0x'+'b'*64, 'timestamp': hex(1000)}
    reader = AsyncMock()
    reader.rpc.side_effect = lambda method, params: {'eth_chainId': '0x89', 'eth_blockNumber': hex(300),
                                                   'eth_getBlockByNumber': block}[method]
    call = AsyncMock(side_effect=[2, sum(numerators), *numerators])
    monkeypatch.setattr('app.services.paper_resolution.LiveWalletSnapshot._call_uint', call)
    result = await resolution_evidence(reader, cid, 'yes', {'conditionId': cid, 'closed': True,
        'umaResolutionStatus': 'resolved', 'clobTokenIds': ['yes','no']}, delivered_height=100)
    assert result['payout'] == payout and result['block_number'] == 100
    events = [leg('entry', 'BUY', 100, 1), {'id':'settlement', 'side':'REDEEM', 'timestamp':1001,
        'token_id':'yes', 'quantity':'10', 'resolution':result}]
    report = replay(events, starting_cash=100, ratio='.1', marks={})
    assert report['positions'] == {}
    assert report['events'][-1]['status'] == 'settled'
    assert float(report['cash']) == 95+10*float(payout)


@pytest.mark.asyncio
async def test_closed_market_without_final_resolution_is_not_settled():
    reader = AsyncMock()
    assert await resolution_evidence(reader, 'condition', 'yes', {'conditionId':'condition', 'closed':True}, delivered_height=100) is None
    reader.rpc.assert_not_called()
