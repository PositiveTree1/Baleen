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
    if not client:
        logger.warning("No Groq API keys configured")
        return None, None

    pnl = wallet_stats.get('all_time_pnl_usd', 0)
    win_rate = wallet_stats.get('win_rate_pct', 0)
    trades_per_day = wallet_stats.get('avg_trades_per_day', 0)
    max_dd = wallet_stats.get('max_drawdown_pct', 0)
    total_trades = wallet_stats.get('total_trades_analyzed', 100)

    prompt = f"""
    You are an expert quantitative hedge fund analyst evaluating a top Polymarket prediction market trader.
    Provide a concise 2-sentence executive summary detailing their trading edge, positioning conviction, and risk control.
    Then, provide a high-conviction 2-3 word style tag (e.g. 'High-Conviction Sniper', 'Macro Event Scalper', 'Asymmetric Alpha Hunter', 'Momentum Trend Whale').

    Metrics:
    - Realized PnL: ${pnl:,.2f}
    - Win Rate: {win_rate}%
    - Average Daily Activity: {trades_per_day} trades/day
    - Historical Max Drawdown: {max_dd}%
    - Total Trades Analyzed: {total_trades}

    Output format EXACTLY:
    SUMMARY: <2 punchy, analytical sentences detailing their edge, profit consistency, and risk discipline>
    TAG: <2-3 word uppercase tag>
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
            
            for line in response_text.split('\n'):
                line = line.strip().replace('**', '')
                if line.upper().startswith("SUMMARY:"):
                    summary = line[line.upper().index("SUMMARY:") + 8:].strip()
                elif line.upper().startswith("TAG:"):
                    tag = line[line.upper().index("TAG:") + 4:].strip()
                    
            if summary:
                if not tag:
                    tag = "Alpha Whale"
                return summary, tag

        except Exception as e:
            logger.error(f"Error generating AI summary with {model_name}: {e}")

    # Fallback to analytical template if Groq API rate limits
    summary = f"Systematic quantitative prediction trader exhibiting ${pnl:,.0f} realized profit and {win_rate:.1f}% accuracy with disciplined risk control."
    tag = "High-Conviction Sniper" if win_rate >= 80 else "Macro Whale"
    return summary, tag

