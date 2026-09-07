import logging
from typing import List, Any

logger = logging.getLogger(__name__)

def get_target_wallet_count(capital_usd: float) -> int:
    """
    Computes the optimal number of wallets to copy based on total available capital.
    
    Tiers:
      - Under $250: Follow 1 Top Wallet (100% sleeve = $100-$250)
      - $250 to $1,000: Follow 2 Top Wallets ($125-$500 sleeve)
      - $1,000 to $3,000: Follow 4 Top Wallets ($250-$750 sleeve)
      - $3,000 to $5,000: Follow 6 Wallets ($500-$833 sleeve)
      - $5,000+: Follow 10 Wallets ($500-$1,000+ sleeve)
    """
    c = max(0.0, float(capital_usd or 0.0))
    if c < 250.0:
        return 1
    elif c < 1000.0:
        return 2
    elif c < 3000.0:
        return 4
    elif c < 5000.0:
        return 6
    else:
        return 10

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

def filter_active_wallets_by_capital(wallets: List[Any], capital_usd: float) -> List[Any]:
    """
    Given a list of qualified active wallets ordered by Baleen score / tier,
    returns the exact top subset appropriate for the user's capital level.
    """
    target_count = get_target_wallet_count(capital_usd)
    return wallets[:target_count]
