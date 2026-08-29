def check_slippage(whale_price: float, current_price: float, side: str = "BUY") -> str:
    """
    Directional slippage validator:
    Allows favorable price improvements (discounts on BUY, higher fills on SELL).
    Rejects only adverse price moves that exceed category thresholds.
    """
    if whale_price <= 0:
        return 'EXECUTE_ORDER'
        
    if side.upper() == "BUY":
        adverse_pct = (current_price - whale_price) / whale_price
    else:
        adverse_pct = (whale_price - current_price) / whale_price

    if adverse_pct <= 0:
        return 'EXECUTE_ORDER'

    if whale_price <= 0.25 and adverse_pct > 0.012:
        return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
    elif whale_price <= 0.50 and adverse_pct > 0.02:
        return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
    elif adverse_pct > 0.03:
        return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
    return 'EXECUTE_ORDER'
