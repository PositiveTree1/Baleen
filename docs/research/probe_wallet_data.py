"""Read-only public API sample. No application imports, database writes or orders."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

BASE = "https://data-api.polymarket.com"
WALLET = "0x204f72f35326db932158cba6adff0b9a1da95e14"
report = {"started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "wallet": WALLET, "scope": "One public wallet; smoke test, not a completeness or profitability certification", "requests": []}


def get(path, params, base=BASE):
    url = base + path + "?" + urllib.parse.urlencode(params)
    record = {"url": url}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read()
            data = json.loads(raw)
            record.update(status=response.status, sha256=hashlib.sha256(raw).hexdigest())
            rows = data if isinstance(data, list) else data.get("data") if isinstance(data, dict) else None
            record["count"] = len(rows) if isinstance(rows, list) else None
            record["sample"] = rows[0] if isinstance(rows, list) and rows else data
            if isinstance(data, dict) and "pagination" in data:
                record["pagination"] = data["pagination"]
    except Exception as exc:
        data = None
        record["error"] = str(exc)
    return record, data


def main():
    specs = [("/v1/leaderboard", {"user": WALLET, "timePeriod": p, "limit": 1}) for p in ("ALL", "WEEK", "MONTH")]
    specs += [("/v1/leaderboard", {"timePeriod": "ALL", "limit": 100}),
              ("/v2/trades", {"user": WALLET, "limit": 2, "takerOnly": "false"}),
              ("/v2/user-stats", {"user": WALLET}),
              ("/v2/user-pnl", {"user": WALLET}),
              ("/positions", {"user": WALLET, "limit": 2, "sizeThreshold": 0}),
              ("/closed-positions", {"user": WALLET, "limit": 2, "sortBy": "TIMESTAMP", "sortDirection": "DESC"}),
              ("/activity", {"user": WALLET, "limit": 2})]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for rec, _ in pool.map(lambda s: get(*s), specs):
            report["requests"].append(rec)
    cutoff = int(time.time())
    trades = []
    for offset in range(0, 4000, 500):
        rec, rows = get("/trades", {"user": WALLET, "limit": 500, "offset": offset, "takerOnly": "false", "end": cutoff})
        if isinstance(rows, list):
            rec.pop("sample", None)
            trades.extend(rows)
        report["requests"].append(rec)
        if not isinstance(rows, list) or len(rows) < 500:
            break
    keys = [json.dumps([t.get(k) for k in ("transactionHash", "proxyWallet", "asset", "side", "size", "price", "timestamp")]) for t in trades]
    timestamps = [t["timestamp"] for t in trades if isinstance(t.get("timestamp"), (int, float))]
    report["trade_sample"] = {"rows": len(trades), "distinct_composite_keys": len(set(keys)),
        "wrong_wallet_rows": sum(t.get("proxyWallet", "").lower() != WALLET for t in trades),
        "oldest": min(timestamps) if timestamps else None, "newest": max(timestamps) if timestamps else None,
        "coverage_days": (max(timestamps)-min(timestamps))/86400 if timestamps else None,
        "nonincreasing_timestamps": all(a >= b for a, b in zip(timestamps, timestamps[1:])),
        "note": "Composite-key uniqueness is diagnostic only; no log-index event identity or full-history completeness proven."}
    rec, markets = get("/markets", {"limit": 1, "active": "true", "closed": "false"}, "https://gamma-api.polymarket.com")
    if isinstance(markets, list) and markets:
        m = markets[0]
        rec["sample"] = {k: m.get(k) for k in ("conditionId", "question", "orderMinSize", "orderPriceMinTickSize", "clobTokenIds")}
        report["requests"].append(rec)
        token = json.loads(m["clobTokenIds"])[0]
        rec, book = get("/book", {"token_id": token}, "https://clob.polymarket.com")
        if isinstance(book, dict):
            rec["sample"] = {k: book.get(k) for k in ("asset_id", "timestamp", "min_order_size", "tick_size")}
        report["requests"].append(rec)
    else:
        report["requests"].append(rec)
    path = Path(__file__).with_name("wallet_api_probe_2026-09-15.json")
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path), "trade_sample": report["trade_sample"], "requests": [{k: r[k] for k in ("url", "status", "count", "error") if k in r} for r in report["requests"]]}, indent=2))


if __name__ == "__main__":
    main()
