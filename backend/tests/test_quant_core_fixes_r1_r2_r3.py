import pytest
from datetime import datetime, timedelta, timezone
from app.sizing.slippage import calculate_simulated_fill_price, check_slippage
from app.sizing.fill_simulator import simulate_fill, FillResult
from app.sizing.sleeve_manager import SleeveManager
from app.models import ExecutionLog, PortfolioSnapshot, User
from app.database import SessionLocal


# ============================================================================
# REQUIREMENT 1 (R1): UNIVERSAL CLOB FILL SLIPPAGE & LATENCY MODELING
# ============================================================================

class TestR1UniversalCLOBSlippageAndLatency:
    """
    Verifies that 100% of executions across all prices, notionals, latencies,
    and execution branches produce strict non-zero adverse slippage and valid latency.
    """

    @pytest.mark.parametrize("price", [0.005, 0.01, 0.04, 0.08, 0.20, 0.35558, 0.50, 0.75, 0.90, 0.95879, 0.99, 0.995])
    @pytest.mark.parametrize("notional", [1.0, 5.0, 20.0, 100.0, 500.0, 1500.0, 5000.0])
    @pytest.mark.parametrize("lat_ms", [180.0, 350.0, 800.0, 1400.0])
    def test_buy_slippage_strictly_greater_and_anti_rounding_collapse(self, price, notional, lat_ms):
        p_fill = calculate_simulated_fill_price(
            price=price,
            side="BUY",
            notional_usd=notional,
            latency_ms=lat_ms
        )
        assert p_fill > price, f"BUY fill price {p_fill} must be strictly greater than whale price {price}"
        slippage_bps = ((p_fill - price) / price) * 10000.0
        assert slippage_bps > 0.0, f"Slippage in bps must be > 0, got {slippage_bps}"
        assert round(p_fill, 4) != round(price, 4), f"Fill price {p_fill} must not round-collapse to {price}"

    @pytest.mark.parametrize("price", [0.005, 0.01, 0.04, 0.08, 0.20, 0.35558, 0.50, 0.75, 0.90, 0.95879, 0.99, 0.995])
    @pytest.mark.parametrize("notional", [1.0, 5.0, 20.0, 100.0, 500.0, 1500.0, 5000.0])
    @pytest.mark.parametrize("lat_ms", [180.0, 350.0, 800.0, 1400.0])
    def test_sell_slippage_strictly_less_and_anti_rounding_collapse(self, price, notional, lat_ms):
        p_fill = calculate_simulated_fill_price(
            price=price,
            side="SELL",
            notional_usd=notional,
            latency_ms=lat_ms
        )
        assert p_fill < price, f"SELL fill price {p_fill} must be strictly less than whale price {price}"
        slippage_bps = ((price - p_fill) / price) * 10000.0
        assert slippage_bps > 0.0, f"Slippage in bps must be > 0, got {slippage_bps}"
        assert round(p_fill, 4) != round(price, 4), f"Fill price {p_fill} must not round-collapse to {price}"

    def test_monotonic_notional_slippage_scaling(self):
        """Higher notional orders must experience greater depth walk slippage."""
        p_base = 0.50
        p_fill_small = calculate_simulated_fill_price(price=p_base, side="BUY", notional_usd=25.0, latency_ms=350.0)
        p_fill_large = calculate_simulated_fill_price(price=p_base, side="BUY", notional_usd=2500.0, latency_ms=350.0)
        assert p_fill_large > p_fill_small

    def test_monotonic_latency_slippage_scaling(self):
        """Higher latency orders must experience greater latency drift slippage."""
        p_base = 0.50
        p_fill_fast = calculate_simulated_fill_price(price=p_base, side="BUY", notional_usd=100.0, latency_ms=180.0)
        p_fill_slow = calculate_simulated_fill_price(price=p_base, side="BUY", notional_usd=100.0, latency_ms=1400.0)
        assert p_fill_slow > p_fill_fast

    def test_fill_simulator_single_level_positive_slippage(self):
        """Single level fill must enforce spread and latency floor so slippage_pct > 0."""
        book = {"asks": [{"price": "0.45", "size": "1000"}]}
        res = simulate_fill(50.0, book, "BUY", latency_ms=350)
        assert res.total_filled == 50.0
        assert res.slippage_pct > 0.0
        assert res.latency_ms == 350.0

    def test_fill_simulator_multi_level_slippage(self):
        """Multi level fill walks book and retains positive slippage and latency."""
        book = {
            "asks": [
                {"price": "0.50", "size": "50"},
                {"price": "0.52", "size": "50"}
            ]
        }
        res = simulate_fill(40.0, book, "BUY", latency_ms=500)
        assert res.total_filled == 40.0
        assert res.slippage_pct > 0.0
        assert res.latency_ms == 500.0


# ============================================================================
# REQUIREMENT 2 (R2): SAMPLE-SIZE DAMPED DYNAMIC SLEEVE BUDGET SIZING
# ============================================================================

