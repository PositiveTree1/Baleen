"""Confirmed CTF payout read for paper inventory, not a redemption transaction."""
import json
import re
from decimal import Decimal
from app.services.live_wallet_snapshot import LiveWalletSnapshot, CTF
from app.services.settlement_receipts import hex_number


async def resolution_evidence(receipts, condition, token, market, *, delivered_height):
    if (not isinstance(market, dict) or market.get('conditionId', '').lower() != condition.lower()
            or market.get('closed') is not True or market.get('umaResolutionStatus') != 'resolved'):
        return None
    if not re.fullmatch(r'0x[0-9a-fA-F]{64}', condition): raise ValueError('Invalid resolution condition')
    tokens = market['clobTokenIds']
    if isinstance(tokens, str): tokens = json.loads(tokens)
    if len(tokens) != 2 or len(set(tokens)) != 2 or token not in tokens:
        raise ValueError('Unsupported outcome mapping')
    if hex_number(await receipts.rpc('eth_chainId', [])) != 137: raise ValueError('Resolution chain mismatch')
    height = min(hex_number(await receipts.rpc('eth_blockNumber', []))-128, delivered_height)
    if height < 0: raise ValueError('Confirmed resolution block unavailable')
    block = await receipts.rpc('eth_getBlockByNumber', [hex(height), False])
    if not isinstance(block, dict) or hex_number(block['number']) != height or not re.fullmatch(r'0x[0-9a-fA-F]{64}', block['hash']):
        raise ValueError('Resolution block unavailable')
    reader = LiveWalletSnapshot(receipts)
    cid = bytes.fromhex(condition[2:])
    slots = await reader._call_uint(CTF, 'getOutcomeSlotCount(bytes32)', ['bytes32'], [cid], hex(height))
    denominator = await reader._call_uint(CTF, 'payoutDenominator(bytes32)', ['bytes32'], [cid], hex(height))
    if denominator == 0: return None
    if slots != 2: raise ValueError('Unsupported non-binary settlement')
    payouts = [await reader._call_uint(CTF, 'payoutNumerators(bytes32,uint256)', ['bytes32', 'uint256'], [cid, i], hex(height)) for i in range(2)]
    if sum(payouts) != denominator: raise ValueError('Resolution payouts do not reconcile')
    # Verify the pinned height did not change during the multiple reads.
    if (await receipts.rpc('eth_getBlockByNumber', [hex(height), False]))['hash'] != block['hash']:
        raise ValueError('Resolution block changed during observation')
    return {'condition': condition, 'token_id': token, 'payout': str(Decimal(payouts[tokens.index(token)])/denominator),
            'block_number': height, 'block_hash': block['hash'], 'block_time': hex_number(block['timestamp']),
            'token_mapping': tokens, 'mapping_source': 'gamma_market', 'payout_source': 'confirmed_ctf_contract'}
