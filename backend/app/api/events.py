from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.models import SystemEvent
from app.services.event_logger import get_recent_events_from_memory

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("")
async def get_events(
    limit: int = Query(100, le=500),
    event_type: Optional[str] = None,
    since: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Returns recent system events. Falls back to in-memory buffer if DB is empty."""
    try:
        stmt = select(SystemEvent).order_by(SystemEvent.created_at.desc())

        if event_type:
            stmt = stmt.where(SystemEvent.event_type == event_type)

        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                stmt = stmt.where(SystemEvent.created_at >= since_dt)
            except Exception:
                pass

        stmt = stmt.limit(limit)
        rows = (await db.execute(stmt)).scalars().all()

        if rows:
            return [
                {
                    "id": str(r.id),
                    "eventType": r.event_type,
                    "severity": r.severity,
                    "title": r.title,
                    "detail": r.detail,
                    "relatedAddress": r.related_address,
                    "relatedMarket": r.related_market,
                    "createdAt": (r.created_at.isoformat() + "Z") if r.created_at else None,
                }
                for r in rows
            ]
    except Exception:
        pass

    # Fallback: return from in-memory buffer
    memory_events = get_recent_events_from_memory(limit)
    return [
        {
            "id": f"mem-{i}",
            "eventType": e.get("event_type", ""),
            "severity": e.get("severity", "info"),
            "title": e.get("title", ""),
            "detail": e.get("detail"),
            "relatedAddress": e.get("related_address"),
            "relatedMarket": e.get("related_market"),
            "createdAt": e.get("created_at"),
        }
        for i, e in enumerate(memory_events)
    ]
