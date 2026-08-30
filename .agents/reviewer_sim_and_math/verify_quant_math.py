import sys
sys.path.insert(0, r"c:\Users\arthu\Documents\Baleen-master\backend")
import math
from app.sizing.slippage import calculate_simulated_fill_price, check_slippage
from app.sizing.fill_simulator import simulate_fill
from app.sizing.sleeve_manager import SleeveManager

def test_slippage_comprehensive():
    print("=== Testing Slippage & Latency ===")
    
    # 1. Test grid of prices from 0.001 to 0.999
    prices = [0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.98, 0.99, 0.995, 0.999]
    notionals = [0.0, 1.0, 5.0, 50.0, 100.0, 500.0, 1500.0, 5000.0, 20000.0]
    latencies = [0.0, 100.0, 180.0, 350.0, 800.0, 1400.0, 5000.0]
    
    buy_fails = 0
    sell_fails = 0
    
    for p in prices:
        for notional in notionals:
            for lat in latencies:
                # BUY
                p_buy = calculate_simulated_fill_price(p, "BUY", notional, lat)
                if p_buy <= p and p < 0.999:
                    print(f"BUY FAIL: price={p}, notional={notional}, lat={lat} -> fill={p_buy}")
                    buy_fails += 1
                
                # SELL
                p_sell = calculate_simulated_fill_price(p, "SELL", notional, lat)
                if p_sell >= p and p > 0.001:
                    print(f"SELL FAIL: price={p}, notional={notional}, lat={lat} -> fill={p_sell}")
                    sell_fails += 1
                    
    print(f"Slippage sweep completed: {len(prices)*len(notionals)*len(latencies)} combinations.")
    print(f"BUY failures: {buy_fails}, SELL failures: {sell_fails}")
    assert buy_fails == 0
    assert sell_fails == 0

def test_bayesian_credibility_comprehensive():
    print("=== Testing Bayesian Credibility Z(N) & Sleeve Sizing ===")
    
    # 1. Test N < 15 anchoring under extreme shocks
    shocks = [-1e9, -10000.0, -500.0, -100.0, 0.0, 100.0, 500.0, 10000.0, 1e9]
    scores = [0.0, 10.0, 50.0, 80.0, 100.0, 150.0]
    base_budget = 1000.0
    
    bound_violations = 0
    for n in range(15):
        for shock in shocks:
            for score in scores:
                adj = SleeveManager.calculate_adjusted_sleeve_budget(base_budget, shock, score, trades_count=n)
                if adj < 900.0 or adj > 1100.0:
                    print(f"BOUND VIOLATION: N={n}, shock={shock}, score={score} -> adj=${adj}")
                    bound_violations += 1
    
    print(f"Low-sample N < 15 shock test: {15 * len(shocks) * len(scores)} tests, violations: {bound_violations}")
    assert bound_violations == 0

    # 2. Test Continuity at N=15
    adj_14 = SleeveManager.calculate_adjusted_sleeve_budget(1000.0, -1e6, 80.0, trades_count=14)
    adj_15 = SleeveManager.calculate_adjusted_sleeve_budget(1000.0, -1e6, 80.0, trades_count=15)
    adj_16 = SleeveManager.calculate_adjusted_sleeve_budget(1000.0, -1e6, 80.0, trades_count=16)
    print(f"Continuity at N=15 (worst loss): N=14 -> {adj_14}, N=15 -> {adj_15}, N=16 -> {adj_16}")
    assert adj_14 == 906.67
    assert adj_15 == 900.00
    assert adj_16 == 871.43

    # 3. Monotonicity for N >= 0
    # For a fixed negative shock, adj_budget should be monotonically non-increasing in N
    prev_adj = 1000.0
    for n in range(200):
        adj = SleeveManager.calculate_adjusted_sleeve_budget(1000.0, -500.0, 80.0, trades_count=n)
        assert adj <= prev_adj + 1e-6, f"Monotonicity violated at N={n}: {adj} > {prev_adj}"
        prev_adj = adj
    print("Monotonicity under drawdown verified across N in [0, 200].")

    # 4. Asymptotic Convergence to 1.0
    # As N -> infty, mult -> clamped_raw
    adj_100k = SleeveManager.calculate_adjusted_sleeve_budget(1000.0, -1e6, 80.0, trades_count=100000)
    adj_10m = SleeveManager.calculate_adjusted_sleeve_budget(1000.0, -1e6, 80.0, trades_count=10_000_000)
    print(f"Asymptotic value at N=100,000: ${adj_100k}, N=10,000,000: ${adj_10m} (floor $300.00)")
    assert abs(adj_100k - 300.0) < 0.20
    assert adj_10m == 300.0

    # 5. Backward compatibility
    adj_none_pos = SleeveManager.calculate_adjusted_sleeve_budget(1000.0, 1e6, 80.0, trades_count=None)
    adj_none_neg = SleeveManager.calculate_adjusted_sleeve_budget(1000.0, -1e6, 80.0, trades_count=None)
    print(f"Backward compatibility (trades_count=None): pos=${adj_none_pos}, neg=${adj_none_neg}")
    assert adj_none_pos == 1500.0
    assert adj_none_neg == 300.0

    # 6. EMA clipping
    ema_val = SleeveManager.update_copy_pnl_ema(0.0, -999999.0, alpha=0.05)
    print(f"EMA clipping on -$999k: {ema_val} (expected -25.0)")
    assert ema_val == -25.0

    ema_val_pos = SleeveManager.update_copy_pnl_ema(0.0, 999999.0, alpha=0.05)
    print(f"EMA clipping on +$999k: {ema_val_pos} (expected 25.0)")
    assert ema_val_pos == 25.0

if __name__ == "__main__":
    test_slippage_comprehensive()
    test_bayesian_credibility_comprehensive()
    print("\nALL MATHEMATICAL CHECKS PASSED PERFECTLY!")
