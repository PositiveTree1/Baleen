"""Account-owned session setup and explicit copy policy; no owner private keys."""
from datetime import datetime
from decimal import Decimal
import json
import re
from types import SimpleNamespace
from typing import Literal
import uuid
from eth_account import Account
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.auth import get_current_user, encrypt_secret
from app.database import get_db, SessionLocal
from app.models import User, LiveSigningSession, LiveWalletLink, LiveCopyPolicy, LiveSessionOperation, LiveSourcePosition, LiveOrderIntent, LiveExecutionAccount
from app.services.live_copy_coordinator import policy_limits
from app.services.live_runtime import live_runtime, verify_owner_wallet
from app.api.live_trading import _disable_order_account

router = APIRouter(prefix='/api/live-trading', tags=['live-setup'])


def public_session(row):
    stale = row.valid_until is None or row.valid_until <= datetime.utcnow()
    state = 'locally_disabled' if row.revoked_at else (
        'awaiting_owner_authorization' if row.verified_at is None else 'expired' if stale else 'authorization_observed')
    return {'walletAddress':row.wallet_address, 'sessionAddress':row.session_address,
        'verifiedAt':row.verified_at, 'validUntil':row.valid_until, 'revokedAt':row.revoked_at,
        'scope':'CLOB', 'status':state,
        'ownerAuthorizationRequired':row.verified_at is None or stale or row.revoked_at is not None,
        'liveExecutionReady':False}


@router.get('/session')
async def get_session(user: User = Depends(get_current_user), db=Depends(get_db)):
    row = await db.get(LiveSigningSession, user.id)
    return public_session(row) if row else {'status':'not_configured','liveExecutionReady':False}


@router.post('/session')
async def prepare_session(user: User = Depends(get_current_user), db=Depends(get_db)):
    # Account row locks serialize policy/setup/stop operations even before a
    # funded live-execution account exists.
    await db.execute(select(User).where(User.id == user.id).with_for_update())
    row = await db.get(LiveSigningSession, user.id)
    if row:
        return public_session(row)  # Never silently replace an authorized key.
    link = await db.get(LiveWalletLink, user.id)
    if (not link or link.signature_type != 3 or not link.signer_address
            or not re.fullmatch(r'0x[0-9a-fA-F]{40}', link.polymarket_wallet_address or '')):
        raise HTTPException(409, 'Configure Deposit Wallet and owner API credentials first')
    wallet = link.polymarket_wallet_address.lower()
    try:
        await verify_owner_wallet(link)
    except Exception as exc:
        raise HTTPException(409, 'Deposit Wallet ownership could not be verified with the saved owner credentials') from exc
    if (await db.execute(select(LiveSigningSession.user_id).where(
            LiveSigningSession.wallet_address == wallet))).first():
        raise HTTPException(409, 'This wallet already has a signing session on another account')
    key = Account.create()
    row = LiveSigningSession(user_id=user.id, wallet_address=wallet, session_address=key.address.lower(),
        encrypted_key=encrypt_secret(json.dumps({'purpose':'baleen-clob-session', 'user_id':str(user.id),
            'wallet':wallet,'key':key.key.hex()})))
    db.add(row)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, 'Wallet session setup conflicted; reload the current setup') from exc
    return public_session(row)


@router.post('/session/verify')
async def verify_session(user: User = Depends(get_current_user), db=Depends(get_db)):
    try:
        async with live_runtime(SessionLocal, user.id) as runtime:
            expiry = await runtime.signer.verify_authorization()
            address = runtime.signer.session_address
    except Exception as exc:
        raise HTTPException(409, 'Owner-approved CLOB session authorization is not verified') from exc
    await db.execute(select(User).where(User.id == user.id).with_for_update())
    row = await db.get(LiveSigningSession, user.id)
    if row is None or row.revoked_at or row.session_address != address:
        raise HTTPException(409, 'Session changed during verification')
    row.verified_at, row.valid_until = datetime.utcnow(), datetime.utcfromtimestamp(expiry)
    operations = (await db.execute(select(LiveSessionOperation).where(
        LiveSessionOperation.user_id == user.id, LiveSessionOperation.kind == 'AUTHORIZE',
        LiveSessionOperation.session_address == address,
        LiveSessionOperation.state.in_(['SUBMITTING','UNKNOWN','PENDING'])))).scalars().all()
    for operation in operations:
        if operation.valid_until == expiry:
            operation.state = 'GRANT_OBSERVED'
    await db.commit()
    return public_session(row)


@router.post('/session/disable')
async def disable_session(user: User = Depends(get_current_user), db=Depends(get_db)):
    await db.execute(select(User).where(User.id == user.id).with_for_update())
    await _disable_order_account(db, user.id)
    row = await db.get(LiveSigningSession, user.id)
    if row:
        row.revoked_at, row.verified_at = datetime.utcnow(), None
    operations = (await db.execute(select(LiveSessionOperation).where(
        LiveSessionOperation.user_id == user.id, LiveSessionOperation.kind == 'AUTHORIZE',
        LiveSessionOperation.state == 'PREPARED'))).scalars().all()
    for operation in operations:
        operation.state = 'VOID'
    await db.commit()
    return {'localSigningDisabled':True, 'ownerRevocationRequired':True,
            'message':'Local signing stopped; revoke the session grant with the Deposit Wallet owner to remove exchange authority.'}


class CopyPolicyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_wallets: list[str] = Field(min_length=1, max_length=20)
    copy_ratio: Decimal = Field(gt=0, le=1)
    max_order_cash: Decimal = Field(gt=0)
    max_total_exposure: Decimal = Field(gt=0)
    max_token_exposure: Decimal = Field(gt=0)
    max_daily_loss: Decimal = Field(gt=0)
    max_open_orders: int = Field(gt=0, le=100, strict=True)
    max_slippage_bps: Decimal = Field(ge=0, le=10000)
    max_quote_age_ms: int = Field(gt=0, le=60000, strict=True)
    max_source_age_ms: int = Field(gt=0, le=3600000, strict=True)
    max_fee_bps: Decimal = Field(ge=0, le=10000)


@router.put('/copy-policy')
async def save_policy(req: CopyPolicyRequest, user: User = Depends(get_current_user), db=Depends(get_db)):
    sources = [a.lower() for a in req.source_wallets]
    if len(set(sources)) != len(sources) or any(not re.fullmatch(r'0x[0-9a-f]{40}', a) for a in sources):
        raise HTTPException(422, 'Source wallet addresses must be valid and unique')
    values = req.model_dump(mode='json')
    values.pop('source_wallets')
    values.pop('copy_ratio')
    policy_limits(SimpleNamespace(limits=values))
    await db.execute(select(User).where(User.id == user.id).with_for_update())
    await db.execute(select(LiveExecutionAccount.user_id).where(LiveExecutionAccount.user_id == user.id).with_for_update())
    row = await db.get(LiveCopyPolicy, user.id)
    if row is not None and row.copy_ratio != req.copy_ratio:
        holdings = (await db.execute(select(LiveSourcePosition.token_id).where(
            LiveSourcePosition.user_id == user.id, LiveSourcePosition.quantity > 0).limit(1))).first()
        pending = (await db.execute(select(LiveOrderIntent.id).where(
            LiveOrderIntent.user_id == user.id,
            LiveOrderIntent.state.in_(['PREPARED', 'SUBMITTING', 'UNKNOWN', 'ACKNOWLEDGED', 'PARTIAL'])).limit(1))).first()
        if holdings or pending:
            raise HTTPException(409, 'Copy ratio is fixed while source holdings or unresolved orders remain')
    await _disable_order_account(db, user.id)
    if row is None:
        row = LiveCopyPolicy(user_id=user.id, revision=0)
        db.add(row)
    row.revision += 1
    row.source_wallets, row.copy_ratio, row.limits, row.updated_at = sources, req.copy_ratio, values, datetime.utcnow()
    await db.commit()
    return {'revision':row.revision, 'source_wallets':row.source_wallets, 'copy_ratio':str(row.copy_ratio),
            'limits':row.limits, 'requiresReactivation':True}


@router.get('/copy-policy')
async def get_policy(user: User = Depends(get_current_user), db=Depends(get_db)):
    row = await db.get(LiveCopyPolicy, user.id)
    return {'revision':row.revision, 'source_wallets':row.source_wallets, 'copy_ratio':str(row.copy_ratio),
            'limits':row.limits} if row else None


class SessionChallengeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['AUTHORIZE','REVOKE']


class SessionSignatureRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    signature: str = Field(pattern=r'^0x[0-9a-fA-F]{130}$')


@router.post('/session/operations')
async def prepare_session_operation(req: SessionChallengeRequest, user: User = Depends(get_current_user)):
    from app.services.session_authorization import SessionAuthorization, SessionRelay
    try:
        return await SessionAuthorization(SessionLocal, SessionRelay()).prepare(user.id, req.kind)
    except Exception as exc:
        raise HTTPException(409, 'Session operation unavailable: approved builder access and verified Deposit Wallet setup are required') from exc


@router.post('/session/operations/{operation_id}/signature')
async def submit_session_operation(operation_id: uuid.UUID, req: SessionSignatureRequest,
                                   user: User = Depends(get_current_user)):
    from app.services.session_authorization import SessionAuthorization, SessionRelay
    try:
        return await SessionAuthorization(SessionLocal, SessionRelay()).submit(user.id, operation_id, req.signature)
    except Exception as exc:
        raise HTTPException(409, 'Operation could not be confirmed; reload its status before signing another request') from exc


@router.get('/session/operations')
async def list_session_operations(user: User = Depends(get_current_user), db=Depends(get_db)):
    from app.services.session_authorization import public_operation
    rows = (await db.execute(select(LiveSessionOperation).where(LiveSessionOperation.user_id == user.id)
        .order_by(LiveSessionOperation.created_at.desc()).limit(20))).scalars().all()
    return [public_operation(row) for row in rows]


@router.post('/initialize-account')
async def initialize_live_account(user: User = Depends(get_current_user)):
    import asyncio
    import httpx
    from app.config import settings
    from app.services.live_bootstrap import LiveBootstrap
    from app.services.live_wallet_snapshot import LiveWalletSnapshot
    from app.services.settlement_receipts import PolygonSettlementReader
    if not settings.POLYGON_SETTLEMENT_RPC_URL:
        raise HTTPException(409, 'Confirmed Polygon wallet evidence is not configured')
    try:
        async with asyncio.timeout(90), live_runtime(SessionLocal, user.id) as runtime, httpx.AsyncClient(
            base_url=settings.POLYGON_SETTLEMENT_RPC_URL, timeout=10, follow_redirects=False) as rpc:
            return await LiveBootstrap(SessionLocal, runtime, LiveWalletSnapshot(PolygonSettlementReader(rpc))).initialize(user.id)
    except Exception as exc:
        raise HTTPException(409, 'Live account initialization needs a verified session, complete confirmed funding, no open orders and no unimported positions') from exc
