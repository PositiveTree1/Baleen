# Handoff Report: Requirement R1 Survey (Authentic On-Chain Trade History & Real Classification)

**Agent**: survey_explorer_1  
**Working Directory**: `c:\Users\arthu\Documents\Baleen-master\.agents\survey_explorer_1`  
**Date**: 2026-08-30  
**Handoff Type**: Hard (Task Complete)

---

## 1. Observation

1. **Polymarket Data API Client & Ingestion**:
   - `backend/app/discovery/polymarket_client.py:23-26`:
     ```python
     self.data_api_url = settings.POLYMARKET_DATA_API_URL  # "https://data-api.polymarket.com"
     self.clob_api_url = settings.CLOB_API_URL            # "https://clob.polymarket.com"
     self.gamma_api_url = settings.GAMMA_API_URL          # "https://gamma-api.polymarket.com"
     ```
   - Candidate discovery implemented in `polymarket_client.py:57-179` (`discover_candidates`) via 3 pillars:
     1. Large BUY trades: `f"{self.data_api_url}/trades"` (`filterType=CASH`, `filterAmount=2000`, `side=BUY`).
     2. Multi-period Leaderboard: `f"{self.data_api_url}/leaderboard"` (`timePeriod` in `["ALL", "MONTH", "WEEK"]`, `orderBy="PNL"`, `offset` in `[0, 100, 200]`).
     3. Top Volume Active Markets: `f"{self.gamma_api_url}/markets"` (`active="true"`, `limit=40`) -> queries trades per top condition ID.
   - Deep trade history ingestion:
     - Positions: `polymarket_client.py:181-197` (`fetch_wallet_positions` pulling `/positions` with `limit=500`, `sortBy="CASHPNL"`, `sortDirection="DESC"`).
     - Activity: `polymarket_client.py:262-292` (`fetch_wallet_activity` pulling `/activity` with multi-page pagination up to 4,000 items).
     - Trades: `polymarket_client.py:228-260` (`fetch_wallet_trades` pulling `/trades` with pagination up to 4,000 items and maker address fallback).
     - Profile: `polymarket_client.py:199-212` (`fetch_wallet_profile` pulling `/v1/leaderboard`).

2. **Trade Data Parsing, Date Grouping & PnL Separation**:
   - `backend/app/discovery/scanner.py:215-286`:
     - Closed positions filtered via `p.get("redeemable") or float(p.get("cashPnl") or 0.0) != 0.0`.
     - Timestamp converted from ms/sec to UTC date string `YYYY-MM-DD`.
     - Daily aggregation in `daily_map[d_str]`:
       - `daily_map[d_str]["won"] += pnl_val` if `pnl_val > 0`
       - `daily_map[d_str]["lost"] += abs(pnl_val)` if `pnl_val < 0`
       - `daily_map[d_str]["net"] += pnl_val`
     - Output emitted in `daily_pnl_history`:
       ```python
       "won_usd": round(d_info["won"], 2),
       "lost_usd": round(-abs(d_info["lost"]), 2),
       "net_pnl": round(d_info["net"], 2),
       "daily_pnl": round(d_info["net"], 2),
       "cumulative_pnl": round(running_cum, 2),
       "trades_count": d_info["count"]
       ```
     - Activity log fallback parses `REDEMPTION`/`REDEEM` as gross won and `SELL` fills relative to purchase price.

3. **Whale Classification & Gatekeeper Filters**:
   - `backend/app/scoring/engine.py:11-75` (`score_wallet`):
     - Filter 1: Realized PnL $\ge \$50,000$ & Volume $\ge \$150,000$ (with high PnL exemption $\ge \$250k$).
     - Filter 2: Track record $\ge 150$ trades & $\ge 60$ active days (exempt if $\text{PnL} \ge \$500k$).
     - Filter 3: Anti-HFT $\le 65$ trades/day.
     - Filter 4: Outlier single position concentration $\le 25\%$ of positive PnL sum.
     - Filter 5: Sleeve size compatibility ($\$20 \le \text{median trade size} \le \$3,000$).
     - Filter 6: Wash-trading ratio $\le 10\%$.
     - Filter 7: Mandatory on-chain history requirement.
     - Filter 8: Anti-boundary arbitrage ($0.01 / 0.99$ sniper rejection).
     - Filter 9: Minimum win rate $\ge 55.0\%$.
     - Tier: `gold_sniper` if `win_rate >= 80.0%` and `max_drawdown <= 12.0%`.
   - `backend/app/scoring/basket.py`:
     - 5-factor intra-pool dynamic normalization (`normalize_and_score_pool`): Odds Edge (30%), Sharpe (30%), Recency EMA (20%), Category (10%), Copyability Penalty (-10%).
     - 5-point incumbency hysteresis (`select_top_10_roster`) protecting incumbent whales with a $+5.0$ defense bonus.

