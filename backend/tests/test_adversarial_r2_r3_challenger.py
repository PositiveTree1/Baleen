"""
Challenger 2 Empirical Verification:
Adversarial Stress Testing for Requirement 2 (Bayesian Sizing Bounds) & Requirement 3 (Timeframe Convergence).
"""

import pytest
import math
from datetime import datetime, timedelta
from sqlalchemy import select, delete

from app.sizing.sleeve_manager import SleeveManager
from app.models import PortfolioSnapshot, ExecutionLog, User
from app.database import SessionLocal, init_db
from app.services.mark_to_market import MarkToMarketService, _last_known_pnl, _live_price_cache
from app.api.execution_logs import get_portfolio_snapshots, get_portfolio_summary


# ============================================================================
# REQUIREMENT 2 (R2): BAYESIAN SIZING BOUNDS EMPIRICAL STRESS MATRIX
# ============================================================================

REALIZED_PNLS = [-1e9, -10000.0, -500.0, -100.0, -1.0, 0.0, 1.0, 100.0, 500.0, 10000.0, 1e9]
BALEEN_SCORES = [0.0, 20.0, 50.0, 80.0, 100.0]
LOW_SAMPLE_SIZES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
MID_HIGH_SAMPLE_SIZES = [15, 20, 35, 50, 75, 100, 500, 1000]
BASE_BUDGET = 1000.0


