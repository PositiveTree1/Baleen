"""
Comprehensive Test Suite for the Baleen Quantitative Backtesting System
Validates execution realism, slippage, latency, fees, portfolio accounting,
sleeve budgeting, market resolutions, and strategy implementations.
"""
import pytest
from app.backtesting.config import BacktestConfig
from app.backtesting.models import TradeSignal, ExecutionFill, PortfolioPosition, ClosedTrade, BacktestResult
from app.backtesting.execution import RealisticExecutionModel
from app.backtesting.portfolio import SimulatedPortfolio
from app.backtesting.strategies import (
    FixedProportionalStrategy,
    SleeveConvictionStrategy,
    FeeAwareGatedStrategy,
    AntiConflictGatedStrategy,
    AdaptiveProductionStrategy,
)
from app.backtesting.engine import BacktestEngine
from app.sizing.slippage import calculate_simulated_fill_price
from app.services.polymarket_fees import calculate_polymarket_fee

# -------------------------------------------------------------------------
# 1. Execution Model Tests
# -------------------------------------------------------------------------

def test_execution_model_fill_pricing_is_adverse_on_buy():
    config = BacktestConfig(latency_ms=350.0, adverse_bias_bps=10.0)
    exec_model = RealisticExecutionModel(config)

    signal = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale1",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=1000.0,
        whale_shares=2000.0,
        market_title="Will Fed cut rates?",
        category="Economics / Finance"
    )

    fill = exec_model.simulate_copy_execution(
        signal=signal,
        intended_size_usd=100.0,
        available_cash=10000.0,
        available_sleeve_cash=1000.0
    )

    assert fill.status in ("FILLED", "PARTIALLY_FILLED")
    # Buy fill price MUST be strictly higher than whale price (conservative/adverse)
    assert fill.fill_price > signal.whale_price
    assert fill.slippage_bps > 0
    assert fill.fee_usd > 0
    assert fill.filled_size_usd > 0
    assert fill.executed_at > signal.timestamp


def test_execution_model_fill_pricing_is_adverse_on_sell():
    config = BacktestConfig(latency_ms=350.0, adverse_bias_bps=10.0)
    exec_model = RealisticExecutionModel(config)

    signal = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale1",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="SELL",
        whale_price=0.60,
        whale_size_usd=1000.0,
        whale_shares=1666.6,
        market_title="Will Fed cut rates?",
        category="Economics / Finance"
    )

    fill = exec_model.simulate_copy_execution(
        signal=signal,
        intended_size_usd=100.0,
        available_cash=10000.0,
        available_sleeve_cash=1000.0
    )

    # Sell fill price MUST be strictly lower than whale price
    assert fill.fill_price < signal.whale_price
    assert fill.slippage_bps > 0


def test_execution_model_liquidity_cap():
    # If whale order is small ($20), copy order cannot exceed participation cap
    config = BacktestConfig(liquidity_participation_cap=0.20, min_trade_size_usd=2.0)
    exec_model = RealisticExecutionModel(config)

    signal = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale1",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=50.0,  # Small whale order
        whale_shares=100.0,
        market_title="Solana match",
        category="Crypto"
    )

    fill = exec_model.simulate_copy_execution(
        signal=signal,
        intended_size_usd=200.0,  # User wanted $200
        available_cash=10000.0,
        available_sleeve_cash=1000.0
    )

    # Capped to 20% of $50 = $10.0
    assert fill.filled_size_usd <= 10.05
    assert fill.status == "PARTIALLY_FILLED"


def test_execution_model_rejects_insufficient_capital():
    config = BacktestConfig(min_trade_size_usd=5.0)
    exec_model = RealisticExecutionModel(config)

    signal = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale1",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=500.0,
        whale_shares=1000.0
    )

    fill = exec_model.simulate_copy_execution(
        signal=signal,
        intended_size_usd=100.0,
        available_cash=2.0,  # Only $2 left!
        available_sleeve_cash=1000.0
    )
    assert fill.status == "SKIPPED_CAPITAL"
    assert fill.filled_size_usd == 0.0


# -------------------------------------------------------------------------
# 2. Portfolio Accounting & Settlement Tests
# -------------------------------------------------------------------------

