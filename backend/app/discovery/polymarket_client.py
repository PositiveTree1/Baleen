import httpx
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Set
from app.config import settings

logger = logging.getLogger(__name__)

def _to_decimal_token(asset: str) -> str:
    if not asset:
        return ""
    a = str(asset).strip()
    try:
        if a.startswith("0x") or a.startswith("0X"):
            return str(int(a, 16))
        return str(int(a))
    except Exception:
        return a

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
        backoff = 1.2
        
        for attempt in range(retries):
            try:
                response = await self.client.get(url, params=params)
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", backoff))
                    logger.debug(f"Rate limited by {url}. Backing off {retry_after:.1f}s...")
                    await asyncio.sleep(retry_after)
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
                    if w and len(w) == 42 and w.startswith("0x") and w not in candidates:
                        trade_cash = float(t.get("usdcSize") or (float(t.get("size", 0)) * float(t.get("price", 1))))
                        candidates[w] = {
                            "address": w,
                            "source": "large_trade",
                            "trade_cash": trade_cash,
                            "volume": trade_cash * 10
                        }
        except Exception as e:
            logger.debug(f"Large trades discovery error: {e}")

        # 1. Paginated Multi-Period Leaderboards (ALL, MONTH, WEEK)
        for period in ["ALL", "MONTH", "WEEK"]:
            for offset in [0, 100, 200]:
                try:
                    lb_data = await self._fetch_with_retry(f"{self.data_api_url}/leaderboard", {
                        "timePeriod": period,
                        "category": "OVERALL",
                        "orderBy": "PNL",
                        "limit": 100,
                        "offset": offset
                    })
                    rows = lb_data if isinstance(lb_data, list) else (lb_data.get("data") or lb_data.get("results") or []) if isinstance(lb_data, dict) else []
                    for entry in rows:
                        if isinstance(entry, dict):
                            w = (entry.get("proxyWallet") or entry.get("address") or entry.get("user") or "").lower()
                            if w and len(w) == 42 and w.startswith("0x"):
                                pnl = float(entry.get("profile_profit") or entry.get("profit") or entry.get("pnl") or 0.0)
                                vol = float(entry.get("profile_volume") or entry.get("volume") or 0.0)
                                name = entry.get("name") or entry.get("username") or ""
                                if w not in candidates:
                                    candidates[w] = {
                                        "address": w,
                                        "source": f"leaderboard_{period.lower()}",
                                        "profit": pnl,
                                        "volume": vol if vol > 0 else pnl * 5,
                                        "name": name,
                                        "rank": entry.get("rank")
                                    }
                    await asyncio.sleep(0.04)
                except Exception as e:
                    logger.debug(f"Leaderboard {period} offset {offset} error: {e}")

        # 3. High-Value Large Trades Discovery
        try:
            top_trades = await self._fetch_with_retry(f"{self.data_api_url}/trades", {
                "limit": 200,
                "filterType": "CASH",
                "filterAmount": 1000,
                "side": "BUY"
            })
            if top_trades and isinstance(top_trades, list):
                for t in top_trades:
                    w = (t.get("proxyWallet") or t.get("maker_address") or t.get("user") or "").lower()
                    if w and len(w) == 42 and w.startswith("0x") and w not in candidates:
                        cash = float(t.get("usdcSize") or t.get("size", 0) * t.get("price", 1))
                        candidates[w] = {
                            "address": w,
                            "source": "large_trade",
                            "trade_cash": cash,
                            "profit": 0.0,
                            "volume": cash * 5
                        }
        except Exception as e:
            logger.debug(f"Large trades discovery error: {e}")

        # 4. Top Volume Active Markets Scan
        try:
            market_data = await self._fetch_with_retry(f"{self.gamma_api_url}/markets", {
                "limit": 40,
                "active": "true"
            })
            if market_data and isinstance(market_data, list):
                top_mkts = sorted(market_data, key=lambda m: float(m.get("volume") or 0), reverse=True)[:15]
                for m in top_mkts:
                    cid = m.get("conditionId") or m.get("condition_id")
                    if not cid:
                        continue
                    m_trades = await self._fetch_with_retry(f"{self.data_api_url}/trades", {
                        "conditionId": cid,
                        "limit": 50,
                        "filterType": "CASH",
                        "side": "BUY",
                        "filterAmount": 500
                    })
                    if m_trades and isinstance(m_trades, list):
                        for t in m_trades:
                            w = (t.get("proxyWallet") or t.get("maker_address") or t.get("user") or "").lower()
                            if w and len(w) == 42 and w.startswith("0x") and w not in candidates:
                                cash = float(t.get("usdcSize") or 5000)
                                candidates[w] = {
                                    "address": w,
                                    "source": "market_scan",
                                    "profit": 0.0,
                                    "volume": cash * 5
                                }
                    await asyncio.sleep(0.04)
        except Exception as e:
            logger.debug(f"Market scan error: {e}")

        logger.info(f"Titan discovery yielded {len(candidates)} unique whale candidates.")
        return candidates

    async def fetch_wallet_positions(self, address: str) -> List[Dict]:
        """Pulls all positions for a wallet with exact cashPnl, realizedPnl, and avgPrice."""
        try:
            url = f"{self.data_api_url}/positions"
            data = await self._fetch_with_retry(url, params={
                "user": address,
                "limit": 500,
                "sortBy": "CASHPNL",
                "sortDirection": "DESC"
            })
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("data") or data.get("results") or []
        except Exception as e:
            logger.debug(f"Error fetching positions for {address}: {e}")
        return []

    async def fetch_wallet_closed_positions(self, address: str, max_items: int = 4000) -> List[Dict]:
        """Pulls authentic historical closed & settled positions with exact resolution dates and realized PnL."""
        all_closed = []
        batch_size = 50
        offset = 0
        while len(all_closed) < max_items:
            url = f"{self.data_api_url}/closed-positions"
            data = await self._fetch_with_retry(url, params={
                "user": address,
                "limit": batch_size,
                "offset": offset
            })
            batch = []
            if isinstance(data, list):
                batch = data
            elif isinstance(data, dict):
                batch = data.get("data") or data.get("results") or []
            if not batch:
                break
            all_closed.extend(batch)
            if len(batch) < batch_size:
                break
            offset += len(batch)
            await asyncio.sleep(0.03)
        return all_closed

    async def fetch_wallet_profile(self, address: str) -> Optional[Dict]:
        """Pulls verified Polymarket leaderboard profile stats."""
        try:
            for period in ["ALL", "MONTH"]:
                lb_data = await self._fetch_with_retry(f"{self.data_api_url}/v1/leaderboard", {
                    "user": address,
                    "timePeriod": period
                })
                rows = lb_data if isinstance(lb_data, list) else (lb_data.get("data") or lb_data.get("results") or []) if isinstance(lb_data, dict) else []
                if rows and isinstance(rows[0], dict):
                    return rows[0]
        except Exception as e:
            logger.debug(f"Error fetching profile for {address}: {e}")
        return None

    async def fetch_wallet_profile_pnl(self, address: str) -> Optional[float]:
        """Queries Polymarket Data API directly to verify true all-time realized PnL."""
        prof = await self.fetch_wallet_profile(address)
        if prof:
            pnl = float(prof.get("pnl") or prof.get("profit") or prof.get("profile_profit") or 0.0)
            if pnl != 0.0:
                return round(pnl, 2)
        positions = await self.fetch_wallet_positions(address)
        if positions:
            pnl_sum = sum(float(p.get("cashPnl") or 0.0) for p in positions)
            if abs(pnl_sum) > 10.0:
                return round(pnl_sum, 2)
        return None

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

    async def fetch_wallet_activity(self, address: str, max_items: int = 4000) -> List[Dict]:
        """Pulls trade fills, closures, and redemptions from Polymarket activity endpoint with multi-page pagination."""
        all_activity = []
        batch_size = 500
        offset = 0
        while len(all_activity) < max_items:
            url = f"{self.data_api_url}/activity"
            data = await self._fetch_with_retry(url, params={
                "user": address,
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
            await asyncio.sleep(0.04)
            
        return all_activity

    async def fetch_order_book(self, token_id: str) -> Optional[Dict]:
        dec_tok = _to_decimal_token(token_id)
        url = f"{self.clob_api_url}/book"
        return await self._fetch_with_retry(url, params={"token_id": dec_tok})

    async def fetch_market_info(self, condition_id: str) -> Optional[Dict]:
        url = f"{self.gamma_api_url}/markets"
        data = await self._fetch_with_retry(url, params={"condition_ids": condition_id})
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        elif isinstance(data, dict):
            return data
        return None

    async def get_token_id_for_condition(self, condition_id: str, outcome: str = "Yes") -> Optional[str]:
        """Resolves the exact CLOB decimal token ID for a given condition ID and outcome."""
        if not condition_id:
            return None
        try:
            data = await self._fetch_with_retry(
                f"{self.gamma_api_url}/markets",
                params={"condition_ids": condition_id, "limit": 1}
            )
            m = data[0] if (isinstance(data, list) and data) else (data if isinstance(data, dict) else None)
            if m:
                tokens_raw = m.get("clobTokenIds") or m.get("clob_token_ids") or "[]"
                tokens = json.loads(tokens_raw) if isinstance(tokens_raw, str) else list(tokens_raw)
                outcomes_raw = m.get("outcomes") or "[]"
                outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else list(outcomes_raw)
                
                outc_lower = outcome.strip().lower()
                for idx, o in enumerate(outcomes):
                    if str(o).strip().lower() == outc_lower and idx < len(tokens):
                        return _to_decimal_token(str(tokens[idx]))
                if tokens:
                    if outc_lower in ("yes", "buy", "true", "1") and len(tokens) >= 1:
                        return _to_decimal_token(str(tokens[0]))
                    elif outc_lower in ("no", "sell", "false", "0") and len(tokens) >= 2:
                        return _to_decimal_token(str(tokens[1]))
                    return _to_decimal_token(str(tokens[0]))
        except Exception:
            pass
        return None

    async def fetch_live_token_price(
        self,
        condition_id: str = "",
        asset: str = "",
        outcome: str = "Yes",
        slug: str = "",
        event_slug: str = ""
    ) -> Optional[float]:
        """
        Titan Full Price Engine: Resolves live mark-to-market prices directly using Titan's multi-stage strategy.
        Handles binary Yes/No markets, multi-candidate markets, and nested multi-event containers.
        """
        dec_asset = _to_decimal_token(asset) if asset else ""

        # Pre-Stage: Resolve exact decimal token ID if condition_id is known
        if not dec_asset and condition_id:
            dec_asset = await self.get_token_id_for_condition(condition_id, outcome)

        # Fallback to Data API recent trades to find asset token ID if still unknown
        if not dec_asset and condition_id:
            try:
                t_hints = await self._fetch_with_retry(f"{self.data_api_url}/trades", params={"conditionId": condition_id, "limit": 4})
                if isinstance(t_hints, list) and t_hints:
                    for th in t_hints:
                        if isinstance(th, dict):
                            th_outcome = str(th.get("outcome") or "")
                            th_asset = str(th.get("asset") or "")
                            if th_asset and (not outcome or th_outcome.lower() == outcome.lower()):
                                dec_asset = _to_decimal_token(th_asset)
                                break
            except Exception:
                pass

        # ── Stage 0: Direct CLOB Midpoint / Price by Token ID ──
        if dec_asset:
            try:
                mid_data = await self._fetch_with_retry(f"{self.clob_api_url}/midpoint", params={"token_id": dec_asset})
                if isinstance(mid_data, dict) and "mid" in mid_data:
                    mid = float(mid_data["mid"])
                    if 0.001 <= mid <= 0.999:
                        return round(mid, 4)
            except Exception:
                pass

            try:
                price_data = await self._fetch_with_retry(f"{self.clob_api_url}/price", params={"token_id": dec_asset, "side": "BUY"})
                if isinstance(price_data, dict) and "price" in price_data:
                    p = float(price_data["price"])
                    if 0.001 <= p <= 0.999:
                        return round(p, 4)
            except Exception:
                pass

        # ── Stage 1: Gamma Market lookup (by clob_token_ids, condition_ids, or slug) ──
        market_payload = None

        if dec_asset:
            data = await self._fetch_with_retry(f"{self.gamma_api_url}/markets", params={"clob_token_ids": dec_asset, "limit": 1})
            if isinstance(data, list) and data:
                market_payload = data[0]

        if not market_payload and condition_id:
            data = await self._fetch_with_retry(f"{self.gamma_api_url}/markets", params={"condition_ids": condition_id, "limit": 1})
            if isinstance(data, list) and data:
                market_payload = data[0]
            elif isinstance(data, dict) and "outcomePrices" in data:
                market_payload = data

        if not market_payload and slug:
            data = await self._fetch_with_retry(f"{self.gamma_api_url}/markets", params={"slug": slug, "limit": 1})
            if isinstance(data, list) and data:
                market_payload = data[0]

        if market_payload and isinstance(market_payload, dict):
            try:
                raw_prices = market_payload.get("outcomePrices") or "[]"
                prices = json.loads(raw_prices) if isinstance(raw_prices, str) else list(raw_prices)
                prices = [float(p) for p in prices]

                raw_tokens = market_payload.get("clobTokenIds") or market_payload.get("clob_token_ids") or "[]"
                tokens = json.loads(raw_tokens) if isinstance(raw_tokens, str) else list(raw_tokens)
                tokens = [_to_decimal_token(str(t)) for t in tokens]

                raw_outcomes = market_payload.get("outcomes") or "[]"
                outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else list(raw_outcomes)

                # Priority 1: Match by token ID
                if dec_asset and tokens:
                    for idx, tok in enumerate(tokens):
                        if tok == dec_asset and idx < len(prices):
                            return round(prices[idx], 4)

                # Priority 2: Match by outcome name
                if outcome and outcomes:
                    for idx, o in enumerate(outcomes):
                        if str(o).strip().lower() == outcome.strip().lower() and idx < len(prices):
                            return round(prices[idx], 4)

                # Priority 3: Yes/No mapping
                if outcome.strip().lower() in ("yes", "buy", "true", "1") and len(prices) >= 1:
                    return round(prices[0], 4)
                elif outcome.strip().lower() in ("no", "sell", "false", "0") and len(prices) >= 2:
                    return round(prices[1], 4)
            except Exception:
                pass

        # ── Stage 2: Data API recent trades strictly filtered by market (condition ID) or asset ──
        if dec_asset:
            try:
                t_recent = await self._fetch_with_retry(f"{self.data_api_url}/trades", params={"asset": dec_asset, "limit": 4})
                if isinstance(t_recent, list) and t_recent:
                    for tr in t_recent:
                        if _to_decimal_token(tr.get("asset") or "") == dec_asset:
                            p_val = float(tr.get("price") or 0.0)
                            if 0.001 <= p_val <= 0.999:
                                return round(p_val, 4)
            except Exception:
                pass

        if condition_id:
            try:
                t_recent = await self._fetch_with_retry(f"{self.data_api_url}/trades", params={"market": condition_id, "limit": 8})
                if isinstance(t_recent, list) and t_recent:
                    for tr in t_recent:
                        tr_outc = str(tr.get("outcome") or "").strip().lower()
                        p_val = float(tr.get("price") or 0.0)
                        if 0.001 <= p_val <= 0.999:
                            if not outcome or tr_outc == outcome.strip().lower():
                                return round(p_val, 4)
                            elif outcome.strip().lower() in ("yes", "no") and tr_outc in ("yes", "no"):
                                return round(1.0 - p_val, 4)
            except Exception:
                pass

        return None

    async def fetch_batch_live_prices(self, condition_ids: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Batch fetches live prices efficiently using Gamma API bulk endpoints and throttled fallbacks.
        Returns mapping: { condition_id_lower: { outcome_lower: price } }
        """
        if not condition_ids:
            return {}
        
        clean_cids = list(set(str(c).strip().lower() for c in condition_ids if c and len(str(c).strip()) > 5))
        if not clean_cids:
            return {}

        results: Dict[str, Dict[str, float]] = {}

        # 1. High-speed Bulk Fetch: Pull 100 active markets in ONE single HTTP request from Gamma API
        try:
            bulk_markets = await self._fetch_with_retry(
                f"{self.gamma_api_url}/markets",
                params={"active": "true", "limit": 100, "closed": "false"}
            )
            if isinstance(bulk_markets, list):
                for m in bulk_markets:
                    if not isinstance(m, dict):
                        continue
                    m_cid = str(m.get("conditionId") or m.get("condition_id") or "").lower().strip()
                    if not m_cid:
                        continue

                    # Parse outcomes and prices
                    outcomes = m.get("outcomes") or ["Yes", "No"]
                    outcome_prices = m.get("outcomePrices") or []
                    clob_tokens = m.get("clobTokenIds") or []
                    if isinstance(outcomes, str):
                        try: outcomes = json.loads(outcomes)
                        except Exception: outcomes = ["Yes", "No"]
                    if isinstance(outcome_prices, str):
                        try: outcome_prices = json.loads(outcome_prices)
                        except Exception: outcome_prices = []
                    if isinstance(clob_tokens, str):
                        try: clob_tokens = json.loads(clob_tokens)
                        except Exception: clob_tokens = []

                    m_map = {}
                    for idx, outc in enumerate(outcomes):
                        if idx < len(outcome_prices):
                            try:
                                p_flt = float(outcome_prices[idx])
                                if 0.001 <= p_flt <= 0.999:
                                    m_map[str(outc).lower().strip()] = round(p_flt, 4)
                            except Exception:
                                pass
                    if m_map:
                        results[m_cid] = m_map

                    # Map token IDs directly
                    for idx, tok in enumerate(clob_tokens):
                        if idx < len(outcome_prices):
                            try:
                                p_flt = float(outcome_prices[idx])
                                if 0.001 <= p_flt <= 0.999 and tok:
                                    results[f"token:{str(tok).strip()}"] = {"price": round(p_flt, 4)}
                            except Exception:
                                pass
        except Exception as e:
            logger.debug(f"Gamma bulk markets fetch note: {e}")

        # 2. For missing condition IDs, fetch all concurrently with controlled concurrency (max 10 parallel)
        missing_cids = [cid for cid in clean_cids if cid not in results]
        if missing_cids:
            sem = asyncio.Semaphore(10)
            async def _fetch_single_cid(cid: str) -> None:
                async with sem:
                    try:
                        m_data = await self._fetch_with_retry(
                            f"{self.gamma_api_url}/markets",
                            params={"condition_id": cid}
                        )
                        if isinstance(m_data, list) and m_data and isinstance(m_data[0], dict):
                            m = m_data[0]
                            outcomes = m.get("outcomes") or ["Yes", "No"]
                            outcome_prices = m.get("outcomePrices") or []
                            if isinstance(outcomes, str):
                                try: outcomes = json.loads(outcomes)
                                except Exception: outcomes = ["Yes", "No"]
                            if isinstance(outcome_prices, str):
                                try: outcome_prices = json.loads(outcome_prices)
                                except Exception: outcome_prices = []

                            m_map = {}
                            for idx, outc in enumerate(outcomes):
                                if idx < len(outcome_prices):
                                    try:
                                        p_flt = float(outcome_prices[idx])
                                        if 0.001 <= p_flt <= 0.999:
                                            m_map[str(outc).lower().strip()] = round(p_flt, 4)
                                    except Exception:
                                        pass
                            if m_map:
                                results[cid] = m_map
                    except Exception:
                        pass

            await asyncio.gather(*[_fetch_single_cid(c) for c in missing_cids], return_exceptions=True)

        return results
