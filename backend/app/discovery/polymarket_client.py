import httpx
import asyncio
import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Set
from app.config import settings

logger = logging.getLogger(__name__)


class ProviderResponseStatus(str, Enum):
    COMPLETE_WITH_DATA = "COMPLETE_WITH_DATA"
    COMPLETE_EMPTY = "COMPLETE_EMPTY"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass
class ProviderQueryResult:
    """Typed result wrapper for external provider queries."""
    status: ProviderResponseStatus
    data: Any
    scope: str = ""
    endpoint_version: str = "v1"
    page_count: int = 1
    total_items: int = 0
    reason: Optional[str] = None
    observed_at: datetime = field(default_factory=datetime.utcnow)


class ProviderCoverageError(RuntimeError):
    """History could not be proven complete; partial rows are available for diagnostics."""
    def __init__(self, message: str, result: "ProviderListResult"):
        super().__init__(message)
        self.result = result


class ProviderListResult(list):
    """List-compatible provider history with explicit coverage metadata."""
    def __init__(self, values=(), *, status=ProviderResponseStatus.COMPLETE_WITH_DATA,
                 requested_wallet: str = "", page_count: int = 0, reason: Optional[str] = None):
        super().__init__(values)
        self.status = status
        self.requested_wallet = requested_wallet
        self.page_count = page_count
        self.reason = reason


def _coverage_error(endpoint: str, values: list, wallet: str, pages: int, reason: str) -> ProviderCoverageError:
    result = ProviderListResult(values, status=ProviderResponseStatus.PARTIAL if values else ProviderResponseStatus.UNAVAILABLE,
                                requested_wallet=wallet, page_count=pages, reason=reason)
    return ProviderCoverageError(f"Incomplete {endpoint} history: {reason}", result)


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


