import os
import logging
import asyncio
import math
import json
import time
import inspect
from typing import List, Dict, Optional, Tuple, Any, Set
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text, func
from app.discovery.polymarket_client import PolymarketClient
from app.models import Wallet, WalletSnapshot, ExecutionLog, KeyValue
from app.scoring.engine import score_wallet
from app.scoring.basket import compute_baleen_score
from app.analysis.ai_summary import generate_summary
from app.services.event_logger import log_event

logger = logging.getLogger(__name__)

def parse_date_to_utc_str(ts_raw: Any, fallback_str: str) -> str:
    if not ts_raw:
        return fallback_str
    if isinstance(ts_raw, (int, float)):
        val = float(ts_raw)
        ts_sec = val / 1000.0 if val > 1e11 else val
        try:
            return datetime.fromtimestamp(ts_sec, timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            return fallback_str
    if isinstance(ts_raw, str):
        try:
            val = float(ts_raw)
            ts_sec = val / 1000.0 if val > 1e11 else val
            return datetime.fromtimestamp(ts_sec, timezone.utc).strftime("%Y-%m-%d")
        except ValueError:
            pass
        try:
            clean_s = ts_raw.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_s)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
        if len(ts_raw) >= 10 and ts_raw[4] == '-' and ts_raw[7] == '-':
            return ts_raw[:10]
    return fallback_str

# Global Live Progress State for UI
discovery_state = {
    "status": "idle", # "idle" | "running" | "completed" | "error"
    "progress_pct": 0,
    "step_description": "Engine ready.",
    "wallets_scanned": 0,
    "active_whales_in_basket": 0,
    "gold_snipers": 0,
    "started_at": None,
    "completed_at": None,
    "error_message": None
}

_KV_DISCOVERY_STATE_KEY = "discovery_state"

async def _persist_discovery_state(db: AsyncSession):
    """Save the current discovery_state dict to the kv_store table."""
    try:
        serializable = {k: v for k, v in discovery_state.items()}
        value_json = json.dumps(serializable)
        existing = (await db.execute(
            select(KeyValue).where(KeyValue.key == _KV_DISCOVERY_STATE_KEY)
        )).scalar_one_or_none()
        if existing:
            existing.value = value_json
            existing.updated_at = datetime.utcnow()
        else:
            db.add(KeyValue(key=_KV_DISCOVERY_STATE_KEY, value=value_json))
        await db.commit()
    except Exception as e:
        logger.debug(f"Could not persist discovery state: {e}")

async def load_discovery_state_from_db():
    """Load the last persisted discovery_state from DB on startup."""
    global discovery_state
    try:
        from app.database import SessionLocal
        async with SessionLocal() as db:
            row = (await db.execute(
                select(KeyValue).where(KeyValue.key == _KV_DISCOVERY_STATE_KEY)
            )).scalar_one_or_none()
            if row and row.value:
                saved = json.loads(row.value)
                # If the last state was "running", it means the server crashed mid-scan
                if saved.get("status") == "running":
                    saved["status"] = "interrupted"
                    saved["step_description"] = (
                        f"Previous scan was interrupted (server restarted). "
                        f"Last progress: {saved.get('progress_pct', 0)}%. "
                        f"A new scan will run automatically."
                    )
                discovery_state.update(saved)
                logger.info(f"Restored discovery state from DB: status={discovery_state['status']}")
    except Exception as e:
        logger.debug(f"Could not load discovery state from DB: {e}")


def calc_wilson_lower_bound(wins: int, total: int, z: float = 1.645) -> float:
    """Calculates the 90% Wilson confidence lower bound for win rate (from Titan)."""
    if total <= 0:
        return 0.0
    p_hat = float(wins) / float(total)
    n = float(total)
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p_hat + z2 / (2.0 * n)
    spread = z * math.sqrt((p_hat * (1.0 - p_hat) + z2 / (4.0 * n)) / n)
    return round(max(0.0, (centre - spread) / denom) * 100.0, 1)

