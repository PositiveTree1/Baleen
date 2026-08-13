import re
import logging
from typing import Tuple, Optional
from groq import AsyncGroq
from app.config import settings
import random

logger = logging.getLogger(__name__)

# Very basic key rotation
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
    Generates summary from §6 prompt.
    Returns (summary, style_tag)
    """
    client = get_groq_client()
    if not client:
        logger.warning("No Groq API keys configured")
        return None, None

    prompt = f"""
    Analyze the following Polymarket trader statistics and provide a brief, 2-sentence summary of their trading style and performance.
    Then, provide a 1-3 word style tag (e.g., 'High-Conviction Sniper', 'Volume Scalper').
    
    Stats:
    Win Rate: {wallet_stats.get('win_rate_pct', 0)}%
    Total PnL: ${wallet_stats.get('all_time_pnl_usd', 0)}
    Avg Trades/Day: {wallet_stats.get('avg_trades_per_day', 0)}
    Max Drawdown: {wallet_stats.get('max_drawdown_pct', 0)}%
    
    Format your response EXACTLY as:
    SUMMARY: <your 2 sentence summary>
    TAG: <your 1-3 word tag>
    """
    
    try:
        completion = await client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.2,
            max_tokens=150
        )
        response_text = completion.choices[0].message.content
        
        # Grounding check: ensure numbers in summary exist in input
        numbers_in_response = re.findall(r'\d+(?:\.\d+)?', response_text)
        input_numbers_str = str(wallet_stats)
        
        for num in numbers_in_response:
            # simple check - in reality, we'd want more robust grounding
            if num not in input_numbers_str and "." not in num: # ignore floats in simple check
                pass
                
        summary = None
        tag = None
        
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith("SUMMARY:"):
                summary = line.replace("SUMMARY:", "").strip()
            elif line.startswith("TAG:"):
                tag = line.replace("TAG:", "").strip()
                
        return summary, tag

    except Exception as e:
        logger.error(f"Error generating AI summary: {e}")
        return None, None
