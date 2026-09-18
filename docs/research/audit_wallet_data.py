"""Public GET-only wallet capability audit. Independent of the application/database.

Run from any directory: python docs/research/audit_wallet_data.py
Saves dated observations, not investment recommendations. Bounded history walks
report truncation explicitly. All cursor requests retain original query filters.
"""
import concurrent.futures
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = Path(__file__).parent / ("wallet_audit_" + datetime.now(timezone.utc).strftime("%Y-%m-%d"))
BASE = "https://data-api.polymarket.com"
HFT = "0x204f72f35326db932158cba6adff0b9a1da95e14"
NOW = int(time.time())
REQUESTS = []


def get(path, params=None, base=BASE):
    url = base + path + "?" + urllib.parse.urlencode(params or {})
    record = {"url": url, "received_at": datetime.now(timezone.utc).isoformat()}
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
                data = json.loads(raw)
                record.update(status=response.status, sha256=hashlib.sha256(raw).hexdigest(), attempts=attempt+1)
                REQUESTS.append(record)
                return data
        except urllib.error.HTTPError as error:
            record.update(status=error.code, error=error.read().decode(errors="replace")[:400])
            if error.code not in (429, 500, 502, 503, 504):
                break
        except Exception as error:
            record["error"] = str(error)
        time.sleep(0.3 * (attempt+1))
    REQUESTS.append(record)
    return {"audit_error": record}


def walk(path, params, max_pages=20):
    params = dict(params)
    rows, cursors, fingerprints = [], set(), set()
    for page in range(max_pages):
        result = get(path, params)
        batch = result.get("data") if isinstance(result, dict) else None
        if not isinstance(batch, list) or not isinstance(result.get("pagination"), dict):
            return rows, {"complete": False, "pages": page+1, "reason": "invalid response", "response": result}
        fp = hashlib.sha256(json.dumps(batch, sort_keys=True).encode()).hexdigest()
        if batch and fp in fingerprints:
            return rows, {"complete": False, "pages": page+1, "reason": "repeated page"}
        fingerprints.add(fp)
        rows.extend(batch)
        cursor = result["pagination"].get("next_cursor")
        if cursor is None:
            return rows, {"complete": not result["pagination"].get("has_more", False), "pages": page+1, "reason": "cursor exhausted"}
        if cursor in cursors or not batch:
            return rows, {"complete": False, "pages": page+1, "reason": "cursor loop or empty intermediate page"}
        cursors.add(cursor)
        params["cursor"] = cursor
    return rows, {"complete": False, "pages": max_pages, "reason": "audit page budget reached"}


def trade_key(t):
    return tuple(t.get(a, t.get(b)) for a,b in [("transaction_hash","transactionHash"), ("token_id","asset"), ("side","side"), ("price","price"), ("size","size"), ("timestamp","timestamp")])


def summarize(rows, address, start=None):
    ts = [t["timestamp"] for t in rows if isinstance(t.get("timestamp"), (float,int))]
    return {"rows": len(rows), "distinct_diagnostic_keys": len({trade_key(t) for t in rows}),
        "transactions": len({t.get("transaction_hash", t.get("transactionHash")) for t in rows}),
        "wrong_wallet": sum(t.get("proxy_wallet", t.get("proxyWallet", "")).lower() != address for t in rows),
        "oldest": min(ts) if ts else None, "newest": max(ts) if ts else None,
        "outside_requested_window": sum(t > NOW or (start is not None and t < start) for t in ts),
        "descending": all(a >= b for a,b in zip(ts,ts[1:])),
        "span_hours": (max(ts)-min(ts))/3600 if ts else None,
        "daily_fills": dict(sorted(Counter(datetime.fromtimestamp(t,timezone.utc).strftime("%Y-%m-%d") for t in ts).items()))}


def screening(entry):
    address = entry["proxyWallet"].lower()
    rows, coverage = walk("/v2/trades", {"user": address, "limit": 211, "start": NOW-7*86400, "end": NOW, "taker_only": "false"}, 1)
    return {"address": address, "name": entry.get("userName"), "source_period": entry["source_period"],
        "source_pnl": entry.get("pnl"), "coverage": coverage, "trades": summarize(rows,address,NOW-7*86400),
        "weekly_fill_band": coverage["complete"] and 14 <= len(rows) <= 210}


