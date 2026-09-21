"""V2 collateral/share/fee evidence from canonical Polygon transaction receipts.

Contract reference: Polymarket/ctf-exchange-v2 Trading.sol and Events.sol.
No fee schedule, API fee-rate estimate, or whole-transaction cash heuristic.
"""
from decimal import Decimal
from datetime import datetime, timezone
import re
from eth_abi import decode
from eth_utils import keccak
from app.services.scoped_signer import EXCHANGES

TOPIC = '0x' + keccak(text='OrderFilled(bytes32,address,address,uint8,uint256,uint256,uint256,uint256,bytes32,bytes32)').hex()
V1_TOPIC = '0x' + keccak(text='OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)').hex()
V1_EXCHANGES = {'0x4bfb41d5b3570defd03c39a9a4d8de6bd8b8982e', '0xc5d563a36ae78145c45a50134d48a1215220f80a'}
UNIT = Decimal(1000000)


class SettlementEvidenceError(ValueError):
    pass


class SettlementPending(SettlementEvidenceError):
    """Known transaction is still awaiting finality; retain reservations and retry reads."""


def hex_number(value):
    if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-fA-F]+', value):
        raise SettlementEvidenceError('Invalid chain integer')
    return int(value, 16)


def receipt_order_fill(receipt, order, wallet):
    if not isinstance(receipt.get('logs'), list):
        raise SettlementEvidenceError('Receipt logs unavailable')
    quantity = cash = fee = Decimal(0)
    seen = set()
    for log in receipt['logs']:
        topics = log.get('topics', [])
        if (str(log.get('address', '')).lower() not in EXCHANGES or not topics
                or str(topics[0]).lower() != TOPIC):
            continue
        if len(topics) != 4:
            raise SettlementEvidenceError('Invalid V2 fill topics')
        if str(topics[1]).lower() != order.signed_order_hash.lower():
            continue
        maker = str(topics[2]).lower()
        if maker != '0x' + '0' * 24 + wallet.lower().removeprefix('0x'):
            raise SettlementEvidenceError('Receipt order wallet mismatch')
        index = hex_number(log.get('logIndex'))
        if index in seen or log.get('removed') is True:
            raise SettlementEvidenceError('Repeated or removed settlement log')
        seen.add(index)
        try:
            data = bytes.fromhex(log['data'].removeprefix('0x'))
            if len(data) != 7 * 32:
                raise ValueError('Invalid event length')
            side, token, making, taking, charge, _, _ = decode(
                ['uint8', 'uint256', 'uint256', 'uint256', 'uint256', 'bytes32', 'bytes32'], data)
        except Exception as exc:
            raise SettlementEvidenceError('Malformed V2 settlement event') from exc
        if side not in (0, 1) or ('BUY' if side == 0 else 'SELL') != order.side or str(token) != order.token_id:
            raise SettlementEvidenceError('Receipt token or side mismatch')
        shares, collateral = (taking, making) if side == 0 else (making, taking)
        if shares <= 0 or collateral <= 0 or collateral > shares:
            raise SettlementEvidenceError('Invalid settled amounts')
        quantity += Decimal(shares) / UNIT
        cash += Decimal(collateral) / UNIT
        fee += Decimal(charge) / UNIT
    if not seen:
        raise SettlementEvidenceError('Signed order absent from settlement receipt')
    return {'quantity': quantity, 'cash_amount': cash, 'price': cash / quantity, 'fee': fee}


