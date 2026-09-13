import math
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, select

from app.api.signals import WhaleTradeSignalPayload
from app.config import settings
from app.database import SessionLocal, init_db
from app.models import ExecutionLog, User, Wallet, CanonicalSourceEvent
from app.services.live_poller import LiveTradeMirrorService, live_trade_mirror
from app.services.paper_accounting import paper_totals


@pytest.fixture(autouse=True)
async def isolate_batch_b_review_rows():
    await init_db()
    yield
    async with SessionLocal() as db:
        await db.execute(delete(ExecutionLog).where(ExecutionLog.source_wallet_address.like("0xbr%")))
        await db.execute(delete(CanonicalSourceEvent).where(CanonicalSourceEvent.source_wallet_address.like("0xbr%")))
        await db.execute(delete(Wallet).where(Wallet.address.like("0xbr%")))
        await db.execute(delete(User).where(User.email.like("%@batch-b-review.invalid")))
        await db.commit()


@pytest.mark.asyncio
async def test_onchain_signal_accepts_old_source_timestamp_and_converts_raw_units():
    captured = {}

    async def capture(**kwargs):
        captured.update(kwargs)

    original = live_trade_mirror.process_trade_fill
    live_trade_mirror.process_trade_fill = capture
    try:
        live_trade_mirror.started_at = datetime.utcnow().timestamp() + 3600
        await live_trade_mirror.process_onchain_signal(
            wallet_address="0x" + "1" * 40,
            asset_id="asset-old",
            amount_filled="100000000",
            price_str="0.50",
            side="BUY",
            tx_hash="0x" + "2" * 64,
            log_index=0,
            block_number=123,
            timestamp_ms=int((datetime.utcnow() - timedelta(days=1)).timestamp() * 1000),
        )
    finally:
        live_trade_mirror.process_trade_fill = original

    assert captured["shares"] == pytest.approx(100.0)
    assert captured["cash_usd"] == pytest.approx(50.0)


