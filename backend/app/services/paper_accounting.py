"""Reconcile existing paper lots without treating marked equity as spendable cash.

This is a compatibility calculation over the existing lot records, not the
future immutable journal. Missing marks retain cost less recorded entry fees.
"""
from decimal import Decimal, ROUND_DOWN
from sqlalchemy import select
from app.models import ExecutionLog, PortfolioSnapshot


def money(value):
    result = Decimal(str(value if value is not None else 0))
    if not result.is_finite():
        raise ValueError('Non-finite paper accounting value')
    return result


def affordable_order(notional, cash, price, title):
    """Fit the requested paper purchase and its quoted fee inside cash."""
    from app.services.polymarket_fees import calculate_polymarket_fee
    budget = max(Decimal(0), money(cash))
    amount = min(money(notional), budget)
    for _ in range(4):
        fee = calculate_polymarket_fee(float(amount), price, title, is_maker=False)
        total = amount + money(fee['fee_usd'])
        if total <= budget:
            return float(amount), fee
        amount = (amount * budget / total).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    return 0.0, calculate_polymarket_fee(0.0, price, title, is_maker=False)


async def paper_totals(db, user_id, starting_balance):
    await db.flush()
    rows = (await db.execute(select(ExecutionLog).where(
        ExecutionLog.user_id == user_id if user_id is not None else ExecutionLog.user_id.is_(None),
        ExecutionLog.is_sandbox.is_(True), ExecutionLog.side == 'BUY',
        ExecutionLog.status.in_(['FILLED', 'CLOSED', 'RESOLVED'])))).scalars().all()
    realized = sum((money(r.realized_pnl_usd) for r in rows if r.status != 'FILLED'), Decimal(0))
    opened = [r for r in rows if r.status == 'FILLED']
    committed = sum((money(r.notional_usd) + money(r.fee_usd) for r in opened), Decimal(0))
    # Cached marks never fund entries; only realized cash less committed cost does.
    from app.services.mark_to_market import _last_known_pnl
    open_pnl = sum((money(_last_known_pnl.get(str(r.id), -float(money(r.fee_usd))))
                    for r in opened), Decimal(0))
    base = money(starting_balance)
    return {'cash': base + realized - committed, 'equity': base + realized + open_pnl,
            'realized': realized, 'open_count': len(opened)}


async def reconcile_user(db, user, snapshot=False):
    start = user.sandbox_starting_balance_usd
    if start is None:
        raise ValueError('Missing account starting balance')
    totals = await paper_totals(db, user.id, start)
    user.sandbox_balance_usd = float(totals['equity'])
    previous = user.sandbox_high_water_mark_usd
    user.sandbox_high_water_mark_usd = max(float(start if previous is None else previous), user.sandbox_balance_usd)
    if snapshot:
        db.add(PortfolioSnapshot(user_id=user.id, run_id=user.active_paper_run_id, balance=user.sandbox_balance_usd,
                                total_pnl=float(totals['equity'] - money(start)),
                                active_trades_count=totals['open_count']))
    return totals
