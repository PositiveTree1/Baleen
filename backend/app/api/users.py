from fastapi import APIRouter, Depends, HTTPException, Body, Request, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from typing import Optional
from pydantic import BaseModel, Field, model_validator
import uuid
from datetime import datetime

from app.database import get_db
from app.models import User, ExecutionLog, PortfolioSnapshot
from app.auth import (
    validate_email,
    validate_password_strength,
    hash_password,
    verify_password,
    needs_rehash,
    create_access_token,
    get_current_user,
    get_current_user_optional,
    revoke_token,
    require_admin,
    auth_rate_limiter,
    guest_rate_limiter,
)

router = APIRouter(tags=["users"])


class SignupRequest(BaseModel):
    email: str = Field(max_length=512)
    password: str = Field(max_length=256)
    sandbox_starting_balance_usd: float = Field(default=10000.0, alias='startingBalance', allow_inf_nan=False)

    class Config:
        populate_by_name = True


class LoginRequest(BaseModel):
    email: str = Field(max_length=512)
    password: str = Field(max_length=256)


class UpdateSettingsRequest(BaseModel):
    risk_profile: Optional[str] = None
    daily_digest_opt_in: Optional[bool] = None

    class Config:
        populate_by_name = True

    @model_validator(mode='before')
    @classmethod
    def convert_camel_case(cls, data):
        if isinstance(data, dict):
            converted = {}
            for key, value in data.items():
                snake_key = ''.join(['_' + c.lower() if c.isupper() else c for c in key]).lstrip('_')
                converted[snake_key] = value
            return converted
        return data


def user_to_response(user: User) -> dict:
    start_bal = float(user.sandbox_starting_balance_usd) if user.sandbox_starting_balance_usd is not None else 10000.0
    curr_bal = float(user.sandbox_balance_usd) if user.sandbox_balance_usd is not None else 10000.0
    return {
        "id": str(user.id),
        "email": user.email,
        "startingBalance": start_bal,
        "currentBalance": curr_bal,
        "riskProfile": user.risk_profile or "Balanced",
        "dailyDigestOptIn": user.daily_digest_opt_in if user.daily_digest_opt_in is not None else True,
        "isAdmin": bool(getattr(user, "is_admin", False)),
        "role": getattr(user, "role", "user") or "user",
    }


def _get_request_ip(request: Request) -> str:
    # Uvicorn resolves forwarded addresses only from configured trusted proxies.
    # Raw client-supplied headers must not select a new rate-limit bucket.
    return request.client.host if request.client else "127.0.0.1"


