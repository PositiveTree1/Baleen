def check_dormancy(hours_since_last_trade: float, median_inter_trade_gap_hours: float) -> bool:
    """
    Check if a wallet is dormant based on §4.1:
    A wallet is dormant if hours_since_last_trade > 8 * median_inter_trade_gap_hours.
    """
    if median_inter_trade_gap_hours is None or median_inter_trade_gap_hours <= 0:
        return False
    return hours_since_last_trade > 8 * median_inter_trade_gap_hours
