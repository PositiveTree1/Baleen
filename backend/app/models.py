import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from app.database import Base

# Polyfill for generic UUID handling in SQLite vs Postgres
import sqlalchemy.types as types

class GUID(types.TypeDecorator):
    impl = types.CHAR
    cache_ok = True
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PGUUID())
        else:
            return dialect.type_descriptor(types.CHAR(32))
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                return "%.32x" % value.int
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value

class Wallet(Base):
    __tablename__ = "wallets"

    address = Column(String, primary_key=True, index=True)
    status = Column(String, default="pending")
    tier = Column(String, nullable=True)
    all_time_pnl_usd = Column(Float, nullable=True)
    win_rate_pct = Column(Float, nullable=True)
    total_trades_analyzed = Column(Integer, nullable=True)
    avg_trades_per_day = Column(Float, nullable=True)
    median_inter_trade_gap_hours = Column(Float, nullable=True)
    max_drawdown_pct = Column(Float, nullable=True)
    outlier_concentration_pct = Column(Float, nullable=True)
    baleen_score = Column(Float, nullable=True)
    rejection_reason = Column(String, nullable=True)
    ai_summary = Column(String, nullable=True)
    ai_style_tag = Column(String, nullable=True)
    dormant = Column(Boolean, default=False)
    is_hft = Column(Boolean, default=False)
    trades_per_hour = Column(Float, nullable=True)
    wilson_lb = Column(Float, nullable=True)
    alpha_per_trade = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    first_trade_at = Column(DateTime, nullable=True)
    last_trade_at = Column(DateTime, nullable=True)
    cached_daily_pnl = Column(String, nullable=True)
    name = Column(String, nullable=True)
    pseudonym = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_scored_at = Column(DateTime, nullable=True)

class WalletSnapshot(Base):
    __tablename__ = "wallet_snapshots"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    wallet_address = Column(String, ForeignKey("wallets.address"))
    baleen_score = Column(Float, nullable=True)
    win_rate_pct = Column(Float, nullable=True)
    pnl_usd = Column(Float, nullable=True)
    snapshot_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    google_id = Column(String, unique=True, nullable=True)
    risk_profile = Column(String, default="balanced")
    sandbox_starting_balance_usd = Column(Float, default=10000.0)
    sandbox_balance_usd = Column(Float, default=10000.0)
    sandbox_high_water_mark_usd = Column(Float, default=10000.0)
    live_trading_enabled = Column(Boolean, default=False)
    live_high_water_mark_usd = Column(Float, nullable=True)
    daily_digest_opt_in = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LiveWalletLink(Base):
    __tablename__ = "live_wallet_links"

    user_id = Column(GUID(), ForeignKey("users.id"), primary_key=True)
    provider = Column(String)
    provider_user_id = Column(String)
    polymarket_wallet_address = Column(String)
    clob_api_key_enc = Column(String)
    clob_api_secret_enc = Column(String, nullable=True)
    clob_api_passphrase_enc = Column(String, nullable=True)
    is_live_active = Column(Boolean, default=False)
    live_balance_usdc = Column(Float, default=0.0)
    last_verified_at = Column(DateTime, nullable=True)
    kms_key_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"))
    source_wallet_address = Column(String, ForeignKey("wallets.address"))
    market_condition_id = Column(String)
    market_question = Column(String)
    event_slug = Column(String, nullable=True)
    icon = Column(String, nullable=True)
    side = Column(String) # BUY or SELL
    whale_entry_price = Column(Float)
    user_fill_price = Column(Float, nullable=True)
    notional_usd = Column(Float)
    active_basket_size_at_trade = Column(Integer)
    is_sandbox = Column(Boolean, default=True)
    status = Column(String)
    failure_detail = Column(String, nullable=True)
    latency_ms = Column(Float, nullable=True)
    resolution_outcome = Column(String, nullable=True)
    realized_pnl_usd = Column(Float, nullable=True)
    fee_usd = Column(Float, default=0.0)
    market_category = Column(String, default="General")
    onchain_tx_hash = Column(String, nullable=True)
    onchain_log_index = Column(Integer, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint('onchain_tx_hash', 'onchain_log_index', 'user_id', name='uix_tx_log_user'),
        CheckConstraint(side.in_(['BUY', 'SELL']), name='check_side_buy_sell')
    )

class FeeCharge(Base):
    __tablename__ = "fee_charges"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"))
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    starting_high_water_mark_usd = Column(Float)
    ending_value_usd = Column(Float)
    profit_above_hwm_usd = Column(Float)
    fee_pct = Column(Float)
    fee_amount_usd = Column(Float)
    charged_at = Column(DateTime, default=datetime.utcnow)

class KeyValue(Base):
    """Simple key-value store for persisting lightweight state across restarts.
    Used for discovery progress, last scan timestamps, etc."""
    __tablename__ = "kv_store"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    balance = Column(Float, nullable=False)
    total_pnl = Column(Float, nullable=False)
    active_trades_count = Column(Integer, default=0)

class SystemEvent(Base):
    __tablename__ = "system_events"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_type = Column(String, index=True)  # TRADE_COPIED, WALLET_DISCOVERED, WALLET_REJECTED, TRADE_SKIPPED, WALLET_PROMOTED, WALLET_DORMANT
    severity = Column(String, default="info")  # info, warning, success, error
    title = Column(String)
    detail = Column(String, nullable=True)
    related_address = Column(String, nullable=True)
    related_market = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class SandboxRun(Base):
    __tablename__ = "sandbox_runs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    run_number = Column(Integer, autoincrement=True, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    initial_balance_usd = Column(Float, default=10000.0)
    final_balance_usd = Column(Float, nullable=True)
    total_realized_pnl_usd = Column(Float, default=0.0)
    total_fees_paid_usd = Column(Float, default=0.0)
    total_trades_copied = Column(Integer, default=0)
    winning_trades_count = Column(Integer, default=0)
    losing_trades_count = Column(Integer, default=0)
    win_rate_pct = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    high_water_mark_usd = Column(Float, default=10000.0)
    total_reevaluations_count = Column(Integer, default=0)
    active_whales_roster = Column(JSON, nullable=True) # Native JSON / JSONB
    status = Column(String, default="ACTIVE") # ACTIVE, COMPLETED, RESET

class SandboxReevaluation(Base):
    __tablename__ = "sandbox_reevaluations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    run_id = Column(GUID(), ForeignKey("sandbox_runs.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    trigger_type = Column(String, default="SCHEDULED_CRON") # SCHEDULED_CRON, STARTUP_SYNC, MANUAL_SCAN, THRESHOLD_CHANGE
    total_candidates_scanned = Column(Integer, default=0)
    qualified_whales_count = Column(Integer, default=0)
    rejected_whales_count = Column(Integer, default=0)
    top10_active_roster = Column(JSON, nullable=True) # Native JSON / JSONB
    promotions = Column(JSON, nullable=True) # Native JSON / JSONB
    demotions = Column(JSON, nullable=True) # Native JSON / JSONB
    execution_duration_ms = Column(Float, default=0.0)


