from dataclasses import dataclass

@dataclass
class FillResult:
    avg_price: float
    total_filled: float
    slippage_pct: float
    levels_consumed: int

def simulate_fill(order_value_usd: float, order_book: dict, side: str, latency_ms: int = 1000) -> FillResult:
    """
    Simulated fill model from §5.1.
    Walk the real order book (asks for BUY, bids for SELL).
    Apply latency penalty before the snapshot.
    Calculate weighted average fill price across levels.
    """
    # In a real app we'd apply latency penalities (e.g., stripping best levels)
    # For now, just a basic depth walk.
    
    is_buy = str(side).upper() == "BUY"
    raw_levels = order_book.get("asks" if is_buy else "bids", [])
    
    # Sort levels (ascending for asks, descending for bids) without mutating caller's order book
    levels = sorted(raw_levels, key=lambda x: float(x.get("price", 0)), reverse=not is_buy)
        
    if not levels:
        return FillResult(avg_price=0.0, total_filled=0.0, slippage_pct=0.0, levels_consumed=0)
        
    remaining_value = order_value_usd
    total_shares = 0.0
    weighted_price_sum = 0.0
    levels_consumed = 0
    
    best_price = float(levels[0].get("price", 0))
    
    for level in levels:
        if remaining_value <= 0:
            break
            
        price = float(level.get("price", 0))
        size = float(level.get("size", 0))
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
        return FillResult(avg_price=0.0, total_filled=0.0, slippage_pct=0.0, levels_consumed=0)
        
    avg_price = weighted_price_sum / total_shares
    total_filled = order_value_usd - remaining_value
    
    if best_price > 0:
        slippage_pct = abs(avg_price - best_price) / best_price
    else:
        slippage_pct = 0.0
        
    return FillResult(
        avg_price=avg_price,
        total_filled=total_filled,
        slippage_pct=slippage_pct,
        levels_consumed=levels_consumed
    )
