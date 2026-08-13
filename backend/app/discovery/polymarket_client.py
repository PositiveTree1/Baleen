import httpx
import asyncio
import logging
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class PolymarketClient:
    def __init__(self):
        self.data_api_url = settings.POLYMARKET_DATA_API_URL
        self.clob_api_url = settings.CLOB_API_URL
        self.gamma_api_url = settings.GAMMA_API_URL
        self.client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        await self.client.aclose()

    async def _fetch_with_retry(self, url: str, params: Dict = None) -> Any:
        retries = 3
        backoff = 1.0
        
        for attempt in range(retries):
            try:
                response = await self.client.get(url, params=params)
                if response.status_code == 429:
                    logger.warning(f"Rate limited by {url}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"HTTP Error fetching {url}: {e}")
                if attempt == retries - 1:
                    return None
                await asyncio.sleep(backoff)
                backoff *= 2
        return None

    async def fetch_recent_trades(self, limit: int = 500) -> List[Dict]:
        url = f"{self.data_api_url}/trades"
        data = await self._fetch_with_retry(url, params={"limit": limit})
        return data if isinstance(data, list) else []

    async def fetch_leaderboard(self, window: str = 'all', limit: int = 100) -> List[Dict]:
        url = f"{self.data_api_url}/v1/leaderboard"
        data = await self._fetch_with_retry(url, params={"window": window, "limit": limit})
        return data if isinstance(data, list) else []

    async def fetch_wallet_trades(self, address: str, limit: int = 500) -> List[Dict]:
        url = f"{self.data_api_url}/trades"
        data = await self._fetch_with_retry(url, params={"maker": address, "limit": limit})
        return data if isinstance(data, list) else []

    async def fetch_order_book(self, token_id: str) -> Optional[Dict]:
        url = f"{self.clob_api_url}/book"
        return await self._fetch_with_retry(url, params={"token_id": token_id})

    async def fetch_market_info(self, condition_id: str) -> Optional[Dict]:
        url = f"{self.gamma_api_url}/markets"
        data = await self._fetch_with_retry(url, params={"condition_id": condition_id})
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return None
