"""Read-only current equity observation; never a historical capital estimate."""
import csv
import hashlib
import io
import zipfile
from datetime import datetime, timezone
from app.sizing.proportional import decimal


def parse_snapshot(content):
    if len(content) > 4_000_000:
        raise ValueError("Snapshot compressed size exceeds budget")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()
        if sorted(names) != ["equity.csv", "positions.csv"]:
            raise ValueError("Unexpected snapshot members")
        if sum(i.file_size for i in archive.infolist()) > 20_000_000:
            raise ValueError("Snapshot expanded size exceeds budget")
        def rows(name):
            return list(csv.DictReader(io.StringIO(archive.read(name).decode("utf-8-sig"))))
        positions, equity_rows = rows("positions.csv"), rows("equity.csv")
    if len(equity_rows) != 1:
        raise ValueError("Expected one equity observation")
    row = equity_rows[0]
    cash, position_value, equity = map(decimal, (row["cashBalance"], row["positionsValue"], row["equity"]))
    stamp = datetime.fromisoformat(row["valuationTime"].replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Snapshot valuation time needs timezone")
    age = (datetime.now(timezone.utc)-stamp).total_seconds()
    if not -60 <= age <= 300:
        raise ValueError("Snapshot valuation is stale or in the future")
    calculated = decimal(0)
    for position in positions:
        size, price = decimal(position["size"]), decimal(position["curPrice"])
        if size < 0 or not 0 <= price <= 1 or position["valuationTime"] != row["valuationTime"]:
            raise ValueError("Invalid or mixed-time position valuation")
        calculated += size * price
    if cash < 0 or abs(cash+position_value-equity) > decimal(".02") or abs(calculated-position_value) > decimal(".02"):
        raise ValueError("Snapshot equity identity does not reconcile")
    return {"status": "observed", "cash_usd": str(cash), "positions_value_usd": str(position_value),
            "equity_usd": str(equity), "valuation_time": row["valuationTime"], "position_rows": len(positions),
            "sha256": hashlib.sha256(content).hexdigest(), "source": "polymarket_accounting_snapshot",
            "historical_strategy_capital_verified": False}


async def accounting_snapshot(client, address):
    try:
        # Stream with a hard body budget, rather than allocating an arbitrary ZIP.
        content = bytearray()
        async with client.client.stream("GET", f"{client.data_api_url}/v1/accounting/snapshot", params={"user": address}) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > 4_000_000:
                    raise ValueError("Snapshot size budget exceeded")
        return {**parse_snapshot(bytes(content)), "requested_wallet": address}
    except Exception as exc:
        return {"status": "unavailable", "reason": type(exc).__name__, "requested_wallet": address,
                "historical_strategy_capital_verified": False}
