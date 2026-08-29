"""
Baleen Scenario Stress Matrix — Suite 2: Timing, Network & Settlement Dynamics.

Contains 55 distinct operational and market scenarios stressing:
  - S056-S065: Asynchronous block latency sweeps (1s, 5s, 15s, 30s, 60s, 120s lag).
  - S066-S075: Out-of-order Envio HyperSync log delivery (SELL arriving before BUY, inverted split log index).
  - S076-S085: Duplicate transaction processing, re-ingestion, and idempotency guarantees.
  - S086-S095: WebSocket disconnection/reconnection cycles, buffered event burst delivery.
  - S096-S105: Abrupt RPC downtime, rate-limiting (429), and fallback failover.
  - S106-S110: Binary resolution payouts ($1.00 / $0.00), condition ID redemption, and lot closure.

All scenarios execute through InvariantMonitor validation to guarantee:
  1. Cash Non-Negativity
  2. Settled Cash - Open Margin Conservation
  3. High-Water Mark Monotonicity
  4. FIFO Lot Splitting Conservation
  5. Polymarket Quadratic Fee Bounds (Theta in [0.00, 0.072])
  6. Zero Orphaned Positions
  7. Ghost Sell Fill Prevention
  8. IEEE Floating-Point Numerical Safety
  9. MTM Isolation from Settled Cash
  10. Equity Identity Invariance
"""

import copy
import pytest
from tests.scenarios.invariant_monitor import (
    InvariantCheckType,
    InvariantMonitor,
    PortfolioState,
    PositionLot,
    TradeExecution,
)
from tests.scenarios.mock_market_factory import (
    EventStreamGenerator,
    MockMarketFactory,
    SyntheticEvent,
)
from tests.scenarios.runner import (
    ScenarioDefinition,
    ScenarioReport,
    ScenarioResult,
    ScenarioRunner,
)


@pytest.fixture
def runner() -> ScenarioRunner:
    return ScenarioRunner(strict_invariants=True)


@pytest.fixture
def monitor() -> InvariantMonitor:
    return InvariantMonitor(strict_mode=True)


def create_state(user_id: str, balance: float = 10000.0, open_margin: float = 0.0) -> PortfolioState:
    free_cash = max(0.0, balance - open_margin)
    return PortfolioState(
        user_id=user_id,
        settled_cash_usd=balance,
        free_cash_usd=free_cash,
        open_margin_usd=open_margin,
        high_water_mark_usd=balance,
        open_positions=[],
        closed_positions=[],
        total_realized_pnl_usd=0.0,
        total_unrealized_pnl_usd=0.0,
        equity_usd=balance,
    )


def create_event(
    event_id: str,
    condition_id: str,
    side: str,
    price: float,
    notional: float,
    outcome: str = "Yes",
    category: str = "Crypto",
    block_num: int = 5000,
    log_idx: int = 0,
    tx_hash: str = "0xtx",
    wallet_addr: str = "0xWhaleNet1",
    question: str = "Synthetic Network Market",
    event_type: str = "TRADE_LOG",
    latency_sec: float = 0.0,
    is_duplicate: bool = False,
) -> SyntheticEvent:
    price = max(0.001, min(0.999, price))
    shares = round(notional / price, 4) if price > 0 else 0.0
    block_ts = float(block_num * 2.0)
    arrival_ts = block_ts + latency_sec + 0.1
    return SyntheticEvent(
        event_id=event_id,
        event_type=event_type,
        condition_id=condition_id,
        wallet_address=wallet_addr,
        side=side,
        price=price,
        notional_usd=round(notional, 2),
        shares=shares,
        tx_hash=tx_hash,
        log_index=log_idx,
        block_number=block_num,
        block_timestamp=block_ts,
        arrival_timestamp=arrival_ts,
        latency_seconds=latency_sec,
        is_duplicate=is_duplicate,
        outcome=outcome,
        market_question=question,
        market_category=category,
    )


# ============================================================================
# SCENARIO BUILDER: 55 DISTINCT NETWORK & TIMING SCENARIOS
# ============================================================================

