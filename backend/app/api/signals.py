import uuid
import json
import logging
from datetime import datetime
from typing import Optional
from decimal import Decimal, InvalidOperation
import re
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_listener_service_key
from app.database import get_db
from app.models import SignalInbox, Wallet, ExecutionLog, LiveCopyPolicy, LiveExecutionAccount, LiveSourcePosition
from app.services.live_poller import live_trade_mirror

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get('/watched-wallets')
async def watched_wallets(db: AsyncSession = Depends(get_db),
                          _authenticated: bool = Depends(verify_listener_service_key)):
    active = (await db.execute(select(Wallet.address).where(Wallet.status == 'active'))).scalars().all()
    held = (await db.execute(select(ExecutionLog.source_wallet_address).where(
        ExecutionLog.side == 'BUY', ExecutionLog.status == 'FILLED').distinct())).scalars().all()
    policies = (await db.execute(select(LiveCopyPolicy.source_wallets).join(LiveExecutionAccount,
        LiveExecutionAccount.user_id == LiveCopyPolicy.user_id).where(LiveExecutionAccount.enabled.is_(True)))).scalars().all()
    live_held = (await db.execute(select(LiveSourcePosition.source_wallet_address).where(
        LiveSourcePosition.quantity > 0))).scalars().all()
    return sorted({a.lower() for a in [*active, *held, *live_held, *(a for sources in policies for a in sources)] if a})


class WhaleTradeSignalPayload(BaseModel):
    walletAddress: str
    side: str  # BUY or SELL
    assetId: str
    amountFilled: str
    price: str
    transactionHash: str
    logIndex: int
    blockNumber: int
    timestamp: Optional[int] = None
    amountUnit: str
    chainId: int = 137
    contractAddress: Optional[str] = None
    blockHash: Optional[str] = None
    sourceVersion: Optional[str] = None
    isMaker: Optional[bool] = None

    @field_validator('chainId')
    @classmethod
    def validate_chain(cls, v):
        if v != 137:
            raise ValueError('Unsupported chain')
        return v

    @field_validator('amountUnit')
    @classmethod
    def validate_unit(cls, v):
        if v != 'raw_6':
            raise ValueError('amountFilled must be raw six-decimal token units')
        return v

    @field_validator("walletAddress")
    @classmethod
    def validate_wallet(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.fullmatch(r'0x[0-9a-f]{40}', clean):
            raise ValueError("Invalid wallet address format (must be 0x-prefixed 42-character hex).")
        return clean

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        s = v.strip().upper()
        if s not in ("BUY", "SELL"):
            raise ValueError("Side must be 'BUY' or 'SELL'.")
        return s

    @field_validator("amountFilled")
    @classmethod
    def validate_amount(cls, v: str) -> str:
        try:
            amt = Decimal(v)
            if not amt.is_finite() or amt <= 0 or amt != amt.to_integral_value() or amt >= 2 ** 256:
                raise ValueError("amountFilled must be positive.")
        except (ValueError, InvalidOperation):
            raise ValueError("amountFilled must be a valid positive numeric string.")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("price is required.")
        try:
            p = float(v)
            if not (0.0001 <= p <= 0.9999):
                raise ValueError("price must be between 0.0001 and 0.9999.")
        except ValueError:
            raise ValueError("price must be a valid float between 0.0001 and 0.9999.")
        return v

    @field_validator("transactionHash")
    @classmethod
    def validate_tx_hash(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.fullmatch(r'0x[0-9a-f]{64}', clean):
            raise ValueError("Invalid transactionHash format (must be 0x-prefixed 64-hex-character string).")
        return clean

    @field_validator("logIndex")
    @classmethod
    def validate_log_index(cls, v: int) -> int:
        if v < 0:
            raise ValueError("logIndex cannot be negative.")
        return v


@router.post("")
async def receive_whale_signal(
    signal: WhaleTradeSignalPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _authenticated: bool = Depends(verify_listener_service_key)
):
    """
    Ingests live on-chain OrderFilled signals from listener.
    Requires listener service authentication.
    Atomically persists into signal_inbox before returning HTTP 200 acknowledgement.
    """
    idempotency_key = f"137:{signal.transactionHash.lower()}:{signal.logIndex}:{signal.walletAddress.lower()}"

    try:
        # 1. Idempotency Check in durable signal_inbox
        stmt = select(SignalInbox).where(SignalInbox.idempotency_key == idempotency_key).limit(1)
        existing = (await db.execute(stmt)).scalars().first()
        if existing:
            payload_data = existing.payload if isinstance(existing.payload, dict) else json.loads(existing.payload)
            # Detect contradictory conflict under same identity
            normalized_old = WhaleTradeSignalPayload.model_validate(payload_data).model_dump()
            if normalized_old != signal.model_dump():
                logger.warning(f"Conflicting payload for identical idempotency key {idempotency_key}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Conflicting signal payload for key {idempotency_key}"
                )
            return {
                "status": "queued",
                "accepted": True,
                "duplicate": True,
                "inboxId": str(existing.id),
                "txHash": signal.transactionHash,
                "logIndex": signal.logIndex
            }

        # 2. Persist new durable inbox record
        inbox_entry = SignalInbox(
            id=uuid.uuid4(),
            source="listener",
            idempotency_key=idempotency_key,
            payload=signal.model_dump(),
            status="PENDING",
            received_at=datetime.utcnow()
        )
        db.add(inbox_entry)
        try:
            await db.commit()
        except IntegrityError:
            # Another replica may have committed this identity after our read.
            await db.rollback()
            return await receive_whale_signal(signal, background_tasks, db, _authenticated)
        inbox_id_str = str(inbox_entry.id)

        # The scheduled inbox worker also finds this row after an API restart.
        from app.services.signal_worker import drain_signal_inbox
        background_tasks.add_task(drain_signal_inbox)

        return {
            "status": "queued",
            "accepted": True,
            "inboxId": inbox_id_str,
            "txHash": signal.transactionHash,
            "logIndex": signal.logIndex
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error persisting incoming on-chain whale signal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
