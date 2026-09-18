"""Independent cash/inventory accounting from explicitly supplied event evidence."""
from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal
import json
from app.sizing.proportional import decimal

ZERO = Decimal(0)


@dataclass
class Ledger:
    starting_cash: Decimal
    cash: Decimal = field(init=False)
    quantities: dict = field(default_factory=dict)
    costs: dict = field(default_factory=dict)
    external_flows: Decimal = ZERO
    income: Decimal = ZERO
    realized: Decimal = ZERO
    fees: Decimal = ZERO
    seen: dict = field(default_factory=dict)

    def __post_init__(self):
        self.starting_cash = decimal(self.starting_cash)
        if self.starting_cash < 0:
            raise ValueError("Negative starting cash")
        self.cash = self.starting_cash

    def _remove(self, token, quantity):
        held = self.quantities.get(token, ZERO)
        if quantity <= 0 or quantity > held:
            raise ValueError("Missing starting inventory or oversell")
        basis = self.costs.get(token, ZERO) * quantity / held
        self.quantities[token] = held - quantity
        self.costs[token] -= basis
        return basis

    def _add(self, token, quantity, cost):
        if not token or quantity <= 0 or cost < 0:
            raise ValueError("Invalid inventory evidence")
        self.quantities[token] = self.quantities.get(token, ZERO) + quantity
        self.costs[token] = self.costs.get(token, ZERO) + cost

    def apply(self, event):
        identity = event.get("id")
        if not isinstance(identity, str) or not identity:
            raise ValueError("Verified unique event identity required")
        signature = json.dumps(event, sort_keys=True, default=str)
        if identity in self.seen:
            if self.seen[identity] != signature:
                raise ValueError("Conflicting event identity; investigate reorg/correction")
            return False
        previous = deepcopy(self.__dict__)
        try:
            kind = event["type"]
            fee = decimal(event.get("fee_usd", 0))
            if fee < 0:
                raise ValueError("Negative fee; model rebates as income")
            if kind in ("DEPOSIT", "WITHDRAW", "INCOME"):
                amount = decimal(event["amount_usd"])
                if amount < 0:
                    raise ValueError("Negative cash movement")
                if kind == "WITHDRAW": amount = -amount
                self.cash += amount
                if kind == "INCOME": self.income += amount
                else: self.external_flows += amount
            elif kind in ("BUY", "SELL", "REDEEM", "TRANSFER_IN", "TRANSFER_OUT"):
                token, quantity = event["token_id"], decimal(event["quantity"])
                if kind.startswith("TRANSFER"):
                    value = decimal(event["value_usd"])
                    if value < 0: raise ValueError("Negative transfer valuation")
                    if kind == "TRANSFER_IN":
                        self._add(token, quantity, value)
                        self.external_flows += value
                    else:
                        self._remove(token, quantity)
                        self.external_flows -= value
                else:
                    price = decimal(event["price"])
                    if not 0 <= price <= 1: raise ValueError("Invalid outcome price")
                    amount = quantity * price
                    if kind == "BUY":
                        self._add(token, quantity, amount+fee)
                        self.cash -= amount
                    else:
                        basis = self._remove(token, quantity)
                        self.cash += amount
                        self.realized += amount-basis-fee
            elif kind in ("SPLIT", "MERGE"):
                tokens, quantity = event["token_ids"], decimal(event["quantity"])
                if len(tokens) != 2 or len(set(tokens)) != 2 or quantity <= 0:
                    raise ValueError("Verified binary complete set required")
                if kind == "SPLIT":
                    for token in tokens: self._add(token, quantity, (quantity+fee)/2)
                    self.cash -= quantity
                else:
                    basis = sum((self._remove(token, quantity) for token in tokens), ZERO)
                    self.cash += quantity
                    self.realized += quantity-basis-fee
            else:
                raise ValueError("Unsupported event; accounting coverage is incomplete")
            self.cash -= fee
            self.fees += fee
            if self.cash < 0:
                raise ValueError("Insufficient cash or missing funding evidence")
            self.seen[identity] = signature
            return True
        except Exception:
            self.__dict__.update(previous)
            raise

    def value(self, marks):
        position_value = ZERO
        for token, quantity in self.quantities.items():
            if not quantity: continue
            if token not in marks: raise ValueError("Missing mark; equity and P&L unavailable")
            price = decimal(marks[token])
            if not 0 <= price <= 1: raise ValueError("Invalid mark")
            position_value += quantity * price
        equity = self.cash + position_value
        return {"cash": self.cash, "positions": position_value, "equity": equity,
                "economic_pnl": equity-self.starting_cash-self.external_flows,
                "realized_pnl": self.realized, "income": self.income, "fees": self.fees}
