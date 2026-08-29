"""
Baleen Synthetic Mock Market & Event Stream Factory.

Generates extreme order book topologies and deterministic synthetic event streams
to stress test execution engines, invariant monitors, and ingestion pipelines:
  - Order Book Topologies: Empty, Crossed/Inverted, Micro-liquidity ($0.01 depth),
    Whale Depth ($1M+ sweeps), Extreme Price Shocks (0.99 <-> 0.01), Zero/Ceiling Contracts ($0.00 / $1.00).
  - Event Streams: Out-of-order Envio HyperSync logs, Asynchronous block latency (1s-60s),
    WebSocket reconnection bursts, Duplicate transactions (idempotency), RPC failover/retries,
    Binary resolution payouts ($1.00 / $0.00), and Multi-Whale Consensus triggers.
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class OrderBookLevel:
    """Individual price level in an order book."""
    price: float
    size: float

    def to_dict(self) -> Dict[str, float]:
        return {"price": round(self.price, 4), "size": round(self.size, 4)}


@dataclass
class OrderBookSnapshot:
    """Complete snapshot of an order book."""
    condition_id: str
    outcome: str
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, List[Dict[str, float]]]:
        return {
            "bids": [level.to_dict() for level in self.bids],
            "asks": [level.to_dict() for level in self.asks],
        }

    @property
    def best_bid(self) -> Optional[float]:
        return max((b.price for b in self.bids), default=None)

    @property
    def best_ask(self) -> Optional[float]:
        return min((a.price for a in self.asks), default=None)

    @property
    def spread(self) -> Optional[float]:
        bb = self.best_bid
        ba = self.best_ask
        if bb is not None and ba is not None:
            return round(ba - bb, 4)
        return None

    @property
    def is_inverted(self) -> bool:
        bb = self.best_bid
        ba = self.best_ask
        return bb is not None and ba is not None and bb > ba


@dataclass
class SyntheticEvent:
    """Structured mock blockchain or WebSocket trade event."""
    event_id: str
    event_type: str  # TRADE_LOG, HYPERSYNC_FILL, WS_BURST, DUPLICATE_TX, RESOLUTION_PAYOUT, RPC_RETRY
    condition_id: str
    wallet_address: str
    side: str  # BUY or SELL
    price: float
    notional_usd: float
    shares: float
    tx_hash: str
    log_index: int
    block_number: int
    block_timestamp: float
    arrival_timestamp: float
    latency_seconds: float = 0.0
    is_duplicate: bool = False
    outcome: str = "Yes"
    market_question: str = "Synthetic Test Market Question"
    market_category: str = "Crypto"
    payload: Dict[str, Any] = field(default_factory=dict)


class MockMarketFactory:
    """Factory generating extreme and boundary-case order book snapshots."""

    @staticmethod
    def create_empty_book(
        condition_id: str = "cond_empty",
        outcome: str = "Yes",
    ) -> OrderBookSnapshot:
        """Completely empty order book (0 bids, 0 asks)."""
        return OrderBookSnapshot(condition_id=condition_id, outcome=outcome, bids=[], asks=[])

    @staticmethod
    def create_empty_bids_book(
        condition_id: str = "cond_empty_bids",
        outcome: str = "Yes",
        mid_price: float = 0.50,
        depth: int = 5,
    ) -> OrderBookSnapshot:
        """Order book with asks but zero bids."""
        asks = [
            OrderBookLevel(price=round(mid_price + (i * 0.02), 4), size=100.0 * (i + 1))
            for i in range(depth)
        ]
        return OrderBookSnapshot(condition_id=condition_id, outcome=outcome, bids=[], asks=asks)

    @staticmethod
    def create_empty_asks_book(
        condition_id: str = "cond_empty_asks",
        outcome: str = "Yes",
        mid_price: float = 0.50,
        depth: int = 5,
    ) -> OrderBookSnapshot:
        """Order book with bids but zero asks."""
        bids = [
            OrderBookLevel(price=round(max(0.01, mid_price - (i * 0.02)), 4), size=100.0 * (i + 1))
            for i in range(depth)
        ]
        return OrderBookSnapshot(condition_id=condition_id, outcome=outcome, bids=bids, asks=[])

    @staticmethod
    def create_inverted_book(
        condition_id: str = "cond_inverted",
        outcome: str = "Yes",
        best_bid: float = 0.65,
        best_ask: float = 0.55,
        depth: int = 5,
    ) -> OrderBookSnapshot:
        """Crossed / inverted order book where best bid exceeds best ask."""
        bids = [
            OrderBookLevel(price=round(best_bid - (i * 0.01), 4), size=50.0)
            for i in range(depth)
        ]
        asks = [
            OrderBookLevel(price=round(best_ask + (i * 0.01), 4), size=50.0)
            for i in range(depth)
        ]
        return OrderBookSnapshot(condition_id=condition_id, outcome=outcome, bids=bids, asks=asks)

    @staticmethod
    def create_zero_spread_book(
        condition_id: str = "cond_zero_spread",
        outcome: str = "Yes",
        price: float = 0.50,
        depth: int = 5,
    ) -> OrderBookSnapshot:
        """Zero spread book where top of book bid == ask."""
        bids = [
            OrderBookLevel(price=round(price - (i * 0.01), 4), size=100.0)
            for i in range(depth)
        ]
        asks = [
            OrderBookLevel(price=round(price + (i * 0.01), 4), size=100.0)
            for i in range(depth)
        ]
        return OrderBookSnapshot(condition_id=condition_id, outcome=outcome, bids=bids, asks=asks)

    @staticmethod
    def create_micro_liquidity_book(
        condition_id: str = "cond_micro_liq",
        outcome: str = "Yes",
        mid_price: float = 0.50,
        tick_size_usd: float = 0.01,
    ) -> OrderBookSnapshot:
        """Micro-liquidity book with $0.01 dust levels to test liquidity exhaustion."""
        bids = [
            OrderBookLevel(price=round(mid_price - 0.01, 4), size=tick_size_usd / mid_price),
            OrderBookLevel(price=round(mid_price - 0.05, 4), size=tick_size_usd / mid_price),
        ]
        asks = [
            OrderBookLevel(price=round(mid_price + 0.01, 4), size=tick_size_usd / mid_price),
            OrderBookLevel(price=round(mid_price + 0.05, 4), size=tick_size_usd / mid_price),
        ]
        return OrderBookSnapshot(condition_id=condition_id, outcome=outcome, bids=bids, asks=asks)

    @staticmethod
    def create_whale_depth_book(
        condition_id: str = "cond_whale_depth",
        outcome: str = "Yes",
        mid_price: float = 0.50,
        total_depth_usd: float = 1_000_000.0,
        levels: int = 20,
    ) -> OrderBookSnapshot:
        """Deep order book capable of absorbing massive whale orders without exhaustion."""
        usd_per_level = total_depth_usd / (levels * 2)
        bids = []
        asks = []
        for i in range(1, levels + 1):
            bid_p = round(max(0.01, mid_price - (i * 0.01)), 4)
            ask_p = round(min(0.99, mid_price + (i * 0.01)), 4)
            bids.append(OrderBookLevel(price=bid_p, size=usd_per_level / bid_p))
            asks.append(OrderBookLevel(price=ask_p, size=usd_per_level / ask_p))
        return OrderBookSnapshot(condition_id=condition_id, outcome=outcome, bids=bids, asks=asks)

    @staticmethod
    def create_price_shock_book(
        condition_id: str = "cond_shock",
        outcome: str = "Yes",
        from_price: float = 0.99,
        to_price: float = 0.01,
        shock_type: str = "crash",
    ) -> OrderBookSnapshot:
        """Flash crash (0.99 -> 0.01) or flash rally (0.01 -> 0.99) book."""
        target_p = to_price if shock_type == "crash" else from_price
        bids = [
            OrderBookLevel(price=round(max(0.001, target_p - 0.005), 4), size=5000.0),
            OrderBookLevel(price=round(max(0.001, target_p - 0.01), 4), size=10000.0),
        ]
        asks = [
            OrderBookLevel(price=round(min(0.999, target_p + 0.005), 4), size=5000.0),
            OrderBookLevel(price=round(min(0.999, target_p + 0.01), 4), size=10000.0),
        ]
        return OrderBookSnapshot(condition_id=condition_id, outcome=outcome, bids=bids, asks=asks)

    @staticmethod
    def create_zero_price_contract_book(
        condition_id: str = "cond_zero_price",
        outcome: str = "Yes",
    ) -> OrderBookSnapshot:
        """Near-zero boundary contract (p = 0.000 / 0.001) to test division by zero."""
        bids = [
            OrderBookLevel(price=0.000, size=1000.0),
            OrderBookLevel(price=0.001, size=2000.0),
        ]
        asks = [
            OrderBookLevel(price=0.001, size=2000.0),
            OrderBookLevel(price=0.002, size=5000.0),
        ]
        return OrderBookSnapshot(condition_id=condition_id, outcome=outcome, bids=bids, asks=asks)

    @staticmethod
    def create_ceiling_price_contract_book(
        condition_id: str = "cond_ceiling_price",
        outcome: str = "Yes",
    ) -> OrderBookSnapshot:
        """Ceiling boundary contract (p = 0.999 / 1.000)."""
        bids = [
            OrderBookLevel(price=0.998, size=5000.0),
            OrderBookLevel(price=0.999, size=10000.0),
        ]
        asks = [
            OrderBookLevel(price=0.999, size=10000.0),
            OrderBookLevel(price=1.000, size=20000.0),
        ]
        return OrderBookSnapshot(condition_id=condition_id, outcome=outcome, bids=bids, asks=asks)

    @staticmethod
    def create_normal_book(
        condition_id: str = "cond_normal",
        outcome: str = "Yes",
        mid_price: float = 0.50,
        spread: float = 0.02,
        depth: int = 10,
        total_liquidity_usd: float = 50000.0,
    ) -> OrderBookSnapshot:
        """Standard balanced two-sided market."""
        half_spread = spread / 2.0
        usd_per_side = total_liquidity_usd / 2.0
        usd_per_level = usd_per_side / depth

        bids = []
        asks = []
        for i in range(depth):
            bid_p = round(max(0.01, mid_price - half_spread - (i * 0.01)), 4)
            ask_p = round(min(0.99, mid_price + half_spread + (i * 0.01)), 4)
            bids.append(OrderBookLevel(price=bid_p, size=round(usd_per_level / bid_p, 2)))
            asks.append(OrderBookLevel(price=ask_p, size=round(usd_per_level / ask_p, 2)))

        return OrderBookSnapshot(condition_id=condition_id, outcome=outcome, bids=bids, asks=asks)

    @staticmethod
    def create_subpenny_dust_book(
        condition_id: str = "cond_subpenny",
        outcome: str = "Yes",
    ) -> OrderBookSnapshot:
        """Book with granular subpenny fractions and precision noise."""
        bids = [
            OrderBookLevel(price=0.48555, size=123.4567),
            OrderBookLevel(price=0.48123, size=89.1234),
        ]
        asks = [
            OrderBookLevel(price=0.51444, size=345.6789),
            OrderBookLevel(price=0.51888, size=456.7891),
        ]
        return OrderBookSnapshot(condition_id=condition_id, outcome=outcome, bids=bids, asks=asks)


class EventStreamGenerator:
    """Deterministic generator for synthetic edge-case event streams."""

    @staticmethod
    def generate_out_of_order_envio_stream(
        count: int = 20,
        condition_id: str = "cond_envio_ooo",
        wallet_address: str = "0xWhaleEnvio1",
        invert_ratio: float = 0.3,
        seed: int = 42,
    ) -> List[SyntheticEvent]:
        """Simulates HyperSync logs arriving out of chronological order (SELL arriving before BUY)."""
        rng = random.Random(seed)
        base_time = 1700000000.0
        events: List[SyntheticEvent] = []

        for i in range(count):
            side = "BUY" if i % 2 == 0 else "SELL"
            price = round(0.40 + (rng.random() * 0.20), 4)
            notional = round(100.0 + (rng.random() * 200.0), 2)
            shares = round(notional / price, 4)
            block_num = 50000000 + i
            block_ts = base_time + (i * 12.0)

            # Invert arrival timestamp for out-of-order delivery
            if rng.random() < invert_ratio and i > 0:
                arrival_ts = block_ts - 30.0  # Arrives earlier than previous
            else:
                arrival_ts = block_ts + (rng.random() * 5.0)

            events.append(
                SyntheticEvent(
                    event_id=f"evt_ooo_{i}",
                    event_type="HYPERSYNC_FILL",
                    condition_id=condition_id,
                    wallet_address=wallet_address,
                    side=side,
                    price=price,
                    notional_usd=notional,
                    shares=shares,
                    tx_hash=f"0x{uuid.uuid4().hex[:32]}",
                    log_index=i,
                    block_number=block_num,
                    block_timestamp=block_ts,
                    arrival_timestamp=arrival_ts,
                    latency_seconds=max(0.0, arrival_ts - block_ts),
                )
            )

        # Sort by arrival timestamp to simulate the stream as received
        events.sort(key=lambda e: e.arrival_timestamp)
        return events

    @staticmethod
    def generate_latency_sweep_stream(
        latencies: Optional[List[float]] = None,
        condition_id: str = "cond_latency_sweep",
        wallet_address: str = "0xWhaleLatency1",
    ) -> List[SyntheticEvent]:
        """Generates events with step-wise latency increases (1s, 5s, 15s, 30s, 60s, 120s)."""
        if latencies is None:
            latencies = [1.0, 5.0, 15.0, 30.0, 60.0, 120.0]

        base_time = 1700000000.0
        events: List[SyntheticEvent] = []

        for idx, lat in enumerate(latencies):
            block_ts = base_time + (idx * 30.0)
            arrival_ts = block_ts + lat
            events.append(
                SyntheticEvent(
                    event_id=f"evt_lat_{idx}",
                    event_type="TRADE_LOG",
                    condition_id=condition_id,
                    wallet_address=wallet_address,
                    side="BUY",
                    price=0.50,
                    notional_usd=250.0,
                    shares=500.0,
                    tx_hash=f"0x{uuid.uuid4().hex[:32]}",
                    log_index=idx,
                    block_number=51000000 + idx,
                    block_timestamp=block_ts,
                    arrival_timestamp=arrival_ts,
                    latency_seconds=lat,
                )
            )

        return events

    @staticmethod
    def generate_websocket_reconnect_burst(
        burst_size: int = 50,
        disconnect_duration_seconds: float = 10.0,
        condition_id: str = "cond_ws_burst",
        wallet_address: str = "0xWhaleWsBurst",
    ) -> List[SyntheticEvent]:
        """Simulates a sudden reconnect burst of events buffered during a network outage."""
        base_time = 1700000000.0
        reconnect_time = base_time + disconnect_duration_seconds
        events: List[SyntheticEvent] = []

        for i in range(burst_size):
            block_ts = base_time + (i * 0.2)
            # All burst events arrive nearly simultaneously at reconnect_time
            arrival_ts = reconnect_time + (i * 0.001)
            events.append(
                SyntheticEvent(
                    event_id=f"evt_burst_{i}",
                    event_type="WS_BURST",
                    condition_id=condition_id,
                    wallet_address=wallet_address,
                    side="BUY" if i % 2 == 0 else "SELL",
                    price=round(0.48 + ((i % 5) * 0.01), 4),
                    notional_usd=150.0,
                    shares=300.0,
                    tx_hash=f"0x{uuid.uuid4().hex[:32]}",
                    log_index=i,
                    block_number=52000000 + (i // 10),
                    block_timestamp=block_ts,
                    arrival_timestamp=arrival_ts,
                    latency_seconds=arrival_ts - block_ts,
                )
            )

        return events

    @staticmethod
    def generate_duplicate_transaction_stream(
        count: int = 20,
        duplicate_ratio: float = 0.4,
        condition_id: str = "cond_duplicate",
        wallet_address: str = "0xWhaleDup",
        seed: int = 42,
    ) -> List[SyntheticEvent]:
        """Simulates re-ingestion of identical transaction hashes to test idempotency."""
        rng = random.Random(seed)
        events: List[SyntheticEvent] = []
        seen_templates: List[SyntheticEvent] = []

        base_time = 1700000000.0

        for i in range(count):
            if seen_templates and rng.random() < duplicate_ratio:
                # Pick an existing template to duplicate
                tmpl = rng.choice(seen_templates)
                dup_event = SyntheticEvent(
                    event_id=f"evt_dup_{i}",
                    event_type="DUPLICATE_TX",
                    condition_id=tmpl.condition_id,
                    wallet_address=tmpl.wallet_address,
                    side=tmpl.side,
                    price=tmpl.price,
                    notional_usd=tmpl.notional_usd,
                    shares=tmpl.shares,
                    tx_hash=tmpl.tx_hash,  # Same tx_hash!
                    log_index=tmpl.log_index,  # Same log_index!
                    block_number=tmpl.block_number,
                    block_timestamp=tmpl.block_timestamp,
                    arrival_timestamp=base_time + (i * 5.0),
                    latency_seconds=5.0,
                    is_duplicate=True,
                )
                events.append(dup_event)
            else:
                new_event = SyntheticEvent(
                    event_id=f"evt_orig_{i}",
                    event_type="TRADE_LOG",
                    condition_id=condition_id,
                    wallet_address=wallet_address,
                    side="BUY",
                    price=0.55,
                    notional_usd=200.0,
                    shares=363.6364,
                    tx_hash=f"0x{uuid.uuid4().hex[:32]}",
                    log_index=i,
                    block_number=53000000 + i,
                    block_timestamp=base_time + (i * 5.0),
                    arrival_timestamp=base_time + (i * 5.0) + 0.5,
                    latency_seconds=0.5,
                    is_duplicate=False,
                )
                events.append(new_event)
                seen_templates.append(new_event)

        return events

    @staticmethod
    def generate_rpc_failure_and_retry_stream(
        count: int = 20,
        failure_rate: float = 0.25,
        retry_delay_seconds: float = 2.0,
        condition_id: str = "cond_rpc_fail",
        wallet_address: str = "0xWhaleRpcFail",
        seed: int = 42,
    ) -> List[SyntheticEvent]:
        """Simulates 429 / 500 RPC failures and subsequent retries."""
        rng = random.Random(seed)
        events: List[SyntheticEvent] = []
        base_time = 1700000000.0

        for i in range(count):
            is_failure = rng.random() < failure_rate
            ts = base_time + (i * 3.0)
            if is_failure:
                # Add failure record followed by retry
                events.append(
                    SyntheticEvent(
                        event_id=f"evt_rpc_fail_{i}",
                        event_type="RPC_FAILOVER",
                        condition_id=condition_id,
                        wallet_address=wallet_address,
                        side="BUY",
                        price=0.50,
                        notional_usd=100.0,
                        shares=200.0,
                        tx_hash=f"0x{uuid.uuid4().hex[:32]}",
                        log_index=i,
                        block_number=54000000 + i,
                        block_timestamp=ts,
                        arrival_timestamp=ts + 0.1,
                        latency_seconds=0.1,
                        payload={"status_code": 429, "error": "Too Many Requests"},
                    )
                )
                # Retry event
                events.append(
                    SyntheticEvent(
                        event_id=f"evt_rpc_retry_{i}",
                        event_type="RPC_RETRY",
                        condition_id=condition_id,
                        wallet_address=wallet_address,
                        side="BUY",
                        price=0.50,
                        notional_usd=100.0,
                        shares=200.0,
                        tx_hash=f"0x{uuid.uuid4().hex[:32]}",
                        log_index=i,
                        block_number=54000000 + i,
                        block_timestamp=ts,
                        arrival_timestamp=ts + retry_delay_seconds,
                        latency_seconds=retry_delay_seconds,
                        payload={"status_code": 200, "retry_attempt": 1},
                    )
                )
            else:
                events.append(
                    SyntheticEvent(
                        event_id=f"evt_rpc_ok_{i}",
                        event_type="TRADE_LOG",
                        condition_id=condition_id,
                        wallet_address=wallet_address,
                        side="BUY",
                        price=0.50,
                        notional_usd=100.0,
                        shares=200.0,
                        tx_hash=f"0x{uuid.uuid4().hex[:32]}",
                        log_index=i,
                        block_number=54000000 + i,
                        block_timestamp=ts,
                        arrival_timestamp=ts + 0.5,
                        latency_seconds=0.5,
                        payload={"status_code": 200},
                    )
                )

        return events

    @staticmethod
    def generate_binary_resolution_events(
        condition_ids: List[str],
        winning_outcome: str = "Yes",
    ) -> List[SyntheticEvent]:
        """Generates binary resolution settlement events ($1.00 payout for winner, $0.00 for loser)."""
        events: List[SyntheticEvent] = []
        base_time = 1700000000.0

        for idx, cid in enumerate(condition_ids):
            ts = base_time + (idx * 60.0)
            events.append(
                SyntheticEvent(
                    event_id=f"evt_res_{idx}",
                    event_type="RESOLUTION_PAYOUT",
                    condition_id=cid,
                    wallet_address="0xOracleResolutionContract",
                    side="SELL",
                    price=1.00 if winning_outcome == "Yes" else 0.00,
                    notional_usd=0.0,
                    shares=0.0,
                    tx_hash=f"0x{uuid.uuid4().hex[:32]}",
                    log_index=0,
                    block_number=55000000 + idx,
                    block_timestamp=ts,
                    arrival_timestamp=ts + 1.0,
                    outcome=winning_outcome,
                    payload={"winning_outcome": winning_outcome, "payout_per_share": 1.00},
                )
            )

        return events

    @staticmethod
    def generate_multi_whale_consensus_stream(
        condition_id: str = "cond_consensus",
        whale_addresses: Optional[List[str]] = None,
        side: str = "BUY",
        notional_per_whale: float = 500.0,
    ) -> List[SyntheticEvent]:
        """Generates aligned trades across multiple whales on the same condition to trigger consensus sizing."""
        if whale_addresses is None:
            whale_addresses = [
                "0xWhaleConsensusAlpha",
                "0xWhaleConsensusBeta",
                "0xWhaleConsensusGamma",
            ]

        events: List[SyntheticEvent] = []
        base_time = 1700000000.0

        for idx, addr in enumerate(whale_addresses):
            ts = base_time + (idx * 2.0)
            events.append(
                SyntheticEvent(
                    event_id=f"evt_con_{idx}",
                    event_type="TRADE_LOG",
                    condition_id=condition_id,
                    wallet_address=addr,
                    side=side,
                    price=0.52,
                    notional_usd=notional_per_whale,
                    shares=round(notional_per_whale / 0.52, 4),
                    tx_hash=f"0x{uuid.uuid4().hex[:32]}",
                    log_index=idx,
                    block_number=56000000 + idx,
                    block_timestamp=ts,
                    arrival_timestamp=ts + 0.2,
                    outcome="Yes",
                )
            )

        return events

    @staticmethod
    def generate_interleaved_buy_sell_stream(
        condition_id: str = "cond_interleaved",
        whale_address: str = "0xWhaleInterleaved",
        trade_count: int = 10,
        base_notional: float = 100.0,
    ) -> List[SyntheticEvent]:
        """Generates alternating BUY and partial SELL sequence on the same condition."""
        events: List[SyntheticEvent] = []
        base_time = 1700000000.0

        for i in range(trade_count):
            side = "BUY" if i % 2 == 0 else "SELL"
            price = 0.50 if side == "BUY" else 0.60
            notional = base_notional if side == "BUY" else (base_notional * 0.5)
            shares = round(notional / price, 4)
            ts = base_time + (i * 10.0)

            events.append(
                SyntheticEvent(
                    event_id=f"evt_intl_{i}",
                    event_type="TRADE_LOG",
                    condition_id=condition_id,
                    wallet_address=whale_address,
                    side=side,
                    price=price,
                    notional_usd=notional,
                    shares=shares,
                    tx_hash=f"0x{uuid.uuid4().hex[:32]}",
                    log_index=i,
                    block_number=57000000 + i,
                    block_timestamp=ts,
                    arrival_timestamp=ts + 0.5,
                    outcome="Yes",
                )
            )

        return events
