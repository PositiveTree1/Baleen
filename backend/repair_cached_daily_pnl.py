#!/usr/bin/env python3
"""
repair_cached_daily_pnl.py

Iterates through active wallets in baleen.db, fetches complete on-chain trade
and closed position histories via Polymarket's authentic APIs, and updates
cached_daily_pnl with full multi-month daily win/loss data.
"""

import argparse
import asyncio
import json
import logging
import os
import sqlite3
import sys
from typing import List, Dict, Any, Optional

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.discovery.polymarket_client import PolymarketClient
from app.discovery.scanner import calculate_authentic_wallet_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("repair_daily_pnl")


async def fetch_wallet_deep_data(client: PolymarketClient, clean_addr: str) -> tuple:
    """Fetch parallel batches of closed positions, trades, activity, positions, and profile."""
    cp_desc = [
        client._fetch_with_retry(
            f"{client.data_api_url}/closed-positions",
            params={"user": clean_addr, "limit": 50, "offset": i * 50, "sortBy": "timestamp", "sortDirection": "DESC"}
        )
        for i in range(25)
    ]
    cp_asc = [
        client._fetch_with_retry(
            f"{client.data_api_url}/closed-positions",
            params={"user": clean_addr, "limit": 50, "offset": i * 50, "sortBy": "timestamp", "sortDirection": "ASC"}
        )
        for i in range(15)
    ]
    tr_tasks = [
        client._fetch_with_retry(
            f"{client.data_api_url}/trades",
            params={"user": clean_addr, "limit": 500, "offset": i * 500}
        )
        for i in range(4)
    ]
    act_tasks = [
        client._fetch_with_retry(
            f"{client.data_api_url}/activity",
            params={"user": clean_addr, "limit": 500, "offset": i * 500, "sortBy": "TIMESTAMP", "sortDirection": "DESC"}
        )
        for i in range(4)
    ]
    pos_task = client.fetch_wallet_positions(clean_addr)
    prof_task = client.fetch_wallet_profile(clean_addr)

    all_results = await asyncio.gather(
        *cp_desc, *cp_asc, *tr_tasks, *act_tasks, pos_task, prof_task,
        return_exceptions=True
    )

    # Deduplicate closed positions
    closed_positions = []
    seen_cp = set()
    for r in all_results[:40]:
        if isinstance(r, list):
            for item in r:
                if isinstance(item, dict):
                    k = (str(item.get("conditionId") or ""), str(item.get("asset") or ""), str(item.get("timestamp") or ""))
                    if k not in seen_cp:
                        seen_cp.add(k)
                        closed_positions.append(item)

    # Trades
    trades = []
    for r in all_results[40:44]:
        if isinstance(r, list):
            trades.extend([t for t in r if isinstance(t, dict)])

    # Activity
    activity = []
    for r in all_results[44:48]:
        if isinstance(r, list):
            activity.extend([a for a in r if isinstance(a, dict)])

    positions = all_results[48] if isinstance(all_results[48], list) else []
    profile = all_results[49] if isinstance(all_results[49], dict) else {}

    return closed_positions, trades, activity, positions, profile


async def repair_wallet(
    client: PolymarketClient,
    conn: sqlite3.Connection,
    address: str,
    pseudonym: Optional[str],
    current_cached: Optional[str],
    total_trades: int,
    force: bool = False
) -> bool:
    clean_addr = address.lower().strip()
    current_pts = []
    if current_cached:
        try:
            current_pts = json.loads(current_cached)
        except Exception:
            current_pts = []

    if not force and len(current_pts) >= 15:
        logger.info(f"Skipping {pseudonym or clean_addr[:10]}: already has {len(current_pts)} daily points.")
        return False

    logger.info(f"Repairing {pseudonym or clean_addr[:10]} ({clean_addr}): current points={len(current_pts)}, total_trades={total_trades}...")

    try:
        closed_positions, trades, activity, positions, profile = await asyncio.wait_for(
            fetch_wallet_deep_data(client, clean_addr),
            timeout=15.0
        )

        if not (closed_positions or trades or positions or activity):
            logger.warning(f"No on-chain records returned for {clean_addr}")
            return False

        stats = calculate_authentic_wallet_stats(
            address=clean_addr,
            positions=positions,
            activity=activity,
            profile=profile,
            trades=trades,
            closed_positions=closed_positions
        )

        real_hist = stats.get("daily_pnl_history", [])
        if not real_hist:
            logger.warning(f"Failed to generate daily PnL history for {clean_addr}")
            return False

        new_cached = json.dumps(real_hist)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE wallets SET cached_daily_pnl = ? WHERE lower(address) = ?",
            (new_cached, clean_addr)
        )
        conn.commit()

        logger.info(
            f"Successfully repaired {pseudonym or clean_addr[:10]}: "
            f"{len(current_pts)} -> {len(real_hist)} points "
            f"({real_hist[0]['date']} to {real_hist[-1]['date']}), "
            f"total trades analyzed: {stats.get('total_trades_analyzed', total_trades)}"
        )
        return True
    except asyncio.TimeoutError:
        logger.error(f"Timed out fetching data for {clean_addr}")
        return False
    except Exception as e:
        logger.error(f"Error repairing {clean_addr}: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Repair cached daily PnL series in baleen.db")
    parser.add_argument("--db", default=os.path.join(BASE_DIR, "baleen.db"), help="Path to baleen.db")
    parser.add_argument("--wallet", help="Repair specific wallet address")
    parser.add_argument("--force", action="store_true", help="Force rebuild even if points >= 15")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of wallets to repair")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        logger.error(f"Database not found at {args.db}")
        sys.exit(1)

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    if args.wallet:
        cursor.execute(
            "SELECT address, pseudonym, cached_daily_pnl, total_trades_analyzed FROM wallets WHERE lower(address) = ?",
            (args.wallet.lower().strip(),)
        )
        wallets = cursor.fetchall()
    else:
        cursor.execute(
            "SELECT address, pseudonym, cached_daily_pnl, total_trades_analyzed FROM wallets WHERE status = 'active' ORDER BY total_trades_analyzed DESC"
        )
        wallets = cursor.fetchall()

    if args.limit > 0:
        wallets = wallets[:args.limit]

    logger.info(f"Targeting {len(wallets)} wallet(s) for audit/repair.")

    client = PolymarketClient()
    repaired_count = 0
    try:
        for row in wallets:
            addr, pseudo, cached, trades = row
            repaired = await repair_wallet(
                client=client,
                conn=conn,
                address=addr,
                pseudonym=pseudo,
                current_cached=cached,
                total_trades=trades or 0,
                force=args.force
            )
            if repaired:
                repaired_count += 1
            # Rate-limit cushion
            await asyncio.sleep(0.3)
    finally:
        await client.close()
        conn.close()

    logger.info(f"Repair complete. Repaired {repaired_count} wallet(s).")


if __name__ == "__main__":
    asyncio.run(main())
