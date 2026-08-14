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

    async def fetch_recent_trades(self, limit: int = 1000) -> List[Dict]:
        url = f"{self.data_api_url}/trades"
        data = await self._fetch_with_retry(url, params={"limit": limit})
        return data if isinstance(data, list) else []

    async def fetch_high_volume_market_trades(self, max_trades: int = 3000) -> List[Dict]:
        """Pulls large batches of recent Polymarket market trades to discover active volume whales."""
        all_trades = []
        batch_size = 500
        offset = 0
        while len(all_trades) < max_trades:
            url = f"{self.data_api_url}/trades"
            data = await self._fetch_with_retry(url, params={"limit": batch_size, "offset": offset})
            batch = []
            if isinstance(data, list):
                batch = data
            elif isinstance(data, dict):
                batch = data.get("data") or data.get("results") or []
            if not batch:
                break
            all_trades.extend(batch)
            if len(batch) < batch_size:
                break
            offset += len(batch)
            await asyncio.sleep(0.05)
        return all_trades

    async def fetch_leaderboard(self, window: str = 'all', limit: int = 100) -> List[Dict]:
        url = f"{self.data_api_url}/v1/leaderboard"
        data = await self._fetch_with_retry(url, params={"window": window, "limit": limit})
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("data") or data.get("results") or []
        return []

    async def fetch_all_leaderboard_windows(self) -> List[Dict]:
        """Fetches all-time, monthly, and weekly leaderboards to capture the entire whale landscape."""
        windows = ['all', 'month', 'week']
        combined = []
        seen = set()
        for w in windows:
            entries = await self.fetch_leaderboard(window=w, limit=100)
            for e in entries:
                if isinstance(e, dict):
                    addr = e.get("proxyWallet") or e.get("address") or e.get("user")
                    if addr and addr.lower() not in seen:
                        seen.add(addr.lower())
                        combined.append(e)
        return combined

    async def fetch_wallet_trades(self, address: str, max_trades: int = 4000) -> List[Dict]:
        all_trades = []
        batch_size = 500
        offset = 0
        
        while len(all_trades) < max_trades:
            url = f"{self.data_api_url}/trades"
            data = await self._fetch_with_retry(url, params={"maker_address": address, "limit": batch_size, "offset": offset})
            trades_batch = []
            if isinstance(data, list):
                trades_batch = data
            elif isinstance(data, dict):
                trades_batch = data.get("data") or data.get("results") or []
                
            if not trades_batch and offset == 0:
                data_user = await self._fetch_with_retry(url, params={"user": address, "limit": batch_size})
                if isinstance(data_user, list):
                    trades_batch = data_user
                elif isinstance(data_user, dict):
                    trades_batch = data_user.get("data") or data_user.get("results") or []
                    
            if not trades_batch:
                break
                
            all_trades.extend(trades_batch)
            if len(trades_batch) < batch_size:
                break
                
            offset += len(trades_batch)
            await asyncio.sleep(0.05)
            
        return all_trades

    async def fetch_order_book(self, token_id: str) -> Optional[Dict]:
        url = f"{self.clob_api_url}/book"
        return await self._fetch_with_retry(url, params={"token_id": token_id})

    async def fetch_market_info(self, condition_id: str) -> Optional[Dict]:
        url = f"{self.gamma_api_url}/markets"
        data = await self._fetch_with_retry(url, params={"condition_id": condition_id})
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return None