@router.post("/api/auth/signup")
async def signup(req: SignupRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = _get_request_ip(request)
    await auth_rate_limiter.check(db, client_ip, "signup")

    clean_email = validate_email(req.email)
    validate_password_strength(req.password)

    starting_bal = max(100.0, min(10_000_000.0, float(req.sandbox_starting_balance_usd if req.sandbox_starting_balance_usd is not None else 10000.0)))

    stmt = select(User).where(User.email == clean_email)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    new_user = User(
        email=clean_email,
        password_hash=hash_password(req.password),
        sandbox_starting_balance_usd=starting_bal,
        sandbox_balance_usd=starting_bal,
        sandbox_high_water_mark_usd=starting_bal,
        is_admin=False,
        role="user"
    )

    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    token = create_access_token(str(new_user.id), role=new_user.role)
    resp = user_to_response(new_user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "id": str(new_user.id),
        "email": new_user.email,
        **resp
    }


@router.post("/api/auth/login")
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = _get_request_ip(request)
    clean_email = validate_email(req.email)
    await auth_rate_limiter.check(db, f"{client_ip}:{clean_email}", "login")

    stmt = select(User).where(User.email == clean_email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # Upgrade legacy SHA-256 hash to PBKDF2 on successful login
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(req.password)
        await db.commit()
        await db.refresh(user)

    token = create_access_token(str(user.id), role=getattr(user, "role", "user") or "user")
    resp = user_to_response(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "id": str(user.id),
        "email": user.email,
        **resp
    }


@router.post("/api/auth/logout")
async def logout(
    authorization: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Revokes the current JWT bearer token so it can no longer authenticate requests.
    """
    if authorization:
        await revoke_token(authorization, db)
    return {"status": "ok", "message": "Successfully logged out."}


@router.post("/api/auth/guest")
async def guest_login(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Spawns an isolated, unique guest session with independent paper balance.
    Demo sessions cannot overwrite or pollute each other's financial state.
    """
    client_ip = _get_request_ip(request)
    await guest_rate_limiter.check(db, client_ip, "guest session creation")

    guest_uid = uuid.uuid4()
    guest_email = f"guest_{guest_uid.hex[:8]}@baleen.local"
    guest_password = f"guest_key_{uuid.uuid4().hex[:16]}"

    guest_user = User(
        id=guest_uid,
        email=guest_email,
        password_hash=hash_password(guest_password),
        sandbox_starting_balance_usd=10000.0,
        sandbox_balance_usd=10000.0,
        sandbox_high_water_mark_usd=10000.0,
        risk_profile="balanced",
        is_admin=False,
        role="guest"
    )
    db.add(guest_user)
    # No ORM relationship links these objects; enforce FK insert order while
    # keeping the user and genesis snapshot in the same transaction.
    await db.flush()

    # Initial genesis snapshot for this guest user
    db.add(PortfolioSnapshot(
        user_id=guest_user.id,
        timestamp=datetime.utcnow(),
        balance=10000.0,
        total_pnl=0.0,
        active_trades_count=0
    ))

    await db.commit()
    await db.refresh(guest_user)

    token = create_access_token(str(guest_user.id), role="guest")
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": guest_email,
        "password": guest_password,
        **user_to_response(guest_user)
    }


@router.get("/api/me")
@router.get("/api/users/me")
async def get_my_settings(current_user: User = Depends(get_current_user)):
    """Returns the authenticated caller's profile and settings."""
    return user_to_response(current_user)


@router.get("/api/users/{user_id}")
async def get_settings(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetches user profile. Rejects mismatch unless caller is an administrator."""
    try:
        target_uid = uuid.UUID(str(user_id).strip())
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if str(current_user.id) != str(target_uid) and not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot view another user's profile."
        )

    stmt = select(User).where(User.id == target_uid)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user_to_response(user)


@router.patch("/api/users/{user_id}")
async def update_settings(
    user_id: str,
    req: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates user profile. Rejects mismatch unless caller is an administrator."""
    try:
        target_uid = uuid.UUID(str(user_id).strip())
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if str(current_user.id) != str(target_uid) and not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot modify another user's profile."
        )

    stmt = select(User).where(User.id == target_uid)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if req.risk_profile is not None:
        valid_profiles = {"conservative", "balanced", "aggressive"}
        if req.risk_profile.lower() not in valid_profiles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk profile. Must be one of {valid_profiles}."
            )
        user.risk_profile = req.risk_profile.capitalize()

    if req.daily_digest_opt_in is not None:
        user.daily_digest_opt_in = bool(req.daily_digest_opt_in)

    await db.commit()
    await db.refresh(user)
    return user_to_response(user)


class ResetSandboxRequest(BaseModel):
    new_starting_balance: float = Field(default=10000.0, alias='newBalance')

    class Config:
        populate_by_name = True


@router.get("/api/users/{user_id}/paper-runs")
async def list_paper_runs(user_id: str, current_user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    from app.models import SandboxRun
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.id != uid and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    rows = (await db.execute(select(SandboxRun).where(SandboxRun.user_id == uid)
                            .order_by(SandboxRun.started_at.desc()))).scalars().all()
    return [{"id": str(r.id), "status": r.status, "startedAt": r.started_at,
             "endedAt": r.ended_at, "startingBalance": r.initial_balance_usd}
            for r in rows]


@router.get("/api/users/{user_id}/paper-runs/{run_id}/trades")
async def paper_run_trades(user_id: str, run_id: str,
                           current_user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    from app.models import SandboxRun
    try:
        uid, rid = uuid.UUID(user_id), uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Paper run not found")
    if current_user.id != uid and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    run = await db.get(SandboxRun, rid)
    if run is None or run.user_id != uid:
        raise HTTPException(status_code=404, detail="Paper run not found")
    rows = (await db.execute(select(ExecutionLog).execution_options(include_archived_runs=True)
        .where(ExecutionLog.user_id == uid, ExecutionLog.run_id == rid,
               ExecutionLog.is_sandbox.is_(True)).order_by(ExecutionLog.executed_at, ExecutionLog.id))).scalars().all()
    return [{"id": str(r.id), "runId": str(r.run_id), "side": r.side, "status": r.status,
             "tokenId": r.token_id, "sourceWallet": r.source_wallet_address,
             "executedAt": r.executed_at, "fillPrice": r.user_fill_price,
             "notionalUsd": r.notional_usd, "feeUsd": r.fee_usd,
             "realizedPnlUsd": r.realized_pnl_usd} for r in rows]


@router.post("/api/users/{user_id}/reset-sandbox")
async def reset_user_sandbox(
    user_id: str,
    req: ResetSandboxRequest = Body(default=ResetSandboxRequest()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resets paper trading state STRICTLY scoped to the authenticated user.
    Never deletes live records (is_sandbox=False) and never mutates another user's data.
    """
    try:
        target_uid = uuid.UUID(str(user_id).strip())
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if str(current_user.id) != str(target_uid) and not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot reset another user's sandbox."
        )

    stmt = select(User).where(User.id == target_uid)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    from app.services.paper_runs import archive_and_start
    try:
        await archive_and_start(db, user, req.new_starting_balance)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await db.commit()
    await db.refresh(user)
    return user_to_response(user)


@router.post("/api/users/reset-sandbox")
async def reset_global_sandbox(
    req: ResetSandboxRequest = Body(default=ResetSandboxRequest()),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Global sandbox reset - strictly restricted to administrators.
    """
    raise HTTPException(status_code=409,
        detail="Global reset is disabled. Archive and restart a specific account's paper run instead.")
