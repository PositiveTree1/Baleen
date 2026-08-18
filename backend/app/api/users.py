from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel, Field, model_validator
import uuid
# We'd normally use passlib, but keeping it simple/mocked without extra dependencies for now
import hashlib 

from app.database import get_db
from app.models import User

router = APIRouter(tags=["users"])

class SignupRequest(BaseModel):
    email: str
    password: str
    sandbox_starting_balance_usd: float = Field(default=10000.0, alias='startingBalance')

    class Config:
        populate_by_name = True

class LoginRequest(BaseModel):
    email: str
    password: str

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
                # Convert camelCase to snake_case
                snake_key = ''.join(['_' + c.lower() if c.isupper() else c for c in key]).lstrip('_')
                converted[snake_key] = value
            return converted
        return data

def user_to_response(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "startingBalance": user.sandbox_starting_balance_usd,
        "currentBalance": user.sandbox_balance_usd,
        "riskProfile": user.risk_profile or "Balanced",
        "dailyDigestOptIn": user.daily_digest_opt_in if user.daily_digest_opt_in is not None else True,
    }

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed

@router.post("/api/auth/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == req.email)
    user = (await db.execute(stmt)).scalar_one_or_none()
    
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"id": str(user.id), "email": user.email, **user_to_response(user)}

@router.get("/api/users/{user_id}")
async def get_settings(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return user_to_response(user)

@router.patch("/api/users/{user_id}")
async def update_settings(user_id: str, req: UpdateSettingsRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if req.risk_profile is not None:
        user.risk_profile = req.risk_profile
    if req.daily_digest_opt_in is not None:
        user.daily_digest_opt_in = req.daily_digest_opt_in
        
    await db.commit()
    return user_to_response(user)

@router.post("/api/auth/signup")
async def signup(req: SignupRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == req.email)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    new_user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        sandbox_starting_balance_usd=req.sandbox_starting_balance_usd,
        sandbox_balance_usd=req.sandbox_starting_balance_usd,
        sandbox_high_water_mark_usd=req.sandbox_starting_balance_usd
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return user_to_response(new_user)

SHARED_GUEST_EMAIL = "guest@baleen.local"
SHARED_GUEST_PASSWORD = "baleen_shared_guest_sandbox_password"

@router.post("/api/auth/guest")
async def guest_login(db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == SHARED_GUEST_EMAIL)
    guest = (await db.execute(stmt)).scalar_one_or_none()
    
    if not guest:
        guest = User(
            email=SHARED_GUEST_EMAIL,
            password_hash=hash_password(SHARED_GUEST_PASSWORD),
            sandbox_starting_balance_usd=10000.0,
            sandbox_balance_usd=10000.0,
            sandbox_high_water_mark_usd=10000.0,
        )
        db.add(guest)
        await db.commit()
        await db.refresh(guest)
        
    return {"email": SHARED_GUEST_EMAIL, "password": SHARED_GUEST_PASSWORD, **user_to_response(guest)}


class ResetSandboxRequest(BaseModel):
    new_starting_balance: float = Field(default=10000.0, alias='newBalance')

    class Config:
        populate_by_name = True


@router.post("/api/users/{user_id}/reset-sandbox")
async def reset_user_sandbox(
    user_id: str,
    req: ResetSandboxRequest = Body(default=ResetSandboxRequest()),
    db: AsyncSession = Depends(get_db)
):
    from app.models import ExecutionLog, PortfolioSnapshot
    from sqlalchemy import delete
    from datetime import datetime
    import uuid, time

    try:
        u_uuid = uuid.UUID(user_id)
        stmt = select(User).where(User.id == u_uuid)
    except Exception:
        stmt = select(User).where(User.id == user_id)

    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_bal = float(req.new_starting_balance or 10000.0)
    user.sandbox_starting_balance_usd = new_bal
    user.sandbox_balance_usd = new_bal
    user.sandbox_high_water_mark_usd = new_bal

    # Clear execution logs and snapshots for this user
    await db.execute(delete(ExecutionLog).where(ExecutionLog.user_id == user.id))
    await db.execute(delete(PortfolioSnapshot).where(PortfolioSnapshot.user_id == user.id))

    # Also clear system global logs if demo/guest
    if user.email == SHARED_GUEST_EMAIL:
        await db.execute(delete(ExecutionLog).where(ExecutionLog.user_id.is_(None)))
        await db.execute(delete(PortfolioSnapshot).where(PortfolioSnapshot.user_id.is_(None)))

    # Initial starting snapshot
    now_dt = datetime.utcnow()
    db.add(PortfolioSnapshot(
        user_id=user.id,
        timestamp=now_dt,
        balance=new_bal,
        total_pnl=0.0,
        active_trades_count=0
    ))

    # Reset poller started_at to now
    try:
        from app.services.live_poller import live_poller_service
        live_poller_service.started_at = time.time()
        live_poller_service.seen_trade_keys.clear()
    except Exception:
        pass

    # Clear price caches
    try:
        from app.services.mark_to_market import _live_price_cache
        _live_price_cache.clear()
    except Exception:
        pass

    await db.commit()
    await db.refresh(user)
    return user_to_response(user)


@router.post("/api/users/reset-sandbox")
async def reset_global_sandbox(
    req: ResetSandboxRequest = Body(default=ResetSandboxRequest()),
    db: AsyncSession = Depends(get_db)
):
    from app.models import ExecutionLog, PortfolioSnapshot
    from sqlalchemy import delete
    from datetime import datetime
    import time

    new_bal = float(req.new_starting_balance or 10000.0)

    # 1. Reset guest user
    stmt = select(User).where(User.email == SHARED_GUEST_EMAIL)
    guest = (await db.execute(stmt)).scalar_one_or_none()
    if guest:
        guest.sandbox_starting_balance_usd = new_bal
        guest.sandbox_balance_usd = new_bal
        guest.sandbox_high_water_mark_usd = new_bal

    # 2. Reset ALL execution logs & snapshots
    await db.execute(delete(ExecutionLog))
    await db.execute(delete(PortfolioSnapshot))

    # Initial starting snapshot
    now_dt = datetime.utcnow()
    db.add(PortfolioSnapshot(
        user_id=None,
        timestamp=now_dt,
        balance=new_bal,
        total_pnl=0.0,
        active_trades_count=0
    ))

    # Reset poller started_at to now
    try:
        from app.services.live_poller import live_poller_service
        live_poller_service.started_at = time.time()
        live_poller_service.seen_trade_keys.clear()
    except Exception:
        pass

    # Clear price caches
    try:
        from app.services.mark_to_market import _live_price_cache
        _live_price_cache.clear()
    except Exception:
        pass

    await db.commit()
    return {
        "success": True,
        "message": "Sandbox completely reset",
        "startingBalance": new_bal,
        "currentBalance": new_bal
    }


