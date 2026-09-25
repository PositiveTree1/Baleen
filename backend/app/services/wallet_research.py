"""Non-destructive, bounded re-evaluation of retained wallet identities."""
import logging
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import and_, select, or_
from app.models import Wallet, WalletEvidence, WalletEvidenceObservation
from app.discovery.polymarket_client import PolymarketClient
from app.discovery.wallet_evidence import collect_evidence, POLICY_VERSION
from app.services.wallet_reset import current_generation, research_lock

logger = logging.getLogger(__name__)
EVIDENCE_BATCH_SIZE = 4


async def refresh_wallet_evidence(db, *, limit=25, client=None):
    cutoff = datetime.utcnow() - timedelta(hours=24)
    wallets = (await db.execute(select(Wallet).outerjoin(WalletEvidence, Wallet.address == WalletEvidence.wallet_address)
        # A retained legacy address is not current research merely because it
        # has no evidence.  Only addresses admitted through the $50k profile
        # gate (pending) enter their first evidence pass; observed wallets are
        # then re-evaluated on the normal freshness cadence.
        .where(or_(and_(WalletEvidence.observed_at.is_(None), Wallet.status == "pending"),
                   WalletEvidence.observed_at < cutoff,
                   WalletEvidence.payload["policy_version"].as_string() != POLICY_VERSION))
        .order_by(WalletEvidence.observed_at.asc().nullsfirst(), Wallet.first_seen_at.asc(), Wallet.address.asc())
        .limit(limit))).scalars().all()
    addresses = [w.address for w in wallets]
    # The addresses are materialized above. Release the database connection
    # before the provider calls below, which can take tens of seconds per
    # batch. Holding it would starve API requests on the small production pool.
    await db.commit()
    owned = client is None
    client = client or PolymarketClient()
    count = 0
    try:
        for start in range(0, len(addresses), EVIDENCE_BATCH_SIZE):
            batch = addresses[start:start + EVIDENCE_BATCH_SIZE]
            generation = await current_generation(db)
            await db.commit()

            async def collect(address):
                try:
                    return address, await asyncio.wait_for(collect_evidence(client, address), timeout=90), None
                except Exception as exc:
                    return address, None, exc

            results = await asyncio.gather(*(collect(address) for address in batch))
            for address, payload, error in results:
                if error is not None or payload is None:
                    logger.error("Wallet evidence refresh failed for %s: %s", address, type(error).__name__)
                    continue
                try:
                    wallet = await db.get(Wallet, address)
                    await research_lock(db)
                    if await current_generation(db) != generation:
                        await db.rollback()
                        continue
                    payload["generation"] = generation
                    evidence = await db.get(WalletEvidence, wallet.address)
                    if evidence is None:
                        evidence = WalletEvidence(wallet_address=wallet.address)
                        db.add(evidence)
                    evidence.observed_at = datetime.utcnow()
                    evidence.payload = payload
                    db.add(WalletEvidenceObservation(wallet_address=address, generation=generation,
                                                      observed_at=evidence.observed_at, payload=payload))
                    # Keep identities and existing follower positions. This flag is
                    # only eligibility for NEW allocations, never an instruction to sell.
                    wallet.status = "tracked"
                    wallet.rejection_reason = "; ".join(payload["reasons"])
                    wallet.avg_trades_per_day = payload["metrics"]["fills_per_day_30d"] if payload["trade_coverage"]["complete"] else None
                    if payload["metrics"].get("economic_pnl") is not None:
                        wallet.all_time_pnl_usd = payload["metrics"]["economic_pnl"]
                    wallet.total_trades_analyzed = payload["metrics"].get("fills_30d") if payload["trade_coverage"]["complete"] else None
                    wallet.cached_daily_pnl = None
                    wallet.trades_per_hour = None
                    # Retire unsupported legacy metrics rather than displaying
                    # heuristic values beside verified provider observations.
                    wallet.max_drawdown_pct = None
                    wallet.wilson_lb = None
                    wallet.alpha_per_trade = None
                    wallet.ai_summary = "Research status: " + payload["classification"].replace("_", " ") + ". Copy performance has not been validated."
                    wallet.ai_style_tag = payload["classification"].replace("_", " ")
                    wallet.is_hft = "FILL_RATE_ABOVE_40_OR_DAILY_BURST" in payload["reasons"]
                    wallet.win_rate_pct = payload["metrics"].get("closed_position_win_rate_pct")
                    wallet.profit_factor = payload["metrics"].get("closed_position_profit_factor")
                    wallet.baleen_score = payload["metrics"].get("evidence_quality_score")
                    wallet.median_inter_trade_gap_hours = payload["metrics"].get("median_inter_fill_gap_hours")
                    wallet.last_scored_at = evidence.observed_at
                    await db.commit()
                    count += 1
                except Exception:
                    await db.rollback()
                    logger.exception("Wallet evidence persistence failed")
    finally:
        if owned:
            await client.close()
    return count
