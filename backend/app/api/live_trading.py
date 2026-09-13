import logging
import uuid
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.database import get_db
from app.models import User, LiveWalletLink, ExecutionLog, LiveExecutionAccount, LiveOrderIntent, LivePosition, LiveReconciliation, LiveSigningSession, LiveCopyPolicy, LiveWalletBaseline
from app.config import settings
from app.auth import get_current_user, encrypt_secret, decrypt_secret

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/live-trading", tags=["live-trading"])


async def _disable_order_account(db, user_id):
    account = (await db.execute(select(LiveExecutionAccount).where(
        LiveExecutionAccount.user_id == user_id).with_for_update())).scalar_one_or_none()
    if account:
        account.enabled = False
        # Preserve reservations: an in-flight order still needs reconciliation.
        orders = (await db.execute(select(LiveOrderIntent).where(
            LiveOrderIntent.user_id == user_id,
            LiveOrderIntent.state.in_(['PREPARED', 'SUBMITTING', 'UNKNOWN', 'ACKNOWLEDGED', 'PARTIAL'])))).scalars().all()
        for order in orders:
            if order.cancel_requested_at is None:
                order.cancel_requested_at = datetime.utcnow()


@router.get('/capabilities')
async def live_capabilities(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    link = (await db.execute(select(LiveWalletLink).where(LiveWalletLink.user_id == current_user.id))).scalar_one_or_none()
    configured = bool(link and link.clob_api_key_enc and link.clob_api_secret_enc and link.clob_api_passphrase_enc)
    session = await db.get(LiveSigningSession, current_user.id)
    bound = bool(link and ((link.signer_address and link.signature_type == 0
                 and link.signer_address.lower() == (link.polymarket_wallet_address or '').lower())
        or (link.signature_type == 3 and session and session.wallet_address == link.polymarket_wallet_address.lower()
            and session.verified_at and session.revoked_at is None and session.valid_until
            and session.valid_until > datetime.utcnow())))
    verified = bool(configured and bound and (link.last_verified_at or (session and session.verified_at)))
    blockers = ['external_cash_and_settlement_accounting', 'owner_revocation_confirmation',
                'browser_and_deployment_acceptance', 'bounded_pilot_validation']
    if not verified or not link or link.signature_type != 3: blockers.append('verified_scoped_wallet_authorization')
    if await db.get(LiveCopyPolicy, current_user.id) is None: blockers.append('approved_live_risk_policy')
    if await db.get(LiveWalletBaseline, current_user.id) is None: blockers.append('verified_wallet_funding_baseline')
    return {'credentials_configured': configured,
            'credentials_verified': verified,
            'wallet_binding_verified': bound,
            'live_execution_ready': False,
            'blocking_requirements': blockers,
            'collateral_currency': 'pUSD'}


@router.get('/execution-state')
async def live_execution_state(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(LiveExecutionAccount, current_user.id)
    if account is None:
        return {'status': 'unavailable', 'reason': 'No reconciled live account',
                'cash': None, 'reservedCash': None, 'positions': [], 'orders': [], 'liveExecutionReady': False}
    positions = (await db.execute(select(LivePosition).where(LivePosition.user_id == current_user.id))).scalars().all()
    orders = (await db.execute(select(LiveOrderIntent).where(LiveOrderIntent.user_id == current_user.id)
                              .order_by(LiveOrderIntent.created_at.desc()).limit(100))).scalars().all()
    latest = (await db.execute(select(LiveReconciliation).where(LiveReconciliation.user_id == current_user.id)
                              .order_by(LiveReconciliation.started_at.desc()).limit(1))).scalar_one_or_none()
    return {'status': 'available', 'liveExecutionReady': False, 'runId': str(account.run_id),
            'cash': str(account.cash), 'reservedCash': str(account.reserved_cash),
            'availableCash': str(account.cash - account.reserved_cash),
            'reconciledAt': account.reconciled_at.isoformat() if account.reconciled_at else None,
            'collateralCurrency': 'pUSD',
            'reconciliation': {'status': latest.status, 'detail': latest.detail,
                'finishedAt': latest.finished_at.isoformat() if latest.finished_at else None} if latest else None,
            'positions': [{'tokenId': p.token_id, 'quantity': str(p.quantity),
                           'reservedQuantity': str(p.reserved_quantity), 'costBasis': str(p.cost_basis)} for p in positions],
            'orders': [{'id': str(o.id), 'tokenId': o.token_id, 'side': o.side, 'state': o.state,
                        'quantity': str(o.quantity), 'filledQuantity': str(o.filled_quantity),
                        'limitPrice': str(o.limit_price),
                        'cancelRequestedAt': o.cancel_requested_at.isoformat() if o.cancel_requested_at else None} for o in orders]}


class SaveCredentialsRequest(BaseModel):
    user_id: Optional[str] = None
    polymarket_wallet_address: str
    clob_api_key: str
    clob_api_secret: str
    clob_api_passphrase: str
    signer_address: Optional[str] = None
    signature_type: Optional[int] = Field(default=None, ge=0, le=3)


class TestConnectionRequest(BaseModel):
    user_id: Optional[str] = None
    polymarket_wallet_address: Optional[str] = None
    clob_api_key: Optional[str] = None
    clob_api_secret: Optional[str] = None
    clob_api_passphrase: Optional[str] = None
    signer_address: Optional[str] = None
    signature_type: Optional[int] = Field(default=None, ge=0, le=3)


class ToggleLiveTradingRequest(BaseModel):
    user_id: Optional[str] = None
    enabled: bool


def _mask_key(key: Optional[str]) -> str:
    if not key:
        return ""
    k = str(key).strip()
    if len(k) <= 8:
        return "********"
    return f"{k[:4]}...{k[-4:]}"


async def _resolve_user(
    db: AsyncSession,
    current_user: User,
    user_id_str: Optional[str] = None
) -> User:
    """
    Ensures caller is authenticated and authorizes account access.
    Derives identity from verified current_user.
    If user_id_str is provided, only administrators may access another user's live settings.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access live trading services."
        )

    if user_id_str and str(user_id_str).strip():
        cleaned = str(user_id_str).strip()
        is_admin = getattr(current_user, "is_admin", False) or getattr(current_user, "role", "") == "admin"
        if str(current_user.id) != cleaned and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot view or modify another user's live trading credentials."
            )
        if str(current_user.id) != cleaned and is_admin:
            try:
                target_uid = uuid.UUID(cleaned)
                stmt = select(User).where(User.id == target_uid)
                target = (await db.execute(stmt)).scalar_one_or_none()
                if target:
                    return target
            except Exception:
                pass
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")

    return current_user


@router.post("/credentials")
async def save_credentials(
    req: SaveCredentialsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Saves or updates Polymarket CLOB L2 API credentials using authenticated encryption."""
    user = await _resolve_user(db, current_user, req.user_id)

    clean_addr = req.polymarket_wallet_address.strip().lower()
    if not re.fullmatch(r'0x[0-9a-f]{40}', clean_addr):
        raise HTTPException(
            status_code=400,
            detail="Invalid Polymarket Proxy Wallet address format (must be 0x-prefixed 42 chars)."
        )

    await db.execute(select(User).where(User.id == user.id).with_for_update())
    stmt = select(LiveWalletLink).where(LiveWalletLink.user_id == user.id)
    link = (await db.execute(stmt)).scalar_one_or_none()

    signing = await db.get(LiveSigningSession, user.id)
    if signing and (signing.wallet_address != clean_addr or link is None
            or (req.signer_address is not None and req.signer_address.strip().lower() != (link.signer_address or '').lower())
            or (req.signature_type is not None and req.signature_type != 3)):
        raise HTTPException(409, 'An existing signing session cannot be rebound to another wallet or owner.')

    account = (await db.execute(select(LiveExecutionAccount).where(
        LiveExecutionAccount.user_id == user.id).with_for_update())).scalar_one_or_none()
    if account is not None:
        # Credentials can rotate; the wallet owning journaled money cannot.
        if (account.wallet_address.lower() != clean_addr or link is None
                or (req.signer_address is not None and req.signer_address.strip().lower() != (link.signer_address or '').lower())
                or (req.signature_type is not None and req.signature_type != link.signature_type)):
            raise HTTPException(status_code=409,
                detail='An existing live journal cannot be rebound to another wallet or signing identity.')

    # Encrypt all secrets before persistence
    enc_key = encrypt_secret(req.clob_api_key.strip())
    enc_secret = encrypt_secret(req.clob_api_secret.strip())
    enc_passphrase = encrypt_secret(req.clob_api_passphrase.strip())

    if not link:
        link = LiveWalletLink(
            user_id=user.id,
            provider="polymarket_clob",
            provider_user_id=clean_addr,
            polymarket_wallet_address=clean_addr,
            clob_api_key_enc=enc_key,
            clob_api_secret_enc=enc_secret,
            clob_api_passphrase_enc=enc_passphrase,
            is_live_active=False,
            live_balance_usdc=0.0,
            created_at=datetime.utcnow()
        )
        db.add(link)
    else:
        link.polymarket_wallet_address = clean_addr
        link.clob_api_key_enc = enc_key
        link.clob_api_secret_enc = enc_secret
        link.clob_api_passphrase_enc = enc_passphrase
        link.last_used_at = datetime.utcnow()

    if req.signer_address is not None:
        signer = req.signer_address.strip().lower()
        if not re.fullmatch(r'0x[0-9a-f]{40}', signer):
            raise HTTPException(status_code=400, detail='Invalid signer address')
        link.signer_address = signer
    if req.signature_type is not None:
        link.signature_type = req.signature_type
    # Rotating credentials invalidates prior verification and order permission.
    link.last_verified_at = None
    if signing:
        signing.verified_at = None
    link.is_live_active = False
    user.live_trading_enabled = False
    await _disable_order_account(db, user.id)
    await db.commit()
    await db.refresh(link)

    decrypted_key = decrypt_secret(link.clob_api_key_enc)
    return {
        "success": True,
        "is_configured": True,
        "polymarket_wallet_address": link.polymarket_wallet_address,
        "clob_api_key_masked": _mask_key(decrypted_key),
        "is_live_active": bool(link.is_live_active),
        "live_balance_usdc": None,
        "last_verified_at": link.last_verified_at.isoformat() if link.last_verified_at else None
    }


@router.get("/credentials")
async def get_credentials(
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns status and masked credentials for L2 live trading."""
    user = await _resolve_user(db, current_user, user_id)

    stmt = select(LiveWalletLink).where(LiveWalletLink.user_id == user.id)
    link = (await db.execute(stmt)).scalar_one_or_none()

    if not link or not link.polymarket_wallet_address or not link.clob_api_key_enc:
        return {
            "is_configured": False,
            "polymarket_wallet_address": "",
            "clob_api_key_masked": "",
            "is_live_active": False,
            "live_balance_usdc": None,
            "last_verified_at": None
        }

    decrypted_key = decrypt_secret(link.clob_api_key_enc)
    return {
        "is_configured": True,
        "polymarket_wallet_address": link.polymarket_wallet_address,
        "signer_address": link.signer_address,
        "signature_type": link.signature_type,
        "clob_api_key_masked": _mask_key(decrypted_key),
        "is_live_active": False,
        "live_balance_usdc": float(link.live_balance_usdc) if link.last_verified_at and link.live_balance_usdc is not None else None,
        "last_verified_at": link.last_verified_at.isoformat() if link.last_verified_at else None
    }


@router.post("/test-connection")
async def test_connection(
    req: TestConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Authenticate L2 credentials and read collateral; never count positions as cash."""
    from app.services.clob_gateway import ClobCredentials, ClobGateway, ExchangeAuthenticationError, ExchangeUnavailable
    user = await _resolve_user(db, current_user, req.user_id)
    link = (await db.execute(select(LiveWalletLink).where(LiveWalletLink.user_id == user.id))).scalar_one_or_none()
    address = req.polymarket_wallet_address or (link.polymarket_wallet_address if link else None)
    signer = req.signer_address or (link.signer_address if link else None)
    signature_type = req.signature_type if req.signature_type is not None else (link.signature_type if link else None)
    if not address or not signer or signature_type is None:
        raise HTTPException(status_code=400, detail='Wallet address, signer address and wallet signature type are required')
    if not re.fullmatch(r'0x[0-9a-fA-F]{40}', address) or not re.fullmatch(r'0x[0-9a-fA-F]{40}', signer):
        raise HTTPException(status_code=400, detail='Invalid wallet or signer address')
    def credential(provided, field):
        return provided if provided is not None else (decrypt_secret(getattr(link, field)) if link else '')
    credentials = ClobCredentials(signer, credential(req.clob_api_key, 'clob_api_key_enc'),
        credential(req.clob_api_secret, 'clob_api_secret_enc'), credential(req.clob_api_passphrase, 'clob_api_passphrase_enc'))
    bound_wallet = signature_type == 0 and address.lower() == signer.lower()
    try:
        async with httpx.AsyncClient(base_url=settings.CLOB_API_URL, timeout=10.0, follow_redirects=False) as client:
            gateway = ClobGateway(credentials, client)
            evidence = await gateway.collateral_balance(signature_type)
            if signature_type == 3:
                identity = await gateway._get('/v1/user/session-signers')
                bound_wallet = (isinstance(identity, dict) and identity.get('wallet', '').lower() == address.lower()
                    and isinstance(identity.get('signers'), list))
    except (ValueError, ExchangeAuthenticationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ExchangeUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    # Authentication proves the signer credentials, not an arbitrary supplied
    # proxy/deposit wallet binding or order-signing authority.
    now = datetime.utcnow()
    if link and bound_wallet and address.lower() == link.polymarket_wallet_address.lower():
        saved_matches = (signer.lower() == (link.signer_address or '').lower()
            and signature_type == link.signature_type
            and credentials.api_key == decrypt_secret(link.clob_api_key_enc)
            and credentials.secret == decrypt_secret(link.clob_api_secret_enc)
            and credentials.passphrase == decrypt_secret(link.clob_api_passphrase_enc))
        if saved_matches:
            link.last_verified_at = now
            link.live_balance_usdc = float(evidence['balance'])
            await db.commit()
    return {'connected': True, 'credentials_verified': True, 'wallet_binding_verified': bound_wallet,
        'live_execution_ready': False, 'wallet_address': address.lower(),
        'signer_address': signer.lower(), 'balance_usdc': float(evidence['balance']) if bound_wallet else None,
        'collateral_currency': 'pUSD', 'balance_source': evidence['source'],
        'verified_at': now.isoformat(),
        'status_message': 'CLOB credentials authenticated. Order signing and reconciliation must pass before live activation.'}


@router.post("/toggle")
async def toggle_live_trading(
    req: ToggleLiveTradingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Enables or disables live copy-trading execution.
    Enforces server-side LIVE_EXECUTION_ENABLED capability flag.
    """
    user = await _resolve_user(db, current_user, req.user_id)

    if req.enabled:
        # Server-enforced live capability gate
        if not getattr(settings, "LIVE_EXECUTION_ENABLED", False):
            raise HTTPException(
                status_code=400,
                detail="Live exchange execution is currently disabled for security and financial audit. Paper trading remains active."
            )

        raise HTTPException(status_code=409,
            detail='Live activation requires the reviewed signing, order journal and reconciliation pipeline. Credential verification alone is insufficient.')


    stmt = select(LiveWalletLink).where(LiveWalletLink.user_id == user.id)
    link = (await db.execute(stmt)).scalar_one_or_none()
    if link:
        link.is_live_active = req.enabled
    user.live_trading_enabled = req.enabled
    await _disable_order_account(db, user.id)

    await db.commit()

    return {
        "success": True,
        "is_live_active": req.enabled,
        "status": "CLOB Live Trading Active" if req.enabled else "Live Trading Disabled"
    }


@router.get("/dashboard")
async def get_live_dashboard(
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Legacy account records are audit data, not verified exchange executions."""
    user = await _resolve_user(db, current_user, user_id)
    link = await db.get(LiveWalletLink, user.id)
    configured = bool(link and link.polymarket_wallet_address and link.clob_api_key_enc)
    rows = (await db.execute(select(ExecutionLog).where(ExecutionLog.is_sandbox.is_(False),
        ExecutionLog.user_id == user.id).order_by(ExecutionLog.executed_at.desc()).limit(100))).scalars().all()
    from app.services.execution_valuation import finite
    legacy = [{'id': str(r.id), 'timestamp': r.executed_at.isoformat() if r.executed_at else None,
        'walletAddress': r.source_wallet_address, 'marketQuestion': r.market_question,
        'marketConditionId': r.market_condition_id, 'side': r.side, 'outcome': r.resolution_outcome,
        'fillPrice': finite(r.user_fill_price), 'size': finite(r.notional_usd),
        'recordedStatus': r.status, 'recordedPnl': finite(r.realized_pnl_usd),
        'feeUsd': finite(r.fee_usd), 'evidence': 'legacy_unverified'} for r in rows]
    return {
        'is_configured': configured, 'is_live_active': False,
        'status_badge': 'Live execution preparation — not activated' if configured else 'Credentials Required',
        'polymarket_wallet_address': link.polymarket_wallet_address if link else '',
        'clob_api_key_masked': _mask_key(decrypt_secret(link.clob_api_key_enc)) if link else '',
        'usdc_balance': None, 'open_positions_value': None, 'portfolio_net_worth': None, 'live_pnl': None,
        'last_verified_at': link.last_verified_at.isoformat() if link and link.last_verified_at else None,
        'live_execution_ready': False, 'execution_evidence': 'legacy_unverified',
        'balance_source': 'unavailable; inspect authenticated execution-state',
        'execution_logs': [], 'active_positions': [], 'legacy_records': legacy,
    }
