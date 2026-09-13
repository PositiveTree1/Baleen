"""Polymarket profile chart observations, never reconstructed from cash flows."""
import math
from datetime import datetime, timezone

SOURCE = "polymarket-user-pnl-v1"


def normalize_pnl_series(rows):
    if not isinstance(rows, list):
        raise ValueError("PnL provider did not return a series")
    points = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Malformed PnL observation")
        t, p = row.get("t"), row.get("p")
        if (isinstance(t, bool) or isinstance(p, bool) or
                not isinstance(t, (int, float)) or not isinstance(p, (int, float)) or
                not math.isfinite(t) or not math.isfinite(p) or t <= 0):
            raise ValueError("Invalid PnL timestamp/value")
        if t in points and points[t] != p:
            raise ValueError("Conflicting PnL observations")
        points[t] = p
    result = []
    previous = None
    observed = datetime.now(timezone.utc).isoformat()
    for t, p in sorted(points.items()):
        # The first observation is a baseline, not a day's earnings.
        delta = p - previous if previous is not None else None
        result.append({"date": datetime.fromtimestamp(t, timezone.utc).isoformat(),
                       "timestamp": t, "cumulative_pnl": p,
                       "daily_pnl": delta, "net_pnl": delta,
                       "source": SOURCE, "observed_at": observed})
        previous = p
    return result


def verified_history(points, max_age_seconds=86400):
    if not isinstance(points, list) or not points:
        return False
    try:
        now = datetime.now(timezone.utc)
        return all(p.get("source") == SOURCE and
                   0 <= (now - datetime.fromisoformat(p["observed_at"])).total_seconds() <= max_age_seconds
                   for p in points)
    except (KeyError, TypeError, ValueError):
        return False
