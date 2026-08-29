import math
import sys
import os
import asyncio
from typing import Dict, Any

print('=' * 75)
print('BALEEN QUANTITATIVE MATH AND CONCURRENCY CHALLENGER TEST HARNESS')
print('=' * 75)

# 1. WILSON SCORE LOWER BOUND EMPIRICAL STRESS TEST
print('\n[CHALLENGE 1] Wilson Score Lower Bound Edge Cases and Continuity')

def calc_wilson_lower_bound(wins: int, total: int, z: float = 1.645) -> float:
    if total <= 0:
        return 0.0
    p_hat = float(wins) / float(total)
    n = float(total)
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p_hat + z2 / (2.0 * n)
    spread = z * math.sqrt((p_hat * (1.0 - p_hat) + z2 / (4.0 * n)) / n)
    return round(max(0.0, (centre - spread) / denom) * 100.0, 1)

def calc_wilson_lower_bound_robust(wins: int, total: int, z: float = 1.645) -> float:
    if total <= 0:
        return 0.0
    wins = max(0, min(wins, total))
    p_hat = float(wins) / float(total)
    n = float(total)
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p_hat + z2 / (2.0 * n)
    variance_term = (p_hat * (1.0 - p_hat) + z2 / (4.0 * n)) / n
    spread = z * math.sqrt(max(0.0, variance_term))
    return round(max(0.0, (centre - spread) / denom) * 100.0, 1)

cases = [
    (0, 0, 'N=0, wins=0 (Empty)'),
    (0, 1, 'N=1, wins=0 (0%)'),
    (1, 1, 'N=1, wins=1 (100%)'),
    (0, 2, 'N=2, wins=0 (0%)'),
    (1, 2, 'N=2, wins=1 (50%)'),
    (2, 2, 'N=2, wins=2 (100%)'),
    (0, 5, 'N=5, wins=0 (0%)'),
    (3, 5, 'N=5, wins=3 (60%)'),
    (5, 5, 'N=5, wins=5 (100%)'),
    (0, 10, 'N=10, wins=0 (0%)'),
    (5, 10, 'N=10, wins=5 (50%)'),
    (9, 10, 'N=10, wins=9 (90%)'),
    (10, 10, 'N=10, wins=10 (100%)'),
    (0, 10000, 'N=10000, wins=0 (0%)'),
    (5000, 10000, 'N=10000, wins=5000 (50%)'),
    (7000, 10000, 'N=10000, wins=7000 (70%)'),
    (10000, 10000, 'N=10000, wins=10000 (100%)'),
]

for w, n, label in cases:
    res = calc_wilson_lower_bound(w, n)
    raw_p = (w / n * 100.0) if n > 0 else 0.0
    print(f'  {label:35} -> Raw WinRate: {raw_p:5.1f}%, Wilson LB (z=1.645): {res:5.1f}%')

print('\n  -- Stressing unconstrained / invalid inputs --')
invalid_cases = [(-1, 5), (10, 5), (-5, 10), (15, 10)]
for w, n in invalid_cases:
    try:
        res = calc_wilson_lower_bound(w, n)
        print(f'  Original with wins={w}, total={n} -> {res}%')
    except Exception as e:
        print(f'  Original with wins={w}, total={n} -> CRASHED: {type(e).__name__}: {e}')
    res_rob = calc_wilson_lower_bound_robust(w, n)
    print(f'  Robust   with wins={w}, total={n} -> {res_rob}%')

# 2. SCORING ENGINE AND SCANNER FILTER DISCREPANCIES
print('\n[CHALLENGE 2] Scoring Engine Filters and Tier Assignment Edge Cases')
sys.path.insert(0, 'backend')
from app.scoring.engine import score_wallet, ScoringResult
from app.scoring.basket import compute_baleen_score

test_wallets = [
    {
        'name': 'Catastrophic Drawdown Whale ( PnL, 70% WinRate, 95% Max DD)',
        'stats': {
            'all_time_pnl_usd': 1000000.0,
            'avg_trades_per_day': 5.0,
            'outlier_concentration_pct': 0.15,
            'win_rate_pct': 70.0,
            'max_drawdown_pct': 95.0,
        }
    },
    {
        'name': 'Discovery vs Engine Threshold Divergence ( PnL, 150 trades/day)',
        'stats': {
            'all_time_pnl_usd': 35000.0,
            'avg_trades_per_day': 150.0,
            'outlier_concentration_pct': 0.20,
            'win_rate_pct': 65.0,
            'max_drawdown_pct': 10.0,
        }
    },
    {
        'name': 'High Win Rate High Drawdown ( PnL, 90% WinRate, 25% Max DD)',
        'stats': {
            'all_time_pnl_usd': 60000.0,
            'avg_trades_per_day': 10.0,
            'outlier_concentration_pct': 0.10,
            'win_rate_pct': 90.0,
            'max_drawdown_pct': 25.0,
        }
    },
    {
        'name': 'Boundary Gold Sniper ( PnL, 70.0% WinRate, 50% Drawdown)',
        'stats': {
            'all_time_pnl_usd': 100000.0,
            'avg_trades_per_day': 5.0,
            'outlier_concentration_pct': 0.10,
            'win_rate_pct': 70.0,
            'max_drawdown_pct': 50.0,
        }
    },
]

for tw in test_wallets:
    res = score_wallet(tw['stats'])
    b_score = compute_baleen_score(tw['stats'])
    print(f"\n  Wallet: {tw['name']}")
    print(f"    Inputs: PnL=${tw['stats']['all_time_pnl_usd']:,.0f}, Trades/Day={tw['stats']['avg_trades_per_day']}, WR={tw['stats']['win_rate_pct']}%, MaxDD={tw['stats']['max_drawdown_pct']}%")
    print(f"    Engine Result -> status={res.status}, tier={res.tier}, rejection_reason={res.rejection_reason}")
    print(f"    Baleen Score  -> {b_score}/100")

# 3. DATABASE RETRY LOGIC NameError: asyncio REPRODUCTION
print('\n[CHALLENGE 3] Database Reconnect Retry Logic and NameError Verification')

import app.database as db_mod

print(f"  Checking backend/app/database.py namespace for 'asyncio'...")
has_asyncio = hasattr(db_mod, 'asyncio')
print(f"  hasattr(backend.app.database, 'asyncio') == {has_asyncio}")

async def test_db_retry_crash():
    print('  Triggering simulated connection failure in init_db()...')
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        bad_engine = create_async_engine('postgresql+asyncpg://invalid:user@127.0.0.1:59999/nonexistent', connect_args={'timeout': 0.1})
        db_mod.engine = bad_engine
        await db_mod.init_db()
    except Exception as exc:
        print(f'  OBSERVED EXCEPTION DURING RETRY: {type(exc).__name__}: {exc}')
        if isinstance(exc, NameError) and 'asyncio' in str(exc):
            print('  >>> EMPIRICALLY CONFIRMED BUG: NameError asyncio crashed DB retry loop immediately on attempt 1! <<<')

asyncio.run(test_db_retry_crash())

print('\n' + '=' * 75)
print('PYTHON EMPIRICAL TESTS COMPLETE')
print('=' * 75)