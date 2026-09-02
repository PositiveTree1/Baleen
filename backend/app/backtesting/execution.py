"""
Realistic Execution Engine for Backtesting
Simulates CLOB fill pricing, liquidity participation limits, copy latency delay,
adverse selection drift, directional slippage checks, and exact Polymarket fees.
"""
import uuid
import math
from app.backtesting.config import BacktestConfig
from app.backtesting.models import TradeSignal, ExecutionFill
from app.sizing.slippage import calculate_simulated_fill_price, check_slippage
from app.services.polymarket_fees import calculate_polymarket_fee, classify_market_category

class RealisticExecutionModel:
    def __init__(self, config: BacktestConfig):
        self.config = config

    def simulate_copy_execution(
        self,
        signal: TradeSignal,
        intended_size_usd: float,
        available_cash: float,
        available_sleeve_cash: float,
    ) -> ExecutionFill:
        """
        Simulates realistic execution of a copy-trade signal.
        Applies:
          1. Capital availability gating (cash & sleeve limit)
          2. Liquidity participation cap
          3. Latency adverse selection & non-linear CLOB depth walk
          4. Intentional adverse bias (zero-optimism guarantee)
          5. Category-specific directional slippage validation
          6. Exact 2026 Polymarket dynamic fee calculation
        """
        order_id = str(uuid.uuid4())[:8]
        exec_timestamp = float(signal.timestamp) + (self.config.latency_ms / 1000.0)

        # 1. Capital Availability Gating
        max_allowed_size = min(intended_size_usd, available_cash, available_sleeve_cash)
        if max_allowed_size < self.config.min_trade_size_usd:
            return ExecutionFill(
                order_id=order_id,
                signal=signal,
                intended_size_usd=intended_size_usd,
                fill_price=signal.whale_price,
                filled_size_usd=0.0,
                filled_shares=0.0,
                slippage_bps=0.0,
                fee_usd=0.0,
                latency_ms=self.config.latency_ms,
                status="SKIPPED_CAPITAL",
                executed_at=exec_timestamp,
                rejection_reason="Insufficient free cash or sleeve budget"
            )

        # 2. Liquidity Participation Cap (Whale Order Slicing)
        # In real CLOB markets, a copy-trader cannot instantly take more than a fraction
        # of the whale's liquidity footprint without clearing out thin books.
        liquidity_cap_usd = max(self.config.min_trade_size_usd, signal.whale_size_usd * self.config.liquidity_participation_cap)
        filled_size_usd = min(max_allowed_size, liquidity_cap_usd, self.config.max_trade_size_usd)
        filled_size_usd = round(filled_size_usd, 2)

        if filled_size_usd < self.config.min_trade_size_usd:
            return ExecutionFill(
                order_id=order_id,
                signal=signal,
                intended_size_usd=intended_size_usd,
                fill_price=signal.whale_price,
                filled_size_usd=0.0,
                filled_shares=0.0,
                slippage_bps=0.0,
                fee_usd=0.0,
                latency_ms=self.config.latency_ms,
                status="SKIPPED_BELOW_MINIMUM",
                executed_at=exec_timestamp,
                rejection_reason=f"Size ${filled_size_usd} below min order threshold"
            )

        # 3. Authentic Fill Price Calculation (Spread, Depth Walk, Latency Selection)
        if self.config.enable_slippage:
            base_fill = calculate_simulated_fill_price(
                price=signal.whale_price,
                side=signal.side,
                notional_usd=filled_size_usd,
                latency_ms=self.config.latency_ms
            )
            # 4. Intentional Adverse Bias (Ensures strictly conservative simulation)
            bias_mult = 1.0 + (self.config.adverse_bias_bps / 10000.0) if signal.side.upper() == "BUY" else 1.0 - (self.config.adverse_bias_bps / 10000.0)
            fill_price = round(base_fill * bias_mult, 4)
            fill_price = max(0.001, min(0.999, fill_price))
        else:
            fill_price = signal.whale_price

        # 5. Directional Slippage Rejection Gate
        slippage_check = check_slippage(
            whale_price=signal.whale_price,
            current_price=fill_price,
            side=signal.side
        )
        if "CANCEL_ORDER" in slippage_check:
            return ExecutionFill(
                order_id=order_id,
                signal=signal,
                intended_size_usd=intended_size_usd,
                fill_price=fill_price,
                filled_size_usd=0.0,
                filled_shares=0.0,
                slippage_bps=round(abs(fill_price - signal.whale_price) / max(0.01, signal.whale_price) * 10000.0, 1),
                fee_usd=0.0,
                latency_ms=self.config.latency_ms,
                status="REJECTED_SLIPPAGE",
                executed_at=exec_timestamp,
                rejection_reason=slippage_check
            )

        # 6. Compute Realized Shares
        filled_shares = round(filled_size_usd / fill_price, 4) if fill_price > 0 else 0.0

        # 7. Polymarket Dynamic 2026 Fee Schedule Calculation
        if self.config.enable_fees:
            fee_info = calculate_polymarket_fee(
                notional_usd=filled_size_usd,
                price=fill_price,
                market_title=signal.market_title or signal.category,
                is_maker=False
            )
            fee_usd = float(fee_info.get("fee_usd", 0.0))
        else:
            fee_usd = 0.0

        slippage_bps = round(abs(fill_price - signal.whale_price) / max(0.01, signal.whale_price) * 10000.0, 1)
        status = "FILLED" if math.isclose(filled_size_usd, intended_size_usd, abs_tol=0.05) else "PARTIALLY_FILLED"

        return ExecutionFill(
            order_id=order_id,
            signal=signal,
            intended_size_usd=intended_size_usd,
            fill_price=fill_price,
            filled_size_usd=filled_size_usd,
            filled_shares=filled_shares,
            slippage_bps=slippage_bps,
            fee_usd=fee_usd,
            latency_ms=self.config.latency_ms,
            status=status,
            executed_at=exec_timestamp
        )