def build_network_timing_scenarios() -> list[ScenarioDefinition]:
    scenarios: list[ScenarioDefinition] = []

    # ------------------------------------------------------------------------
    # S056 - S065: Asynchronous Block Latency Sweeps (10 Scenarios)
    # ------------------------------------------------------------------------
    latencies = [1.0, 5.0, 15.0, 30.0, 60.0, 120.0]
    for idx, lat in enumerate(latencies):
        scenarios.append(
            ScenarioDefinition(
                scenario_id=f"S05{6 + idx}_BLOCK_LATENCY_{int(lat)}S",
                title=f"Asynchronous Block Latency {int(lat)}s Delay Sweep",
                tier="Tier 2: Timing/Network",
                description=f"Tests ingestion and state machine safety under {int(lat)}s network latency",
                initial_state=create_state(f"u_lat_{int(lat)}", 10000.0),
                events=[create_event(f"evt_lat_{int(lat)}", f"0xcond_lat_{int(lat)}", "BUY", 0.50, 200.0, latency_sec=lat)],
            )
        )

    # S062: Non-uniform jittering latency (1s -> 45s -> 2s -> 90s)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S062_JITTERING_LATENCY_SERIES",
            title="Non-Uniform Network Jitter Series (1s -> 45s -> 2s -> 90s)",
            tier="Tier 2: Timing/Network",
            description="Tests handling of volatile network arrival timestamps without state inversion",
            initial_state=create_state("u_s062", 10000.0),
            events=[
                create_event("evt_s062_1", "0xcond_jit", "BUY", 0.50, 100.0, block_num=5010, log_idx=0, latency_sec=1.0),
                create_event("evt_s062_2", "0xcond_jit", "BUY", 0.52, 100.0, block_num=5011, log_idx=1, latency_sec=45.0),
                create_event("evt_s062_3", "0xcond_jit", "BUY", 0.51, 100.0, block_num=5012, log_idx=2, latency_sec=2.0),
                create_event("evt_s062_4", "0xcond_jit", "BUY", 0.53, 100.0, block_num=5013, log_idx=3, latency_sec=90.0),
            ],
        )
    )

    # S063: Latency exceeding trade validity window (300s lag)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S063_STALE_BLOCK_LATENCY_300S",
            title="Stale Block Arrival with 300s Extreme Delay",
            tier="Tier 2: Timing/Network",
            description="Verifies stale block ingestion handles price checks and margin isolation safely",
            initial_state=create_state("u_s063", 10000.0),
            events=[create_event("evt_s063", "0xcond_stale", "BUY", 0.50, 250.0, latency_sec=300.0)],
        )
    )

    # S064: Concurrent dual-node streams with divergent latencies
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S064_DUAL_NODE_DIVERGENT_LATENCY",
            title="Dual RPC Ingestion Streams with Divergent Latency (Fast 0.5s vs Slow 25s)",
            tier="Tier 2: Timing/Network",
            description="Tests interleaved multi-node feeds with different arrival timestamps",
            initial_state=create_state("u_s064", 10000.0),
            events=[
                create_event("evt_s064_fast", "0xcond_div", "BUY", 0.50, 100.0, block_num=5020, log_idx=0, latency_sec=0.5),
                create_event("evt_s064_slow", "0xcond_div", "BUY", 0.52, 100.0, block_num=5019, log_idx=1, latency_sec=25.0),
            ],
        )
    )

    # S065: Monotonic ramp latency sweep (1s -> 120s step-up)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S065_MONOTONIC_RAMP_SWEEP",
            title="Monotonic Network Degradation Sweep (1s -> 120s)",
            tier="Tier 2: Timing/Network",
            description="Simulates network connection degradation from 1s to 120s over 5 trades",
            initial_state=create_state("u_s065", 10000.0),
            events=[
                create_event(f"evt_s065_{i}", "0xcond_ramp", "BUY", 0.50 + (i * 0.01), 50.0, block_num=5030 + i, log_idx=i, latency_sec=float(i * 30.0 + 1.0))
                for i in range(5)
            ],
        )
    )

    # ------------------------------------------------------------------------
    # S066 - S075: Out-of-Order Envio HyperSync Logs (10 Scenarios)
    # ------------------------------------------------------------------------
    # S066: SELL log arriving before BUY log on same condition
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S066_OOO_SELL_BEFORE_BUY",
            title="Out-of-Order Envio Log: SELL Arriving Before BUY",
            tier="Tier 2: Timing/Network",
            description="Simulates SELL arriving before BUY; SELL gracefully skips (0 positions held), then BUY executes",
            initial_state=create_state("u_s066", 10000.0),
            events=[
                create_event("evt_s066_sell", "0xcond_ooo_1", "SELL", 0.60, 100.0, block_num=5100, log_idx=1),
                create_event("evt_s066_buy", "0xcond_ooo_1", "BUY", 0.50, 100.0, block_num=5099, log_idx=0),
            ],
        )
    )

    # S067: Inverted split log index (log_index 1 arriving before log_index 0)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S067_INVERTED_SPLIT_LOG_INDEX",
            title="Inverted Transaction Log Index Delivery (log_index 1 -> 0)",
            tier="Tier 2: Timing/Network",
            description="Simulates multi-event transaction receipt where log 1 arrives prior to log 0",
            initial_state=create_state("u_s067", 10000.0),
            events=[
                create_event("evt_s067_log1", "0xcond_inv_log", "BUY", 0.52, 100.0, block_num=5110, log_idx=1),
                create_event("evt_s067_log0", "0xcond_inv_log", "BUY", 0.50, 100.0, block_num=5110, log_idx=0),
            ],
        )
    )

    # S068: Multi-block out-of-order sequence (Block N+2 arrives before Block N)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S068_MULTI_BLOCK_OOO",
            title="Multi-Block Out-of-Order Delivery (Block N+2 before Block N)",
            tier="Tier 2: Timing/Network",
            description="Ingests Block 5122 before Block 5120 and Block 5121",
            initial_state=create_state("u_s068", 10000.0),
            events=[
                create_event("evt_s068_b5122", "0xcond_mb_ooo", "BUY", 0.55, 100.0, block_num=5122, log_idx=0),
                create_event("evt_s068_b5120", "0xcond_mb_ooo", "BUY", 0.45, 100.0, block_num=5120, log_idx=0),
                create_event("evt_s068_b5121", "0xcond_mb_ooo", "BUY", 0.50, 100.0, block_num=5121, log_idx=0),
            ],
        )
    )

    # S069: Reordered interleaved BUY/SELL events (BUY1, SELL2, BUY2, SELL1)
    init_s069 = create_state("u_s069", 10000.0)
    init_s069.open_positions.append(PositionLot("lot_s069_pre", "0xcond_reorder", "Yes", "BUY", 0.40, 250.0, 100.0, 3.60, "FILLED", "u_s069"))
    init_s069.open_margin_usd = 100.0
    init_s069.free_cash_usd = 9900.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S069_REORDERED_INTERLEAVED_STREAM",
            title="Reordered Interleaved BUY/SELL Ingestion Stream",
            tier="Tier 2: Timing/Network",
            description="Verifies FIFO lot queue consistency when log order differs from execution order",
            initial_state=init_s069,
            events=[
                create_event("evt_s069_1", "0xcond_reorder", "SELL", 0.55, 50.0, block_num=5131, log_idx=1),
                create_event("evt_s069_2", "0xcond_reorder", "BUY", 0.48, 100.0, block_num=5130, log_idx=0),
                create_event("evt_s069_3", "0xcond_reorder", "SELL", 0.60, 50.0, block_num=5132, log_idx=2),
            ],
        )
    )

    # S070: High inversion ratio (50% out-of-order stream generated by factory)
    ooo_events_s070 = EventStreamGenerator.generate_out_of_order_envio_stream(count=6, condition_id="0xcond_ooo_50pct", seed=42)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S070_50_PCT_OOO_INVERSION_STREAM",
            title="Synthetic 50% Out-of-Order HyperSync Stream",
            tier="Tier 2: Timing/Network",
            description="Ingests deterministic 6-event synthetic stream with 50% timestamp inversions",
            initial_state=create_state("u_s070", 10000.0),
            events=ooo_events_s070,
        )
    )

    # S071: Out-of-order SELL on 0 position followed by retroactive BUY
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S071_OOO_SELL_ZERO_POS_RECOVERY",
            title="Out-of-Order Ghost SELL Rejection Followed by Valid BUY",
            tier="Tier 2: Timing/Network",
            description="Ensures ghost sell is rejected with zero fee deduction, followed by successful BUY",
            initial_state=create_state("u_s071", 10000.0),
            events=[
                create_event("evt_s071_ghost_sell", "0xcond_ooo_rec", "SELL", 0.70, 200.0, block_num=5141, log_idx=1),
                create_event("evt_s071_valid_buy", "0xcond_ooo_rec", "BUY", 0.50, 200.0, block_num=5140, log_idx=0),
            ],
        )
    )

    # S072: Reordered resolution log arriving before final trade log
    init_s072 = create_state("u_s072", 10000.0)
    init_s072.open_positions.append(PositionLot("lot_s072", "0xcond_res_ooo", "Yes", "BUY", 0.40, 250.0, 100.0, 3.60, "FILLED", "u_s072"))
    init_s072.open_margin_usd = 100.0
    init_s072.free_cash_usd = 9900.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S072_RESOLUTION_BEFORE_TRADE_LOG",
            title="Resolution Payout Log Delivered Before Final Trade Log",
            tier="Tier 2: Timing/Network",
            description="Tests graceful resolution closure and subsequent post-resolution trade handling",
            initial_state=init_s072,
            events=[
                create_event("evt_s072_res", "0xcond_res_ooo", "SELL", 0.999, 100.0, block_num=5151, log_idx=0, event_type="RESOLUTION_PAYOUT"),
                create_event("evt_s072_trade", "0xcond_res_ooo", "BUY", 0.50, 50.0, block_num=5150, log_idx=1),
            ],
        )
    )

    # S073: Out-of-order partial split events across 3 transactions
    init_s073 = create_state("u_s073", 10000.0)
    init_s073.open_positions.append(PositionLot("lot_s073", "0xcond_split_ooo", "Yes", "BUY", 0.50, 600.0, 300.0, 10.80, "FILLED", "u_s073"))
    init_s073.open_margin_usd = 300.0
    init_s073.free_cash_usd = 9700.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S073_OOO_PARTIAL_SPLITS",
            title="Out-of-Order Partial Split Liquidations",
            tier="Tier 2: Timing/Network",
            description="Executes 2 partial sells arriving out of chronological sequence",
            initial_state=init_s073,
            events=[
                create_event("evt_s073_s2", "0xcond_split_ooo", "SELL", 0.65, 100.0, block_num=5162, log_idx=0),
                create_event("evt_s073_s1", "0xcond_split_ooo", "SELL", 0.60, 100.0, block_num=5161, log_idx=0),
            ],
        )
    )

    # S074: Swapped block index arrival with identical arrival timestamps
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S074_SWAPPED_BLOCK_INDEX_STREAM",
            title="Identical Arrival Timestamp with Inverted Block Index",
            tier="Tier 2: Timing/Network",
            description="Tests tie-breaking logic when arrival timestamps match but block numbers differ",
            initial_state=create_state("u_s074", 10000.0),
            events=[
                create_event("evt_s074_b2", "0xcond_swap_blk", "BUY", 0.55, 100.0, block_num=5172, log_idx=0),
                create_event("evt_s074_b1", "0xcond_swap_blk", "BUY", 0.50, 100.0, block_num=5171, log_idx=0),
            ],
        )
    )

    # S075: Full HyperSync backlog replay in reverse chronological order
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S075_REVERSE_CHRONO_BACKLOG_REPLAY",
            title="Reverse Chronological Backlog Replay (5 Events)",
            tier="Tier 2: Timing/Network",
            description="Simulates replay of 5 historical trades delivered newest-first",
            initial_state=create_state("u_s075", 10000.0),
            events=[
                create_event(f"evt_s075_{4 - i}", "0xcond_rev_replay", "BUY", 0.40 + (i * 0.05), 50.0, block_num=5180 + (4 - i), log_idx=0)
                for i in range(5)
            ],
        )
    )

    # ------------------------------------------------------------------------
    # S076 - S085: Duplicate Transactions & Idempotency (10 Scenarios)
    # ------------------------------------------------------------------------
    # S076: Exact duplicate transaction re-ingestion
    evt_s076 = create_event("evt_s076_orig", "0xcond_dup_1", "BUY", 0.50, 100.0, tx_hash="0xdup_hash_76", log_idx=0)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S076_EXACT_DUPLICATE_TX",
            title="Exact Duplicate Transaction Hash Idempotency",
            tier="Tier 2: Timing/Network",
            description="Ensures identical transaction hash delivered twice is handled without double margin deduction",
            initial_state=create_state("u_s076", 10000.0),
            events=[evt_s076, copy.deepcopy(evt_s076)],
        )
    )

    # S077: 3x identical transaction burst
    evt_s077 = create_event("evt_s077_orig", "0xcond_dup_3x", "BUY", 0.50, 150.0, tx_hash="0xdup_hash_77", log_idx=1)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S077_3X_DUPLICATE_BURST",
            title="3x Identical Transaction Burst Ingestion",
            tier="Tier 2: Timing/Network",
            description="Simulates 3 rapid parallel worker re-deliveries of identical tx hash",
            initial_state=create_state("u_s077", 10000.0),
            events=[copy.deepcopy(evt_s077) for _ in range(3)],
        )
    )

    # S078: 5x identical transaction flood under high concurrency
    evt_s078 = create_event("evt_s078_orig", "0xcond_dup_5x", "BUY", 0.50, 100.0, tx_hash="0xdup_hash_78", log_idx=2)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S078_5X_DUPLICATE_FLOOD",
            title="5x Identical Transaction Flood Ingestion",
            tier="Tier 2: Timing/Network",
            description="Simulates 5 parallel deliveries of same trade; verifies exact single trade state effect",
            initial_state=create_state("u_s078", 10000.0),
            events=[copy.deepcopy(evt_s078) for _ in range(5)],
        )
    )

    # S079: Duplicate with modified arrival timestamp but identical tx_hash & log_index
    evt_s079_1 = create_event("evt_s079_a", "0xcond_dup_mod", "BUY", 0.50, 100.0, tx_hash="0xdup_hash_79", log_idx=0, latency_sec=0.1)
    evt_s079_2 = create_event("evt_s079_b", "0xcond_dup_mod", "BUY", 0.50, 100.0, tx_hash="0xdup_hash_79", log_idx=0, latency_sec=10.0, is_duplicate=True)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S079_DUPLICATE_MODIFIED_ARRIVAL_TS",
            title="Duplicate Tx with Delayed Network Arrival Timestamp",
            tier="Tier 2: Timing/Network",
            description="Tests idempotency check based on tx_hash + log_index rather than arrival timestamp",
            initial_state=create_state("u_s079", 10000.0),
            events=[evt_s079_1, evt_s079_2],
        )
    )

    # S080: Partial duplicate stream (50% duplicates interleaved with unique events)
    dup_stream_s080 = EventStreamGenerator.generate_duplicate_transaction_stream(count=8, duplicate_ratio=0.5, condition_id="0xcond_dup_stream", seed=42)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S080_50_PCT_DUPLICATE_STREAM",
            title="Interleaved 50% Duplicate Ingestion Stream (8 Events)",
            tier="Tier 2: Timing/Network",
            description="Validates invariant monitor across stream with 50% duplicate event ratio",
            initial_state=create_state("u_s080", 10000.0),
            events=dup_stream_s080,
        )
    )

    # S081: Duplicate SELL event on already closed lot
    init_s081 = create_state("u_s081", 10000.0)
    init_s081.open_positions.append(PositionLot("lot_s081", "0xcond_dup_sell", "Yes", "BUY", 0.50, 200.0, 100.0, 3.60, "FILLED", "u_s081"))
    init_s081.open_margin_usd = 100.0
    init_s081.free_cash_usd = 9900.0
    evt_sell_s081 = create_event("evt_s081_sell", "0xcond_dup_sell", "SELL", 0.60, 100.0, tx_hash="0xdup_sell_81", log_idx=0)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S081_DUPLICATE_SELL_ON_CLOSED_LOT",
            title="Duplicate SELL Ingestion on Already Closed Lot",
            tier="Tier 2: Timing/Network",
            description="First SELL closes lot; second duplicate SELL is safely rejected preventing ghost sell",
            initial_state=init_s081,
            events=[evt_sell_s081, copy.deepcopy(evt_sell_s081)],
        )
    )

    # S082: Duplicate resolution payout event idempotency
    init_s082 = create_state("u_s082", 10000.0)
    init_s082.open_positions.append(PositionLot("lot_s082", "0xcond_dup_res", "Yes", "BUY", 0.50, 200.0, 100.0, 3.60, "FILLED", "u_s082"))
    init_s082.open_margin_usd = 100.0
    init_s082.free_cash_usd = 9900.0
    evt_res_s082 = create_event("evt_s082_res", "0xcond_dup_res", "SELL", 0.999, 100.0, tx_hash="0xdup_res_82", log_idx=0, event_type="RESOLUTION_PAYOUT")
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S082_DUPLICATE_RESOLUTION_PAYOUT",
            title="Duplicate Resolution Payout Event Ingestion",
            tier="Tier 2: Timing/Network",
            description="Verifies resolution payout is not applied twice on re-delivery",
            initial_state=init_s082,
            events=[evt_res_s082, copy.deepcopy(evt_res_s082)],
        )
    )

    # S083: Duplicate maker fill event deduplication
    evt_maker_s083 = create_event("evt_s083_m", "0xcond_dup_maker", "BUY", 0.50, 100.0, tx_hash="0xdup_m_83", log_idx=0)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S083_DUPLICATE_MAKER_FILL",
            title="Duplicate Maker Fill Deduplication (0 Fee Invariant)",
            tier="Tier 2: Timing/Network",
            description="Tests deduplication of 0-fee maker executions",
            initial_state=create_state("u_s083", 10000.0),
            events=[evt_maker_s083, copy.deepcopy(evt_maker_s083)],
        )
    )

    # S084: Duplicate transaction arrival after cache eviction window
    evt_s084 = create_event("evt_s084", "0xcond_dup_evict", "BUY", 0.50, 100.0, tx_hash="0xdup_evict_84", log_idx=0)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S084_DUPLICATE_POST_CACHE_EVICTION",
            title="Duplicate Tx Arrival Simulation Post-Cache Eviction",
            tier="Tier 2: Timing/Network",
            description="Tests state machine robustness on duplicate event arriving across distinct blocks",
            initial_state=create_state("u_s084", 10000.0),
            events=[evt_s084, copy.deepcopy(evt_s084)],
        )
    )

    # S085: Cross-worker concurrent duplicate ingestion lock verification
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S085_CROSS_WORKER_CONCURRENT_DUP",
            title="Cross-Worker Concurrent Duplicate Lock Verification",
            tier="Tier 2: Timing/Network",
            description="Tests 4 identical events simulating simultaneous multi-threaded ingestion",
            initial_state=create_state("u_s085", 10000.0),
            events=[
                create_event(f"evt_s085_{i}", "0xcond_worker_dup", "BUY", 0.50, 100.0, tx_hash="0xlock_tx_85", log_idx=0)
                for i in range(4)
            ],
        )
    )

    # ------------------------------------------------------------------------
    # S086 - S095: WebSocket Disconnections & Reconnect Bursts (10 Scenarios)
    # ------------------------------------------------------------------------
    # S086: Sudden WS disconnect with 5s offline buffer
    burst_s086 = EventStreamGenerator.generate_websocket_reconnect_burst(burst_size=5, disconnect_duration_seconds=5.0, condition_id="0xcond_ws_5s")
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S086_WS_RECONNECT_5S_BURST",
            title="WebSocket 5s Disconnection and Reconnect Burst (5 Events)",
            tier="Tier 2: Timing/Network",
            description="Simulates 5s offline queue flush delivered simultaneously upon reconnection",
            initial_state=create_state("u_s086", 10000.0),
            events=burst_s086,
        )
    )

    # S087: 10s WS reconnection burst (10 events delivered in 1ms)
    burst_s087 = EventStreamGenerator.generate_websocket_reconnect_burst(burst_size=10, disconnect_duration_seconds=10.0, condition_id="0xcond_ws_10s")
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S087_WS_RECONNECT_10S_BURST",
            title="WebSocket 10s Disconnection Reconnect Burst (10 Events)",
            tier="Tier 2: Timing/Network",
            description="Tests high-speed sequential queue processing of 10 buffered events",
            initial_state=create_state("u_s087", 10000.0),
            events=burst_s087,
        )
    )

    # S088: 30s extended outage followed by 20-event catch-up burst
    burst_s088 = EventStreamGenerator.generate_websocket_reconnect_burst(burst_size=20, disconnect_duration_seconds=30.0, condition_id="0xcond_ws_30s")
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S088_WS_RECONNECT_30S_20_EVENTS",
            title="WebSocket 30s Extended Outage Catch-Up Burst (20 Events)",
            tier="Tier 2: Timing/Network",
            description="Verifies cash, margin, and HWM integrity across 20-event buffered catch-up",
            initial_state=create_state("u_s088", 20000.0),
            events=burst_s088,
        )
    )

    # S089: Rapid flapping disconnect/reconnect cycle (5 mini-bursts)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S089_WS_FLAPPING_BURST_CYCLE",
            title="WebSocket Flapping Cycle (5 Rapid Connect/Disconnect Waves)",
            tier="Tier 2: Timing/Network",
            description="Simulates unstable network flapping with 5 micro-bursts of 2 events each",
            initial_state=create_state("u_s089", 10000.0),
            events=[
                create_event(f"evt_s089_{i}", f"0xcond_flap_{i // 2}", "BUY", 0.50, 50.0, block_num=5200 + i, log_idx=i % 2)
                for i in range(10)
            ],
        )
    )

    # S090: WS reconnect buffer with out-of-order delivery
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S090_WS_RECONNECT_OOO_BUFFER",
            title="WebSocket Reconnection Buffer with Out-of-Order Sequence",
            tier="Tier 2: Timing/Network",
            description="Tests buffered reconnect burst where event block numbers are inverted",
            initial_state=create_state("u_s090", 10000.0),
            events=[
                create_event("evt_s090_3", "0xcond_ws_ooo", "BUY", 0.54, 50.0, block_num=5212, log_idx=0),
                create_event("evt_s090_1", "0xcond_ws_ooo", "BUY", 0.50, 50.0, block_num=5210, log_idx=0),
                create_event("evt_s090_2", "0xcond_ws_ooo", "BUY", 0.52, 50.0, block_num=5211, log_idx=0),
            ],
        )
    )

    # S091: WS reconnect with duplicate events buffered during outage
    evt_base_s091 = create_event("evt_s091_dup", "0xcond_ws_dup_buf", "BUY", 0.50, 100.0, tx_hash="0xws_dup_91", log_idx=0)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S091_WS_RECONNECT_DUPLICATE_BUFFER",
            title="WebSocket Reconnection with Duplicate Buffered Events",
            tier="Tier 2: Timing/Network",
            description="Tests deduplication logic during intense reconnection burst",
            initial_state=create_state("u_s091", 10000.0),
            events=[evt_base_s091, copy.deepcopy(evt_base_s091), create_event("evt_s091_uniq", "0xcond_ws_dup_buf", "BUY", 0.52, 100.0, tx_hash="0xuniq_91", log_idx=1)],
        )
    )

    # S092: WS reconnect burst across 4 distinct condition IDs
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S092_WS_BURST_MULTI_CONDITION",
            title="WebSocket Reconnect Burst Across 4 Distinct Conditions",
            tier="Tier 2: Timing/Network",
            description="Verifies isolated multi-market position accounting across burst stream",
            initial_state=create_state("u_s092", 10000.0),
            events=[
                create_event(f"evt_s092_{c}", f"0xcond_ws_mc_{c}", "BUY", 0.45 + (c * 0.05), 100.0, block_num=5220, log_idx=c)
                for c in range(4)
            ],
        )
    )

    # S093: WS reconnect burst with mixed BUY, SELL, and RESOLUTION events
    init_s093 = create_state("u_s093", 10000.0)
    init_s093.open_positions.append(PositionLot("lot_s093", "0xcond_ws_mix_1", "Yes", "BUY", 0.50, 200.0, 100.0, 3.60, "FILLED", "u_s093"))
    init_s093.open_margin_usd = 100.0
    init_s093.free_cash_usd = 9900.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S093_WS_BURST_MIXED_EVENT_TYPES",
            title="WebSocket Reconnect Burst with Mixed BUY, SELL, and RESOLUTION",
            tier="Tier 2: Timing/Network",
            description="Validates state machine on multi-type event burst",
            initial_state=init_s093,
            events=[
                create_event("evt_s093_buy", "0xcond_ws_mix_2", "BUY", 0.40, 150.0, block_num=5230, log_idx=0),
                create_event("evt_s093_sell", "0xcond_ws_mix_1", "SELL", 0.60, 100.0, block_num=5230, log_idx=1),
            ],
        )
    )

    # S094: WS reconnect event burst with price gaps across outage window
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S094_WS_BURST_PRICE_GAPS",
            title="WebSocket Outage Window with 30-Cent Price Gap",
            tier="Tier 2: Timing/Network",
            description="Tests execution when pre-outage price (0.30) jumps to post-reconnect price (0.60)",
            initial_state=create_state("u_s094", 10000.0),
            events=[
                create_event("evt_s094_pre", "0xcond_gap", "BUY", 0.30, 100.0, block_num=5240, log_idx=0),
                create_event("evt_s094_post", "0xcond_gap", "BUY", 0.60, 100.0, block_num=5250, log_idx=0),
            ],
        )
    )

    # S095: Zero-loss verification during high-throughput WS reconnect burst
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S095_WS_BURST_ZERO_LOSS_AUDIT",
            title="High-Throughput WebSocket Burst Zero-Loss Audit (15 Events)",
            tier="Tier 2: Timing/Network",
            description="Audits all 10 invariants across 15-event burst stream",
            initial_state=create_state("u_s095", 20000.0),
            events=[
                create_event(f"evt_s095_{i}", f"0xcond_audit_{i % 3}", "BUY", 0.45 + ((i % 5) * 0.02), 75.0, block_num=5260, log_idx=i)
                for i in range(15)
            ],
        )
    )

    # ------------------------------------------------------------------------
    # S096 - S105: RPC Downtime, HTTP 429 & Failover Retries (10 Scenarios)
    # ------------------------------------------------------------------------
    # S096: Single HTTP 429 rate limit with retry success
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S096_RPC_HTTP_429_RETRY",
            title="RPC HTTP 429 Rate Limit and Backoff Retry",
            tier="Tier 2: Timing/Network",
            description="Simulates 429 rate limit backoff followed by successful trade fill",
            initial_state=create_state("u_s096", 10000.0),
            events=[create_event("evt_s096", "0xcond_rpc_429", "BUY", 0.50, 100.0, event_type="RPC_RETRY")],
        )
    )

    # S097: Consecutive 429 rate limits (exponential backoff 1s, 2s, 4s)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S097_RPC_CONSECUTIVE_429_EXPONENTIAL",
            title="Consecutive HTTP 429 Exponential Backoff Retries",
            tier="Tier 2: Timing/Network",
            description="Simulates 3 consecutive 429 backoff attempts before final execution",
            initial_state=create_state("u_s097", 10000.0),
            events=[
                create_event("evt_s097_retry", "0xcond_rpc_exp", "BUY", 0.50, 100.0, latency_sec=7.0, event_type="RPC_RETRY")
            ],
        )
    )

    # S098: HTTP 500 RPC server error failover to secondary provider
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S098_RPC_HTTP_500_FAILOVER",
            title="RPC HTTP 500 Server Error Secondary Provider Failover",
            tier="Tier 2: Timing/Network",
            description="Tests failover switch to secondary RPC node with seamless state continuity",
            initial_state=create_state("u_s098", 10000.0),
            events=[create_event("evt_s098_failover", "0xcond_rpc_500", "BUY", 0.50, 100.0, event_type="RPC_FAILOVER")],
        )
    )

    # S099: Intermittent 25% RPC drop rate with retry success
    rpc_stream_s099 = EventStreamGenerator.generate_rpc_failure_and_retry_stream(count=4, failure_rate=0.25, condition_id="0xcond_rpc_drop25", seed=42)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S099_RPC_INTERMITTENT_25_PCT_DROP",
            title="Intermittent 25% RPC Drop Rate Stream",
            tier="Tier 2: Timing/Network",
            description="Tests stream with 25% intermittent dropped calls resolved via retries",
            initial_state=create_state("u_s099", 10000.0),
            events=rpc_stream_s099,
        )
    )

    # S100: Intermittent 50% RPC drop rate under burst traffic
    rpc_stream_s100 = EventStreamGenerator.generate_rpc_failure_and_retry_stream(count=4, failure_rate=0.50, condition_id="0xcond_rpc_drop50", seed=42)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S100_RPC_INTERMITTENT_50_PCT_DROP",
            title="Heavy 50% RPC Drop Rate Under Burst Traffic",
            tier="Tier 2: Timing/Network",
            description="Tests stream with 50% failure rate under burst conditions",
            initial_state=create_state("u_s100", 10000.0),
            events=rpc_stream_s100,
        )
    )

    # S101: RPC connection timeout (5s timeout) and fallback trigger
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S101_RPC_CONNECTION_TIMEOUT_FALLBACK",
            title="RPC 5-Second Connection Timeout and Fallback Trigger",
            tier="Tier 2: Timing/Network",
            description="Tests timeout detection triggering fallback node execution",
            initial_state=create_state("u_s101", 10000.0),
            events=[create_event("evt_s101", "0xcond_rpc_tout", "BUY", 0.52, 100.0, latency_sec=5.1, event_type="RPC_FAILOVER")],
        )
    )

    # S102: RPC stale block header detected and dropped
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S102_RPC_STALE_BLOCK_HEADER_DROP",
            title="RPC Stale Block Header Detection and Safe Drop",
            tier="Tier 2: Timing/Network",
            description="Ensures stale block header does not corrupt forward block state",
            initial_state=create_state("u_s102", 10000.0),
            events=[
                create_event("evt_s102_cur", "0xcond_stale_blk", "BUY", 0.50, 100.0, block_num=6000, log_idx=0),
                create_event("evt_s102_stale", "0xcond_stale_blk", "BUY", 0.48, 50.0, block_num=5500, log_idx=0),
            ],
        )
    )

    # S103: RPC rate limit during multi-lot liquidation
    init_s103 = create_state("u_s103", 10000.0)
    init_s103.open_positions.append(PositionLot("lot_s103", "0xcond_liq_rpc", "Yes", "BUY", 0.40, 500.0, 200.0, 7.20, "FILLED", "u_s103"))
    init_s103.open_margin_usd = 200.0
    init_s103.free_cash_usd = 9800.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S103_RPC_429_DURING_LIQUIDATION",
            title="RPC 429 Rate Limit Encountered Mid-Liquidation",
            tier="Tier 2: Timing/Network",
            description="Verifies lot status remains uncorrupted if liquidation requires retry",
            initial_state=init_s103,
            events=[create_event("evt_s103", "0xcond_liq_rpc", "SELL", 0.60, 200.0, event_type="RPC_RETRY")],
        )
    )

    # S104: RPC failover mid-transaction without double-execution
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S104_RPC_MID_TX_FAILOVER_IDEMPOTENCY",
            title="RPC Mid-Transaction Failover Idempotency Check",
            tier="Tier 2: Timing/Network",
            description="Verifies that failover retry does not execute order twice",
            initial_state=create_state("u_s104", 10000.0),
            events=[
                create_event("evt_s104_attempt1", "0xcond_mid_fail", "BUY", 0.50, 100.0, tx_hash="0xtx_mid_104", log_idx=0, event_type="RPC_FAILOVER"),
                create_event("evt_s104_attempt2", "0xcond_mid_fail", "BUY", 0.50, 100.0, tx_hash="0xtx_mid_104", log_idx=0, event_type="RPC_RETRY", is_duplicate=True),
            ],
        )
    )

    # S105: Full primary RPC outage with 100% secondary RPC fallback execution
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S105_FULL_RPC_OUTAGE_FALLBACK_STREAM",
            title="100% Secondary RPC Fallback Stream (4 Trades)",
            tier="Tier 2: Timing/Network",
            description="Executes 4 consecutive trades entirely through secondary fallback provider",
            initial_state=create_state("u_s105", 10000.0),
            events=[
                create_event(f"evt_s105_{i}", "0xcond_full_fall", "BUY", 0.48 + (i * 0.02), 50.0, block_num=6100 + i, log_idx=i, event_type="RPC_FAILOVER")
                for i in range(4)
            ],
        )
    )

    # ------------------------------------------------------------------------
    # S106 - S110: Binary Resolution Payouts ($1.00 / $0.00) (5 Scenarios)
    # ------------------------------------------------------------------------
    # S106: Binary resolution payout at $1.00 (Yes winner, full profit)
    init_s106 = create_state("u_s106", 10000.0)
    init_s106.open_positions.append(PositionLot("lot_s106", "0xcond_win", "Yes", "BUY", 0.40, 500.0, 200.0, 7.20, "FILLED", "u_s106"))
    init_s106.open_margin_usd = 200.0
    init_s106.free_cash_usd = 9800.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S106_BINARY_RESOLUTION_WINNER_100",
            title="Binary Market Resolution Winner ($1.00 Payout / $0.999 Bound)",
            tier="Tier 2: Timing/Network",
            description="Settles winning contract at 0.999; realizes clean +$300 PnL and full margin release",
            initial_state=init_s106,
            events=[create_event("evt_s106_res", "0xcond_win", "SELL", 0.999, 200.0, event_type="RESOLUTION_PAYOUT")],
        )
    )

    # S107: Binary resolution payout at $0.00 (Yes loser, full loss)
    init_s107 = create_state("u_s107", 10000.0)
    init_s107.open_positions.append(PositionLot("lot_s107", "0xcond_lose", "Yes", "BUY", 0.60, 333.33, 200.0, 7.20, "FILLED", "u_s107"))
    init_s107.open_margin_usd = 200.0
    init_s107.free_cash_usd = 9800.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S107_BINARY_RESOLUTION_LOSER_000",
            title="Binary Market Resolution Loser ($0.00 Payout / $0.001 Bound)",
            tier="Tier 2: Timing/Network",
            description="Settles losing contract at 0.001; realizes loss without negative cash or open margin leaks",
            initial_state=init_s107,
            events=[create_event("evt_s107_res", "0xcond_lose", "SELL", 0.001, 200.0, event_type="RESOLUTION_PAYOUT")],
        )
    )

    # S108: Multi-lot resolution redemption across 3 open positions
    init_s108 = create_state("u_s108", 10000.0)
    for k in range(3):
        init_s108.open_positions.append(PositionLot(f"lot_s108_{k}", f"0xcond_m_res_{k}", "Yes", "BUY", 0.40, 250.0, 100.0, 3.60, "FILLED", "u_s108"))
    init_s108.open_margin_usd = 300.0
    init_s108.free_cash_usd = 9700.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S108_MULTI_MARKET_SIMULTANEOUS_RESOLUTION",
            title="Simultaneous 3-Market Resolution Settlement",
            tier="Tier 2: Timing/Network",
            description="Settles 3 distinct markets simultaneously releasing all open margin to 0.00",
            initial_state=init_s108,
            events=[
                create_event(f"evt_s108_res_{k}", f"0xcond_m_res_{k}", "SELL", 0.999, 100.0, block_num=7000 + k, log_idx=0, event_type="RESOLUTION_PAYOUT")
                for k in range(3)
            ],
        )
    )

    # S109: Binary resolution on split lots with partial prior realization
    init_s109 = create_state("u_s109", 10000.0)
    init_s109.open_positions.append(PositionLot("lot_s109_split", "0xcond_split_res", "Yes", "BUY", 0.50, 200.0, 100.0, 3.60, "FILLED", "u_s109", parent_lot_id="lot_s109_orig"))
    init_s109.open_margin_usd = 100.0
    init_s109.free_cash_usd = 9900.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S109_RESOLUTION_ON_CHILD_SPLIT_LOT",
            title="Binary Resolution on Child Split Lot",
            tier="Tier 2: Timing/Network",
            description="Verifies child split lot with parent reference settles cleanly upon resolution",
            initial_state=init_s109,
            events=[create_event("evt_s109_res", "0xcond_split_res", "SELL", 0.999, 100.0, event_type="RESOLUTION_PAYOUT")],
        )
    )

    # S110: Zero-price resolution fee zeroing and margin release
    init_s110 = create_state("u_s110", 10000.0)
    init_s110.open_positions.append(PositionLot("lot_s110", "0xcond_zero_res", "Yes", "BUY", 0.50, 200.0, 100.0, 3.60, "FILLED", "u_s110"))
    init_s110.open_margin_usd = 100.0
    init_s110.free_cash_usd = 9900.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S110_ZERO_PRICE_RESOLUTION_AUDIT",
            title="Zero-Price Resolution Full Audit and Margin Clean-up",
            tier="Tier 2: Timing/Network",
            description="Tests full liquidation at $0.001 floor, confirming 0 orphaned lots and exact cash invariance",
            initial_state=init_s110,
            events=[create_event("evt_s110_res", "0xcond_zero_res", "SELL", 0.001, 100.0, event_type="RESOLUTION_PAYOUT")],
        )
    )

    return scenarios