def test_portfolio_lifecycle_and_resolution_settlement():
    config = BacktestConfig(initial_capital=10000.0, max_sleeve_fraction=0.10)
    portfolio = SimulatedPortfolio(config)
    portfolio.register_active_roster(["0xwhale1", "0xwhale2"])

    signal = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale1",
        market_id="market_100",
        condition_id="cond_100",
        token_id="token1",
        side="BUY",
        whale_price=0.40,
        whale_size_usd=500.0,
        whale_shares=1250.0,
        nonusdc_side="token1",
        market_title="Fed cuts 25 bps",
        category="Economics / Finance"
    )

    exec_model = RealisticExecutionModel(config)
    fill = exec_model.simulate_copy_execution(
        signal=signal,
        intended_size_usd=200.0,
        available_cash=portfolio.cash,
        available_sleeve_cash=portfolio.get_available_sleeve_cash("0xwhale1")
    )

    pos = portfolio.open_position(fill)
    assert pos is not None
    assert portfolio.cash < 10000.0
    assert len(portfolio.open_positions) == 1
    assert portfolio.get_available_sleeve_cash("0xwhale1") < 1000.0

    # Settle Market Resolution: token1 WINS!
    settled = portfolio.settle_market_resolution("market_100", "token1", 1700100000.0)
    assert len(settled) == 1
    trade = settled[0]
    assert trade.exit_reason == "RESOLUTION_WIN"
    assert trade.net_pnl > 0.0
    assert len(portfolio.open_positions) == 0
    # Cash should now be greater than initial capital
    assert portfolio.cash > 10000.0


def test_portfolio_settlement_on_loss():
    config = BacktestConfig(initial_capital=10000.0)
    portfolio = SimulatedPortfolio(config)
    portfolio.register_active_roster(["0xwhale1"])

    signal = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale1",
        market_id="market_loss",
        condition_id="cond_loss",
        token_id="token1",
        side="BUY",
        whale_price=0.40,
        whale_size_usd=500.0,
        whale_shares=1250.0,
        nonusdc_side="token1"
    )

    exec_model = RealisticExecutionModel(config)
    fill = exec_model.simulate_copy_execution(
        signal=signal,
        intended_size_usd=100.0,
        available_cash=portfolio.cash,
        available_sleeve_cash=portfolio.get_available_sleeve_cash("0xwhale1")
    )
    portfolio.open_position(fill)

    # Settle Market Resolution: token2 WINS (token1 LOSES)
    settled = portfolio.settle_market_resolution("market_loss", "token2", 1700100000.0)
    assert len(settled) == 1
    trade = settled[0]
    assert trade.exit_reason == "RESOLUTION_LOSS"
    assert trade.net_pnl < 0.0
    assert trade.exit_price == 0.0
    assert portfolio.cash < 10000.0


# -------------------------------------------------------------------------
# 3. Strategy Tests
# -------------------------------------------------------------------------

def test_sleeve_conviction_strategy_ranks_whale_size():
    strategy = SleeveConvictionStrategy()
    portfolio = SimulatedPortfolio(BacktestConfig(initial_capital=10000.0))
    portfolio.register_active_roster(["0xwhale1"])
    strategy.trailing_sizes["0xwhale1"] = [100.0, 200.0, 500.0, 1000.0, 2000.0]

    # Small feeler trade
    sig_small = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale1",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=50.0,
        whale_shares=100.0
    )
    # Huge conviction trade
    sig_huge = TradeSignal(
        timestamp=1700001000,
        whale_address="0xwhale1",
        market_id="m2",
        condition_id="c2",
        token_id="tok2",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=25000.0,
        whale_shares=50000.0
    )

    size_small = strategy.evaluate_signal(sig_small, portfolio)
    size_huge = strategy.evaluate_signal(sig_huge, portfolio)

    assert size_small is not None
    assert size_huge is not None
    assert size_huge > size_small


