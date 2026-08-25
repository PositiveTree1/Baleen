from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.copilot import execute_copilot_chat

router = APIRouter(prefix="/api/copilot", tags=["copilot"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

@router.post("/chat")
async def chat_with_copilot(req: ChatRequest):
    """
    Interacts with the Baleen AI Copilot via Groq function calling.
    """
    if not req.messages:
        raise HTTPException(status_code=400, detail="Messages array cannot be empty")
        
    messages_payload = [{"role": m.role, "content": m.content} for m in req.messages]
    result = await execute_copilot_chat(messages_payload)
    return result
