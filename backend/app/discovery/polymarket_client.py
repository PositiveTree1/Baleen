import httpx
import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
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
        backoff = 0.5
        
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
                if attempt == retries - 1:
                    logger.debug(f"HTTP Error fetching {url}: {e}")
                    return None
                await asyncio.sleep(backoff)
                backoff *= 2
            except Exception as e:
                logger.debug(f"Fetch error {url}: {e}")
                return None
        return None

    async def discover_candidates(self) -> Dict[str, Dict]:
        """
        Discovers candidate whale addresses using Titan's 3-pillar method:
        1. High-Value Buy Trades (Filter CASH >= $2,000)
        2. Multi-Period Leaderboards (ALL, MONTH, WEEK)
        3. Top Volume Active Markets + Market Trade Scraper
        Returns mapping of address_lower -> metadata
        """
        candidates: Dict[str, Dict] = {}

        # 1. Large Recent Buy Trades
        try:
            large_trades = await self._fetch_with_retry(f"{self.data_api_url}/trades", {
                "limit": 200,
                "filterType": "CASH",
                "filterAmount": 2000,
                "side": "BUY"
            })
            if large_trades and isinstance(large_trades, list):
                for t in large_trades:
                    w = (t.get("proxyWallet") or t.get("maker_address") or t.get("user") or "").lower()
                    if w and len(w) == 42 and w.startswith("0x"):
                        if w not in candidates:
                            candidates[w] = {
                                "address": w,
                                "source": "large_trade",
                                "trade_cash": float(t.get("usdcSize") or t.get("size", 0) * t.get("price", 1)),
                                "volume": float(t.get("usdcSize") or 50000) * 10
                            }
        except Exception as e:
            logger.debug(f"Large trades discovery error: {e}")

        # 2. Multi-Period Leaderboards (All, Month, Week)
        periods = ["all", "month", "week"]
        for p in periods:
            try:
                # Try v1/leaderboard and leaderboard
                lb_data = await self._fetch_with_retry(f"{self.data_api_url}/v1/leaderboard", {
                    "window": p,
                    "limit": 100
                })
                if not lb_data:
                    lb_data = await self._fetch_with_retry(f"{self.data_api_url}/leaderboard", {
                        "timePeriod": p.upper(),
                        "category": "OVERALL",
                        "orderBy": "PNL",
                        "limit": 100
                    })
                
                rows = []
                if isinstance(lb_data, list):
                    rows = lb_data
                elif isinstance(lb_data, dict):
                    rows = lb_data.get("data") or lb_data.get("results") or []

                for entry in rows:
                    if isinstance(entry, dict):
                        w = (entry.get("proxyWallet") or entry.get("address") or entry.get("user") or "").lower()
                        if w and len(w) == 42 and w.startswith("0x"):
                            pnl = float(entry.get("profile_profit") or entry.get("profit") or entry.get("pnl") or 0.0)
                            vol = float(entry.get("profile_volume") or entry.get("volume") or 0.0)
                            name = entry.get("name") or entry.get("username") or ""
                            if w not in candidates or pnl > (candidates[w].get("profit") or 0):
                                candidates[w] = {
                                    "address": w,
                                    "source": f"leaderboard_{p}",
                                    "profit": pnl,
                                    "volume": vol,
                                    "name": name,
                                    "rank": entry.get("rank")
                                }
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.debug(f"Leaderboard {p} discovery error: {e}")

        # 3. Top Volume Active Markets Holder Scan
        try:
            market_data = await self._fetch_with_retry(f"{self.gamma_api_url}/markets", {
                "limit": 60,
                "active": "true"
            })
            if market_data and isinstance(market_data, list):
                # Sort by volume descending, take top 15
                top_mkts = sorted(market_data, key=lambda m: float(m.get("volume") or 0), reverse=True)[:15]
                for m in top_mkts:
                    cid = m.get("conditionId") or m.get("condition_id")
                    if not cid:
                        continue
                    m_trades = await self._fetch_with_retry(f"{self.data_api_url}/trades", {
                        "conditionId": cid,
                        "limit": 40,
                        "filterType": "CASH",
                        "side": "BUY",
                        "filterAmount": 500
                    })
                    if m_trades and isinstance(m_trades, list):
                        for t in m_trades:
                            w = (t.get("proxyWallet") or t.get("maker_address") or t.get("user") or "").lower()
                            if w and len(w) == 42 and w.startswith("0x") and w not in candidates:
                                candidates[w] = {
                                    "address": w,
                                    "source": "market_scan",
                                    "volume": float(t.get("usdcSize") or 5000) * 8
                                }
                    await asyncio.sleep(0.05)
        except Exception as e:
            logger.debug(f"Market scan error: {e}")

        logger.info(f"Titan discovery yielded {len(candidates)} unique whale candidates.")
        return candidates

    async def fetch_wallet_trades(self, address: str, max_trades: int = 4000) -> List[Dict]:
        """Pulls multi-page trade history up to 4,000 trades for a wallet."""
        all_trades = []
        batch_size = 500
        offset = 0
        
        while len(all_trades) < max_trades:
            url = f"{self.data_api_url}/trades"
            data = await self._fetch_with_retry(url, params={"user": address, "limit": batch_size, "offset": offset})
            trades_batch = []
            if isinstance(data, list):
                trades_batch = data
            elif isinstance(data, dict):
                trades_batch = data.get("data") or data.get("results") or []
                
            if not trades_batch and offset == 0:
                data_maker = await self._fetch_with_retry(url, params={"maker_address": address, "limit": batch_size})
                if isinstance(data_maker, list):
                    trades_batch = data_maker
                elif isinstance(data_maker, dict):
                    trades_batch = data_maker.get("data") or data_maker.get("results") or []
                    
            if not trades_batch:
                break
                
            all_trades.extend(trades_batch)
            if len(trades_batch) < batch_size:
                break
                
            offset += len(trades_batch)
            await asyncio.sleep(0.05)
            
        return all_trades

    async def fetch_wallet_activity(self, address: str, max_items: int = 1000) -> List[Dict]:
        """Pulls trade closures and redemptions from Polymarket activity endpoint."""
        all_activity = []
        batch_size = 500
        offset = 0
        while len(all_activity) < max_items:
            url = f"{self.data_api_url}/activity"
            data = await self._fetch_with_retry(url, params={
                "user": address,
                "type": "REDEEM",
                "limit": batch_size,
                "offset": offset,
                "sortBy": "TIMESTAMP",
                "sortDirection": "DESC"
            })
            batch = []
            if isinstance(data, list):
                batch = data
            elif isinstance(data, dict):
                batch = data.get("data") or data.get("results") or []
            if not batch:
                break
            all_activity.extend(batch)
            if len(batch) < batch_size:
                break
            offset += len(batch)
            await asyncio.sleep(0.05)
        return all_activity

    async def fetch_order_book(self, token_id: str) -> Optional[Dict]:
        url = f"{self.clob_api_url}/book"
        return await self._fetch_with_retry(url, params={"token_id": token_id})

    async def fetch_market_info(self, condition_id: str) -> Optional[Dict]:
        url = f"{self.gamma_api_url}/markets"
        data = await self._fetch_with_retry(url, params={"condition_id": condition_id})
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return None
