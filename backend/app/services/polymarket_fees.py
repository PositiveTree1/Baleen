"""
Polymarket Dynamic Fee Schedule & Architecture Engine (2026 Official Spec)

Formula:
    Fee (USD) = Theta * C * p * (1 - p)
              = Theta * Notional * (1 - p)

Where:
    - C = Number of contracts/shares = Notional / p
    - p = Trade fill price (0.01 <= p <= 0.99)
    - Theta = Category fee coefficient
    - Effective Fee Rate (%) = Theta * (1 - p) * 100%

Theta Coefficients (2026 Schedule):
    - Crypto: 0.072 (Max effective rate: 3.60%)
    - Economics / Finance: 0.060 (Max effective rate: 3.00%)
    - Culture, Weather & Tech: 0.050 (Max effective rate: 2.50%)
    - Politics: 0.040 (Max effective rate: 2.00%)
    - Sports: 0.030 (Max effective rate: 1.50%)
    - Geopolitics & Macro World Events: 0.000 (0% Fee-Free)

Rounding Rule:
    - Banker's Rounding (ROUND_HALF_EVEN) to nearest cent ($0.01).
"""

import decimal
from typing import Dict, Any, Tuple

_CRYPTO_KEYWORDS = (
    "bitcoin", "btc", "ethereum", "eth", "solana", "sol", "xrp", "doge", "crypto",
    "up or down", "15m", "price of btc", "price of eth", "price of solana", "token", "airdrop"
)

_ECONOMICS_FINANCE_KEYWORDS = (
    "fed ", "federal reserve", "interest rate", "cpi", "inflation", "gdp", "recession",
    "unemployment", "treasury", "s&p", "nasdaq", "dow jones", "stock", "yield"
)

_CULTURE_TECH_KEYWORDS = (
    "apple", "google", "nvidia", "microsoft", "tesla", "elon musk", "musk", "tweet", "spacex",
    "openai", "anthropic", "weather", "temperature", "oscar", "grammy", "movie", "gta 6"
)

_POLITICS_KEYWORDS = (
    "election", "president", "presidential", "senate", "house", "trump", "biden", "harris",
    "democrat", "republican", "primary", "governor", "vote", "voter", "ballot"
)

_SPORTS_KEYWORDS = (
    "vs", "open:", "atp", "wta", "championship", "cup", "league", "fc", "real madrid",
    "barcelona", "arsenal", "chelsea", "manchester", "nba", "nfl", "mlb", "nhl", "ufc",
    "tennis", "set handicap", "match winner", "spread", "over/under", "esports", "f1",
    "formula 1", "grand prix", "lionel messi", "ronaldo", "alcaraz", "sinner", "djokovic"
)

_GEOPOLITICS_KEYWORDS = (
    "war", "ceasefire", "treaty", "sanctions", "nato", "united nations", "un ", "taiwan",
    "ukraine", "russia", "gaza", "israel", "middle east", "invade", "peace agreement", "military"
)


def classify_market_category(market_title: str) -> Tuple[str, float]:
    """
    Classifies a prediction question into its 2026 Polymarket fee category and Theta coefficient.
    """
    title = (market_title or "").lower().strip()

    # 1. Geopolitics & World Events (0% Fee-Free)
    if any(k in title for k in _GEOPOLITICS_KEYWORDS):
        return "Geopolitics", 0.000

    # 2. Crypto (Theta = 0.072)
    if any(k in title for k in _CRYPTO_KEYWORDS):
        return "Crypto", 0.072

    # 3. Economics / Finance (Theta = 0.060)
    if any(k in title for k in _ECONOMICS_FINANCE_KEYWORDS):
        return "Economics / Finance", 0.060

    # 4. Politics (Theta = 0.040)
    if any(k in title for k in _POLITICS_KEYWORDS):
        return "Politics", 0.040

    # 5. Sports (Theta = 0.030)
    if any(k in title for k in _SPORTS_KEYWORDS):
        return "Sports", 0.030

    # 6. Culture, Weather & Tech (Theta = 0.050)
    if any(k in title for k in _CULTURE_TECH_KEYWORDS):
        return "Culture, Weather & Tech", 0.050

    # Default Culture / General (Theta = 0.050)
    return "General", 0.050


def calculate_polymarket_fee(
    notional_usd: float,
    price: float,
    market_title: str,
    is_maker: bool = False
) -> Dict[str, Any]:
    """
    Calculates exact Polymarket taker/maker fee using Banker's Rounding (ROUND_HALF_EVEN).
    """
    category, theta = classify_market_category(market_title)

    if is_maker or notional_usd <= 0 or theta == 0.0:
        return {
            "fee_usd": 0.0,
            "category": category,
            "category_rate": theta,
            "effective_fee_pct": 0.0,
            "is_maker": is_maker,
            "maker_rebate_eligible": True
        }

    p = max(0.001, min(0.999, float(price) if price is not None else 0.5))
    
    # Dynamic Taker Fee: Fee = Theta * Notional * (1 - p)
    raw_fee = notional_usd * theta * (1.0 - p)
    
    # Banker's Rounding (round half to even)
    d_fee = decimal.Decimal(str(raw_fee)).quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_EVEN)
    fee_usd = float(d_fee)
    
    effective_pct = round((fee_usd / notional_usd) * 100.0, 3) if notional_usd > 0 else 0.0

    return {
        "fee_usd": fee_usd,
        "category": category,
        "category_rate": theta,
        "effective_fee_pct": effective_pct,
        "is_maker": False,
        "maker_rebate_eligible": False
    }


def calculate_fee_aware_ev_gate(price: float, market_title: str, expected_edge: float) -> Tuple[bool, float, float]:
    """
    EV_net Gate Rule:
    Do not copy if Expected Edge does not clear 2.5x the taker fee rate:
    Expected Edge > 2.5 * [Theta * (1 - p)]
    
    Returns: (should_pass: bool, fee_rate: float, min_required_edge: float)
    """
    _, theta = classify_market_category(market_title)
    p = max(0.001, min(0.999, float(price) if price is not None else 0.5))
    
    fee_rate = theta * (1.0 - p)
    min_required_edge = 2.5 * fee_rate
    
    should_pass = (expected_edge >= min_required_edge)
    return should_pass, round(fee_rate, 4), round(min_required_edge, 4)
