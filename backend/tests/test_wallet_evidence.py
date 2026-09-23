import json
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from app.discovery.wallet_evidence import cursor_history, assess, chart_history, DAY

ADDRESS = "0x" + "a" * 40


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [0, 1, 499, 500, 501, 4000, 4001])
async def test_exhausts_cursor_and_preserves_identical_fills(count):
    rows = [{"proxy_wallet": ADDRESS, "timestamp": 11}] * count
    batches = [rows[i:i+1000] for i in range(0, count, 1000)] or [[]]
    responses = [{"data": b, "pagination": {"has_more": i < len(batches)-1, "next_cursor": str(i+1)}} for i, b in enumerate(batches)]
    client = type("Client", (), {"data_api_url": "https://example.test", "_fetch_with_retry": AsyncMock(side_effect=responses)})()
    result = await cursor_history(client, "/v2/trades", ADDRESS, {"start": 10, "end": 12, "taker_only": "false"})
    assert result["complete"] and len(result["rows"]) == count
    for call in client._fetch_with_retry.call_args_list:
        assert call.args[1]["start"] == 10 and call.args[1]["end"] == 12
        assert call.args[1]["taker_only"] == "false"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["loop", "missing", "wrong_wallet", "out_of_window", "empty_midstream", "budget"])
async def test_never_calls_partial_history_complete(failure):
    page = {"data": [{"proxy_wallet": ADDRESS, "timestamp": 11}], "pagination": {"has_more": True, "next_cursor": "a"}}
    next_page = json.loads(json.dumps(page))
    if failure == "missing": next_page = None
    if failure == "wrong_wallet": next_page["data"][0]["proxy_wallet"] = "other"
    if failure == "out_of_window": next_page["data"][0]["timestamp"] = 9
    if failure == "empty_midstream": next_page["data"] = []
    client = type("Client", (), {"data_api_url": "", "_fetch_with_retry": AsyncMock(side_effect=[page, next_page])})()
    result = await cursor_history(client, "/v2/trades", ADDRESS, {"start": 10, "end": 12}, max_pages=1 if failure == "budget" else 2)
    assert not result["complete"]


@pytest.mark.asyncio
async def test_busy_window_is_partitioned_before_being_marked_incomplete():
    """The local page budget must not turn a measurable low-rate wallet into needs_data."""
    class Client:
        data_api_url = ""

        def __init__(self):
            self.calls = []

        async def _fetch_with_retry(self, _url, query):
            self.calls.append(dict(query))
            if query["start"] == 0 and query["end"] == 2 * DAY - 1:
                return {"data": [{"proxy_wallet": ADDRESS, "timestamp": 1}],
                        "pagination": {"has_more": True, "next_cursor": "more"}}
            return {"data": [{"proxy_wallet": ADDRESS, "timestamp": query["start"]}],
                    "pagination": {"has_more": False, "next_cursor": None}}

    client = Client()
    result = await cursor_history(client, "/v2/trades", ADDRESS, {"start": 0, "end": 2 * DAY - 1},
                                  max_pages=1, max_total_pages=4, min_window_seconds=DAY)
    assert result["complete"]
    assert result["reason"] == "time_partitioned"
    assert len(result["rows"]) == 2
    assert [(call["start"], call["end"]) for call in client.calls] == [
        (0, 2 * DAY - 1), (0, DAY - 1), (DAY, 2 * DAY - 1)]


@pytest.mark.asyncio
async def test_partitioning_stays_incomplete_when_total_request_budget_is_exhausted():
    page = {"data": [{"proxy_wallet": ADDRESS, "timestamp": 1}],
            "pagination": {"has_more": True, "next_cursor": "more"}}
    complete = {"data": [{"proxy_wallet": ADDRESS, "timestamp": 1}],
                "pagination": {"has_more": False, "next_cursor": None}}
    client = type("Client", (), {"data_api_url": "", "_fetch_with_retry": AsyncMock(side_effect=[page, complete])})()
    result = await cursor_history(client, "/v2/trades", ADDRESS, {"start": 0, "end": 2 * DAY - 1},
                                  max_pages=1, max_total_pages=2, min_window_seconds=DAY)
    assert not result["complete"]
    assert result["reason"] == "incomplete_time_partition"
    assert client._fetch_with_retry.await_count == 2


def fixture_parts():
    root = Path(__file__).resolve().parents[2] / "docs/research/wallet_audit_2026-09-16"
    data = json.loads((root / "0xeee1b757ce93e076fdb4c1f4ff183dc302c53e28.json").read_text())
    c = data["capabilities"]
    return c["trades_30d"], c["curve_all"]["data"], c["stats"]["data"]


