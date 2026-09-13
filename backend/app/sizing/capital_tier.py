import logging
from typing import List, Any, Optional, Dict

logger = logging.getLogger(__name__)

def get_target_wallet_count(capital_usd: float) -> int:
    """Roster upper limit; never fill it by relaxing qualification/diversity."""
    import math
    c = float(capital_usd or 0)
    if not math.isfinite(c) or c <= 0:
        return 0
    if c < 250:
        return 1
    if c < 1000:
        return 2
    if c < 3000:
        return 3
    if c < 10000:
        return 4
    return 5


def calculate_min_capital_required(
    whale_net_worth: float,
    median_trade_usd: float,
    min_order_usd: float = 1.0
) -> float:
    """
    Computes the minimum sleeve capital required so that this whale's typical/median
    bet size clears the Polymarket $1.00 minimum order floor without delay.
    
    Formula:
        f = median_trade_usd / max(1000.0, whale_net_worth)
        sleeve_min = min_order_usd / f
    """
    wnw = max(1000.0, float(whale_net_worth or 50000.0))
    mt = max(5.0, float(median_trade_usd or 250.0))
    f = mt / wnw
    if f <= 0.0:
        return 100.0
    sleeve_min = min_order_usd / f
    return round(max(50.0, min(1000.0, sleeve_min)), 2)

def filter_active_wallets_by_capital(
    wallets: List[Any], 
    capital_usd: float,
    wallet_histories: Optional[Dict[str, List[dict]]] = None,
    wallet_categories: Optional[Dict[str, str]] = None
) -> List[Any]:
    """
    Given a list of qualified active wallets ordered by Baleen score / tier,
    returns the exact top subset appropriate for the user's capital level.
    Applies Gate 13 (Category Concentration Cap <= 40%) and Gate 14 (Pairwise Correlation <= 0.70)
    within that tier's candidate pool before locking in the roster.
    """
    target_count = get_target_wallet_count(capital_usd)
    if not wallets:
        return []
    
    if not wallet_histories and not wallet_categories and all(isinstance(w, str) for w in wallets):
        return wallets[:target_count]
        
    from app.scoring.basket import select_top_10_roster
    return select_top_10_roster(
        candidates=wallets,
        current_incumbent_addresses=None,
        hysteresis_buffer=0.0,
        target_size=target_count,
        wallet_histories=wallet_histories,
        wallet_categories=wallet_categories
    )
