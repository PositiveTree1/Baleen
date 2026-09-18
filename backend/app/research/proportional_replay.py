"""Replay explicit source fills against recorded venue observations.

Missing/partial legs remain visible; no invented depth, fees, fills or equity.
No networking, signing or order submission exists in this module.
"""
from app.research.ledger import Ledger
from app.sizing.proportional import decimal, proportional_quantity


def replay(events, *, starting_cash, ratio, marks, delay_seconds=0, max_slippage_bps=100):
    if decimal(delay_seconds) < 0 or not 0 <= decimal(max_slippage_bps) <= 10000:
        raise ValueError("Invalid delay or slippage limit")
    account = Ledger(starting_cash)
    outcomes, seen = [], set()
    last_time = None
    for event in events:
        identity = event["id"]
        if identity in seen:
            raise ValueError("Replay input contains duplicate source identities")
        seen.add(identity)
        timestamp = decimal(event["timestamp"])
        if last_time is not None and timestamp < last_time:
            raise ValueError("Source events must be chronologically ordered")
        last_time = timestamp
        record = {"source_id": identity, "status": "unavailable", "quantity": "0"}
        outcomes.append(record)
        try:
            side = event["side"]
            if side not in ("BUY", "SELL"):
                raise ValueError("Only entry/exit fills supported in copy replay")
            target = proportional_quantity(event["quantity"], ratio)
            record["target_quantity"] = str(target)
            quote = event["observation"]
            observed_at = decimal(quote["timestamp"])
            record["observed_delay_seconds"] = str(observed_at-timestamp)
            if observed_at < timestamp + decimal(delay_seconds):
                raise ValueError("No quote observed after the specified delay")
            if quote.get("token_id") != event["token_id"] or quote.get("side") != side:
                raise ValueError("Quote scope does not match the source leg")
            source_price, price = decimal(event["price"]), decimal(quote["fill_price"])
            if source_price <= 0 or not 0 < price <= 1:
                raise ValueError("Invalid source or fill price")
            adverse = max(decimal(0), price-source_price if side == "BUY" else source_price-price)
            if adverse/source_price*10000 > decimal(max_slippage_bps):
                raise ValueError("Observed slippage exceeds replay limit")
            minimum = decimal(quote["min_order_size"])
            if minimum <= 0:
                raise ValueError("Venue minimum is invalid or unknown")
            if target < minimum:
                raise ValueError("Proportional quantity is below venue minimum")
            if decimal(quote["available_quantity"]) < target:
                raise ValueError("Insufficient observed depth for the complete leg")
            fee = decimal(quote["fee_usd"])
            account.apply({"id": identity, "type": side, "token_id": event["token_id"],
                           "quantity": str(target), "price": str(price), "fee_usd": str(fee)})
            record.update(status="filled", quantity=str(target), price=str(price), fee_usd=str(fee))
        except (ValueError, KeyError) as exc:
            record["reason"] = str(exc)
    try:
        valuation = {k: str(v) for k, v in account.value(marks).items()}
    except ValueError as exc:
        valuation = {"economic_pnl": None, "reason": str(exc)}
    return {"mode": "recorded_observation_replay", "ratio": str(decimal(ratio)), "events": outcomes,
            "all_legs_copied": bool(outcomes) and all(r["status"] == "filled" for r in outcomes),
            "valuation": valuation, "execution_approved": False}