def calculate_authentic_wallet_stats(
    address: str, 
    positions: List[Dict], 
    activity: List[Dict], 
    profile: Optional[Dict] = None, 
    trades: Optional[List[Dict]] = None,
    closed_positions: Optional[List[Dict]] = None,
    pnl_history: Optional[List[Dict]] = None
) -> Dict:
    """
    Titan Quantitative Scoring Engine:
    Calculates authentic PnL, win rate, Wilson lower bound, profit factor, and daily history
    directly from Polymarket's official positions, activity closures, closed-positions, and profile endpoints.
    """
    profile = profile or {}
    official_pnl = next((profile[k] for k in ("pnl", "profit", "profile_profit") if profile.get(k) is not None), None)
    all_time_pnl = float(official_pnl) if official_pnl is not None else 0.0
    total_volume = float(profile.get("volume") or profile.get("vol") or 0)

    # Completed outcomes only; partial sales and floating marks are not wins.
    raw_closed = []
    seen_closed = set()
    for p in closed_positions or []:
        key = (p.get("conditionId"), p.get("asset"))
        if key in seen_closed:
            continue
        seen_closed.add(key)
        row = dict(p)
        row["cashPnl"] = float(p.get("realizedPnl") if p.get("realizedPnl") is not None else p.get("cashPnl", 0))
        raw_closed.append(row)
    # Settled but unredeemed losses must not disappear from the outcome sample.
    settled_data_complete = True
    for p in positions or []:
        key = (p.get("conditionId"), p.get("asset"))
        if not p.get("redeemable") or key in seen_closed:
            continue
        if p.get("currentValue") is not None and p.get("initialValue") is not None:
            remaining_pnl = float(p["currentValue"]) - float(p["initialValue"])
        elif p.get("avgPrice") is not None and p.get("curPrice") is not None and p.get("size") is not None:
            remaining_pnl = float(p["size"]) * (float(p["curPrice"]) - float(p["avgPrice"]))
        else:
            settled_data_complete = False
            continue
        value = float(p.get("realizedPnl") or 0) + remaining_pnl
        raw_closed.append({**p, "cashPnl": value, "realizedPnl": value})
        seen_closed.add(key)
    if any(not math.isfinite(p['cashPnl']) for p in raw_closed):
        raise ValueError("Non-finite outcome PnL")
    wins = sum(p["cashPnl"] > 0 for p in raw_closed)
    losses = sum(p["cashPnl"] < 0 for p in raw_closed)
    total_resolved = wins + losses
    gross_wins = sum(max(0, p["cashPnl"]) for p in raw_closed)
    gross_losses = sum(abs(min(0, p["cashPnl"])) for p in raw_closed)
    profit_factor = gross_wins / gross_losses if gross_losses else None

    if total_resolved > 0:
        win_rate = round((wins / total_resolved) * 100.0, 1)
        wilson_lb = calc_wilson_lower_bound(wins, total_resolved)
    else:
        win_rate = 0.0
        wilson_lb = 0.0

    closed_positions = raw_closed

    # 3. Position Concentration Cap (Closed positions positive PnL sum)
    pos_pnl_sum = sum(float(p.get("cashPnl") or 0.0) for p in closed_positions if float(p.get("cashPnl") or 0.0) > 0)
    biggest_win = max((float(p.get("cashPnl") or 0.0) for p in closed_positions), default=0.0)
    outlier_concentration = round(biggest_win / pos_pnl_sum, 3) if (pos_pnl_sum > 0 and biggest_win > 0) else 0.10

    # 4. Odds-Weighted Win Rate & Risk-Adjusted Sharpe Ratio
    entry_prices = []
    pct_pnls = []
    for p in closed_positions:
        init_val = float(p.get("initialValue") or p.get("size") or 1.0)
        c_pnl = float(p.get("cashPnl") or 0.0)
        p_price = float(p.get("avgPrice") or p.get("curPrice") or 0.50)
        entry_prices.append(p_price)
        if init_val > 0:
            pct_pnls.append(c_pnl / init_val)

    avg_entry_price = sum(entry_prices) / len(entry_prices) if entry_prices else 0.50
    odds_weighted_edge = (win_rate / 100.0) - avg_entry_price

    if pct_pnls and len(pct_pnls) >= 3:
        mean_pct = sum(pct_pnls) / len(pct_pnls)
        variance = sum((x - mean_pct) ** 2 for x in pct_pnls) / len(pct_pnls)
        stdev = math.sqrt(variance)
        sharpe_ratio = mean_pct / (stdev + 1e-6) if stdev > 0 else 1.0
    else:
        sharpe_ratio = 1.0

    # Pre-build unified combined trades (merging explicit trades with fills/trades from activity)
    combined_trades = list(trades or [])
    seen_trade_sigs = set()
    for t in combined_trades:
        if isinstance(t, dict):
            sig = (
                str(t.get("id") or t.get("transactionHash") or ""),
                str(t.get("timestamp") or t.get("time") or ""),
                str(t.get("asset") or t.get("conditionId") or ""),
                str(t.get("side") or "").upper(),
                float(t.get("size") or 0.0)
            )
            seen_trade_sigs.add(sig)

    for act in list(activity or []):
        if isinstance(act, dict):
            act_type = str(act.get("type") or "").upper()
            act_side = str(act.get("side") or "").upper()
            if act_type in ("TRADE", "BUY", "SELL") or act_side in ("BUY", "SELL"):
                sig = (
                    str(act.get("id") or act.get("transactionHash") or ""),
                    str(act.get("timestamp") or act.get("time") or ""),
                    str(act.get("asset") or act.get("conditionId") or ""),
                    act_side or act_type,
                    float(act.get("size") or 0.0)
                )
                if sig not in seen_trade_sigs:
                    seen_trade_sigs.add(sig)
                    combined_trades.append(act)

    # 5. Track Record Length (Lifetime Trades, Active Days, & Recency)
    all_ts = []
    for item in list(combined_trades) + list(positions or []) + list(closed_positions or []):
        if isinstance(item, dict):
            raw_t = item.get("timestamp") or item.get("time") or item.get("createdAt") or item.get("updatedAt")
            if raw_t:
                try:
                    if isinstance(raw_t, (int, float)):
                        ts_val = float(raw_t) / 1000.0 if float(raw_t) > 1e11 else float(raw_t)
                    elif isinstance(raw_t, str):
                        try:
                            val = float(raw_t)
                            ts_val = val / 1000.0 if val > 1e11 else val
                        except ValueError:
                            clean_s = raw_t.replace("Z", "+00:00")
                            ts_val = datetime.fromisoformat(clean_s).timestamp()
                    else:
                        ts_val = 0.0
                    if ts_val > 1e8:
                        all_ts.append(ts_val)
                except Exception:
                    pass

    now_sec = time.time()
    if all_ts:
        min_ts = min(all_ts)
        max_ts = max(all_ts)
        ref_now = now_sec
        active_days = max(1.0, (max_ts - min_ts) / 86400.0)
        days_since_last_trade = max(0.0, (ref_now - max_ts) / 86400.0)
        is_inactive_7d = bool(days_since_last_trade > 7.0)
    else:
        active_days = 60.0
        days_since_last_trade = 999.0
        is_inactive_7d = True

    total_trade_count = max(len(combined_trades), len(positions or []), len(activity or []), len(closed_positions or []), 0)
    trades_per_day = round(total_trade_count / active_days, 1)
    is_hft = bool(trades_per_day > 50.0)

    # Gate 8: Boundary-Certainty Screen (Spec v2: Tiered bands, no single cliff)
    # Band 1: Price <= 0.03 or >= 0.97: <= 5% of total volume
    # Band 2: Price <= 0.10 or >= 0.90: <= 20% of total volume
    # Band 3: Price <= 0.20 or >= 0.80: <= 40% of total volume
    is_boundary_arb = False
    vol_total_buy = 0.0
    vol_band_03_97 = 0.0
    vol_band_10_90 = 0.0
    vol_band_20_80 = 0.0

    for t in combined_trades:
        if isinstance(t, dict):
            t_side = str(t.get("side") or t.get("maker_direction") or t.get("type") or "").upper()
            t_price = float(t.get("price") or 0.0)
            t_size = float(t.get("usdcSize") or t.get("size") or 0.0)
            t_vol = t_size * (t_price if t_price > 0 else 1.0) if not t.get("usdcSize") else t_size
            if t_vol <= 0:
                t_vol = float(t.get("size") or 0.0)
            if t_side == "BUY" and t_vol > 0 and 0.0 < t_price <= 1.0:
                vol_total_buy += t_vol
                if t_price <= 0.03 or t_price >= 0.97:
                    vol_band_03_97 += t_vol
                if t_price <= 0.10 or t_price >= 0.90:
                    vol_band_10_90 += t_vol
                if t_price <= 0.20 or t_price >= 0.80:
                    vol_band_20_80 += t_vol

    ratio_03_97 = round(vol_band_03_97 / vol_total_buy, 3) if vol_total_buy > 0 else 0.0
    ratio_10_90 = round(vol_band_10_90 / vol_total_buy, 3) if vol_total_buy > 0 else 0.0
    ratio_20_80 = round(vol_band_20_80 / vol_total_buy, 3) if vol_total_buy > 0 else 0.0
    boundary_ratio = max(ratio_03_97, ratio_10_90, ratio_20_80)

    if vol_total_buy > 0:
        if ratio_03_97 > 0.05 or ratio_10_90 > 0.20 or ratio_20_80 > 0.40:
            is_boundary_arb = True

    # 6. Trade Size Compatibility with Sleeve (Median usdcSize)
    trade_sizes = []
    for t in combined_trades:
        if isinstance(t, dict):
            s_val = float(t["usdcSize"]) if t.get("usdcSize") is not None else float(t.get("size") or 0) * float(t.get("price") or 0)
            if s_val > 0:
                trade_sizes.append(s_val)

    trade_sizes.sort()
    if trade_sizes:
        mid_idx = len(trade_sizes) // 2
        median_trade_size = trade_sizes[mid_idx]
    else:
        median_trade_size = 150.0

    is_sleeve_incompatible = bool(median_trade_size < 20.0 or median_trade_size > 3000.0)

    # 7. Wash-Trading / Round-Trip Pair Check (<120s BUY<->SELL pairs)
    wash_pair_count = 0
    trade_list_sorted = sorted(combined_trades, key=lambda x: float(x.get("timestamp") or x.get("time") or 0) if isinstance(x, dict) else 0)
    for i in range(len(trade_list_sorted) - 1):
        t1 = trade_list_sorted[i]
        t2 = trade_list_sorted[i+1]
        cid1 = t1.get("conditionId") or t1.get("asset")
        cid2 = t2.get("conditionId") or t2.get("asset")
        side1 = str(t1.get("side") or "").upper()
        side2 = str(t2.get("side") or "").upper()
        ts1 = float(t1.get("timestamp") or 0) / 1000.0 if float(t1.get("timestamp") or 0) > 1e11 else float(t1.get("timestamp") or 0)
        ts2 = float(t2.get("timestamp") or 0) / 1000.0 if float(t2.get("timestamp") or 0) > 1e11 else float(t2.get("timestamp") or 0)
        
        if cid1 and cid1 == cid2 and side1 != side2 and 0 <= (ts2 - ts1) <= 120:
            wash_pair_count += 1

    wash_ratio = round(wash_pair_count / max(1, len(combined_trades)), 3)
    is_wash_trading = bool(wash_ratio > 0.10 and wash_pair_count >= 2)

    # Profile observations are the only permitted chart/consistency source.
    from app.discovery.pnl_history import verified_history
    daily_pnl_history = list(pnl_history or [])
    history_verified = verified_history(daily_pnl_history)
    if not history_verified:
        daily_pnl_history = []
    final_cum_pnl = daily_pnl_history[-1]["cumulative_pnl"] if daily_pnl_history else 0.0

    # Calculate active unrealized paper loss/gain on open positions
    open_positions = [
        p for p in (positions or []) 
        if isinstance(p, dict) 
        and float(p.get("size") or 0.0) > 0 
        and not p.get("closed") 
        and not p.get("redeemable") 

    ]
    unrealized_open_pnl = sum(
        float(p.get("currentValue", float(p.get("size") or 0) * float(p.get("curPrice") or 0)))
        - float(p.get("size") or 0) * float(p["avgPrice"])
        if p.get("avgPrice") is not None and (p.get("currentValue") is not None or p.get("curPrice") is not None)
        else float(p.get("cashPnl") or 0)
        for p in open_positions)

    # Recency EMA over realized PnL series (30-day half-life decay)
    recency_ema = 0.0
    alpha_30d = 1.0 - math.exp(-math.log(2) / 30.0) # ~0.0228
    for h in daily_pnl_history:
        net_d = float(h.get("daily_pnl") or 0.0)
        recency_ema = (1.0 - alpha_30d) * recency_ema + alpha_30d * net_d

    # Maximum Drawdown
    peak_equity = 0.0
    running_equity = 0.0
    max_dd_dollars = 0.0
    for h in daily_pnl_history:
        running_equity = h["cumulative_pnl"]
        if running_equity > peak_equity:
            peak_equity = running_equity
        drawdown_curr = peak_equity - running_equity
        if drawdown_curr > max_dd_dollars:
            max_dd_dollars = drawdown_curr

    if peak_equity > 0 and max_dd_dollars > 0:
        max_drawdown = round((max_dd_dollars / peak_equity) * 100.0, 1)
    else:
        max_drawdown = 8.0 if not daily_pnl_history else 0.0

    # 9. Category Breadth
    all_categories = set()
    category_keywords = {
        "Sports": ["vs", "fc", "win on", "cup", "league", "match", "tournament"],
        "Politics": ["election", "president", "senate", "house", "party", "vote"],
        "Culture & Tech": ["ai", "temperature", "highest", "lowest", "gta", "movie", "box office"],
        "Macro & Finance": ["fed", "rate", "inflation", "cpi", "gdp", "recession"]
    }
    for p in closed_positions:
        t = str(p.get("title") or p.get("question") or "").lower()
        for cat_name, kw_list in category_keywords.items():
            if any(k in t for k in kw_list):
                all_categories.add(cat_name)

    category_count = max(1, len(all_categories))

    # 10. Conflicting Positions Detection (Mutually exclusive opposing legs)
    # Detects wallets buying both Yes and No / Up and Down or conflicting outcome legs on the same market/event
    market_buys: Dict[str, Set[str]] = {}
    market_sides: Dict[str, Set[str]] = {}
    market_trade_vol: Dict[str, float] = {}

    for t in list(combined_trades):
        if not isinstance(t, dict):
            continue
        side = str(t.get("side") or t.get("maker_direction") or t.get("type") or "").upper()
        if side == "BUY":
            cid = str(t.get("conditionId") or t.get("market_id") or "")
            asset = str(t.get("asset") or t.get("nonusdc_side") or t.get("asset_id") or "")
            outcome = str(t.get("outcome") or "").upper()
            outcome_idx = t.get("outcomeIndex")
            sz = float(t.get("usdcSize") or t.get("usd_amount") or (float(t.get("size") or 0) * float(t.get("price") or 0.5)))

            if cid:
                market_buys.setdefault(cid, set())
                if asset:
                    market_buys[cid].add(asset)
                market_sides.setdefault(cid, set())
                if outcome in ("YES", "NO", "UP", "DOWN"):
                    market_sides[cid].add(outcome)
                elif outcome_idx is not None and str(outcome_idx) in ("0", "1"):
                    market_sides[cid].add("YES" if str(outcome_idx) == "0" else "NO")
                elif outcome:
                    market_sides[cid].add(outcome)
                market_trade_vol[cid] = market_trade_vol.get(cid, 0.0) + sz

    for p in list(positions or []):
        if not isinstance(p, dict):
            continue
        cid = str(p.get("conditionId") or "")
        asset = str(p.get("asset") or "")
        outcome = str(p.get("outcome") or "").upper()
        outcome_idx = p.get("outcomeIndex")
        pos_size = float(p.get("size") or 0.0)
        pos_val = float(p.get("currentValue") or (pos_size * float(p.get("avgPrice") or 0.5)))

        if cid and pos_size > 0:
            market_buys.setdefault(cid, set())
            if asset:
                market_buys[cid].add(asset)
            market_sides.setdefault(cid, set())
            if outcome in ("YES", "NO", "UP", "DOWN"):
                market_sides[cid].add(outcome)
            elif outcome_idx is not None and str(outcome_idx) in ("0", "1"):
                market_sides[cid].add("YES" if str(outcome_idx) == "0" else "NO")
            elif outcome:
                market_sides[cid].add(outcome)
            market_trade_vol[cid] = market_trade_vol.get(cid, 0.0) + pos_val

    conflicting_markets = set()
    for cid, assets in market_buys.items():
        if len(assets) > 1:
            conflicting_markets.add(cid)
    for cid, sides in market_sides.items():
        if ("YES" in sides and "NO" in sides) or ("UP" in sides and "DOWN" in sides) or len(sides) > 1:
            conflicting_markets.add(cid)

    total_markets_traded = max(len(market_buys), len(market_sides), 1)
    conflicting_markets_count = len(conflicting_markets)
    conflicting_ratio = round(conflicting_markets_count / total_markets_traded, 3)

    conflicting_vol = sum(market_trade_vol.get(cid, 0.0) for cid in conflicting_markets)
    total_vol_calc = sum(market_trade_vol.values()) or 1.0
    conflicting_vol_ratio = round(conflicting_vol / total_vol_calc, 3)

    # Check concurrent opposing open positions with heavy paper losses
    open_conflicts = 0
    open_conflict_unrealized_loss = 0.0
    open_by_cid: Dict[str, Set[str]] = {}
    for p in (positions or []):
        if isinstance(p, dict) and float(p.get("size") or 0.0) > 0 and not p.get("closed"):
            p_cid = str(p.get("conditionId") or "")
            p_out = str(p.get("outcome") or "").upper()
            if p_cid:
                open_by_cid.setdefault(p_cid, set())
                if p_out:
                    open_by_cid[p_cid].add(p_out)
                if float(p.get("cashPnl") or 0.0) < 0:
                    open_conflict_unrealized_loss += abs(float(p.get("cashPnl") or 0.0))

    for p_cid, p_outs in open_by_cid.items():
        if ("YES" in p_outs and "NO" in p_outs) or ("UP" in p_outs and "DOWN" in p_outs) or len(p_outs) > 1:
            open_conflicts += 1

    has_opposing_buys = any(
        ("YES" in sides and "NO" in sides) or 
        ("UP" in sides and "DOWN" in sides) or 
        len(sides) > 1 
        for sides in market_sides.values()
    )
    is_conflicting_positions = bool(
        conflicting_markets_count >= 1 or
        has_opposing_buys or
        (open_conflicts >= 1 and open_conflict_unrealized_loss > 10000.0)
    )

    # 11. Consistency Curve Algorithm (Lucky vs Sniper Curve)
    cum_series = [float(h["cumulative_pnl"]) for h in daily_pnl_history]
    daily_pnls = [float(h["daily_pnl"]) for h in daily_pnl_history if h.get("daily_pnl") is not None]
    T = len(cum_series)

    beta = 0.0
    R_squared = 0.0
    if T >= 2:
        x = list(range(1, T + 1))
        x_bar = (T + 1) / 2.0
        c_bar = sum(cum_series) / float(T)
        S_xx = sum((x[i] - x_bar) ** 2 for i in range(T))
        S_xc = sum((x[i] - x_bar) * (cum_series[i] - c_bar) for i in range(T))
        S_cc = sum((cum_series[i] - c_bar) ** 2 for i in range(T))
        if S_xx > 0:
            beta = S_xc / S_xx
        if S_xx > 0 and S_cc > 0:
            R_squared = max(0.0, min(1.0, (S_xc ** 2) / (S_xx * S_cc)))

    # Gate 10: Anti-Stale-Plateau Screen (Spec v2: Trailing 90-day realized PnL >= 35% of total PnL)
    is_stale_plateau = False
    trailing_90d_pnl = 0.0
    trailing_90d_daily_pnls = []
    if daily_pnl_history:
        dates = [h.get("date") for h in daily_pnl_history if h.get("date")]
        latest_d_str = max(dates) if dates else datetime.utcnow().strftime("%Y-%m-%d")
        try:
            latest_dt = datetime.utcnow()
        except Exception:
            latest_dt = datetime.utcnow()
        cutoff_str = (latest_dt - timedelta(days=90)).strftime("%Y-%m-%d")

        for h in daily_pnl_history:
            d_str = str(h.get("date") or "")
            if d_str >= cutoff_str:
                val = float(h.get("daily_pnl") or h.get("net_pnl") or 0.0)
                trailing_90d_pnl += val
                trailing_90d_daily_pnls.append(val)

        if all_time_pnl > 0.0:
            if trailing_90d_pnl < 0.35 * all_time_pnl:
                is_stale_plateau = True
        elif T >= 2:
            mid = T // 2
            if sum(daily_pnls[mid:]) <= 0.0 and sum(daily_pnls[:mid]) > 0:
                is_stale_plateau = True

    # Gate 11: Consistency Gate on Period Returns (Spec v2: Trailing-90-day Sharpe > 1.0 on period returns)
    trailing_90d_sharpe = 0.0
    period_series = trailing_90d_daily_pnls
    if len(period_series) >= 3:
        m_period = sum(period_series) / len(period_series)
        v_period = sum((p - m_period) ** 2 for p in period_series) / len(period_series)
        s_period = math.sqrt(v_period)
        trailing_90d_sharpe = round(m_period / (s_period + 1e-6), 3) if s_period > 0 else (2.0 if m_period > 0 else 0.0)
    else:
        trailing_90d_sharpe = 0.0

    is_period_inconsistent = bool(len(period_series) >= 5 and trailing_90d_sharpe <= 1.0)

    # Roller-Coaster Gambler Detection: Peak-to-trough drawdown > 25% or high variance
    is_roller_coaster = bool(max_drawdown > 25.0)
    if not is_roller_coaster and len(daily_pnls) >= 3:
        mean_p = sum(daily_pnls) / len(daily_pnls)
        var_p = sum((p - mean_p) ** 2 for p in daily_pnls) / len(daily_pnls)
        std_p = math.sqrt(var_p)
        if mean_p > 0 and (std_p / mean_p > 4.0) and max_drawdown > 18.0:
            is_roller_coaster = True

    # Step-jump artifacts and one-hit-wonder profiles
    pos_daily = [h["daily_pnl"] for h in daily_pnl_history if (h.get("daily_pnl") or 0) > 0]
    total_pos_pnl = sum(pos_daily)
    max_single_day_pnl = max(pos_daily, default=0.0)
    top_2_days_pnl = sum(sorted(pos_daily, reverse=True)[:2]) if len(pos_daily) >= 2 else max_single_day_pnl

    max_single_day_pnl_ratio = round(max_single_day_pnl / total_pos_pnl, 3) if total_pos_pnl > 0 else 0.0
    top_2_days_pnl_ratio = round(top_2_days_pnl / total_pos_pnl, 3) if total_pos_pnl > 0 else 0.0

    active_pnl_days = len(daily_pnl_history)
    profitable_days_count = len(pos_daily)
    profit_day_consistency = round(profitable_days_count / max(1, active_pnl_days), 3)

    step_jump = bool(
        active_pnl_days >= 3 and (
            (max_single_day_pnl_ratio > 0.60 and total_pos_pnl > 10000.0) or
            (top_2_days_pnl_ratio > 0.80 and active_pnl_days >= 5 and total_pos_pnl > 10000.0)
        )
    )

    # Combined flag for inconsistent / deceptive profiles
    is_inconsistent_profile = bool(
        is_stale_plateau or
        is_roller_coaster or
        step_jump or
        is_period_inconsistent
    )

    # Primary category extraction for Gate 13 concentration capping
    from app.services.polymarket_fees import classify_market_category
    cat_counts: Dict[str, int] = {}
    for t in combined_trades:
        q = str(t.get("title") or t.get("market") or t.get("market_question") or "")
        if q:
            c_name, _ = classify_market_category(q)
            cat_counts[c_name] = cat_counts.get(c_name, 0) + 1
    for p in (closed_positions or []):
        q = str(p.get("title") or p.get("market") or "")
        if q:
            c_name, _ = classify_market_category(q)
            cat_counts[c_name] = cat_counts.get(c_name, 0) + 1
    primary_category = max(cat_counts.items(), key=lambda x: x[1])[0] if cat_counts else "General"

    step_penalty = max(0.0, (max_single_day_pnl_ratio - 0.20) * 50.0)
    sharpe_component = min(40.0, max(0.0, sharpe_ratio * 20.0))
    winrate_component = min(30.0, (win_rate / 100.0) * 30.0)
    breadth_component = min(30.0, profit_day_consistency * 30.0)
    raw_consistency = sharpe_component + winrate_component + breadth_component - step_penalty
    consistency_score = round(max(0.0, min(100.0, raw_consistency)), 1)

    return {
        "all_time_pnl_usd": round(all_time_pnl, 2),
        "total_volume_usd": round(total_volume, 2),
        "cumulative_pnl": round(final_cum_pnl, 2),
        "unrealized_open_pnl": round(unrealized_open_pnl, 2),
        "win_rate_pct": win_rate,
        "resolved_positions_count": total_resolved,
        "profit_factor": profit_factor,
        "gross_wins": gross_wins,
        "gross_losses": gross_losses,
        "expectancy_usd": (gross_wins - gross_losses) / max(1, total_resolved),
        "history_verified": history_verified,
        "profile_verified": official_pnl is not None,
        "settled_data_complete": settled_data_complete,
        "has_no_history": not history_verified,
        "wilson_lower_bound": wilson_lb,
        "trades_count": total_trade_count,
        "active_days": round(active_days, 1),
        "avg_trades_per_day": trades_per_day,
        "trades_per_day": trades_per_day,
        "is_inactive_7d": is_inactive_7d,
        "days_since_last_trade": round(days_since_last_trade, 2),
        "max_drawdown_pct": max_drawdown,
        "outlier_concentration_pct": outlier_concentration,
        "is_hft": is_hft,
        "is_dormant": False,
        "is_wash_trading": is_wash_trading,
        "wash_ratio": wash_ratio,
        "median_trade_size": round(median_trade_size, 2),
        "min_capital_required": round(max(50.0, min(1000.0, 1.0 / (max(5.0, median_trade_size) / max(1000.0, all_time_pnl)))), 2) if all_time_pnl > 0 else 100.0,
        "is_sleeve_incompatible": is_sleeve_incompatible,
        "odds_weighted_edge": round(odds_weighted_edge, 4),
        "avg_entry_price": round(avg_entry_price, 4),
        "sharpe_ratio": round(sharpe_ratio, 3),
        "recency_ema": round(recency_ema, 2),
        "trailing_90d_sharpe": trailing_90d_sharpe,
        "trailing_90d_pnl": round(trailing_90d_pnl, 2),
        "primary_category": primary_category,
        "category_count": category_count,
        "daily_pnl_history": daily_pnl_history,
        "first_trade_at": datetime.fromtimestamp(min_ts, timezone.utc).replace(tzinfo=None) if all_ts else None,
        "last_trade_at": datetime.fromtimestamp(max_ts, timezone.utc).replace(tzinfo=None) if all_ts else None,
        "is_conflicting_positions": is_conflicting_positions,
        "conflicting_ratio": conflicting_ratio,
        "conflicting_markets_count": conflicting_markets_count,
        "is_boundary_arb": is_boundary_arb,
        "boundary_ratio": boundary_ratio,
        "is_stale_plateau": is_stale_plateau,
        "is_roller_coaster": is_roller_coaster,
        "is_inconsistent_profile": is_inconsistent_profile,
        "max_single_day_pnl_ratio": max_single_day_pnl_ratio,
        "beta": round(beta, 4),
        "r_squared": round(R_squared, 4),
        "ols_slope": round(beta, 4),
        "ols_r2": round(R_squared, 4),
        "t_days": T,
        "consistency_score": consistency_score,
    }