class TestR2EmpiricalBayesianSizing:
    """Exhaustive empirical testing across all 1,210 points in the parametric space."""

    @pytest.mark.parametrize("pnl", REALIZED_PNLS)
    @pytest.mark.parametrize("score", BALEEN_SCORES)
    @pytest.mark.parametrize("n", LOW_SAMPLE_SIZES)
    def test_low_sample_strict_10_percent_bound_matrix(self, pnl, score, n):
        """Invariant: For all N < 15, adjusted budget MUST be strictly within [.00, ,100.00] on base ,000.00."""
        adj = SleeveManager.calculate_adjusted_sleeve_budget(
            base_budget=BASE_BUDGET,
            copy_pnl_ema=pnl,
            baleen_score=score,
            trades_count=n
        )
        assert 900.0 <= adj <= 1100.0, (
            f"Invariant Violation: N={n}, PnL={pnl}, Score={score} produced budget=, "
            f"which is outside the required [.00, ,100.00] corridor!"
        )

    @pytest.mark.parametrize("pnl", REALIZED_PNLS)
    @pytest.mark.parametrize("score", BALEEN_SCORES)
    def test_c0_continuity_at_n15(self, pnl, score):
        """Verify C^0 continuity at boundary N=15 across all PnL and score shocks."""
        score_factor = (score / 80.0) if score > 0 else 1.0
        pnl_factor = (pnl / 500.0)
        raw_mult = max(0.30, min(1.50, score_factor + pnl_factor))

        expected_z_15 = 1.0 / 7.0
        expected_mult_15 = max(0.30, min(1.50, 1.0 + expected_z_15 * (raw_mult - 1.0)))
        expected_adj_15 = round(BASE_BUDGET * expected_mult_15, 2)

        actual_adj_15 = SleeveManager.calculate_adjusted_sleeve_budget(
            base_budget=BASE_BUDGET,
            copy_pnl_ema=pnl,
            baleen_score=score,
            trades_count=15
        )
        assert actual_adj_15 == expected_adj_15

        # Check neighborhood continuity delta: |adj(15) - adj(14)| and |adj(16) - adj(15)|
        adj_14 = SleeveManager.calculate_adjusted_sleeve_budget(BASE_BUDGET, pnl, score, trades_count=14)
        adj_16 = SleeveManager.calculate_adjusted_sleeve_budget(BASE_BUDGET, pnl, score, trades_count=16)

        delta_left = abs(actual_adj_15 - adj_14)
        delta_right = abs(adj_16 - actual_adj_15)
        assert delta_left <= 35.0, f"Excessive jump delta_left={delta_left} at N=15 for PnL={pnl}, Score={score}"
        assert delta_right <= 35.0, f"Excessive jump delta_right={delta_right} at N=15 for PnL={pnl}, Score={score}"

    @pytest.mark.parametrize("pnl", [-1e9, -5000.0, -500.0, -100.0])
    @pytest.mark.parametrize("score", [0.0, 20.0, 50.0])
    def test_monotonic_downward_progression_for_underperforming_whales(self, pnl, score):
        """As sample count N increases, underperforming whales must experience non-increasing budget."""
        all_sample_sizes = list(range(0, 101)) + [200, 500, 1000]
        prev_adj = 1100.0  # Upper bound
        for n in all_sample_sizes:
            curr_adj = SleeveManager.calculate_adjusted_sleeve_budget(BASE_BUDGET, pnl, score, trades_count=n)
            assert curr_adj <= prev_adj + 1e-6, (
                f"Monotonicity violation at N={n}: curr={curr_adj} > prev={prev_adj} (PnL={pnl}, score={score})"
            )
            prev_adj = curr_adj

        # Verify asymptotic expansion matches mathematical model at N=1000
        score_factor = (score / 80.0) if score > 0 else 1.0
        pnl_factor = (pnl / 500.0)
        raw_mult = max(0.30, min(1.50, score_factor + pnl_factor))
        z_1000 = (1.0 / 7.0) + (6.0 / 7.0) * (985.0 / (985.0 + 20.0))
        expected_adj_1000 = round(BASE_BUDGET * max(0.30, min(1.50, 1.0 + z_1000 * (raw_mult - 1.0))), 2)

        adj_1000 = SleeveManager.calculate_adjusted_sleeve_budget(BASE_BUDGET, pnl, score, trades_count=1000)
        assert adj_1000 == expected_adj_1000

    @pytest.mark.parametrize("pnl", [100.0, 500.0, 5000.0, 1e9])
    @pytest.mark.parametrize("score", [80.0, 100.0])
    def test_monotonic_upward_progression_for_profitable_whales(self, pnl, score):
        """As sample count N increases, high-performing whales must experience non-decreasing budget."""
        all_sample_sizes = list(range(0, 101)) + [200, 500, 1000]
        prev_adj = 900.0  # Lower bound
        for n in all_sample_sizes:
            curr_adj = SleeveManager.calculate_adjusted_sleeve_budget(BASE_BUDGET, pnl, score, trades_count=n)
            assert curr_adj >= prev_adj - 1e-6, (
                f"Monotonicity violation at N={n}: curr={curr_adj} < prev={prev_adj} (PnL={pnl}, score={score})"
            )
            prev_adj = curr_adj

        # Verify asymptotic expansion matches mathematical model at N=1000
        score_factor = (score / 80.0) if score > 0 else 1.0
        pnl_factor = (pnl / 500.0)
        raw_mult = max(0.30, min(1.50, score_factor + pnl_factor))
        z_1000 = (1.0 / 7.0) + (6.0 / 7.0) * (985.0 / (985.0 + 20.0))
        expected_adj_1000 = round(BASE_BUDGET * max(0.30, min(1.50, 1.0 + z_1000 * (raw_mult - 1.0))), 2)

        adj_1000 = SleeveManager.calculate_adjusted_sleeve_budget(BASE_BUDGET, pnl, score, trades_count=1000)
        assert adj_1000 == expected_adj_1000

    @pytest.mark.parametrize("shock_pnl", [-1e9, -1e6, -10000.0, -501.0, -500.0, -499.0, 0.0, 499.0, 500.0, 501.0, 10000.0, 1e6, 1e9])
    def test_ema_single_trade_innovation_clipping_bounds(self, shock_pnl):
        """Verify update_copy_pnl_ema bounds single-trade innovation to +/-  * alpha = .00."""
        alpha = 0.05
        max_clip = 500.0
        current_ema = 100.0

        new_ema = SleeveManager.update_copy_pnl_ema(current_ema, shock_pnl, alpha=alpha, max_trade_pnl_clip=max_clip)

        expected_clamped = max(-500.0, min(500.0, shock_pnl))
        expected_new_ema = round((1.0 - alpha) * current_ema + alpha * expected_clamped, 4)
        assert new_ema == expected_new_ema

    def test_consecutive_catastrophic_shocks_on_uncalibrated_whale(self):
        """Simulate 10 consecutive -^9 losses on an uncalibrated whale (N=1..10)."""
        ema = 0.0
        for trade_num in range(1, 11):
            ema = SleeveManager.update_copy_pnl_ema(ema, -1e9, alpha=0.05)
            adj = SleeveManager.calculate_adjusted_sleeve_budget(
                base_budget=1000.0,
                copy_pnl_ema=ema,
                baleen_score=80.0,
                trades_count=trade_num
            )
            # Must NEVER breach [.00, ,100.00]
            assert 900.0 <= adj <= 1100.0, f"Breached at trade {trade_num}: adj={adj}, ema={ema}"


# ============================================================================
# REQUIREMENT 3 (R3): TIMEFRAME SNAPSHOT CONVERGENCE EMPIRICAL STRESS
# ============================================================================

