import logging
from datetime import datetime
from app.database import SessionLocal
from app.models import SystemEvent

logger = logging.getLogger(__name__)

# In-memory ring buffer for recent events (survives even if DB write fails)
_recent_events: list[dict] = []
_MAX_MEMORY_EVENTS = 500


async def log_event(
    event_type: str,
    title: str,
    detail: str | None = None,
    severity: str = "info",
    related_address: str | None = None,
    related_market: str | None = None,
):
    """Log a system event to the database and in-memory buffer."""
    event_dict = {
        "event_type": event_type,
        "severity": severity,
        "title": title,
        "detail": detail,
        "related_address": related_address,
        "related_market": related_market,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Always store in memory ring buffer
    _recent_events.append(event_dict)
    if len(_recent_events) > _MAX_MEMORY_EVENTS:
        _recent_events.pop(0)

    # Persist to database (best-effort, never crash the caller)
    try:
        async with SessionLocal() as db:
            db.add(SystemEvent(
                event_type=event_type,
                severity=severity,
                title=title,
                detail=detail,
                related_address=related_address,
                related_market=related_market,
            ))
            await db.commit()
    except Exception as e:
        logger.debug(f"Event DB write skipped: {e}")


def get_recent_events_from_memory(limit: int = 100) -> list[dict]:
    """Return recent events from in-memory buffer (newest first)."""
    return list(reversed(_recent_events[-limit:]))
