"""Provider evidence, separate from legacy heuristic scores and execution approval."""
import asyncio
import math
from collections import Counter
from app.discovery.accounting_snapshot import accounting_snapshot
from datetime import datetime, timezone

POLICY_VERSION = "wallet-evidence-2026-09-17"
DAY = 86400


def finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError):
        return None


async def cursor_history(client, path, address, params, max_pages=20):
    """Preserve identical fills: diagnostic keys are not unique execution IDs."""
    rows, cursors = [], set()
    query = {**params, "user": address, "limit": 1000}
    reason = "page_budget_exhausted"
    pages = 0
    for _ in range(max_pages):
        result = await client._fetch_with_retry(f"{client.data_api_url}{path}", query.copy())
        pages += 1
        if not isinstance(result, dict) or not isinstance(result.get("data"), list):
            reason = "unavailable_or_invalid_response"
            break
        batch, pagination = result["data"], result.get("pagination")
        if not isinstance(pagination, dict) or type(pagination.get("has_more")) is not bool:
            reason = "invalid_pagination"
            break
        if any(not isinstance(r, dict) or str(r.get("proxy_wallet", "")).lower() != address for r in batch):
            reason = "wallet_identity_mismatch"
            break
        if path in ("/v2/trades", "/v2/activity") and any(
            finite(r.get("timestamp")) is None or not params["start"] <= float(r["timestamp"]) <= params["end"] for r in batch
        ):
            reason = "outside_requested_window"
            break
        rows.extend(batch)
        if pagination["has_more"] is False:
            return {"rows": rows, "complete": True, "pages": pages, "reason": "cursor_exhausted", "scope": params}
        cursor = pagination.get("next_cursor")
        if not isinstance(cursor, str) or not cursor or cursor in cursors or not batch:
            reason = "invalid_or_repeated_cursor"
            break
        cursors.add(cursor)
        query["cursor"] = cursor
    return {"rows": rows, "complete": False, "pages": pages, "reason": reason, "scope": params}


async def pnl_series(client, address):
    response = await client._fetch_with_retry(f"{client.data_api_url}/v2/user-pnl", {
        "user": address, "interval": "all", "fidelity": "1d",
    })
    data = response.get("data") if isinstance(response, dict) else None
    if not isinstance(data, dict) or str(data.get("proxy_wallet", "")).lower() != address:
        return None
    points = data.get("points")
    if not isinstance(points, list) or any(not isinstance(p, dict) or finite(p.get("timestamp")) is None or finite(p.get("economic_pnl")) is None for p in points):
        return None
    return {**data, "points": sorted(points, key=lambda p: p["timestamp"])}


def chart_history(series):
    """Daily changes are marked P&L changes, not realized winning/losing trades."""
    if not series:
        return []
    by_day = {}
    for point in series["points"]:
        by_day[datetime.fromtimestamp(point["timestamp"], timezone.utc).strftime("%Y-%m-%d")] = point
    history, previous = [], None
    for day, point in sorted(by_day.items()):
        cumulative = float(point["economic_pnl"])
        delta = None if previous is None else cumulative - previous
        history.append({"date": day, "cumulative_pnl": cumulative, "daily_pnl": delta,
                        "net_pnl": delta, "won_usd": None if delta is None else max(0, delta),
                        "lost_usd": None if delta is None else min(0, delta), "trades_count": None,
                        "trade_pnl": finite(point.get("trade_pnl")), "wallet_income": finite(point.get("wallet_income")),
                        "source_block": point.get("source_block"), "source_timestamp": point["timestamp"],
                        "metric": "economic_pnl", "source": "polymarket_v2"})
        previous = cumulative
    return history


