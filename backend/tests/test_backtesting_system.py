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
