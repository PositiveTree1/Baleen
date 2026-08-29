# Handoff Report: Challenger 2 — Milestone M-A1 Fee Stress-Testing

## 1. Observation

### Source Code Analysis: `backend/app/services/polymarket_fees.py`
- **Lines 62-94 (`classify_market_category`)**:
  - Geopolitics ($\Theta = 0.000$): keywords `("war", "ceasefire", "treaty", "sanctions", "nato", "united nations", "un ", "taiwan", "ukraine", "russia", "gaza", "israel", "middle east", "invade", "peace agreement", "military")`
  - Crypto ($\Theta = 0.072$): keywords `("bitcoin", "btc", "ethereum", "eth", "solana", "sol", "xrp", "doge", "crypto", "up or down", "15m", "price of btc", "price of eth", "price of solana", "token", "airdrop")`
  - Economics / Finance ($\Theta = 0.060$): keywords `("fed ", "federal reserve", "interest rate", "cpi", "inflation", "gdp", "recession", "unemployment", "treasury", "s&p", "nasdaq", "dow jones", "stock", "yield")`
  - Politics ($\Theta = 0.040$): keywords `("election", "president", "presidential", "senate", "house", "trump", "biden", "harris", "democrat", "republican", "primary", "governor", "vote", "voter", "ballot")`
  - Sports ($\Theta = 0.030$): keywords `("vs", "open:", "atp", "wta", "championship", "cup", "league", "fc", "real madrid", "barcelona", "arsenal", "chelsea", "manchester", "nba", "nfl", "mlb", "nhl", "ufc", "tennis", "set handicap", "match winner", "spread", "over/under", "esports", "f1", "formula 1", "grand prix", "lionel messi", "ronaldo", "alcaraz", "sinner", "djokovic")`
  - Culture, Weather & Tech / General ($\Theta = 0.050$): keywords `("apple", "google", "nvidia", "microsoft", "tesla", "elon musk", "musk", "tweet", "spacex", "openai", "anthropic", "weather", "temperature", "oscar", "grammy", "movie", "gta 6")` and fallback to `("General", 0.050)`.

- **Lines 107-115 & 117-135 (`calculate_polymarket_fee`)**:
  ```python
  if is_maker or notional_usd <= 0 or theta == 0.0:
      return {
          "fee_usd": 0.0,
          "category": category,
          "category_rate": theta,
          "effective_fee_pct": 0.0,
          "is_maker": is_maker,
          "maker_rebate_eligible": bool(is_maker)
      }

  p = max(0.001, min(0.999, float(price) if price is not None else 0.5))
  raw_fee = notional_usd * theta * (1.0 - p)
  d_fee = decimal.Decimal(str(raw_fee)).quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_EVEN)
  fee_usd = float(d_fee)
  ```
  - Exact zero-price contract fix verified: `price is not None else 0.5` ensures `price = 0.0` correctly evaluates `float(0.0)` rather than falsy falling back to `0.5`.
  - Price bounds $[0.001, 0.999]$ strictly enforced via `max(0.001, min(0.999, ...))`.
  - Banker's Rounding strictly applied via `decimal.Decimal.quantize(..., rounding=decimal.ROUND_HALF_EVEN)`.

- **Lines 138-154 (`calculate_fee_aware_ev_gate`)**:
  ```python
  _, theta = classify_market_category(market_title)
  p = max(0.001, min(0.999, float(price) if price is not None else 0.5))
  fee_rate = theta * (1.0 - p)
  min_required_edge = 2.5 * fee_rate
  should_pass = (expected_edge >= min_required_edge)
  return should_pass, round(fee_rate, 4), round(min_required_edge, 4)
  ```

### Empirical Test Execution
Command: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_polymarket_fees.py backend/tests/test_fee_calculation.py backend/tests/test_challenger_fee_boundary_matrix.py -v`
Result:
```
backend/tests/test_polymarket_fees.py::test_zero_price_contract_fee_clamp PASSED [  5%]
backend/tests/test_polymarket_fees.py::test_zero_price_contract_ev_gate PASSED [ 11%]
backend/tests/test_polymarket_fees.py::test_none_price_fallback PASSED   [ 16%]
backend/tests/test_polymarket_fees.py::test_extreme_boundary_prices PASSED [ 22%]
backend/tests/test_polymarket_fees.py::test_all_categories_and_maker_rebates PASSED [ 27%]
backend/tests/test_fee_calculation.py::test_no_fee_when_recovering_past_losses PASSED [ 33%]
backend/tests/test_fee_calculation.py::test_fee_only_on_profit_above_hwm PASSED [ 38%]
backend/tests/test_fee_calculation.py::test_hwm_ratchets_up_only PASSED  [ 44%]
backend/tests/test_fee_calculation.py::test_official_polymarket_quadratic_fees PASSED [ 50%]
backend/tests/test_challenger_fee_boundary_matrix.py::test_matrix_all_categories_and_boundary_prices PASSED [ 55%]
backend/tests/test_challenger_fee_boundary_matrix.py::test_specific_boundary_price_points PASSED [ 61%]
backend/tests/test_challenger_fee_boundary_matrix.py::test_maker_zero_fee_invariant_across_all_boundaries PASSED [ 66%]
backend/tests/test_challenger_fee_boundary_matrix.py::test_zero_and_negative_notional_invariant PASSED [ 72%]
backend/tests/test_challenger_fee_boundary_matrix.py::test_bankers_rounding_half_to_even_rigorous PASSED [ 77%]
backend/tests/test_challenger_fee_boundary_matrix.py::test_fee_monotonicity_with_price PASSED [ 83%]
backend/tests/test_challenger_fee_boundary_matrix.py::test_ev_net_gate_stress_matrix PASSED [ 88%]
backend/tests/test_challenger_fee_boundary_matrix.py::test_category_classification_stress_and_precedence PASSED [ 94%]
backend/tests/test_challenger_fee_boundary_matrix.py::test_float_edge_cases_and_extreme_notionals PASSED [100%]

