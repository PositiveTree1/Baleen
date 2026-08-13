from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel
import uuid
# We'd normally use passlib, but keeping it simple/mocked without extra dependencies for now
import hashlib 

from app.database import get_db
from app.models import User

router = APIRouter(tags=["users"])

class SignupRequest(BaseModel):
    email: str
    password: str
    sandbox_starting_balance_usd: float = 10000.0

class LoginRequest(BaseModel):
    email: str
    password: str

class UpdateSettingsRequest(BaseModel):
    user_id: str
    risk_profile: Optional[str] = None
    daily_digest_opt_in: Optional[bool] = None

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
    
    return {"id": str(user.id), "email": user.email}

@router.get("/api/user/settings")
async def get_settings(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return user

@router.patch("/api/user/settings")
async def update_settings(req: UpdateSettingsRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.id == req.user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if req.risk_profile is not None:
        user.risk_profile = req.risk_profile
    if req.daily_digest_opt_in is not None:
        user.daily_digest_opt_in = req.daily_digest_opt_in
        
    await db.commit()
    return user

@router.post("/api/user/signup")
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
    
    return new_user
