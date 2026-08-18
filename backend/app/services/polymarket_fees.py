"""
Polymarket Official Fee Engine (2026 Dynamic Quadratic Taker-Fee Model)

Polymarket utilizes a dynamic taker-fee model where fees scale quadratically
with market implied probability (price), reaching maximum at 50% ($0.50)
and tapering to 0 as probability approaches 0% or 100%:

    Fee (USDC) = Shares * Category_Rate * Price * (1 - Price)
               = (Notional / Price) * Category_Rate * Price * (1 - Price)
               = Notional * Category_Rate * (1 - Price)

Category Fee Rates:
- Crypto (including 15m Up/Down & High-Velocity Markets): 0.07 (7%)
- Sports (ATP, WTA, NBA, NFL, Soccer, MLB, Esports, etc.): 0.05 (5%)
- Economics, Culture, Weather, General: 0.05 (5%)
- Politics, Finance, Tech, Mentions: 0.04 (4%)
- Geopolitics: 0.00 (0% Permanently Fee-Free)

Maker Orders:
- 0.00% fee (0% for limit orders resting on the book, eligible for daily maker rebates).
"""

from typing import Dict, Any, Tuple

_CRYPTO_KEYWORDS = (
    "bitcoin", "btc", "ethereum", "eth", "solana", "sol", "xrp", "doge", "crypto",
    "up or down", "15m", "price of btc", "price of eth", "price of solana", "token", "airdrop"
)

_SPORTS_KEYWORDS = (
    "vs", "open:", "atp", "wta", "championship", "cup", "league", "fc", "real madrid",
    "barcelona", "arsenal", "chelsea", "manchester", "nba", "nfl", "mlb", "nhl", "ufc",
    "tennis", "set handicap", "match winner", "spread", "over/under", "esports", "f1",
    "formula 1", "grand prix", "lionel messi", "ronaldo", "alcaraz", "sinner", "djokovic"
)

_POLITICS_TECH_KEYWORDS = (
    "election", "president", "presidential", "senate", "house", "trump", "biden", "harris",
    "democrat", "republican", "fed ", "federal reserve", "interest rate", "cpi", "inflation",
    "apple", "google", "nvidia", "microsoft", "tesla", "elon musk", "musk", "tweet", "spacex",
    "openai", "anthropic", "gdp"
)

_GEOPOLITICS_KEYWORDS = (
    "war", "ceasefire", "treaty", "sanctions", "nato", "united nations", "un ", "taiwan",
    "ukraine", "russia", "gaza", "israel", "middle east", "invade", "peace agreement"
)


def classify_market_category(market_title: str) -> Tuple[str, float]:
    """
    Classifies a Polymarket prediction question into its fee category and rate.
    """
    title = (market_title or "").lower().strip()

    # 1. Check Geopolitics (0% Fee-Free)
    if any(k in title for k in _GEOPOLITICS_KEYWORDS):
        return "Geopolitics", 0.00

    # 2. Check Crypto (7% Dynamic Rate)
    if any(k in title for k in _CRYPTO_KEYWORDS):
        return "Crypto", 0.07

    # 3. Check Sports (5% Dynamic Rate)
    if any(k in title for k in _SPORTS_KEYWORDS):
        return "Sports", 0.05

    # 4. Check Politics / Finance / Tech (4% Dynamic Rate)
    if any(k in title for k in _POLITICS_TECH_KEYWORDS):
        return "Politics & Finance", 0.04

    # 5. Default General / Culture / Economics (5% Dynamic Rate)
    return "General", 0.05


def calculate_polymarket_fee(
    notional_usd: float,
    price: float,
    market_title: str,
    is_maker: bool = False
) -> Dict[str, Any]:
    """
    Calculates exact Polymarket taker/maker fee and effective rates for a trade.
    """
    if is_maker or notional_usd <= 0:
        category, rate = classify_market_category(market_title)
        return {
            "fee_usd": 0.0,
            "category": category,
            "category_rate": rate,
            "effective_fee_pct": 0.0,
            "is_maker": True,
            "maker_rebate_eligible": True
        }

    # Constrain price to valid probability range (0.001 - 0.999)
    p = max(0.001, min(0.999, float(price or 0.5)))
    category, rate = classify_market_category(market_title)

    # Dynamic Taker Fee Formula: Notional * Rate * (1 - Price)
    # Equivalent to: Shares * Rate * Price * (1 - Price)
    fee_usd = round(notional_usd * rate * (1.0 - p), 4)
    effective_pct = round((fee_usd / notional_usd) * 100.0, 3) if notional_usd > 0 else 0.0

    return {
        "fee_usd": fee_usd,
        "category": category,
        "category_rate": rate,
        "effective_fee_pct": effective_pct,
        "is_maker": False,
        "maker_rebate_eligible": False
    }
