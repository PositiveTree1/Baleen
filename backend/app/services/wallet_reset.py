"""Transactional, idempotent reset of wallet research, never account accounting."""
import json
import re
from datetime import datetime
from sqlalchemy import select, delete, text
from app.models import Wallet, WalletEvidence, WalletSnapshot, WalletResetBatch, WalletEvidenceArchive, KeyValue

GENERATION_KEY = "wallet_research_generation"
RESET_LOCK = 2026091701


async def research_lock(db):
    if db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": RESET_LOCK})


async def current_generation(db):
    return (await db.execute(select(KeyValue.value).where(KeyValue.key == GENERATION_KEY))).scalar_one_or_none() or "legacy"


def record(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


async def reset_wallet_statistics(db, reset_id):
    """Caller commits/rolls back. Production workers must be stopped for cutover.

    The generation fence also discards concurrent evidence fetched before reset.
    Previous binaries cannot honor that fence, hence the cutover requirement.
    """
    if not isinstance(reset_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}", reset_id) or reset_id == "legacy":
        raise ValueError("Use a stable reset ID of 1–100 letters, digits, dots, underscores or hyphens; 'legacy' is reserved")
    await research_lock(db)
    previous = await db.get(WalletResetBatch, reset_id)
    if previous:
        return {"reset_id": reset_id, "wallet_count": previous.wallet_count, "already_applied": True}
    wallets = (await db.execute(select(Wallet).order_by(Wallet.address))).scalars().all()
    batch = WalletResetBatch(reset_id=reset_id, wallet_count=len(wallets))
    db.add(batch)
    await db.flush()
    for wallet in wallets:
        evidence = await db.get(WalletEvidence, wallet.address)
        snapshots = (await db.execute(select(WalletSnapshot).where(WalletSnapshot.wallet_address == wallet.address))).scalars().all()
        payload = {"wallet": record(wallet), "evidence": record(evidence) if evidence else None,
                   "score_snapshots": [record(s) for s in snapshots]}
        db.add(WalletEvidenceArchive(reset_id=reset_id, wallet_address=wallet.address,
                                    payload=json.loads(json.dumps(payload, default=str))))
        # Explicit identity retention; new model columns default to being cleared.
        for column in Wallet.__table__.columns:
            if column.name not in {"address", "first_seen_at", "status", "dormant", "is_hft"}:
                setattr(wallet, column.name, None)
        wallet.status = "tracked"
        wallet.dormant = False
        wallet.is_hft = False
        wallet.rejection_reason = "FRESH_EVIDENCE_REQUIRED"
    await db.execute(delete(WalletEvidence))
    await db.execute(delete(WalletSnapshot))
    generation = await db.get(KeyValue, GENERATION_KEY)
    if generation is None:
        db.add(KeyValue(key=GENERATION_KEY, value=reset_id, updated_at=datetime.utcnow()))
    else:
        generation.value = reset_id
        generation.updated_at = datetime.utcnow()
    await db.flush()
    return {"reset_id": reset_id, "wallet_count": len(wallets), "already_applied": False}