async def evaluate_pending_wallets(db: AsyncSession, client: Optional[PolymarketClient] = None):
    """
    Stage 2: Deep evaluation of candidate wallets.
    Fetches multi-page trades + redemptions and verifies real all-time Polymarket PnL.
    """
    stmt = select(Wallet).where(Wallet.status == "pending")
    pending_wallets = (await db.execute(stmt)).scalars().all()
    
    if not pending_wallets:
        return 0

    client = client or PolymarketClient()
    total_pending = len(pending_wallets)
    logger.info(f"Stage 2: Starting deep audit of {total_pending} pending candidate wallets...")
    
    active_cnt = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == "active"))).scalar() or 0
    gold_cnt = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == "active", Wallet.tier == "gold_sniper"))).scalar() or 0

    discovery_state["status"] = "running"
    discovery_state["total_candidates"] = total_pending
    discovery_state["wallets_scanned"] = 0
    discovery_state["rejected"] = 0
    discovery_state["active_whales_in_basket"] = active_cnt
    discovery_state["gold_snipers"] = gold_cnt
    discovery_state["step_description"] = "Deep auditing candidate whale trade histories..."

    processed_count = 0
    try:
        for idx, wallet in enumerate(pending_wallets, 1):
            addr = wallet.address.lower()
            discovery_state["wallets_scanned"] = idx
            discovery_state["progress_pct"] = int((idx / total_pending) * 100)
            discovery_state["step_description"] = f"Deep evaluation {addr[:6]}...{addr[-4:]} ({idx}/{total_pending})"
            
            try:
                tasks = [
                    client.fetch_wallet_positions(addr),
                    client.fetch_wallet_activity(addr, max_items=4000),
                    client.fetch_wallet_profile(addr),
                    client.fetch_wallet_trades(addr, max_trades=4000),
                ]
                has_closed_fn = hasattr(client, "fetch_wallet_closed_positions")
                if has_closed_fn:
                    try:
                        closed_call = client.fetch_wallet_closed_positions(addr, max_items=4000)
                        if inspect.isawaitable(closed_call):
                            tasks.append(closed_call)
                    except Exception:
                        pass

                tasks.append(client.fetch_wallet_pnl(addr))
                results = await asyncio.gather(*tasks, return_exceptions=True)
                coverage_errors = [result for result in results if isinstance(result, Exception)]
                if coverage_errors:
                    # Empty fallbacks are unsafe here: a partial provider page
                    # must never look like a clean zero-history wallet.
                    open_stmt = select(ExecutionLog.id).where(
                        ExecutionLog.source_wallet_address.ilike(addr),
                        ExecutionLog.side == "BUY",
                        ExecutionLog.status == "FILLED",
                    ).limit(1)
                    has_open_position = (await db.execute(open_stmt)).scalar_one_or_none() is not None
                    wallet.status = "tracked" if has_open_position else "rejected"
                    wallet.tier = wallet.tier if has_open_position else "rejected"
                    wallet.rejection_reason = (
                        "Insufficient provider coverage; candidate remains unvalidated"
                        + (f": {coverage_errors[0]}" if coverage_errors else "")
                    )
                    wallet.cached_daily_pnl = None
                    wallet.baleen_score = None
                    discovery_state["rejected"] += 1
                    await db.commit()
                    processed_count += 1
                    continue

                raw_positions = results[0] if not isinstance(results[0], Exception) else []
                raw_activity = results[1] if not isinstance(results[1], Exception) else []
                raw_profile = results[2] if not isinstance(results[2], Exception) else {}
                raw_trades = results[3] if not isinstance(results[3], Exception) else []
                raw_closed = results[4] if len(results) > 4 and not isinstance(results[4], Exception) else []
                
                stats = calculate_authentic_wallet_stats(
                    address=addr,
                    positions=raw_positions,
                    activity=raw_activity,
                    profile=raw_profile,
                    trades=raw_trades,
                    closed_positions=raw_closed,
                    pnl_history=results[-1]
                )
                
                if stats['daily_pnl_history']:
                    stats['daily_pnl_history'][0]['assessment'] = {k: v for k, v in stats.items()
                        if k not in {'daily_pnl_history', 'first_trade_at', 'last_trade_at'}}
                baleen_score = compute_baleen_score(stats)
                
                # Score wallet
                scoring = score_wallet(stats)
                is_valid = scoring.status == "active"
                reason = scoring.rejection_reason
                if not is_valid:
                    wallet.status = 'rejected'
                    wallet.tier = 'rejected'
                    wallet.rejection_reason = reason
                    discovery_state["rejected"] += 1
                else:
                    wallet.status = 'active'
                    wallet.tier = scoring.tier
                    wallet.rejection_reason = None
                    discovery_state["active_whales_in_basket"] += 1
                    if scoring.tier == 'gold_sniper':
                        discovery_state["gold_snipers"] += 1

                # Auto-generate AI summary
                try:
                    ai_summary, ai_style_tag = await generate_summary(stats)
                    wallet.ai_summary = ai_summary
                    wallet.ai_style_tag = stats.get('primary_category') or ai_style_tag or "General"
                except Exception:
                    wallet.ai_summary = f"Institutional Polymarket trader with ${stats['all_time_pnl_usd']:,.0f} all-time PnL and {stats['win_rate_pct']}% win rate."
                    wallet.ai_style_tag = stats.get('primary_category') or "General"
                    
                wallet.all_time_pnl_usd = stats.get('all_time_pnl_usd', 0.0)
                wallet.win_rate_pct = stats.get('win_rate_pct', 70.0)
                wallet.total_trades_analyzed = stats.get('trades_count', 1)
                wallet.avg_trades_per_day = stats.get('avg_trades_per_day', 5.0)
                wallet.median_inter_trade_gap_hours = round(24.0 / max(stats.get('avg_trades_per_day', 1.0), 1.0), 1)
                wallet.max_drawdown_pct = stats.get('max_drawdown_pct', 10.0)
                wallet.outlier_concentration_pct = stats.get('outlier_concentration_pct', 0.14)
                wallet.baleen_score = baleen_score
                wallet.dormant = stats.get('is_dormant', False)
                wallet.is_hft = stats.get('is_hft', False)
                wallet.trades_per_hour = stats["trades_per_day"] / 24.0
                wallet.wilson_lb = stats.get('wilson_lower_bound', 65.0)
                wallet.alpha_per_trade = stats.get("expectancy_usd")
                wallet.profit_factor = stats.get('profit_factor')
                wallet.first_trade_at = stats.get('first_trade_at')
                wallet.last_trade_at = stats.get('last_trade_at')
                wallet.cached_daily_pnl = json.dumps(stats.get('daily_pnl_history', [])) if stats.get('daily_pnl_history') else None
                wallet.last_scored_at = datetime.utcnow()
                if raw_profile and isinstance(raw_profile, dict):
                    p_name = raw_profile.get("userName") or raw_profile.get("name") or ""
                    p_pseudo = raw_profile.get("pseudonym") or ""
                    p_img = raw_profile.get("profileImage") or ""
                    if p_name:
                        wallet.name = str(p_name)
                    if p_pseudo:
                        wallet.pseudonym = str(p_pseudo)
                    if p_img:
                        wallet.profile_image = str(p_img)
                    if p_name and not wallet.ai_style_tag:
                        wallet.ai_style_tag = str(p_name)
                
                # Event logging for wallet promotion / rejection
                if wallet.status == 'active':
                    asyncio.create_task(log_event(
                        "WALLET_PROMOTED",
                        f"Wallet promoted: {wallet.name or wallet.pseudonym or wallet.address[:12]}",
                        detail=f"Score: {wallet.baleen_score}, WR: {wallet.win_rate_pct}%, PnL: ${wallet.all_time_pnl_usd:,.0f}. Tier: {wallet.tier}.",
                        severity="success",
                        related_address=wallet.address,
                    ))
                elif wallet.status == 'rejected':
                    pnl = stats.get('all_time_pnl_usd', 0.0) or 0.0
                    win_rate = stats.get('win_rate_pct', 0.0) or 0.0
                    asyncio.create_task(log_event(
                        "WALLET_REJECTED",
                        f"Wallet rejected: {wallet.name or wallet.pseudonym or wallet.address[:12]}",
                        detail=f"Reason: {wallet.rejection_reason}. PnL: ${pnl:,.0f}, WR: {win_rate:.1f}%.",
                        severity="warning",
                        related_address=wallet.address,
                    ))

                await db.commit()
                processed_count += 1
                await asyncio.sleep(0.04)
                
            except Exception as e:
                logger.warning(f"Failed to evaluate candidate {addr}: {e}")
                await db.rollback()

    finally:
        await client.close()
        discovery_state["status"] = "completed"
        discovery_state["step_description"] = f"Evaluation complete. {discovery_state['active_whales_in_basket']} active whales in basket."
    
    return processed_count