def test_anti_conflict_strategy_disqualifies_hedged_whale():
    strategy = AntiConflictGatedStrategy(max_conflict_tolerance=0.15)
    portfolio = SimulatedPortfolio(BacktestConfig(initial_capital=10000.0))
    portfolio.register_active_roster(["0xhedger"])

    # Trade 1: Buy token1 (YES) on Fed rate cut
    sig1 = TradeSignal(
        timestamp=1700000000,
        whale_address="0xhedger",
        market_id="m_fed",
        condition_id="c_fed",
        token_id="tok_yes",
        side="BUY",
        whale_price=0.80,
        whale_size_usd=5000.0,
        whale_shares=6250.0,
        nonusdc_side="token1"
    )
    # Trade 2: Buy token2 (NO) on SAME Fed rate cut (hedging/conflicting)
    sig2 = TradeSignal(
        timestamp=1700000100,
        whale_address="0xhedger",
        market_id="m_fed",
        condition_id="c_fed",
        token_id="tok_no",
        side="BUY",
        whale_price=0.20,
        whale_size_usd=5000.0,
        whale_shares=25000.0,
        nonusdc_side="token2"
    )

    size1 = strategy.evaluate_signal(sig1, portfolio)
    assert size1 is not None

    # Evaluating conflicting trade should trigger disqualification
    size2 = strategy.evaluate_signal(sig2, portfolio)
    assert size2 is None
    assert "0xhedger" in strategy.disqualified_whales

    # Subsequent trades from this whale must be blocked
    sig3 = TradeSignal(
        timestamp=1700000200,
        whale_address="0xhedger",
        market_id="m_cpi",
        condition_id="c_cpi",
        token_id="tok_cpi",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=1000.0,
        whale_shares=2000.0,
        nonusdc_side="token1"
    )
    assert strategy.evaluate_signal(sig3, portfolio) is None


def test_fee_aware_ev_gate_strategy():
    strategy = FeeAwareGatedStrategy(ev_multiplier=2.5)
    portfolio = SimulatedPortfolio(BacktestConfig(initial_capital=10000.0))
    portfolio.register_active_roster(["0xwhale1"])

    # Trade near 0.50 in high-fee Crypto category where edge doesn't clear 2.5x fee
    sig_crypto = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale1",
        market_id="m_btc",
        condition_id="c_btc",
        token_id="tok_btc",
        side="BUY",
        whale_price=0.69,
        whale_size_usd=500.0,
        whale_shares=724.0,
        market_title="Bitcoin Up or Down 15m",
        category="Crypto"
    )
    res = strategy.evaluate_signal(sig_crypto, portfolio)
    # Should be rejected because fee on 15m crypto at 0.69 is high and edge is marginal
    assert res is None


def test_adaptive_production_strategy_end_to_end():
    config = BacktestConfig(initial_capital=10000.0)
    strategy = AdaptiveProductionStrategy(ev_multiplier=2.0)
    portfolio = SimulatedPortfolio(config)
    portfolio.register_active_roster(["0xclean_whale"])

    signal = TradeSignal(
        timestamp=1700000000,
        whale_address="0xclean_whale",
        market_id="m_pol",
        condition_id="c_pol",
        token_id="tok_pol",
        side="BUY",
        whale_price=0.45,
        whale_size_usd=1500.0,
        whale_shares=3333.3,
        market_title="Senate election winner",
        category="Politics",
        nonusdc_side="token1"
    )

    size = strategy.evaluate_signal(signal, portfolio)
    assert size is not None
    assert size >= config.min_trade_size_usd
    assert size <= config.initial_capital * config.max_sleeve_fraction


def test_portfolio_settlement_on_50_50_split_refund():
    # Validates that 50/50 dispute/refund splits properly refund principal rather than stalling
    config = BacktestConfig(initial_capital=10000.0)
    portfolio = SimulatedPortfolio(config)
    portfolio.register_active_roster(["0xwhale1"])

    signal = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale1",
        market_id="m_split",
        condition_id="c_split",
        token_id="tok1",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=100.0,
        whale_shares=200.0,
        nonusdc_side="token1"
    )

    exec_model = RealisticExecutionModel(config)
    fill = exec_model.simulate_copy_execution(
        signal=signal,
        intended_size_usd=100.0,
        available_cash=portfolio.cash,
        available_sleeve_cash=portfolio.get_available_sleeve_cash("0xwhale1")
    )
    portfolio.open_position(fill)

    # Market resolves in 50/50 dispute (each side gets 0.50 per share)
    settled = portfolio.settle_market_resolution(
        market_id="m_split",
        winning_token="split",
        resolution_timestamp=1700100000.0,
        p1_payout=0.50,
        p2_payout=0.50
    )
    assert len(settled) == 1
    t = settled[0]
    assert t.exit_price == 0.50
    assert len(portfolio.open_positions) == 0
    # Because exit price was 0.50 and entry was near 0.50, gross proceeds refunded principal
    assert t.shares > 0
    assert portfolio.cash > 9900.0  # Cash safely recovered (minus fee/slippage)