class PolygonSettlementReader:
    def __init__(self, client, *, confirmations=128):
        if not isinstance(confirmations, int) or confirmations < 128:
            raise ValueError('Settlement requires at least 128 confirmations')
        self.client, self.confirmations = client, confirmations

    async def rpc(self, method, params):
        response = await self.client.post('', json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or data.get('error') or data.get('id') != 1 or data.get('result') is None:
            raise SettlementEvidenceError('Chain evidence unavailable')
        return data['result']

    async def receipt(self, transaction_hash):
        if not isinstance(transaction_hash, str) or not re.fullmatch(r'0x[0-9a-fA-F]{64}', transaction_hash):
            raise SettlementEvidenceError('Trade settlement transaction missing')
        if hex_number(await self.rpc('eth_chainId', [])) != 137:
            raise SettlementEvidenceError('Settlement chain mismatch')
        receipt = await self.rpc('eth_getTransactionReceipt', [transaction_hash])
        if (not isinstance(receipt, dict) or str(receipt.get('transactionHash', '')).lower() != transaction_hash.lower()
                or hex_number(receipt.get('status')) != 1):
            raise SettlementEvidenceError('Settlement failed or receipt identity mismatch')
        height = hex_number(receipt.get('blockNumber'))
        head = hex_number(await self.rpc('eth_blockNumber', []))
        if head - height < self.confirmations:
            raise SettlementPending('Settlement is not sufficiently confirmed')
        block = await self.rpc('eth_getBlockByNumber', [hex(height), False])
        if (not isinstance(block, dict) or hex_number(block.get('number')) != height
                or not re.fullmatch(r'0x[0-9a-fA-F]{64}', str(receipt.get('blockHash', '')))
                or block.get('hash') != receipt['blockHash']):
            raise SettlementEvidenceError('Settlement block is not canonical')
        return receipt, block

    async def source(self, source):
        """Verify the exact listener log and derive amounts without database floats."""
        receipt, block = await self.receipt(source.tx_hash)
        if (source.block_number != hex_number(receipt['blockNumber'])
                or source.block_hash.lower() != receipt['blockHash'].lower()
                or source.block_time.replace(tzinfo=timezone.utc).timestamp() != hex_number(block.get('timestamp'))):
            raise SettlementEvidenceError('Source block identity mismatch')
        logs = [log for log in receipt.get('logs', []) if hex_number(log.get('logIndex')) == source.log_index]
        if len(logs) != 1:
            raise SettlementEvidenceError('Source log missing or repeated')
        log = logs[0]
        topics = log.get('topics', [])
        contract = str(source.emitting_contract or '').lower()
        expected_topic = V1_TOPIC if contract in V1_EXCHANGES else TOPIC
        if (str(log.get('address', '')).lower() != source.emitting_contract.lower()
                or (contract not in EXCHANGES and contract not in V1_EXCHANGES) or len(topics) != 4
                or any(not re.fullmatch(r'0x[0-9a-fA-F]{64}', str(t)) for t in topics)
                or topics[0].lower() != expected_topic or log.get('removed') is True):
            raise SettlementEvidenceError('Source exchange log mismatch')
        wallet_topic = '0x' + '0'*24 + source.source_wallet_address.lower().removeprefix('0x')
        maker, taker = topics[2].lower() == wallet_topic, topics[3].lower() == wallet_topic
        if not maker or taker:
            # Both V1/V2 emit an owned OrderFilled for the taker's signed order.
            # A counterparty topic is not another independent source execution.
            raise SettlementEvidenceError('Source must own this signed order')
        try:
            raw = bytes.fromhex(log['data'].removeprefix('0x'))
            if contract in V1_EXCHANGES:
                if len(raw) != 5*32: raise ValueError('Invalid V1 event length')
                maker_asset, taker_asset, making, taking, _ = decode(['uint256']*5, raw)
                if (maker_asset == 0) == (taker_asset == 0): raise ValueError('Expected one collateral asset')
                side, token = (0, taker_asset) if maker_asset == 0 else (1, maker_asset)
            else:
                if len(raw) != 7*32: raise ValueError('Invalid V2 event length')
                side, token, making, taking, _, _, _ = decode(
                    ['uint8','uint256','uint256','uint256','uint256','bytes32','bytes32'], raw)
        except Exception as exc:
            raise SettlementEvidenceError('Malformed source fill') from exc
        if side not in (0, 1):
            raise SettlementEvidenceError('Invalid source side')
        expected_side = 'BUY' if maker == (side == 0) else 'SELL'
        quantity, cash = (taking, making) if side == 0 else (making, taking)
        if source.side != expected_side or source.token_id != str(token) or not 0 < cash <= quantity:
            raise SettlementEvidenceError('Source trade identity mismatch')
        quantity, cash = Decimal(quantity)/UNIT, Decimal(cash)/UNIT
        # Legacy canonical rows use binary floats. Match their exact float
        # projection, then use receipt Decimals for sizing and risk decisions.
        if float(quantity) != source.shares or float(cash/quantity) != source.price:
            raise SettlementEvidenceError('Stored source amounts differ from receipt')
        return {'quantity':quantity, 'price':cash/quantity, 'cash_amount':cash}

    async def fill(self, transaction_hash, order, wallet):
        receipt, _ = await self.receipt(transaction_hash)
        result = receipt_order_fill(receipt, order, wallet)
        result['trade_id'] = 'polygon:' + transaction_hash.lower() + ':' + order.signed_order_hash.lower()
        return result