class TestR3EmpiricalSnapshotConvergence:
    """Empirical verification of timeframe snapshot convergence and zero balance jumps."""

    @pytest.mark.asyncio
    async def test_multi_timeframe_endpoint_alignment_and_zero_jump(self):
        """
        Generates a 30-day rich synthetic portfolio history and verifies:
        1. 1H, 1D, 1W, ALL all return valid trajectories.
        2. All timeframes terminate at the exact identical current balance.
        3. No temporal glitches or cold cache artifacts.
        """
        await init_db()
        now = datetime.utcnow()

        async with SessionLocal() as db:
            await db.execute(delete(PortfolioSnapshot))
            await db.execute(delete(ExecutionLog))
            await db.execute(delete(User).where(User.email == "r3_adversary@test.com"))

            # Populate 500 snapshots across 30 days (1 snap per ~86 minutes)
            # Balance follows a realistic non-linear trajectory from 10,000 to 12,450.75
            snapshots = []
            for i in range(500):
                ts = now - timedelta(days=30) + timedelta(minutes=i * 86.4)
                t_norm = i / 499.0
                bal = round(10000.0 + 2000.0 * math.sin(t_norm * math.pi) + 450.75 * t_norm, 2)
                pnl = round(bal - 10000.0, 2)
                snapshots.append(PortfolioSnapshot(
                    user_id=None,
                    timestamp=ts,
                    balance=bal,
                    total_pnl=pnl,
                    active_trades_count=int(3 + (i % 5))
                ))
            db.add_all(snapshots)
            await db.commit()

        # Query all 4 timeframes via API endpoint
        async with SessionLocal() as db:
            snaps_1h = await get_portfolio_snapshots(timeframe="1h", db=db)
            snaps_1d = await get_portfolio_snapshots(timeframe="1d", db=db)
            snaps_1w = await get_portfolio_snapshots(timeframe="1w", db=db)
            snaps_all = await get_portfolio_snapshots(timeframe="all", db=db)
            summary = await get_portfolio_summary(timeframe="all", db=db)

        # 1. Verification of Non-Empty Results
        assert len(snaps_1h) >= 1, "1H timeframe returned empty"
        assert len(snaps_1d) >= 1, "1D timeframe returned empty"
        assert len(snaps_1w) >= 1, "1W timeframe returned empty"
        assert len(snaps_all) >= 1, "ALL timeframe returned empty"

        # 2. Terminal Convergence Verification (ZERO BALANCE JUMPS)
        terminal_1h = snaps_1h[-1]["balance"]
        terminal_1d = snaps_1d[-1]["balance"]
        terminal_1w = snaps_1w[-1]["balance"]
        terminal_all = snaps_all[-1]["balance"]
        summary_bal = summary["currentBalance"]

        assert terminal_1h == terminal_1d, f"1H ({terminal_1h}) != 1D ({terminal_1d})"
        assert terminal_1d == terminal_1w, f"1D ({terminal_1d}) != 1W ({terminal_1w})"
        assert terminal_1w == terminal_all, f"1W ({terminal_1w}) != ALL ({terminal_all})"
        assert terminal_all == summary_bal, f"ALL ({terminal_all}) != Summary ({summary_bal})"

        # 3. Genesis Baseline for ALL timeframe
        assert snaps_all[0]["balance"] == 10000.0, f"ALL genesis point must be 10,000.00, got {snaps_all[0]['balance']}"

        # 4. Monotonic Chronological Order
        for name, snap_list in [("1H", snaps_1h), ("1D", snaps_1d), ("1W", snaps_1w), ("ALL", snaps_all)]:
            timestamps = [datetime.fromisoformat(s["timestamp"].replace("Z", "")) for s in snap_list]
            for idx in range(1, len(timestamps)):
                assert timestamps[idx] >= timestamps[idx-1], (
                    f"{name} timeframe not monotonic at index {idx}: {timestamps[idx]} < {timestamps[idx-1]}"
                )

    @pytest.mark.asyncio
    async def test_cold_cache_and_database_restart_resilience(self):
        """
        Simulate severe cold cache (empty _last_known_pnl, empty _live_price_cache)
        and verify that MTM does NOT collapse portfolio balance.
        """
        mtm = MarkToMarketService()
        now = datetime.utcnow()

        # Insert a historical snapshot with balance ,500.00
        async with SessionLocal() as db:
            await db.execute(delete(PortfolioSnapshot))
            await db.execute(delete(ExecutionLog))
            db.add(PortfolioSnapshot(
                user_id=None,
                timestamp=now - timedelta(hours=2),
                balance=13500.0,
                total_pnl=3500.0,
                active_trades_count=5
            ))
            await db.commit()

        # Wipe memory caches
        _last_known_pnl.clear()
        _live_price_cache.clear()

        # Run watchdog gap continuity check
        await mtm._ensure_snapshot_continuity()

        # Verify balance was preserved from last good snapshot
        async with SessionLocal() as db:
            stmt = select(PortfolioSnapshot).where(PortfolioSnapshot.user_id.is_(None)).order_by(PortfolioSnapshot.timestamp.desc())
            latest = (await db.execute(stmt)).scalars().first()
            assert latest is not None
            assert latest.balance == 13500.0
            assert latest.total_pnl == 3500.0
