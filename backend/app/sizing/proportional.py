"""Fixed share scaling shared by live orders and deterministic account replay."""
from decimal import Decimal, ROUND_DOWN, InvalidOperation


def decimal(value):
    try:
        value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid numeric evidence") from exc
    if not value.is_finite():
        raise ValueError("Non-finite sizing input")
    return value


def proportional_quantity(leader_quantity, ratio, *, quantum="0.01", tolerance_bps="10"):
    quantity, multiplier, step, tolerance = map(decimal, (leader_quantity, ratio, quantum, tolerance_bps))
    if quantity <= 0 or multiplier <= 0 or step <= 0 or not 0 <= tolerance <= 10000:
        raise ValueError("Invalid proportional sizing input")
    target = quantity * multiplier
    actual = (target / step).to_integral_value(rounding=ROUND_DOWN) * step
    if actual <= 0 or (target-actual) / target * 10000 > tolerance:
        raise ValueError("Share precision would materially change source proportions")
    return actual
