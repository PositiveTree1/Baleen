from dataclasses import dataclass
from typing import Optional

@dataclass
class SizingResult:
    value: float
    status: str

def calculate_pure_proportional_order_size(
    user_balance: float,
    n_active: int,
    whale_trade_usd: float,
    whale_pnl_or_net_worth: float,
    min_order_usd: float = 1.0,
    available_cash: Optional[float] = None
) -> SizingResult:
    """
    Pure Proportional Sleeve Sizing Architecture:
    Sleeve Budget S_w = current_user_portfolio_balance / n_active
    Whale Trade Fraction f = whale_trade_usd / whale_pnl_or_net_worth
    Copy Order Size = S_w * f

    No artificial multipliers, no arbitrary caps.
    Constrained only by available cash in the account and minimum Polymarket order size ($1.00).
    When the account grows (e.g. from $10,000 to $20,000), S_w automatically scales from $1,000 to $2,000!
    """
    if user_balance <= 0:
        return SizingResult(value=0.0, status='SKIPPED_BELOW_MINIMUM')
    if n_active <= 0:
        return SizingResult(value=0.0, status='SKIPPED_NO_ACTIVE_WALLETS')
    if whale_pnl_or_net_worth <= 0 or whale_trade_usd <= 0:
        return SizingResult(value=0.0, status='SKIPPED_INVALID_PORTFOLIO')

    s_w = float(user_balance) / float(n_active)
    f = float(whale_trade_usd) / float(whale_pnl_or_net_worth)
    order_size = s_w * f

    # Constrained only by available cash in account (if provided) or user_balance
    cash_limit = available_cash if available_cash is not None else user_balance
    order_size = min(order_size, max(0.0, float(cash_limit)))

    if order_size < min_order_usd:
        return SizingResult(value=0.0, status='SKIPPED_BELOW_MINIMUM')

    return SizingResult(value=round(order_size, 2), status='SUCCESS')

def size_trade(
    user_balance: float,
    risk_profile: Optional[str],
    n_active: int,
    whale_trade_value: float,
    whale_portfolio_value: float,
    min_order_usd: float = 1.0,
    pure_proportional: bool = False,
    available_cash: Optional[float] = None
) -> SizingResult:
    """
    Dynamic sizer. If pure_proportional is True or risk_profile is 'pure'/'pure_proportional',
    runs pure proportional sleeve sizing with no artificial multipliers or caps.
    Otherwise applies risk-capped sizing for backward compatibility.
    """
    if pure_proportional or (risk_profile and str(risk_profile).lower() in ('pure', 'pure_proportional', 'proportional')):
        return calculate_pure_proportional_order_size(
            user_balance=user_balance,
            n_active=n_active,
            whale_trade_usd=whale_trade_value,
            whale_pnl_or_net_worth=whale_portfolio_value,
            min_order_usd=min_order_usd,
            available_cash=available_cash
        )

    if user_balance <= 0:
        return SizingResult(value=0.0, status='SKIPPED_BELOW_MINIMUM')

    if n_active <= 0:
        return SizingResult(value=0.0, status='SKIPPED_NO_ACTIVE_WALLETS')
        
    base_notional = user_balance / n_active
    
    if whale_portfolio_value <= 0:
        return SizingResult(value=0.0, status='SKIPPED_INVALID_PORTFOLIO')
        
    whale_risk_pct = whale_trade_value / whale_portfolio_value
    raw_order_value = base_notional * whale_risk_pct
    
    risk_caps = {'conservative': 0.05, 'balanced': 0.10, 'aggressive': 0.20}
    max_allowed = user_balance * risk_caps.get(risk_profile.lower() if risk_profile else 'balanced', 0.10)
    
    order_value = min(raw_order_value, max_allowed)
    
    if order_value < min_order_usd:
        return SizingResult(value=0.0, status='SKIPPED_BELOW_MINIMUM')
        
    return SizingResult(value=round(order_value, 2), status='SUCCESS')