def _finite_float(value: Any) -> Optional[float]:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError):
        return None


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
                    retry_after = min(10.0, float(response.headers.get("Retry-After", backoff)))
                    logger.debug(f"Rate limited by {url}. Backing off {retry_after:.1f}s...")
                    await asyncio.sleep(retry_after)
                    backoff *= 2
                    continue
                if response.status_code in (400, 404):
                    logger.debug(f"Permanent client error {response.status_code} fetching {url}")
                    return None
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (400, 404):
                    return None
                if attempt == retries - 1:
                    logger.debug(f"HTTP Status Error fetching {url}: {e}")
                    return None
                await asyncio.sleep(backoff)
                backoff *= 2
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
                    w = (t.get("proxyWallet") or t.get("user") or "").lower().strip()
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

        # 2. Paginated Multi-Period Leaderboards (ALL, MONTH, WEEK) via documented /v1/leaderboard
        for period in ["ALL", "MONTH", "WEEK"]:
            for offset in [0, 100, 200]:
                try:
                    lb_data = await self._fetch_with_retry(f"{self.data_api_url}/v1/leaderboard", {
                        "timePeriod": period,
                        "category": "OVERALL",
                        "orderBy": "PNL",
                        "limit": 100,
                        "offset": offset
                    })
                    rows = lb_data if isinstance(lb_data, list) else (lb_data.get("data") or lb_data.get("results") or []) if isinstance(lb_data, dict) else []
                    for entry in rows:
                        if isinstance(entry, dict):
                            w = (entry.get("proxyWallet") or entry.get("address") or entry.get("user") or "").lower().strip()
                            if w and len(w) == 42 and w.startswith("0x"):
                                pnl = float(entry.get("profile_profit") or entry.get("profit") or entry.get("pnl") or 0.0)
                                vol = float(entry.get("profile_volume") or entry.get("volume") or entry.get("vol") or 0.0)
                                name = entry.get("name") or entry.get("username") or entry.get("userName") or ""
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
                    w = (t.get("proxyWallet") or t.get("user") or "").lower().strip()
                    if w and len(w) == 42 and w.startswith("0x") and w not in candidates:
                        cash = float(t.get("usdcSize") or (float(t.get("size", 0)) * float(t.get("price", 1))))
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
                    # Data API expects 'market' for condition ID filtering
                    m_trades = await self._fetch_with_retry(f"{self.data_api_url}/trades", {
                        "market": cid,
                        "limit": 50,
                        "filterType": "CASH",
                        "side": "BUY",
                        "filterAmount": 500
                    })
                    if m_trades and isinstance(m_trades, list):
                        for t in m_trades:
                            # Identity validation: ensure returned trade belongs to the requested market
                            t_cid = str(t.get("market") or t.get("conditionId") or "").lower().strip()
                            if t_cid and t_cid != str(cid).lower().strip():
                                continue
                            w = (t.get("proxyWallet") or t.get("user") or "").lower().strip()
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
        norm_addr = address.lower().strip()
        try:
            url = f"{self.data_api_url}/positions"
            data = await self._fetch_with_retry(url, params={
                "user": norm_addr,
                "limit": 500,
                "sortBy": "CASHPNL",
                "sortDirection": "DESC"
            })
            if data is None:
                raise _coverage_error('positions', [], norm_addr, 1, 'provider unavailable')
            rows = data if isinstance(data, list) else (data.get("data") or data.get("results") or []) if isinstance(data, dict) else []
            if len(rows) >= 500:
                raise _coverage_error('positions', rows, norm_addr, 1, 'position cap reached; coverage incomplete')
            valid_positions = []
            for p in rows:
                if isinstance(p, dict):
                    p_user = str(p.get("user") or p.get("proxyWallet") or "").lower().strip()
                    if p_user != norm_addr:
                        logger.warning(f"Identity mismatch in positions: requested {norm_addr}, got {p_user}")
                        continue
                    valid_positions.append(p)
            return valid_positions
        except ProviderCoverageError:
            raise
        except Exception as e:
            raise _coverage_error('positions', [], norm_addr, 1, str(e)) from e

    async def fetch_wallet_closed_positions(self, address: str, max_items: int = 4000) -> List[Dict]:
        """Pulls authentic historical closed & settled positions with exact resolution dates and realized PnL."""
        norm_addr = address.lower().strip()
        all_closed = []
        page_fingerprints = set()
        page_count = 0
        batch_size = 50
        offset = 0
        while len(all_closed) < max_items:
            url = f"{self.data_api_url}/closed-positions"
            data = await self._fetch_with_retry(url, params={
                "user": norm_addr,
                "limit": batch_size,
                "offset": offset,
                "sortBy": "timestamp",
                "sortDirection": "DESC"
            })
            page_count += 1
            batch = data if isinstance(data, list) else (data.get("data") or data.get("results") or []) if isinstance(data, dict) else []
            if data is None:
                raise _coverage_error("closed-positions", all_closed, norm_addr, page_count, "provider failure after a non-empty page")
            if not batch:
                if not all_closed:
                    return ProviderListResult([], status=ProviderResponseStatus.COMPLETE_EMPTY, requested_wallet=norm_addr, page_count=page_count)
                return ProviderListResult(all_closed, requested_wallet=norm_addr, page_count=page_count)
            fingerprint = json.dumps(batch, sort_keys=True, default=str)
            if fingerprint in page_fingerprints:
                raise _coverage_error("closed-positions", all_closed, norm_addr, page_count, "repeated page")
            page_fingerprints.add(fingerprint)
            valid_batch = []
            for p in batch:
                if isinstance(p, dict):
                    p_user = str(p.get("user") or p.get("proxyWallet") or "").lower().strip()
                    if p_user != norm_addr:
                        continue
                    valid_batch.append(p)
            all_closed.extend(valid_batch)
            if len(batch) < batch_size:
                return ProviderListResult(all_closed, requested_wallet=norm_addr, page_count=page_count)
            offset += len(batch)
            await asyncio.sleep(0.03)
        raise _coverage_error("closed-positions", all_closed, norm_addr, page_count, "maximum item cap reached without an end marker")

    async def fetch_wallet_profile(self, address: str) -> Optional[Dict]:
        """Pulls verified Polymarket leaderboard profile stats via /v1/leaderboard."""
        norm_addr = address.lower().strip()
        try:
            for period in ["ALL", "MONTH"]:
                lb_data = await self._fetch_with_retry(f"{self.data_api_url}/v1/leaderboard", {
                    "user": norm_addr,
                    "timePeriod": period
                })
                rows = lb_data if isinstance(lb_data, list) else (lb_data.get("data") or lb_data.get("results") or []) if isinstance(lb_data, dict) else []
                if rows and isinstance(rows[0], dict):
                    entry = rows[0]
                    e_user = str(entry.get("proxyWallet") or entry.get("user") or entry.get("address") or "").lower().strip()
                    if e_user != norm_addr:
                        continue
                    entry["reported_period"] = period
                    return entry
        except Exception as e:
            logger.debug(f"Error fetching profile for {address}: {e}")
        return None

    async def fetch_wallet_profile_pnl(self, address: str) -> Optional[float]:
        """Queries Polymarket Data API directly to verify true realized PnL, preserving valid 0.0."""
        prof = await self.fetch_wallet_profile(address)
        if prof:
            pnl = prof.get("pnl") if prof.get("pnl") is not None else (prof.get("profit") if prof.get("profit") is not None else prof.get("profile_profit"))
            if pnl is not None:
                try:
                    parsed = _finite_float(pnl)
                    if parsed is not None:
                        return round(parsed, 2)
                except (ValueError, TypeError):
                    pass
        positions = await self.fetch_wallet_positions(address)
        if positions:
            pnl_values = [_finite_float(p.get("cashPnl")) for p in positions]
            if any(value is None for value in pnl_values):
                return None
            pnl_sum = sum(value for value in pnl_values if value is not None)
            if abs(pnl_sum) > 0.01:
                return round(pnl_sum, 2)
        return None

    async def fetch_wallet_trades(self, address: str, max_trades: int = 4000) -> List[Dict]:
        """Pulls multi-page trade history up to max_trades for a wallet using documented user= param."""
        norm_addr = address.lower().strip()
        all_trades = []
        page_fingerprints = set()
        page_count = 0
        batch_size = 500
        offset = 0

        while len(all_trades) < max_trades:
            url = f"{self.data_api_url}/trades"
            data = await self._fetch_with_retry(url, params={"user": norm_addr, "limit": batch_size, "offset": offset})
            page_count += 1
            trades_batch = data if isinstance(data, list) else (data.get("data") or data.get("results") or []) if isinstance(data, dict) else []
            if data is None:
                raise _coverage_error("trades", all_trades, norm_addr, page_count, "provider failure after a non-empty page")

            if not trades_batch:
                if not all_trades:
                    return ProviderListResult([], status=ProviderResponseStatus.COMPLETE_EMPTY, requested_wallet=norm_addr, page_count=page_count)
                return ProviderListResult(all_trades, requested_wallet=norm_addr, page_count=page_count)
            fingerprint = json.dumps(trades_batch, sort_keys=True, default=str)
            if fingerprint in page_fingerprints:
                raise _coverage_error("trades", all_trades, norm_addr, page_count, "repeated page")
            page_fingerprints.add(fingerprint)

            valid_batch = []
            for t in trades_batch:
                if isinstance(t, dict):
                    t_user = str(t.get("user") or t.get("proxyWallet") or "").lower().strip()
                    if t_user != norm_addr:
                        continue
                    valid_batch.append(t)

            all_trades.extend(valid_batch)
            if len(trades_batch) < batch_size:
                return ProviderListResult(all_trades[:max_trades], requested_wallet=norm_addr, page_count=page_count)

            offset += len(trades_batch)
            await asyncio.sleep(0.05)

        raise _coverage_error("trades", all_trades[:max_trades], norm_addr, page_count, "maximum item cap reached without an end marker")

    async def fetch_wallet_activity(self, address: str, max_items: int = 4000) -> List[Dict]:
        """Pulls trade fills, closures, and redemptions from Polymarket activity endpoint with multi-page pagination."""
        norm_addr = address.lower().strip()
        all_activity = []
        page_fingerprints = set()
        page_count = 0
        batch_size = 500
        offset = 0
        while len(all_activity) < max_items:
            url = f"{self.data_api_url}/activity"
            data = await self._fetch_with_retry(url, params={
                "user": norm_addr,
                "limit": batch_size,
                "offset": offset,
                "sortBy": "TIMESTAMP",
                "sortDirection": "DESC"
            })
            page_count += 1
            batch = data if isinstance(data, list) else (data.get("data") or data.get("results") or []) if isinstance(data, dict) else []
            if data is None:
                raise _coverage_error("activity", all_activity, norm_addr, page_count, "provider failure after a non-empty page")

            if not batch:
                if not all_activity:
                    return ProviderListResult([], status=ProviderResponseStatus.COMPLETE_EMPTY, requested_wallet=norm_addr, page_count=page_count)
                return ProviderListResult(all_activity, requested_wallet=norm_addr, page_count=page_count)
            fingerprint = json.dumps(batch, sort_keys=True, default=str)
            if fingerprint in page_fingerprints:
                raise _coverage_error("activity", all_activity, norm_addr, page_count, "repeated page")
            page_fingerprints.add(fingerprint)

            valid_batch = []
            for item in batch:
                if isinstance(item, dict):
                    i_user = str(item.get("user") or item.get("proxyWallet") or "").lower().strip()
                    if i_user != norm_addr:
                        continue
                    valid_batch.append(item)

            all_activity.extend(valid_batch)
            if len(batch) < batch_size:
                return ProviderListResult(all_activity, requested_wallet=norm_addr, page_count=page_count)

            offset += len(batch)
            await asyncio.sleep(0.04)

        raise _coverage_error("activity", all_activity, norm_addr, page_count, "maximum item cap reached without an end marker")

    async def fetch_order_book(self, token_id: str) -> Optional[Dict]:
        dec_tok = _to_decimal_token(token_id)
        url = f"{self.clob_api_url}/book"
        return await self._fetch_with_retry(url, params={"token_id": dec_tok})

    async def fetch_market_info(self, condition_id: str) -> Optional[Dict]:
        if not condition_id:
            return None
        norm_cid = condition_id.lower().strip()
        url = f"{self.gamma_api_url}/markets"
        data = await self._fetch_with_retry(url, params={"condition_ids": norm_cid})
        rows = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
        for m in rows:
            if isinstance(m, dict):
                m_cid = str(m.get("conditionId") or m.get("condition_id") or "").lower().strip()
                if m_cid == norm_cid:
                    return m
        return None

    async def get_token_id_for_condition(self, condition_id: str, outcome: str = "Yes") -> Optional[str]:
        """Resolves the exact CLOB decimal token ID for a given condition ID and outcome."""
        if not condition_id:
            return None
        norm_cid = condition_id.lower().strip()
        try:
            data = await self._fetch_with_retry(
                f"{self.gamma_api_url}/markets",
                params={"condition_ids": norm_cid, "limit": 1}
            )
            rows = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
            for m in rows:
                if not isinstance(m, dict):
                    continue
                m_cid = str(m.get("conditionId") or m.get("condition_id") or "").lower().strip()
                if m_cid and m_cid != norm_cid:
                    continue

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
                    return None
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
        Resolves live mark-to-market prices directly using multi-stage strategy.
        Validates condition_id and asset identity at every stage before using prices.
        """
        norm_cid = condition_id.lower().strip() if condition_id else ""
        dec_asset = _to_decimal_token(asset) if asset else ""

        # Pre-Stage: Resolve exact decimal token ID if condition_id is known
        if not dec_asset and norm_cid:
            dec_asset = await self.get_token_id_for_condition(norm_cid, outcome)

        # Fallback to Data API recent trades to find asset token ID if still unknown
        if not dec_asset and norm_cid:
            try:
                t_hints = await self._fetch_with_retry(f"{self.data_api_url}/trades", params={"market": norm_cid, "limit": 4})
                if isinstance(t_hints, list) and t_hints:
                    for th in t_hints:
                        if isinstance(th, dict):
                            t_cid = str(th.get("market") or th.get("conditionId") or "").lower().strip()
                            if t_cid != norm_cid:
                                continue
                            th_outcome = str(th.get("outcome") or "")
                            th_asset = str(th.get("asset") or "")
                            if th_asset and (not outcome or th_outcome.lower() == outcome.lower()):
                                dec_asset = _to_decimal_token(th_asset)
                                break
            except Exception:
                pass

        # Stage 0: Direct CLOB Midpoint / Price by Token ID
        if dec_asset:
            try:
                mid_data = await self._fetch_with_retry(f"{self.clob_api_url}/midpoint", params={"token_id": dec_asset})
                if isinstance(mid_data, dict) and "mid" in mid_data:
                    mid = float(mid_data["mid"])
                    if 0.0001 <= mid <= 0.9999:
                        return round(mid, 4)
            except Exception:
                pass

            try:
                price_data = await self._fetch_with_retry(f"{self.clob_api_url}/price", params={"token_id": dec_asset, "side": "BUY"})
                if isinstance(price_data, dict) and "price" in price_data:
                    p = float(price_data["price"])
                    if 0.0001 <= p <= 0.9999:
                        return round(p, 4)
            except Exception:
                pass

        # Stage 1: Gamma Market lookup (by clob_token_ids or condition_ids)
        market_payload = None

        if dec_asset:
            data = await self._fetch_with_retry(f"{self.gamma_api_url}/markets", params={"clob_token_ids": dec_asset, "limit": 1})
            rows = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
            for m in rows:
                if isinstance(m, dict):
                    clob_toks = m.get("clobTokenIds") or m.get("clob_token_ids") or "[]"
                    tok_list = json.loads(clob_toks) if isinstance(clob_toks, str) else list(clob_toks)
                    if any(_to_decimal_token(str(t)) == dec_asset for t in tok_list):
                        market_payload = m
                        break

        if not market_payload and norm_cid:
            data = await self._fetch_with_retry(f"{self.gamma_api_url}/markets", params={"condition_ids": norm_cid, "limit": 1})
            rows = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
            for m in rows:
                if isinstance(m, dict):
                    m_cid = str(m.get("conditionId") or m.get("condition_id") or "").lower().strip()
                    if m_cid == norm_cid:
                        market_payload = m
                        break

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

                # Match by token ID
                if dec_asset and tokens:
                    for idx, tok in enumerate(tokens):
                        if tok == dec_asset and idx < len(prices):
                            return round(prices[idx], 4)

                # Match by outcome name
                if outcome and outcomes:
                    for idx, o in enumerate(outcomes):
                        if str(o).strip().lower() == outcome.strip().lower() and idx < len(prices):
                            return round(prices[idx], 4)

                if outcome.strip().lower() in ("yes", "buy", "true", "1") and len(prices) >= 1:
                    return round(prices[0], 4)
                elif outcome.strip().lower() in ("no", "sell", "false", "0") and len(prices) >= 2:
                    return round(prices[1], 4)
            except Exception:
                pass

        # Stage 2: Data API recent trades strictly filtered by market (condition ID) or asset
        if dec_asset:
            try:
                t_recent = await self._fetch_with_retry(f"{self.data_api_url}/trades", params={"asset": dec_asset, "limit": 4})
                if isinstance(t_recent, list) and t_recent:
                    for tr in t_recent:
                        if _to_decimal_token(tr.get("asset") or "") == dec_asset:
                            p_val = float(tr.get("price") or 0.0)
                            if 0.0001 <= p_val <= 0.9999:
                                return round(p_val, 4)
            except Exception:
                pass

        if norm_cid:
            try:
                t_recent = await self._fetch_with_retry(f"{self.data_api_url}/trades", params={"market": norm_cid, "limit": 8})
                if isinstance(t_recent, list) and t_recent:
                    for tr in t_recent:
                        t_cid = str(tr.get("market") or tr.get("conditionId") or "").lower().strip()
                        if t_cid != norm_cid:
                            continue
                        tr_outc = str(tr.get("outcome") or "").strip().lower()
                        p_val = float(tr.get("price") or 0.0)
                        if 0.0001 <= p_val <= 0.9999:
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
        Strictly validates that returned condition IDs match the requested list.
        Returns mapping: { condition_id_lower: { outcome_lower: price } }
        """
        if not condition_ids:
            return {}

        clean_cids = list(set(str(c).strip().lower() for c in condition_ids if c and len(str(c).strip()) > 5))
        if not clean_cids:
            return {}

        results: Dict[str, Dict[str, float]] = {}

        # 1. High-speed Bulk Fetch: Pull 100 active markets from Gamma API
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
                    if not m_cid or m_cid not in clean_cids:
                        continue

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
                                if 0.0001 <= p_flt <= 0.9999:
                                    m_map[str(outc).lower().strip()] = round(p_flt, 4)
                            except Exception:
                                pass
                    if m_map:
                        results[m_cid] = m_map

                    for idx, tok in enumerate(clob_tokens):
                        if idx < len(outcome_prices):
                            try:
                                p_flt = float(outcome_prices[idx])
                                if 0.0001 <= p_flt <= 0.9999 and tok:
                                    results[f"token:{str(tok).strip()}"] = {"price": round(p_flt, 4)}
                            except Exception:
                                pass
        except Exception as e:
            logger.debug(f"Gamma bulk markets fetch note: {e}")

        # 2. For missing condition IDs, fetch targeted per condition_ids
        missing_cids = [cid for cid in clean_cids if cid not in results]
        if missing_cids:
            sem = asyncio.Semaphore(10)
            async def _fetch_single_cid(cid: str) -> None:
                async with sem:
                    try:
                        m_data = await self._fetch_with_retry(
                            f"{self.gamma_api_url}/markets",
                            params={"condition_ids": cid}
                        )
                        rows = m_data if isinstance(m_data, list) else ([m_data] if isinstance(m_data, dict) else [])
                        for m in rows:
                            if not isinstance(m, dict):
                                continue
                            m_cid = str(m.get("conditionId") or m.get("condition_id") or "").lower().strip()
                            # CRITICAL: Reject if conditionId does not match the requested cid!
                            if m_cid != cid:
                                continue

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
                                        if 0.0001 <= p_flt <= 0.9999:
                                            m_map[str(outc).lower().strip()] = round(p_flt, 4)
                                    except Exception:
                                        pass
                            if m_map:
                                results[cid] = m_map
                    except Exception:
                        pass

            await asyncio.gather(*[_fetch_single_cid(c) for c in missing_cids], return_exceptions=True)

        return results
