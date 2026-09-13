from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
from app.services.copilot import execute_copilot_chat
from app.auth import get_current_user_optional, copilot_rate_limiter
from app.models import User
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/copilot", tags=["copilot"])

ALLOWED_ROLES = {"user", "assistant"}

class ChatMessage(BaseModel):
    role: str
    content: str = Field(..., max_length=4000)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        r = v.lower().strip()
        if r not in ALLOWED_ROLES:
            raise ValueError(f"Role must be one of {ALLOWED_ROLES}; system and tool roles are disallowed for client requests.")
        return r

class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1, max_length=20)

@router.post("/chat")
async def chat_with_copilot(
    req: ChatRequest,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Interacts with the Baleen AI Copilot via Groq function calling.
    Scoped to the authenticated user's portfolio, strictly enforces payload bounds,
    and throttles via sliding-window rate limiting.
    """
    # Rate limit by user ID if authenticated, otherwise client IP
    client_ip = request.client.host if request.client else "127.0.0.1"
    limiter_key = f"user:{current_user.id}" if current_user else f"ip:{client_ip}"
    user_id = str(current_user.id) if current_user else None
    starting_bal = float(getattr(current_user, "sandbox_starting_balance_usd", 10000.0) or 10000.0)
    await copilot_rate_limiter.check(db, limiter_key, "copilot chat")

    # Aggregate payload length bound
    total_chars = sum(len(m.content) for m in req.messages)
    if total_chars > 16_000:
        raise HTTPException(
            status_code=400,
            detail="Combined message history exceeds maximum allowed payload size (16,000 characters)."
        )

    messages_payload = [{"role": m.role, "content": m.content} for m in req.messages]
    result = await execute_copilot_chat(
        messages_payload,
        user_id=user_id,
        starting_balance=starting_bal
    )
    return result
