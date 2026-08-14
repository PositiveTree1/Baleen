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