def capabilities(item):
    address = item["address"]
    details = {"screen": item, "capabilities": {}}
    specs = [("stats", "/v2/user-stats", {"user": address}),
             ("value", "/v2/value", {"user": address}),
             ("volume", "/v2/user-volume", {"user": address, "start": NOW-30*86400, "end": NOW})]
    specs += [("leaderboard_"+p, "/v1/leaderboard", {"user": address, "timePeriod": p}) for p in ("ALL","WEEK","MONTH")]
    specs += [("curve_"+p, "/v2/user-pnl", {"user": address,"interval": p,"fidelity":"1d"}) for p in ("1w","1m","all")]
    for label,path,params in specs:
        details["capabilities"][label] = get(path,params)
    details["capabilities"]["profile"] = get("/public-profile",{"address":address},"https://gamma-api.polymarket.com")
    for status in ("OPEN","REDEEMABLE","CLOSED"):
        params={"user":address,"status":status,"limit":100,"filter_amount":0,"sort_by":"TIMESTAMP"}
        if status != "CLOSED": params["include_archived"]="true"
        rows,coverage=walk("/v2/positions",params,30)
        details["capabilities"]["positions_"+status]={"coverage":coverage,"count":len(rows),"rows":rows}
    for label,path,params in [
        ("trades_30d","/v2/trades",{"user":address,"start":NOW-30*86400,"end":NOW,"taker_only":"false","limit":100}),
        ("activity_30d","/v2/activity",{"user":address,"start":NOW-30*86400,"end":NOW,"limit":100}),
    ]:
        rows,coverage=walk(path,params,50)
        details["capabilities"][label]={"coverage":coverage,"summary":summarize(rows,address,NOW-30*86400),"rows":rows}
    (OUT/(address+".json")).write_text(json.dumps(details,indent=2),encoding="utf-8")
    return details


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    pool={}
    for period in ("ALL","MONTH","WEEK"):
        rows=get("/v1/leaderboard",{"timePeriod":period,"limit":50,"offset":0})
        if isinstance(rows,list):
            for row in rows:
                pool.setdefault(row["proxyWallet"].lower(),dict(row,source_period=period))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        screened=list(executor.map(screening,pool.values()))
    (OUT/"screening.json").write_text(json.dumps(screened,indent=2),encoding="utf-8")
    # Include bursty counterexamples as well as quieter daily-band fixtures.
    selected=[s for s in screened if s["weekly_fill_band"]][:4]
    selected += [s for s in screened if s["weekly_fill_band"]
                 and max(s['trades']['daily_fills'].values(),default=0) <= 30
                 and s not in selected]
    print(json.dumps({"screened":len(screened),"band_matches":sum(s['weekly_fill_band'] for s in screened),"selected":selected}),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        detailed=list(executor.map(capabilities,selected))
    # Reproduce the original sample with two provider versions at the original cutoff.
    v2,cov=walk("/v2/trades",{"user":HFT,"limit":500,"end":1789506104,"start":1,"taker_only":"false"},8)
    legacy=[]
    for offset in range(0,4000,500):
        rows=get("/trades",{"user":HFT,"limit":500,"offset":offset,"end":1789506104,"start":1,"takerOnly":"false"})
        if isinstance(rows,list): legacy.extend(rows)
    hft={"v2":summarize(v2,HFT),"v1":summarize(legacy,HFT),"coverage":cov,
         "matching_keys":len({trade_key(t) for t in v2}&{trade_key(t) for t in legacy}),
         "sample_rows":v2[:3],"stats":get("/v2/user-stats",{"user":HFT})}
    (OUT/"hft_crosscheck.json").write_text(json.dumps(hft,indent=2),encoding="utf-8")
    extra={"freshness":get("/v2/status"),
           "unknown_stats":get("/v2/user-stats",{"user":"0x0000000000000000000000000000000000000001"}),
           "invalid_cursor":get("/v2/trades",{"user":HFT,"cursor":"invalid-audit-cursor"})}
    if selected:
        address=selected[0]["address"]
        extra["legacy_curve"]=get("/user-pnl",{"user_address":address,"interval":"all","fidelity":"1d"},"https://user-pnl-api.polymarket.com")
        extra["hourly_curve"]=get("/v2/user-pnl",{"user":address,"interval":"1w","fidelity":"1h"})
        extra["taker_comparison"]=get("/v2/trades",{"user":address,"limit":1000,"start":NOW-7*86400,"end":NOW,"taker_only":"true"})
    (OUT/"extra.json").write_text(json.dumps(extra,indent=2),encoding="utf-8")
    (OUT/"requests.json").write_text(json.dumps(REQUESTS,indent=2),encoding="utf-8")
    print(json.dumps({"output":str(OUT),"requests":len(REQUESTS),"http_statuses":dict(Counter(r.get("status","error") for r in REQUESTS)),"hft":{k:v for k,v in hft.items() if k not in ('stats','sample_rows')}}),flush=True)


if __name__ == "__main__":
    main()