async def scan_for_wallets(db: AsyncSession, full_refresh: bool = False):
    """
    Titan Engine Autonomous Discovery & Evaluation System
    """
    global discovery_state
    
    active_cnt = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == "active"))).scalar() or 0
    gold_cnt = (await db.execute(select(func.count()).select_from(Wallet).where(Wallet.status == "active", Wallet.tier == "gold_sniper"))).scalar() or 0
    
    discovery_state["status"] = "running"
    discovery_state["progress_pct"] = 5
    discovery_state["step_description"] = "Connecting to Polymarket Leaderboard & Trade APIs..."
    discovery_state["wallets_scanned"] = 0
    discovery_state["active_whales_in_basket"] = active_cnt
    discovery_state["gold_snipers"] = gold_cnt
    discovery_state["started_at"] = time.time()
    discovery_state["error_message"] = None
    
    client = PolymarketClient()
    processed_count = 0
    
    try:
        if full_refresh:
            # A refresh is a rescore pass. Preserve wallet identities, score
            # history, and any positions keyed to those identities while new
            # provider evidence is collected below.
            discovery_state["step_description"] = "Refreshing candidate evidence without deleting tracked wallets..."
            logger.info("Starting nondestructive wallet refresh; existing wallets and snapshots are retained.")

        discovery_state["progress_pct"] = 15
        discovery_state["step_description"] = "Stage 1: Multi-Period Leaderboard & Trade Scraping..."
        
        candidates = await client.discover_candidates()
        
        # Merge curated verified whale addresses from previous run as high-priority seeds
        from app.discovery.curated_whales import CURATED_WHALE_ADDRESSES
        for seed_addr in CURATED_WHALE_ADDRESSES:
            s_clean = seed_addr.lower().strip()
            if s_clean not in candidates:
                candidates[s_clean] = {
                    "address": s_clean,
                    "source": "curated_seed"
                }

        total_candidates = len(candidates)
        logger.info(f"Discovered {total_candidates} candidate addresses (including {len(CURATED_WHALE_ADDRESSES)} curated seeds).")
        
        if not candidates:
            discovery_state["step_description"] = "Polymarket API returned 0 candidates. Retrying..."
            discovery_state["status"] = "completed"
            return 0

        # STAGE 1: Save all discovered candidates as pending
        saved_count = 0
        for idx, (addr, meta) in enumerate(candidates.items(), 1):
            discovery_state["progress_pct"] = min(50, 15 + int((idx / max(1, total_candidates)) * 35))
            
            stmt = select(Wallet).where(Wallet.address == addr)
            wallet = (await db.execute(stmt)).scalar_one_or_none()
            if not wallet:
                wallet = Wallet(
                    address=addr,
                    status="pending",
                    all_time_pnl_usd=None,
                    first_seen_at=datetime.utcnow()
                )
                db.add(wallet)
                saved_count += 1
            else:
                if full_refresh:
                    wallet.status = "pending"

        await db.commit()
        discovery_state["step_description"] = f"Stage 1 Complete. Ingested {saved_count} whale candidates."
        await asyncio.sleep(0.5)

    except Exception as general_err:
        logger.error(f"Error during Stage 1 discovery: {general_err}", exc_info=True)
        discovery_state["status"] = "error"
        discovery_state["error_message"] = str(general_err)
    finally:
        await client.close()
        
    # STAGE 2: Deep Evaluation
    if discovery_state["status"] != "error":
        try:
            discovery_state["step_description"] = "Stage 2: Deep multi-page trade audit..."
            processed_count = await evaluate_pending_wallets(db)
            
            # Post-Evaluation: Deduplicated Live Tape Sync
            stmt = select(Wallet).where(Wallet.status == 'active').order_by(Wallet.last_scored_at.desc()).limit(10)
            active_wallets = (await db.execute(stmt)).scalars().all()
            discovery_state["progress_pct"] = 95
            discovery_state["step_description"] = "Synchronizing live trade execution tape..."
            
            if active_wallets:
                pass
                    
            discovery_state["progress_pct"] = 100
            discovery_state["step_description"] = f"Complete: {discovery_state['active_whales_in_basket']} active whales ({discovery_state['gold_snipers']} Gold Snipers) audited."
            discovery_state["status"] = "completed"
            discovery_state["completed_at"] = time.time()
            await _persist_discovery_state(db)
        except Exception as e:
            logger.error(f"Error during Stage 2 deep evaluation: {e}", exc_info=True)
            discovery_state["status"] = "error"
            discovery_state["error_message"] = str(e)
            await _persist_discovery_state(db)

    logger.info(f"Evaluation complete. Processed {processed_count} wallets.")
    return processed_count


async def run_discovery_cycle(db: AsyncSession, full_refresh: bool = False) -> int:
    """
    Executes full discovery cycle: multi-period leaderboard scraping,
    4,000-item trade/activity/closed-positions audits, and strict quantitative scoring.
    """
    return await scan_for_wallets(db, full_refresh=full_refresh)

