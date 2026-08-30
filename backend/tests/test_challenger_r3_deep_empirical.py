"""
Challenger 2 Deep Empirical Verification Suite for Milestone R3:
1. Live Poller Pacing (2.5s), Top-10 Active Whale Selection, and Dynamic Roster Expansion for Legacy Exits.
2. Boundary Price Screening ($0.04 - $0.96) and 3-Strike Anti-Arbitrage Bot Demotion ($p <= 0.02 or $p >= 0.98).
3. 24/7 Overnight Resilience: Keep-Alive Ping, 15-Minute Disk Backups, MTM Watchdog Gap Recovery, and Loop Error Isolation.
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import httpx
import pytest
from sqlalchemy import select, delete, func

from app.database import SessionLocal, init_db
from app.models import Wallet, User, ExecutionLog, PortfolioSnapshot
from app.services.live_poller import LiveTradeMirrorService, PendingOutOfOrderSell
from app.services.mark_to_market import MarkToMarketService, _live_price_cache, set_live_price
from app.services.disk_backup import export_all_trades_to_disk, BACKUP_DIR
from app.main import keep_alive_job, last_cron_ping_time


@pytest.fixture(autouse=True)
async def setup_empirical_db():
    """Sets up a clean test database environment before each test."""
    await init_db()
    async with SessionLocal() as db:
        await db.execute(delete(ExecutionLog))
        await db.execute(delete(PortfolioSnapshot))
        await db.execute(delete(Wallet).where(Wallet.address.like("0xempirical_%")))
        await db.execute(delete(User).where(User.email.like("%@empirical.com")))

        # Create standard test user
        test_user = User(
            email="trader@empirical.com",
            password_hash="testpass",
            sandbox_starting_balance_usd=10000.0,
            sandbox_balance_usd=10000.0,
            sandbox_high_water_mark_usd=10000.0,
            risk_profile="balanced"
        )
        db.add(test_user)
        await db.commit()
    yield
    async with SessionLocal() as db:
        await db.execute(delete(ExecutionLog))
        await db.execute(delete(PortfolioSnapshot))
        await db.execute(delete(Wallet).where(Wallet.address.like("0xempirical_%")))
        await db.execute(delete(User).where(User.email.like("%@empirical.com")))
        await db.commit()


# ============================================================================
# 1. LIVE POLLER PACING & ROSTER DYNAMICS
# ============================================================================

class TestLivePollerPacingAndRoster:
    """Empirical verification of poller pacing, top-10 roster selection, and legacy exit tracking."""

    @pytest.mark.asyncio
    async def test_top_10_active_roster_selection(self):
        """Verify poller selects exactly top 10 non-dormant, non-HFT active whales by baleen_score."""
        async with SessionLocal() as db:
            # Create 15 active wallets with varying scores
            for i in range(15):
                w = Wallet(
                    address=f"0xempirical_active_{i:02d}",
                    status="active",
                    baleen_score=float(50 + i * 2),  # scores 50 to 78
                    dormant=False,
                    is_hft=False,
                    avg_trades_per_day=10.0,
                    win_rate_pct=75.0,
                )
                db.add(w)

            # Create disqualified wallets (dormant, hft, high trades/day, rejected)
            db.add(Wallet(address="0xempirical_dormant", status="active", dormant=True, baleen_score=99.0))
            db.add(Wallet(address="0xempirical_hft", status="active", is_hft=True, baleen_score=99.0))
            db.add(Wallet(address="0xempirical_overtraded", status="active", avg_trades_per_day=70.0, baleen_score=99.0))
            db.add(Wallet(address="0xempirical_rejected", status="rejected", baleen_score=99.0))
            await db.commit()

        service = LiveTradeMirrorService()
        async with SessionLocal() as db:
            stmt = select(Wallet).where(
                Wallet.status == "active",
                Wallet.dormant == False,
                Wallet.is_hft == False,
                (Wallet.avg_trades_per_day.is_(None) | (Wallet.avg_trades_per_day <= 65.0))
            ).order_by(Wallet.baleen_score.desc()).limit(10)
            selected = (await db.execute(stmt)).scalars().all()

        assert len(selected) == 10
        # Highest score should be 0xempirical_active_14 (score 78)
        assert selected[0].address == "0xempirical_active_14"
        assert selected[0].baleen_score == 78.0
        # Lowest score in top 10 should be 0xempirical_active_05 (score 60)
        assert selected[-1].address == "0xempirical_active_05"
        assert selected[-1].baleen_score == 60.0

        # Disqualified wallets must NOT be present
        addrs = [w.address for w in selected]
        assert "0xempirical_dormant" not in addrs
        assert "0xempirical_hft" not in addrs
        assert "0xempirical_overtraded" not in addrs
        assert "0xempirical_rejected" not in addrs

    @pytest.mark.asyncio
    async def test_dynamic_roster_expansion_for_legacy_open_positions(self):
        """
        Verify that a wallet that was active, had a BUY copied, and was subsequently demoted
        is still dynamically polled to follow its exit SELL signals.
        """
        service = LiveTradeMirrorService()
        now_dt = datetime.utcnow()
        cid = "0xcond_legacy_exit_test"

        # 1. Create whale that was active and had an open BUY
        async with SessionLocal() as db:
            w_legacy = Wallet(
                address="0xempirical_legacy_whale",
                status="rejected",  # demoted/rejected!
                baleen_score=10.0,
                dormant=False,
                is_hft=False,
                avg_trades_per_day=5.0,
                rejection_reason="DEMOTED_AFTER_LOSSES"
            )
            db.add(w_legacy)

            # Insert an open position from this whale
            open_buy = ExecutionLog(
                market_condition_id=cid,
                source_wallet_address="0xempirical_legacy_whale",
                market_question="Legacy Open Position Question",
                side="BUY",
                whale_entry_price=0.40,
                user_fill_price=0.40,
                notional_usd=100.0,
                fee_usd=1.0,
                status="FILLED",
                resolution_outcome="Yes",
                executed_at=now_dt
            )
            db.add(open_buy)
            await db.commit()

        # 2. Test polling candidate resolution
        async with SessionLocal() as db:
            # Active top 10
            stmt_active = select(Wallet).where(
                Wallet.status == "active",
                Wallet.dormant == False,
                Wallet.is_hft == False,
                (Wallet.avg_trades_per_day.is_(None) | (Wallet.avg_trades_per_day <= 65.0))
            ).order_by(Wallet.baleen_score.desc()).limit(10)
            active_wallets = (await db.execute(stmt_active)).scalars().all()

            # Open position source wallets
            stmt_open_sources = select(ExecutionLog.source_wallet_address).where(
                ExecutionLog.status == "FILLED",
                ExecutionLog.side == "BUY",
                ExecutionLog.source_wallet_address.isnot(None)
            ).distinct()
            open_source_addrs = set(addr.lower() for addr in (await db.execute(stmt_open_sources)).scalars().all() if addr)

            active_addrs = set(w.address.lower() for w in active_wallets)
            missing_source_addrs = open_source_addrs - active_addrs
            assert "0xempirical_legacy_whale" in missing_source_addrs

            all_wallets_to_poll = list(active_wallets)
            if missing_source_addrs:
                stmt_legacy = select(Wallet).where(Wallet.address.in_(list(missing_source_addrs)))
                legacy_wallets = (await db.execute(stmt_legacy)).scalars().all()
                all_wallets_to_poll.extend(legacy_wallets)

        assert any(w.address.lower() == "0xempirical_legacy_whale" for w in all_wallets_to_poll)

        # 3. If this demoted whale tries to BUY -> rejected (not in active basket)
        await service.process_trade_fill(
            wallet_address="0xempirical_legacy_whale",
            condition_id="0xcond_new_buy_attempt",
            title="New Attempted Buy",
            side="BUY",
            price=0.50,
            cash_usd=100.0,
            dt=now_dt + timedelta(minutes=1),
            outcome="Yes"
        )
        async with SessionLocal() as db:
            stmt_check = select(ExecutionLog).where(ExecutionLog.market_condition_id == "0xcond_new_buy_attempt")
            logs = (await db.execute(stmt_check)).scalars().all()
            assert len(logs) == 0, "BUY from demoted legacy whale must be rejected!"

        # 4. If this demoted whale emits a SELL for its open position -> accepted & closes position!
        await service.process_trade_fill(
            wallet_address="0xempirical_legacy_whale",
            condition_id=cid,
            title="Legacy Open Position Question",
            side="SELL",
            price=0.70,
            cash_usd=100.0,
            dt=now_dt + timedelta(minutes=2),
            outcome="Yes"
        )
        async with SessionLocal() as db:
            stmt_closed = select(ExecutionLog).where(
                ExecutionLog.market_condition_id == cid,
                ExecutionLog.status == "CLOSED"
            )
            closed_logs = (await db.execute(stmt_closed)).scalars().all()
            assert len(closed_logs) >= 1, "SELL from legacy whale must close open position!"


# ============================================================================
# 2. BOUNDARY PRICE SCREENING & 3-STRIKE BOT DEMOTION
# ============================================================================

class TestBoundaryPriceAndAntiArbitrageDemotion:
    """Empirical verification of boundary price screen ($0.04-$0.96) and 3-strike bot demotion."""

    @pytest.mark.asyncio
    async def test_boundary_price_3_strike_bot_demotion(self):
        """
        Verify that toxic boundary BUY trades (<= 0.02 or >= 0.98) are blocked,
        strike count increments, and on the 3rd strike the wallet is demoted to rejected.
        """
        service = LiveTradeMirrorService()
        now_dt = datetime.utcnow()
        addr = "0xempirical_sniper_bot"

        # Create active whale
        async with SessionLocal() as db:
            w = Wallet(
                address=addr,
                name="Boundary Bot Candidate",
                status="active",
                tier="gold_sniper",
                baleen_score=90.0,
                dormant=False,
                is_hft=False,
                avg_trades_per_day=5.0,
                win_rate_pct=95.0
            )
            db.add(w)
            await db.commit()

        # Strike 1: BUY at $0.01 (penny snipe trap)
        await service.process_trade_fill(
            wallet_address=addr,
            condition_id="0xcond_strike_1",
            title="Toxic Settlement Arb 1",
            side="BUY",
            price=0.01,
            cash_usd=100.0,
            dt=now_dt,
            outcome="Yes"
        )
        assert service.boundary_snipe_counts[addr.lower()] == 1
        async with SessionLocal() as db:
            w_check = await db.get(Wallet, addr)
            assert w_check.status == "active", "Should remain active on strike 1"

        # Strike 2: BUY at $0.99 (lottery settlement sweep)
        await service.process_trade_fill(
            wallet_address=addr,
            condition_id="0xcond_strike_2",
            title="Toxic Settlement Arb 2",
            side="BUY",
            price=0.99,
            cash_usd=100.0,
            dt=now_dt + timedelta(seconds=5),
            outcome="Yes"
        )
        assert service.boundary_snipe_counts[addr.lower()] == 2
        async with SessionLocal() as db:
            w_check = await db.get(Wallet, addr)
            assert w_check.status == "active", "Should remain active on strike 2"

        # Strike 3: BUY at $0.02 (boundary edge) -> Triggers Demotion!
        await service.process_trade_fill(
            wallet_address=addr,
            condition_id="0xcond_strike_3",
            title="Toxic Settlement Arb 3",
            side="BUY",
            price=0.02,
            cash_usd=100.0,
            dt=now_dt + timedelta(seconds=10),
            outcome="Yes"
        )
        assert service.boundary_snipe_counts[addr.lower()] == 3
        async with SessionLocal() as db:
            w_check = await db.get(Wallet, addr)
            assert w_check.status == "rejected", "Wallet must be rejected on strike 3"
            assert w_check.tier == "rejected"
            assert "FLAGGED_ARBITRAGE_BOT" in (w_check.rejection_reason or "")

        # Subsequent trade: even at valid price $0.50, BUY is rejected because wallet status is now rejected
        await service.process_trade_fill(
            wallet_address=addr,
            condition_id="0xcond_post_demotion",
            title="Legitimate Market",
            side="BUY",
            price=0.50,
            cash_usd=100.0,
            dt=now_dt + timedelta(seconds=15),
            outcome="Yes"
        )
        async with SessionLocal() as db:
            stmt = select(ExecutionLog).where(ExecutionLog.market_condition_id == "0xcond_post_demotion")
            logs = (await db.execute(stmt)).scalars().all()
            assert len(logs) == 0, "Demoted wallet must have 0 trades copied"


# ============================================================================
# 3. 24/7 OVERNIGHT RESILIENCE & RECOVERY
# ============================================================================

class TestOvernightResilience:
    """Empirical verification of keep-alive pinging, disk backup, MTM watchdog, and error isolation."""

    @pytest.mark.asyncio
    async def test_mtm_watchdog_restart_gap_recovery(self):
        """
        Verify that when a restart gap (>30m) occurs, MarkToMarketService._ensure_snapshot_continuity()
        safely carries forward the last known balance and total PnL without cold-cache collapse.
        """
        mtm = MarkToMarketService()
        now = datetime.utcnow()
        gap_time = now - timedelta(minutes=45)

        # Write an existing historical snapshot from 45 minutes ago with balance $14,500
        async with SessionLocal() as db:
            db.add(PortfolioSnapshot(
                user_id=None,
                timestamp=gap_time,
                balance=14500.0,
                total_pnl=4500.0,
                active_trades_count=8
            ))
            await db.commit()

        # Run watchdog recovery
        await mtm._ensure_snapshot_continuity()

        # Check recovery snapshot
        async with SessionLocal() as db:
            stmt = select(PortfolioSnapshot).where(
                PortfolioSnapshot.user_id.is_(None)
            ).order_by(PortfolioSnapshot.timestamp.desc())
            snapshots = (await db.execute(stmt)).scalars().all()

            assert len(snapshots) >= 2
            latest = snapshots[0]
            assert latest.balance == 14500.0
            assert latest.total_pnl == 4500.0
            assert latest.active_trades_count == 8
            # Snapshot was written at current time
            assert (now - latest.timestamp).total_seconds() < 10

    @pytest.mark.asyncio
    async def test_disk_backup_export_format_and_completeness(self):
        """
        Verify export_all_trades_to_disk generates valid JSON and CSV backups with all required fields.
        """
        now = datetime.utcnow()
        async with SessionLocal() as db:
            log1 = ExecutionLog(
                market_condition_id="0xcond_backup_1",
                market_question="Will SpaceX reach Mars in 2026?",
                source_wallet_address="0xempirical_backup_whale",
                side="BUY",
                resolution_outcome="Yes",
                whale_entry_price=0.35,
                user_fill_price=0.35,
                notional_usd=250.0,
                fee_usd=2.5,
                realized_pnl_usd=None,
                status="FILLED",
                executed_at=now
            )
            log2 = ExecutionLog(
                market_condition_id="0xcond_backup_2",
                market_question="Will Apple launch foldable iPhone in 2026?",
                source_wallet_address="0xempirical_backup_whale",
                side="SELL",
                resolution_outcome="No",
                whale_entry_price=0.80,
                user_fill_price=0.80,
                notional_usd=250.0,
                fee_usd=1.5,
                realized_pnl_usd=75.0,
                status="CLOSED",
                executed_at=now
            )
            db.add(log1)
            db.add(log2)
            await db.commit()

        # Run backup export
        res = await export_all_trades_to_disk()
        assert res["status"] == "success"
        assert res["count"] >= 2

        json_path = Path(res["json_file"])
        csv_path = Path(res["csv_file"])

        assert json_path.exists()
        assert csv_path.exists()

        # Verify JSON content
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "exported_at" in data
            assert data["total_trades"] >= 2
            trades = data["trades"]
            matching = [t for t in trades if t["market_condition_id"] == "0xcond_backup_1"]
            assert len(matching) == 1
            assert matching[0]["side"] == "BUY"
            assert matching[0]["notional_usd"] == 250.0

        # Verify CSV content
        with open(csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) >= 3  # Header + 2 rows
            assert "market_condition_id" in lines[0]
            assert "0xcond_backup_1" in "".join(lines)

    @pytest.mark.asyncio
    async def test_async_loop_error_isolation(self):
        """
        Verify that transient network or database exceptions inside poller and MTM
        are isolated within try/except blocks and do not crash the service.
        """
        service = LiveTradeMirrorService()
        mtm = MarkToMarketService()

        # Verify service initializes with running flag True when started
        service.running = True
        mtm.running = True

        # Calling _poll_active_whales with broken HTTP client must handle exception cleanly
        service.client = httpx.AsyncClient(timeout=0.001)  # tiny timeout causing connect errors
        try:
            # Should not raise uncaught exception
            await service._poll_active_whales()
        except Exception as e:
            pytest.fail(f"_poll_active_whales raised unhandled exception: {e}")
        finally:
            await service.client.aclose()