# ============================================================================
# PYTEST TEST CASES
# ============================================================================

ALL_TIER_2_SCENARIOS = build_network_timing_scenarios()


def test_tier_2_scenario_count():
    """Verify exactly 55 scenarios are defined in Tier 2 suite."""
    assert len(ALL_TIER_2_SCENARIOS) == 55, f"Expected 55 scenarios, got {len(ALL_TIER_2_SCENARIOS)}"


@pytest.mark.parametrize("scenario", ALL_TIER_2_SCENARIOS, ids=lambda s: s.scenario_id)
def test_individual_network_timing_scenario(runner: ScenarioRunner, scenario: ScenarioDefinition):
    """Executes each of the 55 Network & Timing scenarios individually against InvariantMonitor."""
    result = runner.run_scenario(scenario)
    assert result.passed is True, (
        f"Scenario {scenario.scenario_id} failed with {len(result.violations)} violations: "
        f"{[v.message for v in result.violations]}"
    )
    assert len(result.violations) == 0
    assert all(s.status == "PASS" for s in result.steps)


def test_tier_2_network_timing_aggregate_matrix(runner: ScenarioRunner):
    """Executes all 55 Network & Timing scenarios in batch matrix and produces summary."""
    report: ScenarioReport = runner.run_matrix(ALL_TIER_2_SCENARIOS)
    assert report.total_scenarios == 55
    assert report.passed_scenarios == 55
    assert report.failed_scenarios == 0
    assert report.total_violations == 0
    assert report.pass_rate_pct == 100.0
