from unittest.mock import AsyncMock
from eth_utils import keccak
import pytest
from app.services.live_market_evidence import LiveMarketEvidence, STANDARD
from app.services.live_risk import RiskRejected


@pytest.mark.asyncio
@pytest.mark.parametrize('cap', [0, 100, 9999, 10000])
async def test_contract_fee_getter_and_zero_means_unlimited(cap):
    rpc = AsyncMock()
    rpc.rpc.side_effect = ['0x89', hex(cap)]
    evidence = LiveMarketEvidence(None, rpc)
    evidence._get = AsyncMock(side_effect=[{'condition_id':'condition','neg_risk':False,
        'tokens':[{'token_id':'111'}], 'accepting_orders':True}, {'asset_id':'111'}])
    if cap in (0, 10000):
        with pytest.raises(RiskRejected, match='unlimited'):
            await evidence.market('condition', '111')
    else:
        assert (await evidence.market('condition', '111'))['fee_cap_bps'] == cap
    rpc.rpc.assert_awaited_with('eth_call', [{'to':STANDARD,
        'data':'0x'+keccak(text='getMaxFeeRate()')[:4].hex()}, 'latest'])
