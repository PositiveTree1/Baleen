"""Non-destructive, bounded re-evaluation of retained wallet identities."""
import logging
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, or_
from app.models import Wallet, WalletEvidence, WalletEvidenceObservation
from app.discovery.polymarket_client import PolymarketClient
from app.discovery.wallet_evidence import collect_evidence
from app.services.wallet_reset import current_generation, research_lock

logger = logging.getLogger(__name__)


async def refresh_wallet_evidence(db, *, limit=25, client=None):
    cutoff = datetime.utcnow() - timedelta(hours=24)
    wallets = (await db.execute(select(Wallet).outerjoin(WalletEvidence, Wallet.address == WalletEvidence.wallet_address)
        .where(or_(WalletEvidence.observed_at.is_(None), WalletEvidence.observed_at < cutoff))
        .order_by(WalletEvidence.observed_at.asc().nullsfirst(), Wallet.first_seen_at.asc(), Wallet.address.asc())
        .limit(limit))).scalars().all()
    owned = client is None
    client = client or PolymarketClient()
    count = 0
    try:
        addresses = [w.address for w in wallets]
        for address in addresses:
            try:
                wallet = await db.get(Wallet, address)
                generation = await current_generation(db)
                payload = await asyncio.wait_for(collect_evidence(client, address), timeout=90)
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
                wallet.win_rate_pct = None
                wallet.wilson_lb = None
                wallet.alpha_per_trade = None
                wallet.profit_factor = None
                wallet.baleen_score = None
                wallet.median_inter_trade_gap_hours = None
                wallet.ai_summary = "Research status: " + payload["classification"].replace("_", " ") + ". Copy performance has not been validated."
                wallet.ai_style_tag = payload["classification"].replace("_", " ")
                wallet.is_hft = "FILL_RATE_ABOVE_30_OR_DAILY_BURST" in payload["reasons"]
                wallet.last_scored_at = evidence.observed_at
                await db.commit()
                count += 1
            except Exception:
                await db.rollback()
                logger.exception("Wallet evidence refresh failed")
    finally:
        if owned:
            await client.close()
    return count
