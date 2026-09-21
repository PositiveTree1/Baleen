"""Cross-replica listener health, distinct from API/database readiness."""
import json
import time
from app.models import KeyValue


async def listener_health(db):
    row = await db.get(KeyValue, 'listener_heartbeat')
    try: data = json.loads(row.value) if row else {}
    except (ValueError, TypeError): data = {}
    now = time.time()
    if not data: status = 'UNKNOWN'
    elif now-data.get('received_at', 0) >= 60: status = 'OFFLINE'
    elif now-data.get('last_progress_at', data.get('received_at', 0)) >= 120: status = 'STALLED'
    else: status = 'ONLINE'
    return {'status': status, **data}