def assess(history, series, profile, end):
    reasons = []
    counts = [0] * 30
    for row in history["rows"]:
        index = int((row["timestamp"] - (end - 30 * DAY)) // DAY)
        if 0 <= index < 30:
            counts[index] += 1
    week, month = sum(counts[-7:]) / 7, sum(counts) / 30
    metrics = {"fills_7d": sum(counts[-7:]), "fills_30d": sum(counts), "fills_per_day_7d": week,
               "fills_per_day_30d": month, "max_daily_fills": max(counts), "active_days_7d": sum(c > 0 for c in counts[-7:]),
               "daily_activity": [{"date": datetime.fromtimestamp(end - (30-i)*DAY, timezone.utc).strftime("%Y-%m-%d"), "fills": c} for i, c in enumerate(counts)],
               "distinct_markets_lifetime": profile.get("trades") if profile else None,
               "views": profile.get("views") if profile else None}
    points = [p for p in series["points"] if p["timestamp"] <= end] if series else []
    latest = points[-1] if points else {}
    pnl = finite(latest.get("economic_pnl"))
    metrics["economic_pnl"] = pnl
    metrics["trade_pnl"] = finite(latest.get("trade_pnl"))
    metrics["wallet_income"] = finite(latest.get("wallet_income"))
    for days in (7, 30):
        target = end - days * DAY
        baseline = next((p for p in reversed(points) if p["timestamp"] <= target), None)
        # Do not use a baseline from an arbitrary distant date.
        start_value = finite(baseline.get("trade_pnl")) if baseline and target - baseline["timestamp"] <= 2*DAY else None
        metrics[f"trade_pnl_{days}d"] = metrics["trade_pnl"] - start_value if start_value is not None and metrics["trade_pnl"] is not None else None
    if not history["complete"]:
        reasons.append("INCOMPLETE_TRADE_WINDOW")
    if pnl is None or not points or end - latest["timestamp"] > 2*DAY or latest["timestamp"] > end + DAY:
        reasons.append("MISSING_OR_STALE_PNL")
    if reasons:
        classification = "needs_data"
    elif pnl < 50000:
        classification, reasons = "excluded", ["PNL_BELOW_50K"]
    elif max(week, month) > 30 or max(counts) > 30:
        classification, reasons = "excluded", ["FILL_RATE_ABOVE_30_OR_DAILY_BURST"]
    elif min(week, month) < 2 or metrics["active_days_7d"] < 5:
        classification, reasons = "watchlist", ["LOW_OR_INTERMITTENT_ACTIVITY"]
    elif any(metrics[f"trade_pnl_{d}d"] is None for d in (7, 30)):
        classification, reasons = "needs_data", ["MISSING_RECENT_TRADE_PNL"]
    elif any(metrics[f"trade_pnl_{d}d"] <= 0 for d in (7, 30)):
        classification, reasons = "excluded", ["NON_POSITIVE_RECENT_TRADE_PNL"]
    else:
        classification, reasons = "research_candidate", ["ACCOUNT_REPLAY_AND_FORWARD_VALIDATION_REQUIRED"]
    return {"policy_version": POLICY_VERSION, "classification": classification, "reasons": reasons,
            "execution_approved": False, "metrics": metrics, "window_start": end-30*DAY, "window_end_exclusive": end,
            "trade_coverage": {k: v for k, v in history.items() if k != "rows"},
            "pnl_source": "polymarket_v2", "source_fidelity": series.get("source_fidelity") if series else None,
            "pnl_source_timestamp": latest.get("timestamp"), "pnl_source_block": latest.get("source_block"),
            "limitations": ["Raw fills are a conservative activity screen, not proven independent decisions.",
                            "Provider P&L is not an independently reconstructed account ledger.",
                            "P&L curves do not establish equity drawdown or strategy capital."]}


async def collect_evidence(client, address, now=None):
    address = address.lower().strip()
    now = now or int(datetime.now(timezone.utc).timestamp())
    end = now // DAY * DAY  # thirty full UTC days; exclude incomplete today
    window = {"start": end-30*DAY, "end": end-1}
    trades, series, profile, activity, positions, closed, snapshot = await asyncio.gather(
        cursor_history(client, "/v2/trades", address, {"start": end-30*DAY, "end": end-1, "taker_only": "false", "filter_amount": 0}),
        pnl_series(client, address), client.fetch_wallet_user_stats(address),
        cursor_history(client, "/v2/activity", address, window),
        cursor_history(client, "/v2/positions", address, {"status": "OPEN", "filter_amount": 0, "include_archived": "true"}),
        cursor_history(client, "/v2/positions", address, {"status": "CLOSED", "filter_amount": 0}),
        accounting_snapshot(client, address),
    )
    report = assess(trades, series, profile, end)
    report["accounting_snapshot"] = snapshot
    report["additional_coverage"] = {name: {k: v for k, v in result.items() if k != "rows"}
                                     for name, result in (("activity", activity), ("open_positions", positions), ("closed_positions", closed))}
    # Compare multisets, not sets: separate fills can have identical visible keys.
    def fill_key(row):
        return tuple(str(row.get(k)) for k in ("transaction_hash", "timestamp", "token_id", "side", "size", "price"))
    matched = (Counter(map(fill_key, trades["rows"])) == Counter(fill_key(r) for r in activity["rows"] if r.get("type") == "TRADE")) if trades["complete"] and activity["complete"] else None
    report["trade_activity_reconciled"] = matched
    def known_sum(result, field):
        values = [finite(r.get(field)) for r in result["rows"]]
        return sum(values) if result["complete"] and all(v is not None for v in values) else None
    report["metrics"].update({
        "marked_open_positions_usd": known_sum(positions, "current_value"),
        "open_positions_unrealized_pnl": known_sum(positions, "unrealized_pnl"),
        "closed_position_rows": len(closed["rows"]) if closed["complete"] else None,
        "activity_types_30d": dict(Counter(r.get("type", "UNKNOWN") for r in activity["rows"])) if activity["complete"] else None,
    })
    if not all(r["complete"] for r in (activity, positions, closed)) or matched is not True:
        report["classification"] = "needs_data"
        report["reasons"].append("INCOMPLETE_OR_UNRECONCILED_SUPPORTING_EVIDENCE")
    return {**report, "observed_at": now, "daily_pnl_history": chart_history(series)}
