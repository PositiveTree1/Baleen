def check_slippage(whale_price: float, current_price: float) -> str:
    """
    Slippage check from spec.
    """
    if whale_price <= 0:
        return 'EXECUTE_ORDER'
        
    diff = abs(current_price - whale_price) / whale_price
    if whale_price <= 0.25 and diff > 0.012:
        return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
    elif whale_price <= 0.50 and diff > 0.02:
        return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
    elif diff > 0.03:
        return 'CANCEL_ORDER: SLIPPAGE_EXCEEDED'
    return 'EXECUTE_ORDER'
