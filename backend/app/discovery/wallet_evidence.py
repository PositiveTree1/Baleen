"""Provider evidence, separate from legacy heuristic scores and execution approval."""
import asyncio
import math
from collections import Counter
from app.discovery.accounting_snapshot import accounting_snapshot
from datetime import datetime, timezone

# Changing this version deliberately requests a re-evaluation of evidence
# collected under an older screen.  Eligibility must never silently retain a
# decision made before curve and realized-position checks existed.
POLICY_VERSION = "wallet-evidence-2026-09-23"
DAY = 86400


def finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError):
        return None


async def cursor_history(client, path, address, params, max_pages=20, max_total_pages=None,
                         min_window_seconds=DAY):
    """Read a complete bounded history window without mistaking a page cap for a result cap.

    A single busy 30-day query may consume the per-window page budget.  In that
    case trades and activity are retried over non-overlapping time slices.  This
    makes the activity screen measure the wallet's actual recent rate instead
    of silently treating a local 20,000-row safety budget as a provider limit.
    The total request budget remains bounded; an unresolved window is still
    explicitly incomplete and therefore cannot be promoted.
    """
    max_total_pages = max_total_pages if max_total_pages is not None else max_pages * 4
    budget = {"remaining": max_total_pages}

    async def walk_window(scope):
        rows, cursors = [], set()
        query = {**scope, "user": address, "limit": 1000}
        reason = "page_budget_exhausted"
        pages = 0
        for _ in range(max_pages):
            if budget["remaining"] <= 0:
                reason = "total_page_budget_exhausted"
                break
            result = await client._fetch_with_retry(f"{client.data_api_url}{path}", query.copy())
            budget["remaining"] -= 1
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
                finite(r.get("timestamp")) is None or not scope["start"] <= float(r["timestamp"]) <= scope["end"] for r in batch
            ):
                reason = "outside_requested_window"
                break
            rows.extend(batch)
            if pagination["has_more"] is False:
                return {"rows": rows, "complete": True, "pages": pages, "reason": "cursor_exhausted", "scope": scope}
            cursor = pagination.get("next_cursor")
            if not isinstance(cursor, str) or not cursor or cursor in cursors or not batch:
                reason = "invalid_or_repeated_cursor"
                break
            cursors.add(cursor)
            query["cursor"] = cursor
        return {"rows": rows, "complete": False, "pages": pages, "reason": reason, "scope": scope}

    can_split = path in ("/v2/trades", "/v2/activity") and "start" in params and "end" in params

    async def collect(scope):
        result = await walk_window(scope)
        width = int(scope["end"]) - int(scope["start"]) + 1 if can_split else 0
        if (result["reason"] != "page_budget_exhausted" or not can_split or
                width <= min_window_seconds or budget["remaining"] <= 0):
            return result
        midpoint = int(scope["start"]) + (width // 2) - 1
        left_scope = {**scope, "end": midpoint}
        right_scope = {**scope, "start": midpoint + 1}
        left = await collect(left_scope)
        right = await collect(right_scope)
        return {
            "rows": left["rows"] + right["rows"],
            "complete": left["complete"] and right["complete"],
            "pages": result["pages"] + left["pages"] + right["pages"],
            "reason": "time_partitioned" if left["complete"] and right["complete"] else "incomplete_time_partition",
            "scope": {"requested": params, "windows": [left["scope"], right["scope"]]},
        }

    return await collect(dict(params))


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


def assess(history, series, profile, end, closed=None):
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
    metrics["realized_pnl"] = finite(latest.get("realized_pnl"))
    metrics["wallet_income"] = finite(latest.get("wallet_income"))
    for days in (7, 30):
        target = end - days * DAY
        baseline = next((p for p in reversed(points) if p["timestamp"] <= target), None)
        # Do not use a baseline from an arbitrary distant date.
        start_value = finite(baseline.get("trade_pnl")) if baseline and target - baseline["timestamp"] <= 2*DAY else None
        metrics[f"trade_pnl_{days}d"] = metrics["trade_pnl"] - start_value if start_value is not None and metrics["trade_pnl"] is not None else None
    # Daily provider curve changes are not individual trade outcomes.  They
    # are still useful evidence of consistency and drawdown, and are kept
    # explicitly separate from realized closed-position win/loss statistics.
    curve_points = [p for p in points if p["timestamp"] >= end - 30 * DAY]
    prior = next((p for p in reversed(points) if p["timestamp"] < end - 30 * DAY), None)
    previous_value = finite(prior.get("trade_pnl")) if prior else None
    daily_changes = []
    for point in curve_points:
        value = finite(point.get("trade_pnl"))
        if value is not None and previous_value is not None:
            daily_changes.append(value - previous_value)
        if value is not None:
            previous_value = value
    positive_days = [change for change in daily_changes if change > 0]
    negative_days = [change for change in daily_changes if change < 0]
    metrics.update({
        "pnl_days_30d": len(daily_changes),
        "positive_pnl_days_30d": len(positive_days),
        "negative_pnl_days_30d": len(negative_days),
        "positive_pnl_day_rate_30d": len(positive_days) / len(daily_changes) if daily_changes else None,
        "daily_pnl_profit_factor_30d": sum(positive_days) / abs(sum(negative_days)) if negative_days else None,
        "no_negative_pnl_days_30d": bool(positive_days and not negative_days),
        "worst_daily_pnl_30d": min(daily_changes) if daily_changes else None,
    })
    curve_values = [finite(p.get("trade_pnl")) for p in ([prior] if prior else []) + curve_points]
    curve_values = [value for value in curve_values if value is not None]
    peak, max_drawdown = None, 0.0
    for value in curve_values:
        peak = value if peak is None else max(peak, value)
        max_drawdown = min(max_drawdown, value - peak)
    metrics["max_curve_drawdown_30d"] = max_drawdown if curve_values else None
    if closed and closed.get("complete"):
        realized = [finite(row.get("realized_pnl")) for row in closed["rows"]]
        realized = [value for value in realized if value is not None and value != 0]
        wins = [value for value in realized if value > 0]
        losses = [value for value in realized if value < 0]
        metrics.update({
            "closed_positions_sample": len(realized),
            "closed_position_wins": len(wins),
            "closed_position_losses": len(losses),
            "closed_position_win_rate_pct": (100 * len(wins) / len(realized)) if realized else None,
            "closed_position_profit_factor": sum(wins) / abs(sum(losses)) if losses else None,
            "no_realized_losses": bool(wins and not losses),
            "worst_closed_position_pnl": min(realized) if realized else None,
        })
    if not history["complete"]:
        reasons.append("INCOMPLETE_TRADE_WINDOW")
    if pnl is None or not points or end - latest["timestamp"] > 2*DAY or latest["timestamp"] > end + DAY:
        reasons.append("MISSING_OR_STALE_PNL")
    if reasons:
        classification = "needs_data"
    elif pnl < 50000:
        classification, reasons = "excluded", ["PNL_BELOW_50K"]
    elif max(week, month) > 40 or max(counts) > 40:
        classification, reasons = "excluded", ["FILL_RATE_ABOVE_40_OR_DAILY_BURST"]
    elif max(week, month) > 30 or max(counts) > 30:
        # Thirty fills/day is the upper bound for the active-copy roster.  A
        # wallet just above it is not necessarily abusive, but it is not the
        # low-turnover strategy the paper copier is intended to mirror.
        classification, reasons = "excluded", ["FILL_RATE_OUTSIDE_ACTIVE_RANGE"]
    elif any(metrics[f"trade_pnl_{d}d"] is None for d in (7, 30)):
        classification, reasons = "needs_data", ["MISSING_RECENT_TRADE_PNL"]
    elif any(metrics[f"trade_pnl_{d}d"] <= 0 for d in (7, 30)):
        classification, reasons = "excluded", ["NON_POSITIVE_RECENT_TRADE_PNL"]
    elif metrics["pnl_days_30d"] < 14 or metrics["positive_pnl_day_rate_30d"] is None:
        classification, reasons = "needs_data", ["INSUFFICIENT_30D_PNL_CURVE"]
    elif metrics["positive_pnl_day_rate_30d"] < 0.55 or (metrics["daily_pnl_profit_factor_30d"] is not None and metrics["daily_pnl_profit_factor_30d"] < 1.25):
        classification, reasons = "excluded", ["INCONSISTENT_30D_PNL_CURVE"]
    elif metrics.get("closed_positions_sample") is None or metrics["closed_positions_sample"] < 10:
        classification, reasons = "needs_data", ["INSUFFICIENT_REALIZED_POSITION_SAMPLE"]
    elif metrics["closed_position_win_rate_pct"] < 60 or (metrics["closed_position_profit_factor"] is not None and metrics["closed_position_profit_factor"] < 1.25):
        classification, reasons = "excluded", ["LOW_REALIZED_WIN_RATE_OR_PROFIT_FACTOR"]
    elif min(week, month) < 2 or metrics["active_days_7d"] < 5:
        # A quiet wallet earns standby monitoring only after passing the same
        # curve and realized-position checks as an active candidate.  This
        # prevents a large historic P&L number alone from creating a sniper.
        classification, reasons = "watchlist", ["LOW_OR_INTERMITTENT_ACTIVITY", "QUALITY_SCREEN_PASSED"]
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
    report = assess(trades, series, profile, end, closed)
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
