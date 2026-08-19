from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import logging
from app.database import get_db, SessionLocal
from app.services.live_poller import live_trade_mirror

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/signals", tags=["signals"])

class WhaleTradeSignalPayload(BaseModel):
    walletAddress: str
    side: str # BUY or SELL
    assetId: str
    amountFilled: str
    price: Optional[str] = "0.5"
    transactionHash: str
    logIndex: int
    blockNumber: int
    timestamp: Optional[int] = None

@router.post("")
async def receive_whale_signal(
    signal: WhaleTradeSignalPayload,
    background_tasks: BackgroundTasks
):
    """
    Ingests live on-chain OrderFilled signals from Envio HyperSync listener.
    Deduplicates against the unified live mirror engine.
    """
    try:
        # Schedule asynchronous processing to acknowledge listener with sub-millisecond response
        background_tasks.add_task(
            live_trade_mirror.process_onchain_signal,
            wallet_address=signal.walletAddress,
            side=signal.side,
            asset_id=signal.assetId,
            amount_filled=signal.amountFilled,
            price_str=signal.price,
            tx_hash=signal.transactionHash,
            log_index=signal.logIndex,
            block_number=signal.blockNumber,
            timestamp_ms=signal.timestamp
        )
        return {"status": "queued", "txHash": signal.transactionHash, "logIndex": signal.logIndex}
    except Exception as e:
        logger.error(f"Error handling incoming on-chain whale signal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