def test_data_loader_parse_outcome_prices_handles_split():
    from app.backtesting.data_loader import PolymarketDataLoader
    loader = PolymarketDataLoader(BacktestConfig())

    tok, p1, p2 = loader.parse_outcome_prices("['0.5', '0.5']")
    assert tok == "split"
    assert p1 == 0.5
    assert p2 == 0.5

    tok, p1, p2 = loader.parse_outcome_prices("['0', '1']")
    assert tok == "token2"
    assert p1 == 0.0
    assert p2 == 1.0

    tok, p1, p2 = loader.parse_outcome_prices("['0.505', '0.495']")
    assert tok == "token1"
    assert p1 == 0.505
    assert p2 == 0.495


def test_fixed_amount_entry_strategy():
    from app.backtesting.strategies import FixedAmountEntryStrategy
    strategy = FixedAmountEntryStrategy(entry_usd=100.0)
    portfolio = SimulatedPortfolio(BacktestConfig(initial_capital=10000.0))

    sig = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale1",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=1000.0,
        whale_shares=2000.0
    )
    assert strategy.evaluate_signal(sig, portfolio) == 100.0

    sig_sell = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale1",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="SELL",
        whale_price=0.50,
        whale_size_usd=1000.0,
        whale_shares=2000.0
    )
    assert strategy.evaluate_signal(sig_sell, portfolio) is None


def test_consensus_confirmation_strategy():
    from app.backtesting.strategies import ConsensusConfirmationStrategy
    strat = ConsensusConfirmationStrategy(min_whales=2, window_sec=86400.0)
    portfolio = SimulatedPortfolio(BacktestConfig(initial_capital=10000.0))

    # Whale 1 buys
    sig1 = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale1",
        market_id="m_consensus",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=500.0,
        whale_shares=1000.0,
        nonusdc_side="token1"
    )
    # First whale alone: NO consensus yet
    assert strat.evaluate_signal(sig1, portfolio) is None

    # Whale 1 buys again on same market: still only 1 distinct whale -> NO consensus
    sig1_repeat = TradeSignal(
        timestamp=1700000100,
        whale_address="0xwhale1",
        market_id="m_consensus",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.52,
        whale_size_usd=500.0,
        whale_shares=1000.0,
        nonusdc_side="token1"
    )
    assert strat.evaluate_signal(sig1_repeat, portfolio) is None

    # Whale 2 buys the SAME outcome on the SAME market within 24h: CONSENSUS CONFIRMED!
    sig2 = TradeSignal(
        timestamp=1700000500,
        whale_address="0xwhale2",
        market_id="m_consensus",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.53,
        whale_size_usd=800.0,
        whale_shares=1500.0,
        nonusdc_side="token1"
    )
    size = strat.evaluate_signal(sig2, portfolio)
    assert size is not None
    assert size == 400.0  # 4% of $10,000


def test_gold_sniper_strategy_conviction_gate():
    from app.backtesting.strategies import GoldSniperStrategy
    from app.backtesting.models import WhaleQualification

    strat = GoldSniperStrategy(min_conviction=0.70)
    portfolio = SimulatedPortfolio(BacktestConfig(initial_capital=10000.0))
    portfolio.register_active_roster(["0xgold", "0xstandard"])

    roster = [
        WhaleQualification(
            address="0xgold",
            realized_pnl=100000.0,
            win_rate_pct=85.0,
            total_volume=500000.0,
            trades_count=100,
            sharpe_ratio=3.5,
            tier="gold_sniper"
        ),
        WhaleQualification(
            address="0xstandard",
            realized_pnl=30000.0,
            win_rate_pct=65.0,
            total_volume=200000.0,
            trades_count=50,
            sharpe_ratio=1.5,
            tier="standard"
        )
    ]
    strat.set_qualified_roster(roster)

    # Standard whale trade should be disqualified
    sig_standard = TradeSignal(
        timestamp=1700000000,
        whale_address="0xstandard",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=5000.0,
        whale_shares=10000.0
    )
    assert strat.evaluate_signal(sig_standard, portfolio) is None

    # Gold sniper with historical sizes: [100, 200, 300, 400, 500]
    strat.trailing_sizes["0xgold"] = [100.0, 200.0, 300.0, 400.0, 500.0]

    # Feeler trade ($50) -> low conviction -> skipped
    sig_feeler = TradeSignal(
        timestamp=1700000000,
        whale_address="0xgold",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=50.0,
        whale_shares=100.0
    )
    assert strat.evaluate_signal(sig_feeler, portfolio) is None

    # High conviction trade ($2000) -> top percentile -> approved!
    sig_heavy = TradeSignal(
        timestamp=1700000100,
        whale_address="0xgold",
        market_id="m2",
        condition_id="c2",
        token_id="tok2",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=2000.0,
        whale_shares=4000.0
    )
    size = strat.evaluate_signal(sig_heavy, portfolio)
    assert size is not None
    assert size > 0.0


