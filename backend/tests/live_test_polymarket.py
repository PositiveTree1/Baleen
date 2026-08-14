import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def test_api():
    try:
        req = urllib.request.Request(
            "https://data-api.polymarket.com/trades?limit=5",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            print(f"Polymarket Trades Success! Fetched {len(data)} trades.")
            if data:
                print("First trade sample:")
                print(json.dumps(data[0], indent=2))
                maker = data[0].get("maker_address") or data[0].get("maker") or data[0].get("user")
                print(f"Sample maker address: {maker}")
                
                # Test leaderboard
                req_lb = urllib.request.Request(
                    "https://data-api.polymarket.com/v1/leaderboard?window=all&limit=5",
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req_lb, timeout=10, context=ctx) as r_lb:
                    lb_data = json.loads(r_lb.read().decode())
                    print(f"Leaderboard fetched: {len(lb_data) if isinstance(lb_data, list) else type(lb_data)}")
                    if isinstance(lb_data, list) and lb_data:
                        print("Leaderboard top entry:")
                        print(json.dumps(lb_data[0], indent=2))
    except Exception as e:
        print(f"Error connecting to Polymarket: {e}")

if __name__ == "__main__":
    test_api()
