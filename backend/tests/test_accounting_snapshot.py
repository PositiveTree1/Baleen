import io
import zipfile
from datetime import datetime, timezone, timedelta
import pytest
from app.discovery.accounting_snapshot import parse_snapshot


def snapshot(cash="10", positions="5", equity="15", stamp=None, price="0.5"):
    stamp = stamp or datetime.now(timezone.utc).isoformat()
    content = io.BytesIO()
    with zipfile.ZipFile(content, "w") as archive:
        archive.writestr("equity.csv", f"cashBalance,positionsValue,equity,valuationTime\n{cash},{positions},{equity},{stamp}\n")
        archive.writestr("positions.csv", f"asset,size,curPrice,valuationTime\nyes,10,{price},{stamp}\n")
    return content.getvalue()


def test_snapshot_includes_cash_and_reconciles_positions():
    result = parse_snapshot(snapshot())
    assert result["cash_usd"] == "10" and result["equity_usd"] == "15"
    assert result["historical_strategy_capital_verified"] is False


@pytest.mark.parametrize("kwargs", [{"equity":"999"}, {"positions":"6","equity":"16"}, {"cash":"NaN"}, {"price":"1.5"},
                                   {"stamp":(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()}])
def test_bad_or_stale_snapshots_are_not_capital_evidence(kwargs):
    with pytest.raises(ValueError): parse_snapshot(snapshot(**kwargs))