def test_top_sharpe_kelly_strategy():
    from app.backtesting.strategies import TopSharpeKellyStrategy
    from app.backtesting.models import WhaleQualification

    strat = TopSharpeKellyStrategy(top_n=2)
    portfolio = SimulatedPortfolio(BacktestConfig(initial_capital=10000.0))

    roster = [
        WhaleQualification("0xsharpe_high", 100000.0, 80.0, 500000.0, 100, 4.5, "gold_sniper"),
        WhaleQualification("0xsharpe_med", 50000.0, 70.0, 250000.0, 80, 2.5, "standard"),
        WhaleQualification("0xsharpe_low", 20000.0, 55.0, 100000.0, 40, 0.8, "standard"),
    ]
    strat.set_qualified_roster(roster)

    # 0xsharpe_low should not be in top 2
    assert "0xsharpe_low" not in strat.top_whales

    # 0xsharpe_high gets dynamic half-kelly sizing
    sig = TradeSignal(
        timestamp=1700000000,
        whale_address="0xsharpe_high",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=1000.0,
        whale_shares=2000.0
    )
    size = strat.evaluate_signal(sig, portfolio)
    assert size is not None
    # For p=0.80 at price=0.50, b=1.0: Kelly = 0.5 * (0.8*2 - 1) = 0.30, clamped to max 8% = $800
    assert size == 800.0


def test_resolution_hold_strategy_refuses_whale_exit():
    from app.backtesting.strategies import ResolutionHoldStrategy
    strat = ResolutionHoldStrategy()
    portfolio = SimulatedPortfolio(BacktestConfig(initial_capital=10000.0))

    sig_sell = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale1",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="SELL",
        whale_price=0.50,
        whale_size_usd=500.0,
        whale_shares=1000.0
    )
    assert strat.should_mirror_whale_exit(sig_sell, portfolio) is False


def test_get_predefined_windows():
    from app.backtesting.data_loader import get_predefined_window

    s1, e1, l1 = get_predefined_window("1m")
    assert s1 == 1727740800
    assert e1 == 1730419200
    assert "1-Month" in l1

    s3, e3, l3 = get_predefined_window("3m")
    assert s3 == 1722470400
    assert e3 == 1730419200
    assert "3-Month" in l3

    s6, e6, l6 = get_predefined_window("6m")
    assert s6 == 1714521600
    assert e6 == 1730419200
    assert "6-Month" in l6


def test_top_sharpe_kelly_negative_ev_rejection():
    from app.backtesting.strategies import TopSharpeKellyStrategy
    from app.backtesting.models import WhaleQualification

    strat = TopSharpeKellyStrategy(top_n=5)
    portfolio = SimulatedPortfolio(BacktestConfig(initial_capital=10000.0))

    roster = [
        WhaleQualification("0xwhale", 50000.0, 60.0, 100000.0, 50, 1.5, "standard")
    ]
    strat.set_qualified_roster(roster)

    # Signal at price=0.80 with win rate=0.60 has negative EV: (0.60 * 1.25 - 1 = -0.25 <= 0)
    sig_bad_ev = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.80,
        whale_size_usd=1000.0,
        whale_shares=1250.0
    )
    # MUST return None (skip negative-EV trade)
    assert strat.evaluate_signal(sig_bad_ev, portfolio) is None


