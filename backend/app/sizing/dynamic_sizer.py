from dataclasses import dataclass

@dataclass
class SizingResult:
    value: float
    status: str

def size_trade(user_balance: float, risk_profile: str, n_active: int, whale_trade_value: float, whale_portfolio_value: float, min_order_usd: float = 5.0) -> SizingResult:
    """
    Exact implementation of §5 dynamic sizer.
    """
    if n_active <= 0:
        return SizingResult(value=0, status='SKIPPED_NO_ACTIVE_WALLETS')
        
    base_notional = user_balance / n_active
    
    if whale_portfolio_value <= 0:
        return SizingResult(value=0, status='SKIPPED_INVALID_PORTFOLIO')
        
    whale_risk_pct = whale_trade_value / whale_portfolio_value
    raw_order_value = base_notional * whale_risk_pct
    
    risk_caps = {'conservative': 0.05, 'balanced': 0.10, 'aggressive': 0.20}
    max_allowed = user_balance * risk_caps.get(risk_profile, 0.10)
    
    order_value = min(raw_order_value, max_allowed)
    
    if order_value < min_order_usd:
        return SizingResult(value=0, status='SKIPPED_BELOW_MINIMUM')
        
    return SizingResult(value=round(order_value, 2), status='SUCCESS')