@pytest.mark.parametrize(
    "field,value",
    [
        ("price", "NaN"),
        ("price", "Infinity"),
        ("amountFilled", "1000000.5"),
        ("walletAddress", "0x" + "g" * 40),
        ("transactionHash", "0x" + "g" * 64),
    ],
)
def test_signal_payload_rejects_nonfinite_fractional_and_nonhex_values(field, value):
    payload = {
        "walletAddress": "0x" + "1" * 40,
        "side": "BUY",
        "assetId": "asset",
        "amountFilled": "1000000",
        "amountUnit": "raw_6",
        "price": "0.50",
        "transactionHash": "0x" + "2" * 64,
        "logIndex": 0,
        "blockNumber": 123,
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        WhaleTradeSignalPayload.model_validate(payload)


@pytest.mark.asyncio
async def test_paper_totals_exposes_negative_cash_after_open_cost_and_fee():
    uid = uuid.uuid4()
    async with SessionLocal() as db:
        db.add(User(id=uid, email=f"totals-{uuid.uuid4().hex}@batch-b-review.invalid", sandbox_starting_balance_usd=100))
        db.add(ExecutionLog(
            user_id=uid, source_wallet_address="0xbr" + "a" * 38,
            market_condition_id="condition", market_question="test", side="BUY",
            whale_entry_price=0.5, user_fill_price=0.5, notional_usd=120,
            active_basket_size_at_trade=1, is_sandbox=True, status="FILLED", fee_usd=3,
        ))
        await db.commit()
        totals = await paper_totals(db, uid, 100)

    assert float(totals["cash"]) == pytest.approx(-23.0)


@pytest.mark.asyncio
async def test_marked_settlement_updates_cash_once_and_is_idempotent():
    uid = uuid.uuid4()
    addr = "0xbr" + "b" * 38
    cid = "0xcondition_marked"
    now = datetime.utcnow()
    async with SessionLocal() as db:
        db.add(Wallet(address=addr))
        db.add(User(id=uid, email=f"marked-{uuid.uuid4().hex}@batch-b-review.invalid",
                    sandbox_starting_balance_usd=10000, sandbox_balance_usd=10080,
                    sandbox_high_water_mark_usd=10080))
        db.add(ExecutionLog(user_id=uid, source_wallet_address=addr, market_condition_id=cid,
                            market_question="marked", side="BUY", whale_entry_price=0.5,
                            user_fill_price=0.5, notional_usd=100, active_basket_size_at_trade=1,
                            is_sandbox=True, status="FILLED", resolution_outcome="Yes", fee_usd=0))
        await db.commit()

    service = LiveTradeMirrorService()
    with patch("app.services.event_logger.log_event", new=AsyncMock()):
        await service.settle_market_resolution(cid, "Yes", resolved_at=now)
        await service.settle_market_resolution(cid, "Yes", resolved_at=now)

    async with SessionLocal() as db:
        user = await db.get(User, uid)
        assert user.sandbox_balance_usd == pytest.approx(10100.0)
        assert user.sandbox_high_water_mark_usd == pytest.approx(10100.0)


@pytest.mark.asyncio
async def test_buy_processing_does_not_spend_more_than_available_cash_including_fees():
    addr = "0xbr" + "c" * 38
    cid = "0xcondition_budget"
    uid = uuid.uuid4()
    async with SessionLocal() as db:
        db.add(Wallet(address=addr, status="active", tier="gold_sniper", dormant=False,
                      is_hft=False, avg_trades_per_day=2, baleen_score=100,
                      all_time_pnl_usd=50000, win_rate_pct=90, wilson_lb=85))
        db.add(User(id=uid, email=f"budget-{uuid.uuid4().hex}@batch-b-review.invalid",
                    sandbox_starting_balance_usd=100, sandbox_balance_usd=100,
                    sandbox_high_water_mark_usd=100))
        await db.commit()

    service = LiveTradeMirrorService()
    with patch("app.services.event_logger.log_event", new=AsyncMock()):
        for i in range(3):
            await service.process_trade_fill(
                wallet_address=addr, condition_id=cid, title="Budget market", side="BUY",
                price=0.5, cash_usd=50000, dt=datetime.utcnow(), asset="asset-budget",
                event_slug="budget", icon="budget", tx_hash="0x" + f"{100+i:064x}", log_index=i,
            )

    async with SessionLocal() as db:
        logs = (await db.execute(select(ExecutionLog).where(
            ExecutionLog.user_id == uid, ExecutionLog.side == "BUY",
            ExecutionLog.status == "FILLED"))).scalars().all()
        spent = sum(float(log.notional_usd or 0) + float(log.fee_usd or 0) for log in logs)
        assert spent > 0, 'Cash conservation must not pass by disabling all buys'
        assert spent <= 100.0 + 1e-6


@pytest.mark.asyncio
async def test_dual_provider_deduplication_with_sufficient_cash():
    addr = "0xbr" + "d" * 38
    cid = "0xcondition_dual"
    tx = "0x" + "e" * 64
    uid = uuid.uuid4()
    async with SessionLocal() as db:
        db.add(Wallet(address=addr, status="active", tier="gold_sniper", dormant=False,
                      is_hft=False, avg_trades_per_day=2, baleen_score=100,
                      all_time_pnl_usd=50000, win_rate_pct=90, wilson_lb=85))
        db.add(User(id=uid, email=f"dual-{uuid.uuid4().hex}@batch-b-review.invalid",
                    sandbox_starting_balance_usd=10000, sandbox_balance_usd=10000,
                    sandbox_high_water_mark_usd=10000))
        await db.commit()

    service = LiveTradeMirrorService()
    with patch("app.services.event_logger.log_event", new=AsyncMock()):
        for log_index in (7, None):
            await service.process_trade_fill(
                wallet_address=addr, condition_id=cid, title="Dual market", side="BUY",
                price=0.5, cash_usd=1000, dt=datetime.utcnow(), asset="asset-dual",
                event_slug="dual", icon="dual", tx_hash=tx, log_index=log_index,
            )

    async with SessionLocal() as db:
        rows = (await db.execute(select(ExecutionLog).where(
            ExecutionLog.user_id == uid, ExecutionLog.onchain_tx_hash == tx))).scalars().all()
        assert len(rows) == 1