def test_consensus_confirmation_cooldown():
    from app.backtesting.strategies import ConsensusConfirmationStrategy

    strat = ConsensusConfirmationStrategy(min_whales=2, window_sec=86400.0)
    portfolio = SimulatedPortfolio(BacktestConfig(initial_capital=10000.0))

    sig1 = TradeSignal(
        timestamp=1700000000,
        whale_address="0xwhale1",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=1000.0,
        whale_shares=2000.0,
        nonusdc_side="token1"
    )
    # Whale 1 alone: awaiting confirmation -> None
    assert strat.evaluate_signal(sig1, portfolio) is None

    sig2 = TradeSignal(
        timestamp=1700000100,
        whale_address="0xwhale2",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=1000.0,
        whale_shares=2000.0,
        nonusdc_side="token1"
    )
    # Whale 2 confirms: fires 4% ($400)
    assert strat.evaluate_signal(sig2, portfolio) == 400.0

    # Whale 2 trades again 10 seconds later: blocked by cooldown -> None
    sig3 = TradeSignal(
        timestamp=1700000110,
        whale_address="0xwhale2",
        market_id="m1",
        condition_id="c1",
        token_id="tok1",
        side="BUY",
        whale_price=0.50,
        whale_size_usd=1000.0,
        whale_shares=2000.0,
        nonusdc_side="token1"
    )
    assert strat.evaluate_signal(sig3, portfolio) is None


def test_parse_outcome_prices_decimals_and_regex():
    from app.backtesting.data_loader import PolymarketDataLoader

    loader = PolymarketDataLoader(BacktestConfig())

    # Decimal format 1
    w2, p1_2, p2_2 = loader.parse_outcome_prices("['0.0005', '0.9995']")
    assert w2 == "token2"
    assert p1_2 == 0.0005
    assert p2_2 == 0.9995

    # Decimal format 2
    w1, p1_1, p2_1 = loader.parse_outcome_prices("['0.9995', '0.0005']")
    assert w1 == "token1"
    assert p1_1 == 0.9995
    assert p2_1 == 0.0005

    # Standard integer string format
    wi, p1_i, p2_i = loader.parse_outcome_prices("['1', '0']")
    assert wi == "token1"
    assert p1_i == 1.0
    assert p2_i == 0.0

    # Non-standard string without brackets
    w_raw, p1_r, p2_r = loader.parse_outcome_prices("0.0005, 0.9995")
    assert w_raw == "token2"


def test_engine_zero_lookahead_end_settlement():
    from app.backtesting.strategies import FixedAmountEntryStrategy
    from app.backtesting.models import TradeSignal

    cfg = BacktestConfig(initial_capital=1000.0, fixed_entry_usd=100.0)
    strat = FixedAmountEntryStrategy(entry_usd=100.0)
    engine = BacktestEngine(config=cfg, strategy=strat)

    # Position in a market that resolves at timestamp 2000
    pos = engine.portfolio.open_position(
        ExecutionFill(
            order_id="ord_test",
            signal=TradeSignal(
                timestamp=1000,
                whale_address="0xwhale1",
                market_id="m_future",
                condition_id="c_future",
                token_id="tok1",
                side="BUY",
                whale_price=0.50,
                whale_size_usd=100.0,
                whale_shares=200.0,
                nonusdc_side="token1"
            ),
            intended_size_usd=100.0,
            fill_price=0.50,
            filled_size_usd=100.0,
            filled_shares=200.0,
            fee_usd=0.0,
            slippage_bps=0.0,
            latency_ms=350.0,
            executed_at=1000.0,
            status="FILLED"
        )
    )
    assert pos is not None
    assert len(engine.portfolio.open_positions) == 1

    # Market metadata: closed=True, but end_timestamp=2000 (resolves in the future)
    engine.data_loader._market_resolutions_cache["m_future"] = {
        "market_id": "m_future",
        "closed": True,
        "end_timestamp": 2000.0,
        "winning_token": "token1",
        "p1_payout": 1.0,
        "p2_payout": 0.0
    }

    # Simulation ends at timestamp 1500 (BEFORE market resolution at 2000)
    # Under zero lookahead bias, m_future CANNOT be settled at timestamp 1500
    remaining_open = {p.market_id for p in engine.portfolio.open_positions.values()}
    for m_id in remaining_open:
        m_info = engine.data_loader._market_resolutions_cache.get(m_id)
        if m_info and m_info.get("closed"):
            end_t = m_info.get("end_timestamp") or 0.0
            # Zero lookahead check:
            if end_t > 0 and end_t <= 1500:  # End of simulation
                engine.portfolio.settle_market_resolution(
                    market_id=m_id,
                    winning_token="token1",
                    resolution_timestamp=float(end_t),
                    p1_payout=1.0,
                    p2_payout=0.0
                )

    # Position MUST remain open at timestamp 1500
    assert len(engine.portfolio.open_positions) == 1
    assert len(engine.portfolio.closed_trades) == 0


