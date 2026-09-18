from decimal import Decimal
import pytest
from app.research.ledger import Ledger
from app.research.proportional_replay import replay
from app.sizing.proportional import proportional_quantity


def test_partial_sell_reopen_fees_and_unknown_marks():
    ledger = Ledger(100)
    ledger.apply(dict(id="b", type="BUY", token_id="yes", quantity=10, price=".4", fee_usd=".1"))
    ledger.apply(dict(id="s", type="SELL", token_id="yes", quantity=4, price=".7", fee_usd=".1"))
    assert ledger.realized == Decimal("1.06")
    ledger.apply(dict(id="b2", type="BUY", token_id="yes", quantity=4, price=".5"))
    with pytest.raises(ValueError, match="Missing mark"): ledger.value({})
    assert ledger.value({"yes": ".5"})["economic_pnl"] == Decimal("1.60")


def test_split_merge_redeem_and_losing_inventory():
    ledger = Ledger(100)
    ledger.apply(dict(id="split", type="SPLIT", token_ids=["yes", "no"], quantity=10))
    assert ledger.value({"yes": ".7", "no": ".3"})["economic_pnl"] == 0
    ledger.apply(dict(id="merge", type="MERGE", token_ids=["yes", "no"], quantity=4))
    ledger.apply(dict(id="redeem_yes", type="REDEEM", token_id="yes", quantity=6, price=1))
    assert ledger.value({"no": 0})["economic_pnl"] == 0
    ledger.apply(dict(id="redeem_no", type="REDEEM", token_id="no", quantity=6, price=0))
    assert ledger.value({})["equity"] == 100


def test_external_flows_not_profit_income_is_profit_and_duplicates_safe():
    ledger = Ledger(100)
    ledger.apply(dict(id="deposit", type="DEPOSIT", amount_usd=1000))
    event = dict(id="rebate", type="INCOME", amount_usd=5)
    assert ledger.apply(event) and not ledger.apply(event)
    ledger.apply(dict(id="transfer", type="TRANSFER_IN", token_id="yes", quantity=10, value_usd=5))
    assert ledger.value({"yes": ".5"})["economic_pnl"] == 5
    with pytest.raises(ValueError, match="Conflicting"): ledger.apply({**event, "amount_usd": 100})
    with pytest.raises(ValueError, match="oversell"):
        ledger.apply(dict(id="bad", type="SELL", token_id="no", quantity=100, price=1))
    assert ledger.value({"yes": ".5"})["economic_pnl"] == 5


def leg(identity, side, quantity, timestamp):
    return dict(id=identity, side=side, quantity=quantity, timestamp=timestamp, token_id="yes", price=".5",
                observation=dict(timestamp=timestamp+2, token_id="yes", side=side,
                                 fill_price=".5", min_order_size=5, available_quantity=10000, fee_usd=0))


@pytest.mark.parametrize("capital,ratio,success", [(20,".01",False),(100,".1",True),(1000,"1",True)])
def test_account_replay_preserves_1_3_6_and_partial_exits(capital, ratio, success):
    events = [leg("a","BUY",100,1), leg("b","BUY",300,2), leg("c","BUY",600,3), leg("exit","SELL",250,4)]
    result = replay(events, starting_cash=capital, ratio=ratio, marks={"yes": ".5"}, delay_seconds=2)
    assert result["all_legs_copied"] is success
    assert result["execution_approved"] is False
    if success:
        quantities = [Decimal(r["quantity"]) for r in result["events"]]
        assert quantities[1] == quantities[0]*3 and quantities[2] == quantities[0]*6
        assert Decimal(result["valuation"]["economic_pnl"]) == 0
    else:
        assert result["events"][0]["quantity"] == "0"  # No rounding up to venue minimum.


def test_replay_missing_leg_cash_depth_and_precision_are_explicit():
    for quote_change, expected in [({"available_quantity": 1}, "depth"), ({"min_order_size": 200}, "minimum")]:
        event = leg("a", "BUY", 100, 1)
        event["observation"].update(quote_change)
        report = replay([event], starting_cash=100, ratio=1, marks={})
        assert expected in report["events"][0]["reason"] and not report["all_legs_copied"]
    report = replay([leg("cash", "BUY", 100, 1)], starting_cash=20, ratio=1, marks={})
    assert "cash" in report["events"][0]["reason"]
    with pytest.raises(ValueError, match="precision"): proportional_quantity(".001", ".1")
