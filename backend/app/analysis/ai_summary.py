import re
import logging
from typing import Tuple, Optional
from groq import AsyncGroq
from app.config import settings
import random

logger = logging.getLogger(__name__)

def get_groq_client() -> Optional[AsyncGroq]:
    keys = [
        settings.GROQ_API_KEY_1,
        settings.GROQ_API_KEY_2,
        settings.GROQ_API_KEY_3
    ]
    valid_keys = [k for k in keys if k]
    if not valid_keys:
        return None
        
    selected_key = random.choice(valid_keys)
    return AsyncGroq(api_key=selected_key)

async def generate_summary(wallet_stats: dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Generates a rich, institutional-grade AI behavioral analysis of the trader.
    Returns (summary, style_tag)
    """
    client = get_groq_client()
    pnl = wallet_stats.get('all_time_pnl_usd', 0)
    win_rate = wallet_stats.get('win_rate_pct', 0)
    trades_per_day = wallet_stats.get('avg_trades_per_day', 0)
    max_dd = wallet_stats.get('max_drawdown_pct', 0)
    total_trades = wallet_stats.get('total_trades_analyzed', 100)

    if not client:
        fallback_summary = f"Institutional Polymarket trader with ${pnl:,.0f} all-time PnL and {win_rate}% win rate across {total_trades} trades."
        fallback_tag = "Alpha Whale" if pnl >= 100000 else "Standard Whale"
        return fallback_summary, fallback_tag

    prompt = f"""
    You are an expert quantitative hedge fund analyst evaluating a top Polymarket prediction market trader.
    Provide a concise 2-sentence executive summary detailing their trading edge, positioning conviction, and risk control.
    Then, provide a high-conviction 2-3 word style tag.

    Metrics:
    - Realized PnL: ${pnl:,.2f}
    - Win Rate: {win_rate}%
    - Average Daily Activity: {trades_per_day} trades/day
    - Historical Max Drawdown: {max_dd}%
    - Total Trades Analyzed: {total_trades}

    Respond ONLY in this exact format with real analytical content (never output angle brackets or template placeholders):
    SUMMARY: The trader exhibits systematic risk management and strong predictive edge across audited markets. Positioning is characterized by disciplined capital deployment.
    TAG: High-Conviction Sniper
    """
    
    for model_name in ["groq/compound-mini", "qwen/qwen3.6-27b"]:
        try:
            completion = await client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
                temperature=0.3,
                max_tokens=250
            )
            response_text = completion.choices[0].message.content or ""
            
            # Remove any thinking block if present
            if "</think>" in response_text:
                response_text = response_text.split("</think>")[-1].strip()

            summary = None
            tag = None
            
            # Robust extraction: regex or prefix matching
            summary_match = re.search(r'(?:SUMMARY|Executive Summary):\s*(.*?)(?=\n(?:TAG|Tag):|\Z)', response_text, re.DOTALL | re.IGNORECASE)
            if summary_match:
                summary = summary_match.group(1).strip().replace('**', '').replace('\n', ' ')
            
            tag_match = re.search(r'(?:TAG|Style Tag):\s*([^\n\r]+)', response_text, re.IGNORECASE)
            if tag_match:
                tag = tag_match.group(1).strip().replace('**', '').strip('"\'')

            # Fallback if format wasn't strictly followed
            if not summary and response_text:
                clean_lines = [l.strip() for l in response_text.split('\n') if l.strip() and not l.upper().startswith(('TAG:', 'METRICS:', 'HERE IS', '1.', '2.'))]
                if clean_lines:
                    summary = " ".join(clean_lines[:2])

            # Sanitize and strip placeholders
            if tag:
                tag = re.sub(r'[<\[].*?[>\]]', '', tag).strip()
                tag = tag.replace('TAG:', '').replace('Style Tag:', '').strip()
                if any(placeholder in tag.upper() for placeholder in ["WORD", "UPPERCASE", "TAG", "PLACEHOLDER", "PUNCHY"]):
                    tag = None

            if summary:
                summary = re.sub(r'[<\[].*?[>\]]', '', summary).strip()
                summary = re.sub(r'^(?:SUMMARY|Executive Summary):\s*', '', summary, flags=re.IGNORECASE).strip()
                if any(bad in summary for bad in ["Metrics Provided:", "Deconstruct Metrics", "2 punchy", "analytical sentences"]):
                    summary = None

            if summary and len(summary) > 20:
                if not tag or len(tag) < 3:
                    tag = "High-Conviction Sniper" if win_rate >= 80 else "Macro Alpha Whale"
                return summary, tag

        except Exception as e:
            logger.error(f"Error generating AI summary with {model_name}: {e}")

    # Fallback to analytical template if Groq API rate limits
    if win_rate >= 80:
        summary = f"High-precision tactical sniper maintaining {win_rate:.1f}% accuracy across {total_trades} audited positions with ${pnl:,.0f} net realized profit and disciplined drawdown management."
        tag = "High-Conviction Sniper"
    elif trades_per_day >= 8:
        summary = f"High-volume systematic market participant generating ${pnl:,.0f} in net profit across high-velocity event contracts with consistent liquidity positioning."
        tag = "Momentum Scalper"
    else:
        summary = f"Institutional macro trader exhibiting ${pnl:,.0f} lifetime profit and {win_rate:.1f}% win rate with strong asymmetric risk-reward execution."
        tag = "Macro Alpha Whale"
        
    return summary, tag


