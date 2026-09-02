"""
High-Performance DuckDB Parquet Data Loader
Queries 28 GB trades.parquet and markets.parquet using chronological pushdown filters.
Streams TradeSignal objects and market resolution events with zero memory bloat.
"""
import ast
import logging
from typing import Dict, List, Optional, Generator, Tuple, Any
import duckdb
from app.backtesting.config import BacktestConfig
from app.backtesting.models import TradeSignal
from app.services.polymarket_fees import classify_market_category

logger = logging.getLogger(__name__)

class PolymarketDataLoader:
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.trades_path = f"{config.data_dir}/{config.trades_file}".replace("\\", "/")
        self.markets_path = f"{config.data_dir}/{config.markets_file}".replace("\\", "/")
        self.conn = duckdb.connect()
        self._market_resolutions_cache: Dict[str, Dict[str, Any]] = {}

    def parse_outcome_prices(self, prices_raw: str) -> Tuple[Optional[str], float, float]:
        """Parses outcome_prices string to determine winning outcome and authentic contract payouts."""
        winning_token = None
        p1, p2 = 0.0, 0.0
        if prices_raw and prices_raw.startswith("[") and prices_raw.endswith("]"):
            try:
                parsed = ast.literal_eval(prices_raw)
                if isinstance(parsed, (list, tuple)) and len(parsed) >= 2:
                    p1 = float(parsed[0] or 0.0)
                    p2 = float(parsed[1] or 0.0)
            except Exception:
                pass
        if p1 > p2:
            winning_token = "token1"
        elif p2 > p1:
            winning_token = "token2"
        elif p1 > 0 and p1 == p2:
            winning_token = "split"
        return winning_token, p1, p2

    def get_market_metadata(self, market_ids: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Loads market questions, end dates, and outcome resolution payouts from cache or markets.parquet.
        """
        if market_ids:
            missing = [m for m in market_ids if m not in self._market_resolutions_cache]
            if missing:
                clean_ids = [f"'{m}'" for m in missing]
                query = f"""
                SELECT id, question, condition_id, token1, token2, closed, outcome_prices,
                       epoch(end_date) as end_timestamp
                FROM '{self.markets_path}'
                WHERE id IN ({', '.join(clean_ids)})
                """
                df = self.conn.execute(query).fetch_df()
                for _, row in df.iterrows():
                    m_id = str(row["id"])
                    winning_tok, p1, p2 = self.parse_outcome_prices(str(row["outcome_prices"] or ""))
                    q_text = str(row["question"] or "")
                    cat, _ = classify_market_category(q_text)
                    self._market_resolutions_cache[m_id] = {
                        "market_id": m_id,
                        "condition_id": str(row["condition_id"] or ""),
                        "question": q_text,
                        "category": cat,
                        "closed": bool(row["closed"]),
                        "winning_token": winning_tok,
                        "p1_payout": p1,
                        "p2_payout": p2,
                        "end_timestamp": float(row["end_timestamp"] or 0.0)
                    }

        return self._market_resolutions_cache

    def find_top_whales_in_window(
        self,
        start_ts: int,
        end_ts: int,
        min_volume_usd: float = 50000.0,
        min_trades: int = 20,
        max_whales: int = 15
    ) -> List[str]:
        """
        Fast aggregation over the specific time window to discover top active candidate whales.
        Progressively relaxes volume constraints if window is narrow or sparsely populated.
        """
        tiers = [
            (min_volume_usd, min_trades),
            (min_volume_usd / 5.0, max(5, min_trades // 2)),
            (min_volume_usd / 20.0, 3),
            (0.0, 1)
        ]
        for vol_thresh, trades_thresh in tiers:
            query = f"""
            SELECT maker as wallet, count(1) as trade_cnt, sum(usd_amount) as total_vol
            FROM '{self.trades_path}'
            WHERE timestamp BETWEEN {start_ts} AND {end_ts}
              AND price BETWEEN 0.02 AND 0.98
            GROUP BY maker
            HAVING sum(usd_amount) >= {vol_thresh} AND count(1) >= {trades_thresh}
            ORDER BY total_vol DESC
            LIMIT {max_whales}
            """
            df = self.conn.execute(query).fetch_df()
            if not df.empty:
                return [str(w).lower() for w in df["wallet"].tolist()]
        return []

    def stream_trades_in_window(
        self,
        start_ts: int,
        end_ts: int,
        whale_addresses: Optional[List[str]] = None,
        limit_trades: Optional[int] = None
    ) -> Generator[TradeSignal, None, None]:
        """
        Streams trades chronologically for specified whales or window with DuckDB partition pushdown
        and joins market metadata directly in the database engine for maximum speed.
        """
        whale_filter = ""
        if whale_addresses:
            clean_addrs = [f"'{w.lower()}'" for w in whale_addresses]
            whale_filter = f"AND lower(t.maker) IN ({', '.join(clean_addrs)})"

        limit_clause = f"LIMIT {limit_trades}" if limit_trades else ""

        query = f"""
        SELECT t.timestamp, t.maker, t.market_id, t.condition_id, t.asset_id,
               t.maker_direction as side, t.price, t.usd_amount, t.token_amount, t.nonusdc_side,
               m.question, m.closed, m.outcome_prices, epoch(m.end_date) as end_timestamp
        FROM '{self.trades_path}' t
        LEFT JOIN '{self.markets_path}' m ON t.market_id = m.id
        WHERE t.timestamp BETWEEN {start_ts} AND {end_ts}
          AND t.price > 0 AND t.usd_amount > 0
          {whale_filter}
        ORDER BY t.timestamp ASC
        {limit_clause}
        """
        cursor = self.conn.execute(query)
        while True:
            chunk = cursor.fetch_df_chunk(5000)
            if chunk is None or len(chunk) == 0:
                break
            for _, row in chunk.iterrows():
                m_id = str(row["market_id"])
                prices_raw = str(row.get("outcome_prices") or "")
                winning_tok, p1, p2 = self.parse_outcome_prices(prices_raw)
                q_text = str(row.get("question") or "")
                cat, _ = classify_market_category(q_text)

                # Cache market metadata
                self._market_resolutions_cache[m_id] = {
                    "market_id": m_id,
                    "condition_id": str(row["condition_id"]),
                    "question": q_text,
                    "category": cat,
                    "closed": bool(row.get("closed")),
                    "winning_token": winning_tok,
                    "p1_payout": p1,
                    "p2_payout": p2,
                    "end_timestamp": float(row.get("end_timestamp") or 0.0)
                }

                yield TradeSignal(
                    timestamp=int(row["timestamp"]),
                    whale_address=str(row["maker"]).lower(),
                    market_id=m_id,
                    condition_id=str(row["condition_id"]),
                    token_id=str(row["asset_id"]),
                    side=str(row["side"]).upper(),
                    whale_price=float(row["price"]),
                    whale_size_usd=float(row["usd_amount"]),
                    whale_shares=float(row["token_amount"]),
                    market_title=q_text,
                    category=cat,
                    nonusdc_side=str(row["nonusdc_side"])
                )

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
