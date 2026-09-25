"""Record fresh source windows and venue books without creating any orders."""
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.models import WalletEvidence, WalletShadowObservation, KeyValue
from app.discovery.polymarket_client import PolymarketClient
from app.discovery.wallet_evidence import cursor_history, POLICY_VERSION
from app.services.wallet_reset import current_generation, research_lock


async def capture_window(client, address, start, end):
    trades = await cursor_history(client, "/v2/trades", address,
                                  {"start": start, "end": end, "taker_only": "false", "filter_amount": 0}, max_pages=2)
    tokens = sorted({str(row["token_id"]) for row in trades["rows"] if row.get("token_id")})
    semaphore = asyncio.Semaphore(3)
    async def observe(token):
        async with semaphore:
            book, fee = await asyncio.gather(client.fetch_order_book(token),
                client._fetch_with_retry(f"{client.clob_api_url}/fee-rate", {"token_id": token}))
            now_ms = int(datetime.now(timezone.utc).timestamp()*1000)
            fresh = isinstance(book, dict) and str(book.get("asset_id")) == token
            try:
                fresh = fresh and 0 <= now_ms-int(book["timestamp"]) <= 30000
            except (ValueError, TypeError, KeyError):
                fresh = False
            # Keep raw market fee rules with the book. The fee-rate endpoint
            # alone does not establish the actual charged fee for a fill.
            market = None
            market_error = None
            condition = book.get("market") if isinstance(book, dict) else None
            if isinstance(condition, str) and condition:
                try:
                    market = await client.fetch_market_info(condition)
                    if not isinstance(market, dict):
                        market = None
                        market_error = "MarketMetadataUnavailable"
                except Exception as exc:
                    market_error = type(exc).__name__
            else:
                market_error = "BookMarketIdentityUnavailable"
            return token, {"observed_at_ms": now_ms, "book": book, "fee_response": fee,
                           "fresh_book": bool(fresh), "market_metadata": market,
                           "market_metadata_error": market_error,
                           "market_observed_at_ms": int(datetime.now(timezone.utc).timestamp()*1000)}
    books = dict(await asyncio.gather(*(observe(t) for t in tokens[:20])))
    return {"source_window": trades, "venue_observations": books, "token_budget_exhausted": len(tokens) > 20,
            "mode": "forward_observation_only", "execution_approved": False,
            "limitations": ["Overlapping windows intentionally retain late-indexed fills; reconcile receipt log IDs before replay.",
                            "Books are observed after discovery, not reconstructed at source execution time.",
                            "No fills, outcomes or fee amounts are assumed from a book snapshot."]}


async def capture_research_batch(db, *, client=None, now=None, limit=5):
    generation = await current_generation(db)
    if generation == "legacy": return 0
    now = now or int(datetime.now(timezone.utc).timestamp())
    observations = (await db.execute(select(WalletEvidence).where(
        WalletEvidence.observed_at >= datetime.utcnow()-timedelta(hours=24)))).scalars().all()
    eligible = [e for e in observations if e.payload.get("generation") == generation
                and e.payload.get("policy_version") == POLICY_VERSION
                and e.payload.get("classification") in ("watchlist", "research_candidate")]
    work = []
    for evidence in eligible:
        key = "shadow_window:" + evidence.wallet_address
        previous = (await db.execute(select(KeyValue.value).where(KeyValue.key == key))).scalar_one_or_none()
        # Rotation is oldest-first; the checkpoint is reset by a generation key.
        try:
            old_generation, timestamp = previous.rsplit(":", 1) if previous else (None, "0")
            checkpoint = int(timestamp) if old_generation == generation else 0
        except (ValueError, AttributeError): checkpoint = 0
        attempt_key = "shadow_attempt:" + evidence.wallet_address
        last_attempt = (await db.execute(select(KeyValue.updated_at).where(KeyValue.key == attempt_key))).scalar_one_or_none()
        work.append((last_attempt or datetime.min, checkpoint, evidence.wallet_address, key,
                     int(evidence.observed_at.replace(tzinfo=timezone.utc).timestamp()), attempt_key))
    # All database values required for the remote observation are now plain
    # Python values. Return the pooled connection before up to 30 seconds of
    # provider and order-book requests.
    await db.commit()
    owned = client is None
    client = client or PolymarketClient()
    count = 0
    try:
        for _, checkpoint, address, key, qualified_at, attempt_key in sorted(work)[:limit]:
            start = max(qualified_at, checkpoint-120 if checkpoint else now-60)
            if start > now: continue
            try:
                payload = await asyncio.wait_for(capture_window(client, address, start, now), timeout=30)
            except Exception as exc:
                payload = {"source_window": {"rows": [], "complete": False, "scope": {"start": start, "end": now},
                                             "reason": type(exc).__name__}, "mode": "forward_observation_only", "execution_approved": False}
            await research_lock(db)
            if await current_generation(db) != generation:
                await db.rollback()
                break
            if payload["source_window"]["rows"] or not payload["source_window"]["complete"]:
                db.add(WalletShadowObservation(wallet_address=address, generation=generation, payload=payload))
                count += 1
            marker = await db.get(KeyValue, key)
            next_checkpoint = now if payload["source_window"]["complete"] else checkpoint or start
            if marker is None: db.add(KeyValue(key=key, value=f"{generation}:{next_checkpoint}"))
            else: marker.value = f"{generation}:{next_checkpoint}"
            attempt = await db.get(KeyValue, attempt_key)
            if attempt is None: db.add(KeyValue(key=attempt_key, value=generation, updated_at=datetime.utcnow()))
            else:
                attempt.value = generation
                attempt.updated_at = datetime.utcnow()
            await db.commit()
    finally:
        if owned: await client.close()
    return count
