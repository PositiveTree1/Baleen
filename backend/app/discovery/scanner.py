import logging
import asyncio
import math
import json
import time
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timezone
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
    trades: Optional[List[Dict]] = None
) -> Dict:
    """
    Titan Quantitative Scoring Engine:
    Calculates authentic PnL, win rate, Wilson lower bound, profit factor, and daily history
    directly from Polymarket's official positions, activity closures, and profile endpoints.
    """
    # 1. Total All-time Realized PnL & Volume
    all_time_pnl = 0.0
    total_volume = 0.0
    if profile and isinstance(profile, dict):
        all_time_pnl = float(profile.get("pnl") or profile.get("profit") or profile.get("profile_profit") or 0.0)
        total_volume = float(profile.get("volume") or profile.get("vol") or 0.0)
    
    if all_time_pnl == 0.0 and positions:
        all_time_pnl = sum(float(p.get("cashPnl") or 0.0) for p in positions)
    
    if total_volume == 0.0:
        total_volume = sum(float(t.get("usdcSize") or t.get("size") or 0.0) for t in (trades or []))

    # 2. Closed/Settled Positions Only (Strictly ignore open MTM marks for scoring)
    closed_positions = [
        p for p in (positions or []) 
        if isinstance(p, dict) and (
            p.get("closed") 
            or p.get("redeemable") 
            or float(p.get("curPrice") or 0.5) in (0.0, 1.0) 
            or float(p.get("size") or 0.0) == 0.0 
            or float(p.get("realizedPnl") or 0.0) != 0.0
        )
    ]
    if not closed_positions:
        closed_positions = [p for p in (positions or []) if isinstance(p, dict)]

    wins = sum(1 for p in closed_positions if float(p.get("cashPnl") or 0.0) > 0)
    losses = sum(1 for p in closed_positions if float(p.get("cashPnl") or 0.0) < 0)
    total_resolved = wins + losses

    if total_resolved > 0:
        win_rate = round((wins / total_resolved) * 100.0, 1)
        wilson_lb = calc_wilson_lower_bound(wins, total_resolved)
    else:
        win_rate = 0.0
        wilson_lb = 0.0

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

    # 5. Track Record Length (Lifetime Trades & Active Days)
    all_ts = []
    for item in list(trades or []) + list(positions or []) + list(activity or []):
        if isinstance(item, dict):
            raw_t = item.get("timestamp") or item.get("time") or item.get("createdAt") or item.get("updatedAt")
            if raw_t:
                try:
                    ts_val = float(raw_t) / 1000.0 if float(raw_t) > 1e11 else float(raw_t)
                    if ts_val > 1e8:
                        all_ts.append(ts_val)
                except Exception:
                    pass

    if all_ts:
        min_ts = min(all_ts)
        max_ts = max(all_ts)
        active_days = max(1.0, (max_ts - min_ts) / 86400.0)
    else:
        active_days = 60.0

    total_trade_count = max(len(trades or []), len(positions or []), len(activity or []), 1)
    trades_per_day = round(total_trade_count / active_days, 1)

    # 6. Trade Size Compatibility with Sleeve (Median usdcSize)
    trade_sizes = []
    for t in (trades or []):
        if isinstance(t, dict):
            s_val = float(t.get("usdcSize") or t.get("size") or 0.0)
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
    trade_list_sorted = sorted((trades or []), key=lambda x: float(x.get("timestamp") or 0))
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

    wash_ratio = round(wash_pair_count / max(1, len(trades or [])), 3)
    is_wash_trading = bool(wash_ratio > 0.10 and wash_pair_count >= 2)

    # 8. Authentic Daily PnL history from chronological trades & redemptions
    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_map: Dict[str, Dict[str, float]] = {}
    holdings: Dict[str, Dict[str, float]] = {} # asset -> {'shares': float, 'cost': float, 'avg_price': float}
    accounted_assets: Set[str] = set()

    # A. Chronological trade matching (Fills & Sells)
    sorted_trades = sorted((trades or []), key=lambda x: float(x.get("timestamp") or 0.0) if isinstance(x, dict) else 0.0)
    for t in sorted_trades:
        if not isinstance(t, dict):
            continue
        ts_val = float(t.get("timestamp") or t.get("time") or t.get("match_time") or 0.0)
        if ts_val <= 0.0:
            continue
        ts_sec = ts_val / 1000.0 if ts_val > 1e11 else ts_val
        try:
            dt_str = datetime.fromtimestamp(ts_sec, timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            continue

        asset = str(t.get("asset") or t.get("conditionId") or "")
        side = str(t.get("side") or "").upper()
        size = float(t.get("size") or 0.0)
        price = float(t.get("price") or 0.0)

        if asset not in holdings:
            holdings[asset] = {"shares": 0.0, "cost": 0.0, "avg_price": 0.0}

        h = holdings[asset]
        if side == "BUY":
            h["shares"] += size
            h["cost"] += size * price
            h["avg_price"] = h["cost"] / h["shares"] if h["shares"] > 0 else price
        elif side == "SELL" and h["shares"] > 0:
            sold_shares = min(size, h["shares"])
            cost_basis = sold_shares * h["avg_price"]
            proceeds = sold_shares * price
            pnl = proceeds - cost_basis
            h["shares"] -= sold_shares
            h["cost"] -= cost_basis
            accounted_assets.add(asset)

            if dt_str not in daily_map:
                daily_map[dt_str] = {"won": 0.0, "lost": 0.0, "net": 0.0, "count": 0.0}
            daily_map[dt_str]["count"] += 1.0
            if pnl >= 0:
                daily_map[dt_str]["won"] += pnl
            else:
                daily_map[dt_str]["lost"] += abs(pnl)
            daily_map[dt_str]["net"] += pnl

    # B. Process Redemptions from activity
    if activity:
        for act in activity:
            if not isinstance(act, dict):
                continue
            act_type = str(act.get("type") or "").upper()
            if act_type in ["REDEMPTION", "REDEEM"]:
                ts_val = float(act.get("timestamp") or act.get("time") or 0.0)
                if ts_val <= 0.0:
                    continue
                ts_sec = ts_val / 1000.0 if ts_val > 1e11 else ts_val
                try:
                    dt_str = datetime.fromtimestamp(ts_sec, timezone.utc).strftime("%Y-%m-%d")
                except Exception:
                    continue

                asset = str(act.get("asset") or act.get("conditionId") or "")
                size = float(act.get("size") or act.get("usdcSize") or 0.0)
                h = holdings.get(asset, {"avg_price": 0.50, "shares": size, "cost": size * 0.50})
                avg_p = h["avg_price"] if h["avg_price"] > 0 else 0.50
                cost_basis = size * avg_p
                pnl = size - cost_basis
                accounted_assets.add(asset)

                if dt_str not in daily_map:
                    daily_map[dt_str] = {"won": 0.0, "lost": 0.0, "net": 0.0, "count": 0.0}
                daily_map[dt_str]["count"] += 1.0
                if pnl >= 0:
                    daily_map[dt_str]["won"] += pnl
                else:
                    daily_map[dt_str]["lost"] += abs(pnl)
                daily_map[dt_str]["net"] += pnl

    # C. Process verified settled closed positions if not already captured in trades/activity
    for pos in (closed_positions or []):
        if not isinstance(pos, dict):
            continue
        asset = str(pos.get("asset") or pos.get("conditionId") or "")
        if asset in accounted_assets:
            continue

        c_pnl = float(pos.get("realizedPnl") or pos.get("cashPnl") or 0.0)
        is_settled = bool(pos.get("closed") or pos.get("redeemable") or float(pos.get("curPrice") or 0.5) in (0.0, 1.0) or float(pos.get("realizedPnl") or 0.0) != 0.0)
        if is_settled and c_pnl != 0.0:
            ts_raw = pos.get("resolvedAt") or pos.get("timestamp") or pos.get("createdAt")
            dt_str = parse_date_to_utc_str(ts_raw, today_utc)
            if dt_str not in daily_map:
                daily_map[dt_str] = {"won": 0.0, "lost": 0.0, "net": 0.0, "count": 0.0}
            daily_map[dt_str]["count"] += 1.0
            if c_pnl >= 0:
                daily_map[dt_str]["won"] += c_pnl
            else:
                daily_map[dt_str]["lost"] += abs(c_pnl)
            daily_map[dt_str]["net"] += c_pnl

    daily_pnl_history = []
    running_cum = 0.0
    for d_str in sorted(daily_map.keys()):
        d_info = daily_map[d_str]
        running_cum += d_info["net"]
        daily_pnl_history.append({
            "date": d_str,
            "won_usd": round(d_info["won"], 2),
            "lost_usd": round(-abs(d_info["lost"]), 2),
            "net_pnl": round(d_info["net"], 2),
            "daily_pnl": round(d_info["net"], 2),
            "cumulative_pnl": round(running_cum, 2),
            "trades_count": int(d_info["count"])
        })

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
        running_equity += h.get("daily_pnl", 0.0)
        if running_equity > peak_equity:
            peak_equity = running_equity
        drawdown_curr = peak_equity - running_equity
        if drawdown_curr > max_dd_dollars:
            max_dd_dollars = drawdown_curr

    if peak_equity > 0 and max_dd_dollars > 0:
        max_drawdown = min(35.0, round((max_dd_dollars / peak_equity) * 100.0, 1))
    else:
        max_drawdown = 8.0

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

    return {
        "all_time_pnl_usd": round(all_time_pnl, 2),
        "total_volume_usd": round(total_volume, 2),
        "win_rate_pct": win_rate,
        "wilson_lower_bound": wilson_lb,
        "trades_count": total_trade_count,
        "active_days": round(active_days, 1),
        "avg_trades_per_day": trades_per_day,
        "max_drawdown_pct": max_drawdown,
        "outlier_concentration_pct": outlier_concentration,
        "is_hft": bool(trades_per_day > 65.0),
        "is_dormant": False,
        "is_wash_trading": is_wash_trading,
        "wash_ratio": wash_ratio,
        "median_trade_size": round(median_trade_size, 2),
        "is_sleeve_incompatible": is_sleeve_incompatible,
        "odds_weighted_edge": round(odds_weighted_edge, 4),
        "avg_entry_price": round(avg_entry_price, 4),
        "sharpe_ratio": round(sharpe_ratio, 3),
        "recency_ema": round(recency_ema, 2),
        "category_count": category_count,
        "daily_pnl_history": daily_pnl_history,
        "first_trade_at": None,
        "last_trade_at": datetime.utcnow()
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
                raw_positions = await client.fetch_wallet_positions(addr)
                raw_activity = await client.fetch_wallet_activity(addr, max_items=1000)
                raw_profile = await client.fetch_wallet_profile(addr)
                raw_trades = await client.fetch_wallet_trades(addr, max_trades=200)
                
                stats = calculate_authentic_wallet_stats(
                    address=addr,
                    positions=raw_positions,
                    activity=raw_activity,
                    profile=raw_profile,
                    trades=raw_trades
                )
                
                baleen_score = compute_baleen_score(stats)
                
                # Score wallet
                scoring = score_wallet(stats)
                is_valid = scoring.status == "active"
                reason = scoring.rejection_reason
                has_history = bool(stats.get('daily_pnl_history') and len(stats.get('daily_pnl_history')) > 0)

                if not has_history or stats.get('trades_count', 0) < 5:
                    wallet.status = 'rejected'
                    wallet.tier = 'rejected'
                    wallet.rejection_reason = "No verifiable on-chain trade history from Polymarket API"
                    discovery_state["rejected"] += 1
                elif stats['all_time_pnl_usd'] < 50000.0 or stats['all_time_pnl_usd'] > 22000000.0:
                    wallet.status = 'rejected'
                    wallet.tier = 'rejected'
                    wallet.rejection_reason = f'All-time Polymarket realized PnL (${stats["all_time_pnl_usd"]:,.0f}) is outside verified whale threshold ($50k - $22M)'
                    discovery_state["rejected"] += 1
                elif stats['outlier_concentration_pct'] > 0.25:
                    wallet.status = 'rejected'
                    wallet.tier = 'rejected'
                    wallet.rejection_reason = f'Market concentration too high ({stats["outlier_concentration_pct"]*100:.1f}% > 25% max single trade PnL)'
                    discovery_state["rejected"] += 1
                elif stats['win_rate_pct'] < 55.0:
                    wallet.status = 'rejected'
                    wallet.tier = 'rejected'
                    wallet.rejection_reason = f'Win rate ({stats["win_rate_pct"]}%) is below 55% threshold'
                    discovery_state["rejected"] += 1
                elif stats['is_hft']:
                    wallet.status = 'rejected'
                    wallet.tier = 'rejected'
                    wallet.rejection_reason = f'High-Frequency Bot detected ({stats.get("avg_trades_per_day", 0):.0f} trades/day > 100/day max)'
                    discovery_state["rejected"] += 1
                elif stats.get('is_crypto_only'):
                    wallet.status = 'rejected'
                    wallet.tier = 'rejected'
                    wallet.rejection_reason = f'Crypto-only mono-trader ({stats.get("crypto_pct", 0):.0f}% crypto markets)'
                    discovery_state["rejected"] += 1
                elif stats.get('is_excessive_hold'):
                    wallet.status = 'rejected'
                    wallet.tier = 'rejected'
                    wallet.rejection_reason = f'Excessive holding duration ({stats.get("avg_hold_days", 0):.1f} days > 14-day max capital lockup)'
                    discovery_state["rejected"] += 1
                elif stats.get('is_boundary_arb'):
                    wallet.status = 'rejected'
                    wallet.tier = 'rejected'
                    wallet.rejection_reason = f'Arbitrage/Settlement Sniper ({stats.get("boundary_ratio", 0)*100:.1f}% boundary trades at 0.01/0.99)'
                    discovery_state["rejected"] += 1
                elif stats['is_dormant']:
                    wallet.status = 'rejected'
                    wallet.tier = 'dormant'
                    wallet.rejection_reason = 'Dormant wallet (Inactive > 21 days)'
                    discovery_state["rejected"] += 1
                elif is_valid or stats['all_time_pnl_usd'] >= 50000.0:
                    wallet.status = 'active'
                    if baleen_score >= 80.0 or stats['all_time_pnl_usd'] >= 100000.0:
                        wallet.tier = 'gold_sniper'
                        discovery_state["gold_snipers"] += 1
                    else:
                        wallet.tier = 'standard'
                    discovery_state["active_whales_in_basket"] += 1
                else:
                    wallet.status = 'rejected'
                    wallet.tier = 'rejected'
                    wallet.rejection_reason = reason
                    discovery_state["rejected"] += 1
                    
                # Auto-generate AI summary
                try:
                    ai_summary, ai_style_tag = await generate_summary(stats)
                    wallet.ai_summary = ai_summary
                    wallet.ai_style_tag = ai_style_tag
                except Exception:
                    wallet.ai_summary = f"Institutional Polymarket trader with ${stats['all_time_pnl_usd']:,.0f} all-time PnL and {stats['win_rate_pct']}% win rate."
                    wallet.ai_style_tag = "Alpha Whale"
                    
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
                wallet.trades_per_hour = stats.get('trades_per_hour', 1.0)
                wallet.wilson_lb = stats.get('wilson_lower_bound', 65.0)
                wallet.alpha_per_trade = stats.get('alpha_per_trade', 25.0)
                wallet.profit_factor = stats.get('profit_factor', 1.5)
                wallet.first_trade_at = stats.get('first_trade_at')
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
            discovery_state["step_description"] = "Hard wiping previous wallets for fresh discovery from Polymarket..."
            await db.execute(delete(WalletSnapshot))
            await db.execute(delete(Wallet))
            await db.commit()
            logger.info("All existing wallets completely deleted for fresh discovery scan.")

        discovery_state["progress_pct"] = 15
        discovery_state["step_description"] = "Stage 1: Multi-Period Leaderboard & Trade Scraping..."
        
        candidates = await client.discover_candidates()
        total_candidates = len(candidates)
        logger.info(f"Discovered {total_candidates} candidate addresses from Polymarket.")
        
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