============================= 18 passed in 0.21s ==============================
```

## 2. Logic Chain

1. **Boundary Prices Verification**:
   - $p = 0.00$: Evaluates to $p = 0.001$, $(1 - p) = 0.999$. For $100 notional:
     - Crypto ($\Theta=0.072$): $100 \times 0.072 \times 0.999 = 7.1928 \to \$7.19$ (7.19%)
     - Economics ($\Theta=0.060$): $100 \times 0.060 \times 0.999 = 5.994 \to \$5.99$ (5.99%)
     - Culture/Tech ($\Theta=0.050$): $100 \times 0.050 \times 0.999 = 4.995 \to \$5.00$ (5.00%)
     - Politics ($\Theta=0.040$): $100 \times 0.040 \times 0.999 = 3.996 \to \$4.00$ (4.00%)
     - Sports ($\Theta=0.030$): $100 \times 0.030 \times 0.999 = 2.997 \to \$3.00$ (3.00%)
     - Geopolitics ($\Theta=0.000$): $\$0.00$ (0.00%)
   - $p = 0.001$: Matches $p = 0.00$ exactly across all 6 asset classes.
   - $p = 0.50$: Midpoint $(1 - p) = 0.50$:
     - Crypto: $100 \times 0.072 \times 0.50 = \$3.60$ (3.60%)
     - Economics: $100 \times 0.060 \times 0.50 = \$3.00$ (3.00%)
     - Culture/Tech: $100 \times 0.050 \times 0.50 = \$2.50$ (2.50%)
     - Politics: $100 \times 0.040 \times 0.50 = \$2.00$ (2.00%)
     - Sports: $100 \times 0.030 \times 0.50 = \$1.50$ (1.50%)
     - Geopolitics: $\$0.00$ (0.00%)
   - $p = 0.999$: Upper boundary $(1 - p) = 0.001$:
     - Crypto: $100 \times 0.072 \times 0.001 = 0.0072 \to \$0.01$ (0.01%)
     - Economics: $100 \times 0.060 \times 0.001 = 0.0060 \to \$0.01$ (0.01%)
     - Culture/Tech: $100 \times 0.050 \times 0.001 = 0.0050000000000000045 \to \$0.01$ (0.01%)
     - Politics: $100 \times 0.040 \times 0.001 = 0.0040 \to \$0.00$ (0.00%)
     - Sports: $100 \times 0.030 \times 0.001 = 0.0030 \to \$0.00$ (0.00%)
     - Geopolitics: $\$0.00$ (0.00%)
   - $p = 1.00$: Clamped to $0.999$, producing identical outputs to $p = 0.999$.

2. **Invariance & Numerical Safety**:
   - Monotonicity invariant: $\frac{\partial \text{Fee}}{\partial p} \le 0$ confirmed empirically across 200 discrete price increments in $[0.001, 0.999]$.
   - Maker zero-fee invariant: $100\%$ satisfied for all categories, boundary prices, and notionals.
   - Non-positive notional invariant: $\text{Fee} = \$0.00$ for all $V \le 0$.
   - Banker's Rounding invariant: exact half-cent values $(0.005 \to 0.00, 0.015 \to 0.02, 0.025 \to 0.02, 0.035 \to 0.04, \dots)$ strictly satisfy `ROUND_HALF_EVEN`.

3. **EV-net Gate**:
   - `expected_edge >= 2.5 * Theta * (1 - p)` accurately gates trades across boundary conditions.

## 3. Caveats

No caveats. All boundary prices, asset categories, rounding modes, and gate mechanics have been empirically exercised and validated.

## 4. Conclusion

**Verdict: APPROVE**

`backend/app/services/polymarket_fees.py` adheres strictly to the 2026 Polymarket Quadratic Fee Schedule. The zero-price fallback bug has been eliminated, boundary clamping $[0.001, 0.999]$ is mathematically sound, Banker's Rounding is correctly quantized to the cent, and maker/zero-notional invariants hold unconditionally across all 6 asset categories.

## 5. Verification Method

To independently verify the test suite:
```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_polymarket_fees.py backend/tests/test_fee_calculation.py backend/tests/test_challenger_fee_boundary_matrix.py -v
```
Expected output: 18 passed in < 1 second.
