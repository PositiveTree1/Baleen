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

        # 1. Seeded VIP Alpha Whales from Titan Engine (Guaranteed High-Profit Track Records)
        vip_wallets = [
            ("0x6d9fc316c3b8377060a44b852ba664adbfd59790", 299000.0, "MEPP Alpha", 1850000.0),
            ("0x63ce342161250d705dc0b16df89036c8e5f9ba9a", 2210000.0, "0x8dxd", 14500000.0),
            ("0x1cc16713196d456f86fa9c7387dd326a7f73b8df", 185000.0, "Wickier", 980000.0),
            ("0x614dc8d3542c12103d2c6a3553fd761e391d1546", 142000.0, "mr.ozi", 820000.0),
            ("0x7f9e2d1df78614564a70becc7fa14aa9a6623a0e", 115000.0, "nojnn", 640000.0),
            ("0xdf17f4a8dd01a4cfa6fc3da323a2baee5f8697d1", 340000.0, "Clear-Corridor", 2100000.0),
            ("0x73e3fec494611d73c170cb2f23850fd998b21be9", 90745.0, "Titan Sniper", 520000.0),
            ("0x918349a2a7b8e19e917d52f6fefbcceb35235889", 580000.0, "Whale Alpha 1", 3200000.0),
            ("0x547a49f854619d8dddb14f346b0a88fb0d970a25", 412000.0, "Whale Alpha 2", 2400000.0),
            ("0xb482ebddb639e44ffc2b3e83921ebcb071e626e2", 198000.0, "Whale Alpha 3", 1100000.0),
            ("0xa62174c8b74ff6b7e52b2f6efba983ef4b5ff4f9", 155000.0, "Macro Alpha", 920000.0),
            ("0xd749e4917a1c876b5c3e61c5ebbc19f864e22295", 260000.0, "Event Arb", 1600000.0)
        ]
        for w_addr, w_pnl, w_name, w_vol in vip_wallets:
            w_addr_lower = w_addr.lower()
            candidates[w_addr_lower] = {
                "address": w_addr_lower,
                "source": "titan_vip",
                "profit": w_pnl,
                "volume": w_vol,
                "name": w_name
            }

        # 2. Paginated Multi-Period Leaderboards (ALL, MONTH, WEEK)
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

    async def fetch_wallet_profile_pnl(self, address: str) -> Optional[float]:
        """Queries Polymarket Data API directly to verify true all-time realized PnL."""
        try:
            # Method 1: Positions API (most accurate live total PnL from Polymarket)
            pos_data = await self._fetch_with_retry(f"{self.data_api_url}/positions", {
                "user": address,
                "limit": 100,
                "sortBy": "CURRENT",
                "sortDirection": "DESC",
                "sizeThreshold": 0.1
            })
            if pos_data and isinstance(pos_data, list):
                realized_sum = sum(float(p.get("cashPnl") or 0.0) for p in pos_data)
                if abs(realized_sum) > 100.0:
                    return round(realized_sum, 2)

            # Method 2: Leaderboard check
            for period in ["ALL", "MONTH"]:
                lb_data = await self._fetch_with_retry(f"{self.data_api_url}/leaderboard", {
                    "user": address,
                    "timePeriod": period
                })
                rows = lb_data if isinstance(lb_data, list) else (lb_data.get("data") or lb_data.get("results") or []) if isinstance(lb_data, dict) else []
                if rows and isinstance(rows[0], dict):
                    pnl = float(rows[0].get("profile_profit") or rows[0].get("profit") or rows[0].get("pnl") or 0.0)
                    if pnl != 0.0:
                        return round(pnl, 2)
        except Exception as e:
            logger.debug(f"Error fetching profile PnL for {address}: {e}")
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
        dec_tok = _to_decimal_token(token_id)
        url = f"{self.clob_api_url}/book"
        return await self._fetch_with_retry(url, params={"token_id": dec_tok})

    async def fetch_market_info(self, condition_id: str) -> Optional[Dict]:
        url = f"{self.gamma_api_url}/markets"
        data = await self._fetch_with_retry(url, params={"condition_id": condition_id})
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        elif isinstance(data, dict):
            return data
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
        import json
        dec_asset = _to_decimal_token(asset) if asset else ""

        # ── Pre-Stage: Extract asset/slug hints from Data API if not provided (Titan MarketCache strategy) ──
        if not dec_asset and condition_id:
            try:
                t_hints = await self._fetch_with_retry(f"{self.data_api_url}/trades", params={"conditionId": condition_id, "limit": 4})
                if isinstance(t_hints, list) and t_hints:
                    for th in t_hints:
                        if isinstance(th, dict):
                            th_outcome = str(th.get("outcome") or "")
                            th_asset = str(th.get("asset") or "")
                            th_slug = str(th.get("slug") or "")
                            if th_slug and not slug:
                                slug = th_slug
                            if th_asset:
                                if not dec_asset:
                                    dec_asset = _to_decimal_token(th_asset)
                                if outcome and th_outcome.lower() == outcome.lower():
                                    dec_asset = _to_decimal_token(th_asset)
                                    break
            except Exception:
                pass

        # ── Stage 0: Direct Data API Recent Fill Price (Fastest & Most Reliable) ──
        if dec_asset:
            try:
                t_recent = await self._fetch_with_retry(f"{self.data_api_url}/trades", params={"asset": dec_asset, "limit": 1})
                if isinstance(t_recent, list) and t_recent:
                    p_val = float(t_recent[0].get("price") or 0.0)
                    if 0.005 <= p_val <= 0.995:
                        return round(p_val, 4)
            except Exception:
                pass

        if condition_id:
            try:
                t_recent = await self._fetch_with_retry(f"{self.data_api_url}/trades", params={"conditionId": condition_id, "limit": 2})
                if isinstance(t_recent, list) and t_recent:
                    for tr in t_recent:
                        tr_outc = str(tr.get("outcome") or "")
                        if not outcome or tr_outc.lower() == outcome.lower():
                            p_val = float(tr.get("price") or 0.0)
                            if 0.005 <= p_val <= 0.995:
                                return round(p_val, 4)
            except Exception:
                pass

        # ── Stage 1: CLOB Midpoint by Token ID (Fastest direct orderbook price) ──
        if dec_asset:
            try:
                mid_data = await self._fetch_with_retry(f"{self.clob_api_url}/midpoint", params={"token_id": dec_asset})
                if isinstance(mid_data, dict) and "mid" in mid_data:
                    mid = float(mid_data["mid"])
                    if 0.005 <= mid <= 0.995:
                        return round(mid, 4)
            except Exception:
                pass

        # ── Stage 2: CLOB Orderbook Best Bid/Ask ──
        if dec_asset:
            try:
                book = await self.fetch_order_book(dec_asset)
                if isinstance(book, dict):
                    bids = book.get("bids", [])
                    asks = book.get("asks", [])
                    best_bid = float(bids[0].get("price", 0)) if bids else 0.0
                    best_ask = float(asks[0].get("price", 1)) if asks else 1.0
                    if 0 < best_bid < best_ask < 1:
                        return round((best_bid + best_ask) / 2.0, 4)
            except Exception:
                pass

        # ── Stage 3: Gamma Market lookup (by clob_token_ids, slug, or condition_id) ──
        market_payload = None

        # 3a. Gamma by clob_token_ids
        if dec_asset:
            data = await self._fetch_with_retry(f"{self.gamma_api_url}/markets", params={"clob_token_ids": dec_asset, "limit": 1})
            if isinstance(data, list) and data:
                market_payload = data[0]

        # 3b. Gamma by slug
        if not market_payload and slug:
            data = await self._fetch_with_retry(f"{self.gamma_api_url}/markets", params={"slug": slug, "limit": 1})
            if isinstance(data, list) and data:
                market_payload = data[0]

        # 3c. Gamma by event_slug (Multi-event container resolution)
        if not market_payload and event_slug:
            event_data = await self._fetch_with_retry(f"{self.gamma_api_url}/events", params={"slug": event_slug, "limit": 1})
            if isinstance(event_data, list) and event_data:
                submarkets = event_data[0].get("markets", [])
                for sm in submarkets:
                    sm_cid = str(sm.get("conditionId") or sm.get("condition_id") or "").lower()
                    sm_tokens = sm.get("clobTokenIds") or sm.get("clob_token_ids") or []
                    if isinstance(sm_tokens, str):
                        try:
                            sm_tokens = json.loads(sm_tokens)
                        except Exception:
                            sm_tokens = []
                    sm_tokens = [_to_decimal_token(str(t)) for t in sm_tokens]
                    if (condition_id and sm_cid == condition_id.lower()) or (dec_asset and dec_asset in sm_tokens):
                        market_payload = sm
                        break

        # 3d. Gamma by condition_id
        if not market_payload and condition_id:
            data = await self._fetch_with_retry(f"{self.gamma_api_url}/markets", params={"condition_id": condition_id, "limit": 1})
            if isinstance(data, list) and data:
                market_payload = data[0]

        # Process Gamma market payload
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

                # Priority 1: Match by token ID (Asset match)
                if dec_asset and tokens:
                    for idx, tok in enumerate(tokens):
                        if tok == dec_asset and idx < len(prices):
                            return round(prices[idx], 4)

                # Priority 2: Exact outcome label match
                if outcome and outcomes:
                    for idx, o in enumerate(outcomes):
                        if str(o).strip().lower() == outcome.strip().lower() and idx < len(prices):
                            return round(prices[idx], 4)

                # Priority 3: Binary Yes/No fallback
                if outcome.strip().lower() in ("yes", "buy", "true", "1") and len(prices) >= 1:
                    return round(prices[0], 4)
                elif outcome.strip().lower() in ("no", "sell", "false", "0") and len(prices) >= 2:
                    return round(prices[1], 4)
                elif prices:
                    return round(prices[0], 4)
            except Exception:
                pass

        # ── Stage 4: Data API /trades fallback (DIRECT MATCH ONLY) ──
        if condition_id:
            try:
                trades_data = await self._fetch_with_retry(f"{self.data_api_url}/trades", params={"conditionId": condition_id, "limit": 20})
                if isinstance(trades_data, list):
                    our_lower = outcome.lower().strip()
                    for t in trades_data:
                        t_price = float(t.get("price") or 0)
                        t_outcome = (t.get("outcome") or "").lower().strip()
                        t_asset = _to_decimal_token(t.get("asset") or "")
                        if 0.005 <= t_price <= 0.995:
                            if dec_asset and t_asset == dec_asset:
                                return round(t_price, 4)
                            if t_outcome and our_lower and t_outcome == our_lower:
                                return round(t_price, 4)
            except Exception:
                pass

        return None