def test_recorded_dreamlawn_without_quality_curve_stays_unapproved():
    trades, series, profile = fixture_parts()
    end = max(p["timestamp"] for p in series["points"]) // DAY * DAY
    history = {"rows": trades["rows"], "complete": True}
    result = assess(history, series, profile, end)
    assert result["classification"] == "excluded"
    assert result["reasons"] == ["INCONSISTENT_30D_PNL_CURVE"]
    assert result["metrics"]["distinct_markets_lifetime"] == 45
    assert not result["execution_approved"]


def test_chart_does_not_invent_first_day_profit_or_fill_count():
    series = {"points": [{"timestamp": DAY, "economic_pnl": 100}, {"timestamp": 2*DAY, "economic_pnl": 80}]}
    chart = chart_history(series)
    assert chart[0]["daily_pnl"] is None
    assert chart[0]["trades_count"] is None
    assert chart[1]["daily_pnl"] == -20


def test_weekly_average_cannot_hide_one_day_burst():
    end = 100*DAY
    history = {"rows": [{"timestamp": end-DAY+1}]*100, "complete": True}
    series = {"points": [{"timestamp": end, "economic_pnl": 100000, "trade_pnl": 100000}]}
    report = assess(history, series, {}, end)
    assert report["classification"] == "excluded"
    assert report["metrics"]["fills_per_day_7d"] < 30


def test_missing_data_never_becomes_zero_profit_or_approved():
    result = assess({"rows": [], "complete": False}, None, None, 100*DAY)
    assert result["classification"] == "needs_data"
    assert result["metrics"]["economic_pnl"] is None


def test_active_candidate_requires_consistent_curve_and_realized_position_sample():
    end = 100 * DAY
    history = {"rows": [{"timestamp": end - 30 * DAY + day * DAY + 1} for day in range(30) for _ in range(2)], "complete": True}
    series = {"points": [{"timestamp": (69 + day) * DAY, "economic_pnl": 100000 + day * 100,
                            "trade_pnl": 100000 + day * 100} for day in range(32)]}
    closed = {"rows": [{"realized_pnl": 100}] * 10, "complete": True}
    result = assess(history, series, {}, end, closed)
    assert result["classification"] == "research_candidate"
    assert result["metrics"]["closed_position_win_rate_pct"] == 100
    assert result["metrics"]["positive_pnl_day_rate_30d"] == 1


def test_low_realized_win_rate_excludes_wallet_even_when_recent_pnl_is_positive():
    end = 100 * DAY
    history = {"rows": [{"timestamp": end - 30 * DAY + day * DAY + 1} for day in range(30) for _ in range(2)], "complete": True}
    series = {"points": [{"timestamp": (69 + day) * DAY, "economic_pnl": 100000 + day * 100,
                            "trade_pnl": 100000 + day * 100} for day in range(32)]}
    closed = {"rows": [{"realized_pnl": 100}] * 5 + [{"realized_pnl": -100}] * 5, "complete": True}
    result = assess(history, series, {}, end, closed)
    assert result["classification"] == "excluded"
    assert result["reasons"] == ["LOW_REALIZED_WIN_RATE_OR_PROFIT_FACTOR"]


def test_low_activity_wallet_needs_quality_evidence_before_becoming_standby():
    end = 100 * DAY
    history = {"rows": [{"timestamp": end - 2 * DAY + 1}], "complete": True}
    series = {"points": [{"timestamp": (69 + day) * DAY, "economic_pnl": 100000 + day * 100,
                            "trade_pnl": 100000 + day * 100} for day in range(32)]}
    result = assess(history, series, {}, end, {"rows": [], "complete": True})
    assert result["classification"] == "needs_data"
    assert result["reasons"] == ["INSUFFICIENT_REALIZED_POSITION_SAMPLE"]


def test_low_activity_wallet_that_passes_quality_screen_becomes_standby():
    end = 100 * DAY
    history = {"rows": [{"timestamp": end - 2 * DAY + 1}], "complete": True}
    series = {"points": [{"timestamp": (69 + day) * DAY, "economic_pnl": 100000 + day * 100,
                            "trade_pnl": 100000 + day * 100} for day in range(32)]}
    closed = {"rows": [{"realized_pnl": 100}] * 10, "complete": True}
    result = assess(history, series, {}, end, closed)
    assert result["classification"] == "watchlist"
    assert result["reasons"] == ["LOW_OR_INTERMITTENT_ACTIVITY", "QUALITY_SCREEN_PASSED"]