4. **Zero Synthetic / Fabricated Data**:
   - Scratch seed file `backend/add_whales.py` (which had 3 hardcoded fake addresses) was cleaned up by `backend/cleanup_fake.py`.
   - Database initialization in `backend/app/database.py:85-156` (`init_db`) performs idempotent schema creation without inserting dummy seed data.
   - Startup hook in `backend/app/main.py:68-94` (`_auto_discovery_if_empty`) triggers authentic discovery against live Polymarket APIs if `wallets` table is empty.

5. **Test Suite Execution**:
   - Command: `& "C:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\pytest.exe"`
   - Result: `403 passed in 11.20s`.

---

## 2. Logic Chain

1. **Evidence 1 (Observation 1)**: `polymarket_client.py` and `scanner.py` connect directly to Polymarket's official endpoints (`/trades`, `/leaderboard`, `/markets`, `/positions`, `/activity`, `/v1/leaderboard`), handling HTTP 429 rate-limiting backoff and multi-page pagination up to 4,000 trades/items.
   $\to$ **Deduction 1**: The ingestion engine operates completely on genuine on-chain Polymarket data across all candidate whales.

2. **Evidence 2 (Observation 2)**: In `scanner.py:calculate_authentic_wallet_stats`, trade events and closed positions are grouped by UTC date (`YYYY-MM-DD`). Positive PnL is mapped to `won_usd` ($\ge 0$) and negative PnL is mapped to `lost_usd` ($\le 0$).
   $\to$ **Deduction 2**: The daily aggregation provides authentic, non-fabricated dual-column win/loss separation. The negative value for `lost_usd` directly supports Recharts `stackOffset="sign"` dual-column rendering.

3. **Evidence 3 (Observation 3)**: Disqualifying hard filters in `engine.py` (Filters 1-9) prevent low-conviction, wash-trading, boundary-arbitrage, or HFT bot distortion. Wilson lower bounds (90% CI) and risk-adjusted Sharpe ratios are computed from authentic closed position statistics.
   $\to$ **Deduction 3**: Candidate whales are accurately classified with mathematically sound win rates, Sharpe ratios, and copyability parameters.

4. **Evidence 4 (Observation 4 & 5)**: No synthetic seed data is inserted during database init; startup triggers live auto-discovery; all 403 backend tests pass cleanly.
   $\to$ **Deduction 4**: The backend is 100% compliant with Requirement R1.

---

## 3. Caveats

1. **Polymarket API Rate Limits**: Polymarket Data API free tier enforces approximately 30 requests per 5 seconds. The current exponential backoff and 0.04s inter-request pause in `polymarket_client.py` prevents 429 throttling during normal runs, but massive multi-thousand-wallet full discovery scans should maintain polite throttling.
2. **Groq API Keys for AI Summaries**: AI summary generation in `ai_summary.py` gracefully falls back to deterministic quantitative summaries if Groq API keys are not provided or exhausted.

---

## 4. Conclusion

Requirement R1 (Authentic On-Chain Trade History & Real Classification) is fully substantiated, robustly architected, and verified across the Baleen codebase:
- Ingestion pipeline captures real `/positions`, `/activity`, and `/trades` data from Polymarket.
- Daily aggregation calculates authentic separated `won_usd` and `lost_usd` streams.
- Mathematical classification enforces 9 disqualifying filters, 5-factor scoring, and 5-point hysteresis.
- Zero fabricated data exists in production paths.
- Backend test suite is 100% green (403/403 tests passing).

---

## 5. Verification Method

### Test Execution Command
Run the backend pytest suite:
```powershell
& "C:\Users\arthu\Documents\Baleen-master\backend\.venv\Scripts\pytest.exe"
```

### Key Source Files to Inspect
1. `backend/app/discovery/polymarket_client.py`: API client, 3-pillar candidate discovery, positions/trades pagination.
2. `backend/app/discovery/scanner.py`: `calculate_authentic_wallet_stats()`, date grouping, `won_usd`/`lost_usd` calculation, Wilson LB & Sharpe ratio.
3. `backend/app/scoring/engine.py`: 9 disqualifying hard filters and tier classifications.
4. `backend/app/scoring/basket.py`: 5-factor intra-pool normalizer and 5-point incumbency hysteresis.
5. `backend/app/api/wallets.py`: API endpoints serving wallet profiles, snapshots, and daily PnL history.

### Invalidation Conditions
- Any introduction of hardcoded or synthetic wallet data in database initialization.
- Mismatch between `won_usd` (positive) and `lost_usd` (negative) signed values in API responses.
- Any regression in the 403 passing pytest cases.