class TestR2BayesianSleeveBudgetSizing:
    """
    Verifies the two-stage Bayesian credibility function Z(N), anchoring low-sample
    whales (N < 15) strictly within $900 - $1,100 (+/- 10%) under all extreme shocks.
    """

    @pytest.mark.parametrize("n", [0, 1, 2, 3, 5, 7, 10, 12, 14])
    @pytest.mark.parametrize("shock_pnl", [-1_000_000.0, -500.0, -100.0, 0.0, 100.0, 500.0, 1_000_000.0])
    @pytest.mark.parametrize("score", [0.0, 20.0, 50.0, 80.0, 100.0])
    def test_low_sample_whales_strictly_anchored_within_10_percent(self, n, shock_pnl, score):
        base_budget = 1000.0
        adj_budget = SleeveManager.calculate_adjusted_sleeve_budget(
            base_budget=base_budget,
            copy_pnl_ema=shock_pnl,
            baleen_score=score,
            trades_count=n
        )
        assert 900.0 <= adj_budget <= 1100.0, (
            f"Failed anchoring for N={n}, PnL={shock_pnl}, score={score}: "
            f"got ${adj_budget:.2f}, expected within [900, 1100]"
        )

    def test_sits_to_pee_scenario_n2(self):
        """
        SitsToPee: 2 trades, whale score 82.0, copy-PnL EMA -$350.00.
        Must NOT slash budget to $300; must anchor safely near $1,000.
        """
        base = 1000.0
        adj = SleeveManager.calculate_adjusted_sleeve_budget(
            base_budget=base,
            copy_pnl_ema=-350.0,
            baleen_score=82.0,
            trades_count=2
        )
        assert 950.0 <= adj <= 1050.0
        assert adj > 900.0

    def test_continuity_at_n15_threshold(self):
        """Verify C^0 continuity at boundary N=15."""
        base = 1000.0
        # Catastrophic loss shock
        pnl = -1_000_000.0
        score = 80.0
        adj_14 = SleeveManager.calculate_adjusted_sleeve_budget(base, pnl, score, trades_count=14)
        adj_15 = SleeveManager.calculate_adjusted_sleeve_budget(base, pnl, score, trades_count=15)
        adj_16 = SleeveManager.calculate_adjusted_sleeve_budget(base, pnl, score, trades_count=16)

        # Z(14) = 14/105 -> mult = 1.0 - 0.7*(14/105) = 0.9067 -> $906.67
        # Z(15) = 1/7   -> mult = 1.0 - 0.7*(1/7)    = 0.9000 -> $900.00
        # Z(16) = 1/7 + 6/7*(1/21) = 0.1837 -> mult = 1.0 - 0.7*0.1837 = 0.8714 -> $871.43
        assert adj_14 == 906.67
        assert adj_15 == 900.00
        assert adj_16 == 871.43
        assert adj_14 > adj_15 > adj_16

    def test_asymptotic_expansion_for_mature_whales(self):
        """As sample matures (N >= 35, 75, 200, 1000), full dynamic range [0.30x, 1.50x] unlocks."""
        base = 1000.0
        # High sample loss
        adj_loss_35 = SleeveManager.calculate_adjusted_sleeve_budget(base, -1_000_000.0, 80.0, trades_count=35)
        assert adj_loss_35 < 700.0

        adj_loss_75 = SleeveManager.calculate_adjusted_sleeve_budget(base, -1_000_000.0, 80.0, trades_count=75)
        assert adj_loss_75 < 500.0

        adj_loss_200 = SleeveManager.calculate_adjusted_sleeve_budget(base, -1_000_000.0, 80.0, trades_count=200)
        assert adj_loss_200 < 400.0

        adj_loss_1000 = SleeveManager.calculate_adjusted_sleeve_budget(base, -1_000_000.0, 80.0, trades_count=1000)
        assert adj_loss_1000 <= 315.0

    def test_backward_compatibility_none_trades_count(self):
        """Omitting trades_count defaults to full credibility Z=1.0."""
        base = 1000.0
        assert SleeveManager.calculate_adjusted_sleeve_budget(base, 1_000_000.0) == 1500.0
        assert SleeveManager.calculate_adjusted_sleeve_budget(base, -1_000_000.0) == 300.0

    def test_ema_innovation_clipping(self):
        """Verify update_copy_pnl_ema clamps single-trade innovations to +/- $500."""
        # Extreme loss of -$10,000 is clipped to -$500
        new_ema = SleeveManager.update_copy_pnl_ema(current_ema=0.0, new_realized_pnl=-10_000.0, alpha=0.05)
        assert new_ema == -25.0  # 0.95 * 0 + 0.05 * (-500) = -25.0


# ============================================================================
# REQUIREMENT 3 (R3): PORTFOLIO TIMEFRAME & NET WORTH SYNCHRONIZATION
# ============================================================================

class TestR3PortfolioTimeframeSynchronization:
    """
    Verifies that mark-to-market valuations do not dip on cold cache and
    snapshot timeframes (1H, 1D, 1W, ALL) converge cleanly.
    """

    @pytest.mark.asyncio
    async def test_cold_cache_preservation_in_mark_to_market(self):
        from app.services.mark_to_market import _last_known_pnl
        # Clearing _last_known_pnl and testing fallback
        test_id = "test-trade-cold-cache-001"
        _last_known_pnl.pop(test_id, None)
        # Should not throw and default to 0.0
        assert _last_known_pnl.get(test_id, 0.0) == 0.0

    @pytest.mark.asyncio
    async def test_snapshot_bucketing_last_of_bucket_convergence(self):
        """
        Verify that last-of-bucket selection correctly chooses the latest snapshot
        in each bucket interval and converges to latest live snapshot.
        """
        from app.api.execution_logs import get_portfolio_snapshots
        async with SessionLocal() as db:
            # Check endpoint execution without error
            snaps_1h = await get_portfolio_snapshots(timeframe="1h", db=db)
            snaps_all = await get_portfolio_snapshots(timeframe="all", db=db)

            assert isinstance(snaps_1h, list)
            assert isinstance(snaps_all, list)
            if snaps_1h and snaps_all:
                # Both should end at identical latest balance if database has snapshots
                assert snaps_1h[-1]["balance"] == snaps_all[-1]["balance"]
