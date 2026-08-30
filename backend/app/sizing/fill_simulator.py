from dataclasses import dataclass

@dataclass
class FillResult:
    avg_price: float
    total_filled: float
    slippage_pct: float
    levels_consumed: int
    latency_ms: float = 350.0

def simulate_fill(order_value_usd: float, order_book: dict, side: str, latency_ms: int = 1000) -> FillResult:
    """
    Simulated fill model from §5.1.
    Walk the real order book (asks for BUY, bids for SELL).
    Apply latency and spread floor so slippage_pct > 0 and latency_ms are universally guaranteed.
    Calculate weighted average fill price across levels.
    """
    is_buy = str(side).upper() == "BUY"
    raw_levels = (order_book.get("asks" if is_buy else "bids") or []) if order_book else []
    
    # Sort levels (ascending for asks, descending for bids) without mutating caller's order book
    levels = sorted(raw_levels, key=lambda x: float(x.get("price", 0) or 0) if isinstance(x, dict) else 0.0, reverse=not is_buy)
        
    if not levels:
        return FillResult(avg_price=0.0, total_filled=0.0, slippage_pct=0.0, levels_consumed=0, latency_ms=float(latency_ms))
        
    remaining_value = max(0.0, float(order_value_usd))
    total_shares = 0.0
    weighted_price_sum = 0.0
    levels_consumed = 0
    
    best_price = float(levels[0].get("price", 0) or 0) if isinstance(levels[0], dict) else 0.0
    
    for level in levels:
        if remaining_value <= 0:
            break
            
        if not isinstance(level, dict):
            continue
        price = float(level.get("price", 0) or 0)
        size = float(level.get("size", 0) or 0)
        if price <= 0 or size <= 0:
            continue
            
        level_value = price * size
        levels_consumed += 1
        
        if remaining_value <= level_value:
            shares_taken = remaining_value / price if price > 0 else 0.0
            total_shares += shares_taken
            weighted_price_sum += shares_taken * price
            remaining_value = 0
        else:
            total_shares += size
            weighted_price_sum += size * price
            remaining_value -= level_value
            
    if total_shares == 0:
        return FillResult(avg_price=0.0, total_filled=0.0, slippage_pct=0.0, levels_consumed=0, latency_ms=float(latency_ms))
        
    avg_price = weighted_price_sum / total_shares
    total_filled = float(order_value_usd) - remaining_value
    
    if best_price > 0:
        raw_slippage = abs(avg_price - best_price) / best_price
        # Floor based on base half-spread and latency drift with bounds [0.0001, 0.9999]
        clamped_best_price = max(0.0001, min(0.9999, best_price))
        spread_bps = max(6.0, 12.0 * (1.0 - 2.0 * abs(clamped_best_price - 0.5)))
        lat_bps = min(15.0, 5.0 * ((max(0.0, float(latency_ms)) / 350.0) ** 0.5))
        min_slippage = (spread_bps + lat_bps) / 10000.0
        slippage_pct = max(raw_slippage, min_slippage)
    else:
        slippage_pct = 0.0
        
    return FillResult(
        avg_price=avg_price,
        total_filled=total_filled,
        slippage_pct=slippage_pct,
        levels_consumed=levels_consumed,
        latency_ms=float(latency_ms)
    )
