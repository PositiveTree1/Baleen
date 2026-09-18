"""Fresh research approval for new entries after a wallet-statistics cutover."""
from datetime import datetime, timedelta
from app.models import WalletEvidence
from app.discovery.wallet_evidence import POLICY_VERSION
from app.services.wallet_reset import current_generation
from app.services.live_risk import RiskRejected


async def require_research_approval(db, address, side):
    if side != "BUY":
        return  # Demotion/reset must not suppress an existing holding's exit.
    generation = await current_generation(db)
    if generation == "legacy":
        return  # Existing account-owned policies remain unchanged before cutover.
    evidence = await db.get(WalletEvidence, address.lower())
    if (evidence is None or evidence.payload.get("generation") != generation
            or evidence.payload.get("policy_version") != POLICY_VERSION
            or evidence.payload.get("execution_approved") is not True
            or evidence.observed_at < datetime.utcnow()-timedelta(hours=24)):
        raise RiskRejected("Fresh wallet research approval required after statistics reset")
