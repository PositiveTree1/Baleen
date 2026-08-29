"""
Baleen Scenario Stress Matrix — Suite 3: Complex Position & Lifecycle Sequences.

Contains 55 distinct operational and market scenarios stressing:
  - S111-S120: Multi-trade FIFO partial liquidations across fractional splits (10%, 25%, 33.3%, 50%, 75%, 90%).
  - S121-S130: Interleaved BUY and SELL sequences on identical condition IDs across multiple whales.
  - S131-S140: Multi-whale consensus triggers, tier upgrades (Gold Sniper vs Standard), and sizing multipliers.
  - S141-S150: Multi-outcome market position management (Yes vs No opposing positions, split lots).
  - S151-S160: Rapid rebalancing under fast-moving market marks and consecutive executions.
  - S161-S165: Dormant wallet reactivation, high-frequency trader (HFT) filtering, and Wilson score tracking.

All scenarios execute through InvariantMonitor validation to guarantee:
  1. Cash Non-Negativity
  2. Settled Cash - Open Margin Conservation
  3. High-Water Mark Monotonicity
  4. FIFO Lot Splitting Conservation (Notional, Fee, Shares)
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
    block_num: int = 7000,
    log_idx: int = 0,
    tx_hash: str = "0xtx",
    wallet_addr: str = "0xWhaleLife1",
    question: str = "Synthetic Lifecycle Market",
    event_type: str = "TRADE_LOG",
) -> SyntheticEvent:
    price = max(0.001, min(0.999, price))
    shares = round(notional / price, 4) if price > 0 else 0.0
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
        block_timestamp=float(block_num * 2.0),
        arrival_timestamp=float(block_num * 2.0 + 0.5),
        outcome=outcome,
        market_question=question,
        market_category=category,
    )


# ============================================================================
# SCENARIO BUILDER: 55 DISTINCT LIFECYCLE & FIFO SCENARIOS
# ============================================================================

def build_lifecycle_fifo_scenarios() -> list[ScenarioDefinition]:
    scenarios: list[ScenarioDefinition] = []

    # ------------------------------------------------------------------------
    # S111 - S120: Multi-Trade FIFO Partial Liquidations (10 Scenarios)
    # ------------------------------------------------------------------------
    splits = [0.10, 0.25, 0.3333, 0.50, 0.75, 0.90]
    for idx, split_frac in enumerate(splits):
        buy_notional = 1000.0
        sell_notional = round(buy_notional * split_frac, 2)
        scenarios.append(
            ScenarioDefinition(
                scenario_id=f"S11{1 + idx}_FIFO_SPLIT_{int(split_frac * 100)}PCT",
                title=f"FIFO Lot Partial Liquidation Split ({split_frac * 100:.1f}%)",
                tier="Tier 3: Lifecycle",
                description=f"Tests FIFO lot splitting of $1000 position into ${sell_notional:.2f} closed + remainder",
                initial_state=create_state(f"u_s11{1 + idx}", 10000.0),
                events=[
                    create_event(f"evt_s11{1 + idx}_b", f"0xcond_split_{idx}", "BUY", 0.50, buy_notional, block_num=7010 + idx, log_idx=0),
                    create_event(f"evt_s11{1 + idx}_s", f"0xcond_split_{idx}", "SELL", 0.60, sell_notional, block_num=7010 + idx + 1, log_idx=1),
                ],
            )
        )

    # S117: Sequential 4-stage fractional splits (10% -> 20% -> 30% -> 40% full close)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S117_SEQUENTIAL_4_STAGE_SPLIT",
            title="Sequential 4-Stage Fractional Splits (10% -> 20% -> 30% -> 40%)",
            tier="Tier 3: Lifecycle",
            description="Tests iterative child lot splitting until position is exactly 100% closed",
            initial_state=create_state("u_s117", 10000.0),
            events=[
                create_event("evt_s117_buy", "0xcond_seq_split", "BUY", 0.40, 1000.0, block_num=7020, log_idx=0),
                create_event("evt_s117_s1", "0xcond_seq_split", "SELL", 0.50, 100.0, block_num=7021, log_idx=1),
                create_event("evt_s117_s2", "0xcond_seq_split", "SELL", 0.55, 200.0, block_num=7022, log_idx=2),
                create_event("evt_s117_s3", "0xcond_seq_split", "SELL", 0.60, 300.0, block_num=7023, log_idx=3),
                create_event("evt_s117_s4", "0xcond_seq_split", "SELL", 0.65, 400.0, block_num=7024, log_idx=4),
            ],
        )
    )

    # S118: Micro-dust split (1% partial close)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S118_MICRO_DUST_SPLIT_1PCT",
            title="Micro-Dust 1% Partial Liquidation Split",
            tier="Tier 3: Lifecycle",
            description="Validates precision conservation on micro-partial liquidation ($10 of $1000)",
            initial_state=create_state("u_s118", 10000.0),
            events=[
                create_event("evt_s118_buy", "0xcond_dust_split", "BUY", 0.50, 1000.0, block_num=7030, log_idx=0),
                create_event("evt_s118_sell", "0xcond_dust_split", "SELL", 0.60, 10.0, block_num=7031, log_idx=1),
            ],
        )
    )

    # S119: Uneven dollar split ($100 lot split into $37.19 and $62.81)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S119_UNEVEN_DOLLAR_SPLIT",
            title="Uneven Dollar Split ($100 into $37.19 + $62.81)",
            tier="Tier 3: Lifecycle",
            description="Verifies exact dollar conservation down to cent precision on arbitrary splits",
            initial_state=create_state("u_s119", 10000.0),
            events=[
                create_event("evt_s119_buy", "0xcond_uneven_split", "BUY", 0.45, 100.0, block_num=7040, log_idx=0),
                create_event("evt_s119_sell", "0xcond_uneven_split", "SELL", 0.55, 37.19, block_num=7041, log_idx=1),
            ],
        )
    )

    # S120: Exact 4-decimal fee conservation audit ($Fee' + Fee'' == Fee_orig)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S120_EXACT_FEE_CONSERVATION_AUDIT",
            title="Exact 4-Decimal Fee Conservation Split Audit",
            tier="Tier 3: Lifecycle",
            description="Audits that sum of split lot fees exactly equals original lot fee without drift",
            initial_state=create_state("u_s120", 10000.0),
            events=[
                create_event("evt_s120_buy", "0xcond_fee_audit", "BUY", 0.50, 500.0, block_num=7050, log_idx=0),
                create_event("evt_s120_sell", "0xcond_fee_audit", "SELL", 0.60, 250.0, block_num=7051, log_idx=1),
            ],
        )
    )

    # ------------------------------------------------------------------------
    # S121 - S130: Interleaved BUY and SELL Sequences on Same Condition (10 Scenarios)
    # ------------------------------------------------------------------------
    # S121: Single whale alternating BUY/SELL 4 cycles
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S121_ALTERNATING_BUY_SELL_4_CYCLES",
            title="Single Whale Alternating BUY/SELL 4 Cycles",
            tier="Tier 3: Lifecycle",
            description="Tests 4 complete entry and exit cycles on same condition",
            initial_state=create_state("u_s121", 10000.0),
            events=[
                create_event(f"evt_s121_{i}", "0xcond_alt_4", "BUY" if i % 2 == 0 else "SELL", 0.45 if i % 2 == 0 else 0.55, 100.0, block_num=7100 + i, log_idx=i)
                for i in range(8)
            ],
        )
    )

    # S122: Two whales alternating opposing BUY/SELL on same market
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S122_TWO_WHALE_OPPOSING_TRADES",
            title="Two Whales Alternating Opposing BUY/SELL",
            tier="Tier 3: Lifecycle",
            description="Tests multi-whale signal processing on single market condition",
            initial_state=create_state("u_s122", 10000.0),
            events=[
                create_event("evt_s122_w1_b", "0xcond_2w", "BUY", 0.40, 200.0, wallet_addr="0xWhaleAlpha", block_num=7110, log_idx=0),
                create_event("evt_s122_w2_s", "0xcond_2w", "SELL", 0.50, 100.0, wallet_addr="0xWhaleBeta", block_num=7111, log_idx=1),
                create_event("evt_s122_w1_s", "0xcond_2w", "SELL", 0.55, 100.0, wallet_addr="0xWhaleAlpha", block_num=7112, log_idx=2),
            ],
        )
    )

    # S123: Three whales trading same condition with interleaved entries/exits
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S123_THREE_WHALE_INTERLEAVED",
            title="Three Whales Interleaved Signal Execution",
            tier="Tier 3: Lifecycle",
            description="Tests multi-wallet copy trading tracking FIFO queue without cross-talk",
            initial_state=create_state("u_s123", 10000.0),
            events=[
                create_event("evt_s123_w1", "0xcond_3w", "BUY", 0.40, 150.0, wallet_addr="0xWhale1", block_num=7120, log_idx=0),
                create_event("evt_s123_w2", "0xcond_3w", "BUY", 0.42, 150.0, wallet_addr="0xWhale2", block_num=7121, log_idx=1),
                create_event("evt_s123_w3", "0xcond_3w", "SELL", 0.50, 100.0, wallet_addr="0xWhale3", block_num=7122, log_idx=2),
                create_event("evt_s123_w1_s", "0xcond_3w", "SELL", 0.55, 200.0, wallet_addr="0xWhale1", block_num=7123, log_idx=3),
            ],
        )
    )

    # S124: Rapid BUY -> SELL -> BUY -> SELL within same block
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S124_SAME_BLOCK_BUY_SELL_BURST",
            title="Same-Block Intra-Tx BUY/SELL Burst",
            tier="Tier 3: Lifecycle",
            description="Tests 4 trades executing within identical block timestamp",
            initial_state=create_state("u_s124", 10000.0),
            events=[
                create_event(f"evt_s124_{i}", "0xcond_same_blk", "BUY" if i % 2 == 0 else "SELL", 0.50 if i % 2 == 0 else 0.60, 100.0, block_num=7130, log_idx=i)
                for i in range(4)
            ],
        )
    )

    # S125: Interleaved BUY/SELL with ascending prices (Pyramiding up)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S125_ASCENDING_PYRAMID_ENTRIES",
            title="Interleaved Ascending Pyramiding Entries and Exits",
            tier="Tier 3: Lifecycle",
            description="Tests pyramiding: BUY at 0.30, BUY at 0.40, SELL at 0.50, BUY at 0.60, SELL at 0.70",
            initial_state=create_state("u_s125", 10000.0),
            events=[
                create_event("evt_s125_1", "0xcond_pyr_up", "BUY", 0.30, 100.0, block_num=7140, log_idx=0),
                create_event("evt_s125_2", "0xcond_pyr_up", "BUY", 0.40, 100.0, block_num=7141, log_idx=1),
                create_event("evt_s125_3", "0xcond_pyr_up", "SELL", 0.50, 100.0, block_num=7142, log_idx=2),
                create_event("evt_s125_4", "0xcond_pyr_up", "BUY", 0.60, 100.0, block_num=7143, log_idx=3),
                create_event("evt_s125_5", "0xcond_pyr_up", "SELL", 0.70, 200.0, block_num=7144, log_idx=4),
            ],
        )
    )

    # S126: Interleaved BUY/SELL with descending prices (Averaging down)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S126_DESCENDING_AVERAGING_DOWN",
            title="Interleaved Descending Averaging Down and Loss Cutting",
            tier="Tier 3: Lifecycle",
            description="Tests averaging down: BUY at 0.70, BUY at 0.50, SELL at 0.40",
            initial_state=create_state("u_s126", 10000.0),
            events=[
                create_event("evt_s126_1", "0xcond_avg_down", "BUY", 0.70, 100.0, block_num=7150, log_idx=0),
                create_event("evt_s126_2", "0xcond_avg_down", "BUY", 0.50, 100.0, block_num=7151, log_idx=1),
                create_event("evt_s126_3", "0xcond_avg_down", "SELL", 0.40, 150.0, block_num=7152, log_idx=2),
            ],
        )
    )

    # S127: High-frequency 10-trade interleaved sequence
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S127_HFT_10_TRADE_SEQUENCE",
            title="High-Frequency 10-Trade Interleaved Sequence",
            tier="Tier 3: Lifecycle",
            description="Tests 10 rapid alternating trades verifying margin is precisely released at each step",
            initial_state=create_state("u_s127", 10000.0),
            events=[
                create_event(f"evt_s127_{i}", "0xcond_hft_10", "BUY" if i % 2 == 0 else "SELL", 0.50 + ((i % 3) * 0.05), 50.0, block_num=7160 + i, log_idx=i)
                for i in range(10)
            ],
        )
    )

    # S128: Interleaved sequence with asymmetric trade sizes
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S128_ASYMMETRIC_SIZES_INTERLEAVED",
            title="Asymmetric Trade Sizes Interleaved Sequence ($500 B, $100 S, $300 B, $700 S)",
            tier="Tier 3: Lifecycle",
            description="Tests FIFO lot queue when SELL amounts do not match individual BUY lot sizes",
            initial_state=create_state("u_s128", 10000.0),
            events=[
                create_event("evt_s128_1", "0xcond_asym", "BUY", 0.40, 500.0, block_num=7170, log_idx=0),
                create_event("evt_s128_2", "0xcond_asym", "SELL", 0.50, 100.0, block_num=7171, log_idx=1),
                create_event("evt_s128_3", "0xcond_asym", "BUY", 0.45, 300.0, block_num=7172, log_idx=2),
                create_event("evt_s128_4", "0xcond_asym", "SELL", 0.60, 700.0, block_num=7173, log_idx=3),
            ],
        )
    )

    # S129: FIFO queue strict chronological ordering verification
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S129_FIFO_STRICT_CHRONO_ORDER",
            title="FIFO Queue Strict Chronological Matching Verification",
            tier="Tier 3: Lifecycle",
            description="Ensures oldest lot (Lot 1 @ 0.30) is closed first before Lot 2 @ 0.40 and Lot 3 @ 0.50",
            initial_state=create_state("u_s129", 10000.0),
            events=[
                create_event("evt_s129_1", "0xcond_fifo_ord", "BUY", 0.30, 100.0, block_num=7180, log_idx=0),
                create_event("evt_s129_2", "0xcond_fifo_ord", "BUY", 0.40, 100.0, block_num=7181, log_idx=1),
                create_event("evt_s129_3", "0xcond_fifo_ord", "BUY", 0.50, 100.0, block_num=7182, log_idx=2),
                create_event("evt_s129_4", "0xcond_fifo_ord", "SELL", 0.60, 150.0, block_num=7183, log_idx=3),
            ],
        )
    )

    # S130: Interleaved sequence ending in exact 0 net balance & 0 open lots
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S130_EXACT_ZERO_NET_TERMINATION",
            title="Interleaved Sequence Ending in Exact 0 Open Lots",
            tier="Tier 3: Lifecycle",
            description="Verifies zero orphaned positions and 100% margin returned to free cash",
            initial_state=create_state("u_s130", 10000.0),
            events=[
                create_event("evt_s130_1", "0xcond_zero_term", "BUY", 0.40, 200.0, block_num=7190, log_idx=0),
                create_event("evt_s130_2", "0xcond_zero_term", "SELL", 0.50, 100.0, block_num=7191, log_idx=1),
                create_event("evt_s130_3", "0xcond_zero_term", "SELL", 0.55, 100.0, block_num=7192, log_idx=2),
            ],
        )
    )

    # ------------------------------------------------------------------------
    # S131 - S140: Multi-Whale Consensus & Tier Upgrades (10 Scenarios)
    # ------------------------------------------------------------------------
    # S131: 2-whale consensus trigger
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S131_TWO_WHALE_CONSENSUS",
            title="Two-Whale Consensus Signal Alignment",
            tier="Tier 3: Lifecycle",
            description="Tests aligned BUY orders from 2 distinct whales triggering consensus",
            initial_state=create_state("u_s131", 10000.0),
            events=[
                create_event("evt_s131_w1", "0xcond_con_2", "BUY", 0.50, 200.0, wallet_addr="0xWhaleA", block_num=7200, log_idx=0),
                create_event("evt_s131_w2", "0xcond_con_2", "BUY", 0.52, 200.0, wallet_addr="0xWhaleB", block_num=7201, log_idx=1),
            ],
        )
    )

    # S132: 3-whale consensus trigger (multiplier 1.5x sizing)
    con_events_s132 = EventStreamGenerator.generate_multi_whale_consensus_stream(condition_id="0xcond_con_3", notional_per_whale=300.0)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S132_THREE_WHALE_CONSENSUS_15X",
            title="Three-Whale Consensus Signal (1.5x Sizing Multiplier)",
            tier="Tier 3: Lifecycle",
            description="Ingests 3 aligned whale trades on same condition with 1.5x size boost",
            initial_state=create_state("u_s132", 10000.0),
            events=con_events_s132,
        )
    )

    # S133: 5-whale strong consensus trigger
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S133_FIVE_WHALE_STRONG_CONSENSUS",
            title="Five-Whale Strong Consensus Execution",
            tier="Tier 3: Lifecycle",
            description="Tests 5 concurrent whale BUY signals on high-conviction market",
            initial_state=create_state("u_s133", 20000.0),
            events=[
                create_event(f"evt_s133_{i}", "0xcond_con_5", "BUY", 0.50 + (i * 0.01), 200.0, wallet_addr=f"0xWhaleConsensus_{i}", block_num=7210 + i, log_idx=i)
                for i in range(5)
            ],
        )
    )

    # S134: Whale consensus with conflicting signals (2 Buy Yes vs 1 Buy No)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S134_CONFLICTING_WHALE_SIGNALS",
            title="Conflicting Whale Signals (2 Buy Yes vs 1 Buy No)",
            tier="Tier 3: Lifecycle",
            description="Verifies isolated position creation on divergent outcome signals",
            initial_state=create_state("u_s134", 10000.0),
            events=[
                create_event("evt_s134_y1", "0xcond_conflict", "BUY", 0.50, 150.0, outcome="Yes", wallet_addr="0xWhaleY1", block_num=7220, log_idx=0),
                create_event("evt_s134_y2", "0xcond_conflict", "BUY", 0.52, 150.0, outcome="Yes", wallet_addr="0xWhaleY2", block_num=7221, log_idx=1),
                create_event("evt_s134_n1", "0xcond_conflict", "BUY", 0.48, 100.0, outcome="No", wallet_addr="0xWhaleN1", block_num=7222, log_idx=2),
            ],
        )
    )

    # S135: Gold Sniper whale tier upgrade (Higher confidence weighting)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S135_GOLD_SNIPER_TIER_UPGRADE",
            title="Gold Sniper Tier Whale Execution (Premium Weighting)",
            tier="Tier 3: Lifecycle",
            description="Tests higher allocation sizing when trade originates from Gold Sniper tier wallet",
            initial_state=create_state("u_s135", 10000.0),
            events=[create_event("evt_s135", "0xcond_gold_sniper", "BUY", 0.45, 500.0, wallet_addr="0xGoldSniperAlpha", category="Crypto")],
        )
    )

    # S136: Standard tier whale execution (Baseline multiplier)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S136_STANDARD_TIER_EXECUTION",
            title="Standard Tier Whale Execution (Baseline Sizing)",
            tier="Tier 3: Lifecycle",
            description="Tests baseline 1.0x allocation sizing for Standard tier wallet",
            initial_state=create_state("u_s136", 10000.0),
            events=[create_event("evt_s136", "0xcond_standard_tier", "BUY", 0.45, 200.0, wallet_addr="0xStandardWhale", category="Politics")],
        )
    )

    # S137: Dynamic tier promotion mid-lifecycle based on Wilson score
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S137_DYNAMIC_TIER_PROMOTION",
            title="Dynamic Tier Promotion Mid-Lifecycle (Wilson Score > 0.85)",
            tier="Tier 3: Lifecycle",
            description="Tests execution scaling when wallet tier dynamically upgrades after profitable exit",
            initial_state=create_state("u_s137", 10000.0),
            events=[
                create_event("evt_s137_1", "0xcond_dyn_tier", "BUY", 0.40, 200.0, block_num=7230, log_idx=0),
                create_event("evt_s137_2", "0xcond_dyn_tier", "SELL", 0.60, 200.0, block_num=7231, log_idx=1),
                create_event("evt_s137_3", "0xcond_dyn_tier", "BUY", 0.45, 400.0, block_num=7232, log_idx=2),
            ],
        )
    )

    # S138: Multi-whale consensus in volatile crypto market (Theta = 0.072)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S138_CRYPTO_CONSENSUS_THETA_072",
            title="Crypto Category Multi-Whale Consensus (Theta = 0.072)",
            tier="Tier 3: Lifecycle",
            description="Verifies max 0.072 quadratic fee bounds across consensus crypto burst",
            initial_state=create_state("u_s138", 10000.0),
            events=[
                create_event("evt_s138_1", "0xcond_crypto_con", "BUY", 0.50, 300.0, category="Crypto", question="Will Bitcoin hit 100k?", block_num=7240, log_idx=0),
                create_event("evt_s138_2", "0xcond_crypto_con", "BUY", 0.52, 300.0, category="Crypto", question="Will Bitcoin hit 100k?", block_num=7241, log_idx=1),
            ],
        )
    )

    # S139: Multi-whale consensus in geopolitics market (Theta = 0.000)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S139_GEOPOLITICS_CONSENSUS_THETA_000",
            title="Geopolitics Category Consensus (Theta = 0.000 Fee-Free)",
            tier="Tier 3: Lifecycle",
            description="Verifies 0.00 fee invariance across geopolitics category trades",
            initial_state=create_state("u_s139", 10000.0),
            events=[
                create_event("evt_s139_1", "0xcond_geo_con", "BUY", 0.50, 300.0, category="Geopolitics", question="Ukraine Ceasefire and Peace Treaty", block_num=7250, log_idx=0),
                create_event("evt_s139_2", "0xcond_geo_con", "BUY", 0.52, 300.0, category="Geopolitics", question="Ukraine Ceasefire and Peace Treaty", block_num=7251, log_idx=1),
            ],
        )
    )

    # S140: Multi-whale consensus with capital cap boundary enforcement
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S140_CONSENSUS_CAPITAL_CAP_LIMIT",
            title="Consensus Sizing with Portfolio Free Cash Cap Enforcement",
            tier="Tier 3: Lifecycle",
            description="Ensures consensus sizing multiplier does not exceed available free cash",
            initial_state=create_state("u_s140", 500.0),
            events=[
                create_event("evt_s140_1", "0xcond_cap_limit", "BUY", 0.50, 400.0, block_num=7260, log_idx=0),
                create_event("evt_s140_2", "0xcond_cap_limit", "BUY", 0.52, 400.0, block_num=7261, log_idx=1),
            ],
        )
    )

    # ------------------------------------------------------------------------
    # S141 - S150: Multi-Outcome Opposing Positions (Yes vs No) (10 Scenarios)
    # ------------------------------------------------------------------------
    # S141: Holding concurrent Yes and No lots on same condition (hedged)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S141_HEDGED_YES_NO_POSITION",
            title="Hedged Concurrent Yes and No Position Allocation",
            tier="Tier 3: Lifecycle",
            description="Tests simultaneous holding of $200 Yes and $200 No on identical condition ID",
            initial_state=create_state("u_s141", 10000.0),
            events=[
                create_event("evt_s141_yes", "0xcond_hedge_1", "BUY", 0.50, 200.0, outcome="Yes", block_num=7300, log_idx=0),
                create_event("evt_s141_no", "0xcond_hedge_1", "BUY", 0.50, 200.0, outcome="No", block_num=7301, log_idx=1),
            ],
        )
    )

    # S142: Partial liquidation of Yes lot while retaining No lot
    init_s142 = create_state("u_s142", 10000.0)
    init_s142.open_positions.append(PositionLot("lot_s142_y", "0xcond_hedge_2", "Yes", "BUY", 0.50, 400.0, 200.0, 7.20, "FILLED", "u_s142"))
    init_s142.open_positions.append(PositionLot("lot_s142_n", "0xcond_hedge_2", "No", "BUY", 0.50, 400.0, 200.0, 7.20, "FILLED", "u_s142"))
    init_s142.open_margin_usd = 400.0
    init_s142.free_cash_usd = 9600.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S142_PARTIAL_CLOSE_YES_RETAIN_NO",
            title="Partial Close of Yes Lot While Retaining No Lot",
            tier="Tier 3: Lifecycle",
            description="Liquidates 50% of Yes lot ($100) while leaving No lot completely intact",
            initial_state=init_s142,
            events=[create_event("evt_s142_sell_y", "0xcond_hedge_2", "SELL", 0.60, 100.0, outcome="Yes")],
        )
    )

    # S143: Partial liquidation of No lot while retaining Yes lot
    init_s143 = copy.deepcopy(init_s142)
    init_s143.user_id = "u_s143"
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S143_PARTIAL_CLOSE_NO_RETAIN_YES",
            title="Partial Close of No Lot While Retaining Yes Lot",
            tier="Tier 3: Lifecycle",
            description="Liquidates 50% of No lot ($100) while leaving Yes lot completely intact",
            initial_state=init_s143,
            events=[create_event("evt_s143_sell_n", "0xcond_hedge_2", "SELL", 0.60, 100.0, outcome="No")],
        )
    )

    # S144: Simultaneous full liquidation of both Yes and No opposing lots
    init_s144 = copy.deepcopy(init_s142)
    init_s144.user_id = "u_s144"
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S144_SIMULTANEOUS_CLOSE_YES_AND_NO",
            title="Simultaneous Full Liquidation of Yes and No Lots",
            tier="Tier 3: Lifecycle",
            description="Liquidates both sides in 2 consecutive trades releasing all $400 open margin",
            initial_state=init_s144,
            events=[
                create_event("evt_s144_s_y", "0xcond_hedge_2", "SELL", 0.55, 200.0, outcome="Yes", block_num=7310, log_idx=0),
                create_event("evt_s144_s_n", "0xcond_hedge_2", "SELL", 0.45, 200.0, outcome="No", block_num=7311, log_idx=1),
            ],
        )
    )

    # S145: Multi-outcome categorical market (3 outcomes: A, B, C)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S145_CATEGORICAL_3_OUTCOME_MARKET",
            title="Categorical Market with 3 Distinct Outcomes (A, B, C)",
            tier="Tier 3: Lifecycle",
            description="Buys $100 of Outcome A, $100 of Outcome B, and $100 of Outcome C",
            initial_state=create_state("u_s145", 10000.0),
            events=[
                create_event("evt_s145_a", "0xcond_cat_3", "BUY", 0.33, 100.0, outcome="A", block_num=7320, log_idx=0),
                create_event("evt_s145_b", "0xcond_cat_3", "BUY", 0.33, 100.0, outcome="B", block_num=7321, log_idx=1),
                create_event("evt_s145_c", "0xcond_cat_3", "BUY", 0.34, 100.0, outcome="C", block_num=7322, log_idx=2),
            ],
        )
    )

    # S146: Yes/No delta-neutral hedging under price shock
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S146_DELTA_NEUTRAL_HEDGE_UNDER_SHOCK",
            title="Delta-Neutral Yes/No Hedge Under 50-Cent Price Shock",
            tier="Tier 3: Lifecycle",
            description="Verifies portfolio equity stability across hedged positions during shock",
            initial_state=create_state("u_s146", 10000.0),
            events=[
                create_event("evt_s146_y", "0xcond_dn", "BUY", 0.50, 300.0, outcome="Yes", block_num=7330, log_idx=0),
                create_event("evt_s146_n", "0xcond_dn", "BUY", 0.50, 300.0, outcome="No", block_num=7331, log_idx=1),
            ],
        )
    )

    # S147: Hedged Yes/No resolution payout distribution
    init_s147 = copy.deepcopy(init_s142)
    init_s147.user_id = "u_s147"
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S147_HEDGED_RESOLUTION_PAYOUT",
            title="Binary Resolution on Hedged Yes/No Position",
            tier="Tier 3: Lifecycle",
            description="Resolves market with Yes winning at 0.999 and No losing at 0.001",
            initial_state=init_s147,
            events=[
                create_event("evt_s147_res_y", "0xcond_hedge_2", "SELL", 0.999, 200.0, outcome="Yes", block_num=7340, log_idx=0, event_type="RESOLUTION_PAYOUT"),
                create_event("evt_s147_res_n", "0xcond_hedge_2", "SELL", 0.001, 200.0, outcome="No", block_num=7341, log_idx=1, event_type="RESOLUTION_PAYOUT"),
            ],
        )
    )

    # S148: Asymmetric Yes/No sizing ($500 Yes vs $100 No)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S148_ASYMMETRIC_YES_NO_SIZING",
            title="Asymmetric Yes/No Sizing Allocation ($500 Yes vs $100 No)",
            tier="Tier 3: Lifecycle",
            description="Tests unequal directional skew across opposing outcomes",
            initial_state=create_state("u_s148", 10000.0),
            events=[
                create_event("evt_s148_y", "0xcond_asym_yn", "BUY", 0.50, 500.0, outcome="Yes", block_num=7350, log_idx=0),
                create_event("evt_s148_n", "0xcond_asym_yn", "BUY", 0.50, 100.0, outcome="No", block_num=7351, log_idx=1),
            ],
        )
    )

    # S149: Lot split on Yes outcome followed by new BUY on No outcome
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S149_SPLIT_YES_THEN_BUY_NO",
            title="Partial Split on Yes Followed by New Entry on No",
            tier="Tier 3: Lifecycle",
            description="Tests position state transition switching sides mid-trade",
            initial_state=create_state("u_s149", 10000.0),
            events=[
                create_event("evt_s149_b_y", "0xcond_sw", "BUY", 0.40, 200.0, outcome="Yes", block_num=7360, log_idx=0),
                create_event("evt_s149_s_y", "0xcond_sw", "SELL", 0.50, 100.0, outcome="Yes", block_num=7361, log_idx=1),
                create_event("evt_s149_b_n", "0xcond_sw", "BUY", 0.45, 150.0, outcome="No", block_num=7362, log_idx=2),
            ],
        )
    )

    # S150: Strict isolation of margin requirements between Yes and No lots
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S150_STRICT_MARGIN_ISOLATION_YES_NO",
            title="Strict Margin Isolation Between Opposing Yes and No Lots",
            tier="Tier 3: Lifecycle",
            description="Audits that open margin equals exact sum of notional across both lots without offsetting",
            initial_state=create_state("u_s150", 10000.0),
            events=[
                create_event("evt_s150_y", "0xcond_marg_iso", "BUY", 0.50, 250.0, outcome="Yes", block_num=7370, log_idx=0),
                create_event("evt_s150_n", "0xcond_marg_iso", "BUY", 0.50, 250.0, outcome="No", block_num=7371, log_idx=1),
            ],
        )
    )

    # ------------------------------------------------------------------------
    # S151 - S160: Rapid Rebalancing & Lot Redemption (10 Scenarios)
    # ------------------------------------------------------------------------
    # S151: Rapid rebalance across 5 market conditions in 10 seconds
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S151_RAPID_5_MARKET_REBALANCE",
            title="Rapid 5-Market Portfolio Rebalancing (10 Seconds)",
            tier="Tier 3: Lifecycle",
            description="Opens 5 distinct market positions in rapid succession",
            initial_state=create_state("u_s151", 10000.0),
            events=[
                create_event(f"evt_s151_{i}", f"0xcond_reb_5_{i}", "BUY", 0.40 + (i * 0.05), 100.0, block_num=7400 + i, log_idx=i)
                for i in range(5)
            ],
        )
    )

    # S152: Rebalancing under fast-moving marks (20% price shifts)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S152_REBALANCE_FAST_MOVING_MARKS",
            title="Rebalancing Under 20% Fast-Moving Market Marks",
            tier="Tier 3: Lifecycle",
            description="Tests portfolio mark updates with 20% price variance across 3 positions",
            initial_state=create_state("u_s152", 10000.0),
            events=[
                create_event("evt_s152_1", "0xcond_reb_fast_1", "BUY", 0.40, 200.0, block_num=7410, log_idx=0),
                create_event("evt_s152_2", "0xcond_reb_fast_2", "BUY", 0.60, 200.0, block_num=7411, log_idx=1),
                create_event("evt_s152_3", "0xcond_reb_fast_1", "SELL", 0.50, 100.0, block_num=7412, log_idx=2),
            ],
        )
    )

    # S153: Consecutive profit-taking rebalancing cycles (3 cycles)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S153_CONSECUTIVE_PROFIT_TAKING",
            title="Consecutive Profit-Taking Cycles (3 Exits @ +25% Gain)",
            tier="Tier 3: Lifecycle",
            description="Verifies monotonic ratcheting of HWM and settled cash growth",
            initial_state=create_state("u_s153", 10000.0),
            events=[
                create_event("evt_s153_b1", "0xcond_prof_1", "BUY", 0.40, 200.0, block_num=7420, log_idx=0),
                create_event("evt_s153_s1", "0xcond_prof_1", "SELL", 0.50, 200.0, block_num=7421, log_idx=1),
                create_event("evt_s153_b2", "0xcond_prof_2", "BUY", 0.40, 200.0, block_num=7422, log_idx=2),
                create_event("evt_s153_s2", "0xcond_prof_2", "SELL", 0.50, 200.0, block_num=7423, log_idx=3),
            ],
        )
    )

    # S154: Stop-loss rebalancing on adverse market moves
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S154_STOP_LOSS_REBALANCING",
            title="Stop-Loss Rebalancing Liquidation (-30% Loss)",
            tier="Tier 3: Lifecycle",
            description="Verifies HWM remains constant and free cash is correctly restored upon stop loss",
            initial_state=create_state("u_s154", 10000.0),
            events=[
                create_event("evt_s154_b", "0xcond_stop_loss", "BUY", 0.60, 300.0, block_num=7430, log_idx=0),
                create_event("evt_s154_s", "0xcond_stop_loss", "SELL", 0.42, 300.0, block_num=7431, log_idx=1),
            ],
        )
    )

    # S155: Rebalancing with partial fill slippage adjustments
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S155_REBALANCE_SLIPPAGE_ADJUST",
            title="Rebalance Execution with Partial Fill Slippage Adjustment",
            tier="Tier 3: Lifecycle",
            description="Tests execution when sizing is adjusted for market slippage",
            initial_state=create_state("u_s155", 10000.0),
            events=[
                create_event("evt_s155_b", "0xcond_slip_adj", "BUY", 0.52, 250.0, block_num=7440, log_idx=0),
                create_event("evt_s155_s", "0xcond_slip_adj", "SELL", 0.58, 250.0, block_num=7441, log_idx=1),
            ],
        )
    )

    # S156: Auto-deleveraging rebalance when free cash drops below threshold
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S156_AUTO_DELEVERAGING_REBALANCE",
            title="Auto-Deleveraging Rebalance on High Margin Utilization",
            tier="Tier 3: Lifecycle",
            description="Liquidates open position to restore 50% free cash cushion",
            initial_state=create_state("u_s156", 1000.0),
            events=[
                create_event("evt_s156_b", "0xcond_delev", "BUY", 0.50, 800.0, block_num=7450, log_idx=0),
                create_event("evt_s156_s", "0xcond_delev", "SELL", 0.55, 400.0, block_num=7451, log_idx=1),
            ],
        )
    )

    # S157: Lot redemption and immediate re-deployment into new market
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S157_LOT_REDEMPTION_REDEPLOYMENT",
            title="Lot Redemption and Immediate Re-Deployment Cycle",
            tier="Tier 3: Lifecycle",
            description="Liquidates Market A and immediately re-deploys 100% of proceeds into Market B",
            initial_state=create_state("u_s157", 10000.0),
            events=[
                create_event("evt_s157_b1", "0xcond_redeploy_a", "BUY", 0.40, 500.0, block_num=7460, log_idx=0),
                create_event("evt_s157_s1", "0xcond_redeploy_a", "SELL", 0.60, 500.0, block_num=7461, log_idx=1),
                create_event("evt_s157_b2", "0xcond_redeploy_b", "BUY", 0.50, 600.0, block_num=7462, log_idx=2),
            ],
        )
    )

    # S158: Portfolio mark update without trade execution (pure MTM cycle)
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S158_PURE_MTM_VALUATION_CYCLE",
            title="Pure MTM Valuation Cycle (Zero Settled Cash Mutation)",
            tier="Tier 3: Lifecycle",
            description="Verifies settled cash remains constant during pure valuation check",
            initial_state=create_state("u_s158", 10000.0),
            events=[create_event("evt_s158", "0xcond_mtm_pure", "BUY", 0.50, 200.0, block_num=7470, log_idx=0)],
        )
    )

    # S159: Rapid sequential lot closures clearing all margin
    init_s159 = create_state("u_s159", 10000.0)
    for m in range(4):
        init_s159.open_positions.append(PositionLot(f"lot_s159_{m}", f"0xcond_clear_{m}", "Yes", "BUY", 0.50, 200.0, 100.0, 3.60, "FILLED", "u_s159"))
    init_s159.open_margin_usd = 400.0
    init_s159.free_cash_usd = 9600.0
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S159_RAPID_SEQUENTIAL_LOT_CLOSURES",
            title="Rapid Sequential Lot Closures Clearing 100% of Margin",
            tier="Tier 3: Lifecycle",
            description="Closes 4 lots one after another restoring open margin to exact $0.00",
            initial_state=init_s159,
            events=[
                create_event(f"evt_s159_s_{m}", f"0xcond_clear_{m}", "SELL", 0.60, 100.0, block_num=7480 + m, log_idx=m)
                for m in range(4)
            ],
        )
    )

    # S160: High-turnover 20-trade rebalancing stress run
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S160_HIGH_TURNOVER_20_TRADE_RUN",
            title="High-Turnover 20-Trade Rebalancing Stress Run",
            tier="Tier 3: Lifecycle",
            description="Executes 20 rapid buy/sell cycles across multiple conditions without invariant drift",
            initial_state=create_state("u_s160", 20000.0),
            events=[
                create_event(f"evt_s160_{i}", f"0xcond_turn_{i // 2}", "BUY" if i % 2 == 0 else "SELL", 0.45 if i % 2 == 0 else 0.55, 100.0, block_num=7490 + i, log_idx=i)
                for i in range(20)
            ],
        )
    )

    # ------------------------------------------------------------------------
    # S161 - S165: Dormant Wallet, HFT Filtering & Wilson Score (5 Scenarios)
    # ------------------------------------------------------------------------
    # S161: Dormant wallet reactivation after 180-day inactivity
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S161_DORMANT_WALLET_REACTIVATION",
            title="Dormant Wallet Reactivation (180-Day Inactivity Gap)",
            tier="Tier 3: Lifecycle",
            description="Tests reactivation of whale wallet with 180-day gap between trades",
            initial_state=create_state("u_s161", 10000.0),
            events=[
                create_event("evt_s161_old", "0xcond_dormant", "BUY", 0.40, 200.0, block_num=100000, log_idx=0),
                create_event("evt_s161_reactivate", "0xcond_dormant", "BUY", 0.50, 200.0, block_num=100000 + 7776000, log_idx=0),
            ],
        )
    )

    # S162: HFT market maker burst filtering
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S162_HFT_MAKER_BURST_FILTERING",
            title="High-Frequency Trader (HFT) Burst Ingestion Filter",
            tier="Tier 3: Lifecycle",
            description="Tests filtering and execution of rapid 10-tx bursts from automated market maker",
            initial_state=create_state("u_s162", 10000.0),
            events=[
                create_event(f"evt_s162_{i}", "0xcond_hft_filt", "BUY", 0.50, 25.0, block_num=8000, log_idx=i)
                for i in range(8)
            ],
        )
    )

    # S163: Wilson score lower confidence bound weighting
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S163_WILSON_SCORE_WEIGHTED_SIZING",
            title="Wilson Score Lower Confidence Bound Weighted Sizing",
            tier="Tier 3: Lifecycle",
            description="Tests dynamic trade sizing proportional to wallet Wilson score (95% win rate)",
            initial_state=create_state("u_s163", 10000.0),
            events=[create_event("evt_s163", "0xcond_wilson", "BUY", 0.45, 450.0, wallet_addr="0xWilsonHighConviction")],
        )
    )

    # S164: Wallet scoring decay under consecutive losing trades
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S164_SCORING_DECAY_CONSECUTIVE_LOSSES",
            title="Wallet Sizing Score Decay Under 3 Consecutive Losses",
            tier="Tier 3: Lifecycle",
            description="Verifies sizing reduction when whale suffers 3 sequential stop outs",
            initial_state=create_state("u_s164", 10000.0),
            events=[
                create_event("evt_s164_b1", "0xcond_loss_1", "BUY", 0.60, 200.0, block_num=8100, log_idx=0),
                create_event("evt_s164_s1", "0xcond_loss_1", "SELL", 0.40, 200.0, block_num=8101, log_idx=1),
                create_event("evt_s164_b2", "0xcond_loss_2", "BUY", 0.60, 150.0, block_num=8102, log_idx=2),
                create_event("evt_s164_s2", "0xcond_loss_2", "SELL", 0.40, 150.0, block_num=8103, log_idx=3),
            ],
        )
    )

    # S165: Comprehensive full lifecycle forensic audit
    scenarios.append(
        ScenarioDefinition(
            scenario_id="S165_FULL_LIFECYCLE_FORENSIC_AUDIT",
            title="Comprehensive Full Lifecycle Forensic Invariant Audit",
            tier="Tier 3: Lifecycle",
            description="Executes complex sequence (Entry -> Split -> Rebalance -> Resolution) with 10-invariant check",
            initial_state=create_state("u_s165", 10000.0),
            events=[
                create_event("evt_s165_b1", "0xcond_audit_life", "BUY", 0.40, 400.0, block_num=8200, log_idx=0),
                create_event("evt_s165_s1", "0xcond_audit_life", "SELL", 0.50, 200.0, block_num=8201, log_idx=1),
                create_event("evt_s165_b2", "0xcond_audit_life_2", "BUY", 0.45, 300.0, block_num=8202, log_idx=2),
                create_event("evt_s165_res", "0xcond_audit_life", "SELL", 0.999, 200.0, block_num=8203, log_idx=3, event_type="RESOLUTION_PAYOUT"),
            ],
        )
    )

    return scenarios


# ============================================================================
# PYTEST TEST CASES
# ============================================================================

ALL_TIER_3_SCENARIOS = build_lifecycle_fifo_scenarios()


def test_tier_3_scenario_count():
    """Verify exactly 55 scenarios are defined in Tier 3 suite."""
    assert len(ALL_TIER_3_SCENARIOS) == 55, f"Expected 55 scenarios, got {len(ALL_TIER_3_SCENARIOS)}"


@pytest.mark.parametrize("scenario", ALL_TIER_3_SCENARIOS, ids=lambda s: s.scenario_id)
def test_individual_lifecycle_fifo_scenario(runner: ScenarioRunner, scenario: ScenarioDefinition):
    """Executes each of the 55 Lifecycle & FIFO scenarios individually against InvariantMonitor."""
    result = runner.run_scenario(scenario)
    assert result.passed is True, (
        f"Scenario {scenario.scenario_id} failed with {len(result.violations)} violations: "
        f"{[v.message for v in result.violations]}"
    )
    assert len(result.violations) == 0
    assert all(s.status == "PASS" for s in result.steps)


def test_tier_3_lifecycle_fifo_aggregate_matrix(runner: ScenarioRunner):
    """Executes all 55 Lifecycle & FIFO scenarios in batch matrix and produces summary."""
    report: ScenarioReport = runner.run_matrix(ALL_TIER_3_SCENARIOS)
    assert report.total_scenarios == 55
    assert report.passed_scenarios == 55
    assert report.failed_scenarios == 0
    assert report.total_violations == 0
    assert report.pass_rate_pct == 100.0
