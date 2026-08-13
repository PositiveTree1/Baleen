-- BALEEN — PostgreSQL Schema (§2 of spec)
-- For local dev, this is translated to SQLAlchemy models that work with SQLite.
-- This file serves as the canonical schema reference for production PostgreSQL.

-- WALLETS: current + historical basket members
CREATE TABLE wallets (
    address TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',        -- pending | active | rejected
    tier TEXT NOT NULL DEFAULT 'standard',          -- gold_sniper | standard
    all_time_pnl_usd NUMERIC(14,2) DEFAULT 0,
    win_rate_pct NUMERIC(5,2) DEFAULT 0,
    total_trades_analyzed INT DEFAULT 0,
    avg_trades_per_day NUMERIC(6,2) DEFAULT 0,
    median_inter_trade_gap_hours NUMERIC(8,2) DEFAULT 0,
    max_drawdown_pct NUMERIC(5,2) DEFAULT 0,
    outlier_concentration_pct NUMERIC(5,2) DEFAULT 0,
    baleen_score NUMERIC(8,2) DEFAULT 0,
    rejection_reason TEXT,
    ai_summary TEXT,
    ai_style_tag TEXT,
    dormant BOOLEAN NOT NULL DEFAULT false,
    first_seen_at TIMESTAMPTZ DEFAULT now(),
    last_scored_at TIMESTAMPTZ DEFAULT now()
);

-- WALLET_SNAPSHOTS: append-only score history, powers decay visualization
CREATE TABLE wallet_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_address TEXT REFERENCES wallets(address) ON DELETE CASCADE,
    baleen_score NUMERIC(8,2),
    win_rate_pct NUMERIC(5,2),
    pnl_usd NUMERIC(14,2),
    snapshot_at TIMESTAMPTZ DEFAULT now()
);

-- USERS
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    google_id TEXT UNIQUE,
    risk_profile TEXT NOT NULL DEFAULT 'balanced',
    sandbox_starting_balance_usd NUMERIC(14,2) NOT NULL,
    sandbox_balance_usd NUMERIC(14,2) NOT NULL,
    sandbox_high_water_mark_usd NUMERIC(14,2) NOT NULL,
    live_trading_enabled BOOLEAN NOT NULL DEFAULT false,
    live_high_water_mark_usd NUMERIC(14,2),
    daily_digest_opt_in BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- LIVE_WALLET_LINKS (Phase 2)
CREATE TABLE live_wallet_links (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    provider_user_id TEXT NOT NULL,
    polymarket_wallet_address TEXT NOT NULL,
    clob_api_key_enc BYTEA,
    kms_key_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ
);

-- EXECUTION_LOGS: the audit trail
CREATE TABLE execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    source_wallet_address TEXT NOT NULL,
    market_condition_id TEXT NOT NULL,
    market_question TEXT,
    side TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
    whale_entry_price NUMERIC(6,4) NOT NULL,
    user_fill_price NUMERIC(6,4),
    notional_usd NUMERIC(14,2) NOT NULL,
    active_basket_size_at_trade INT NOT NULL,
    is_sandbox BOOLEAN NOT NULL,
    status TEXT NOT NULL,
    failure_detail TEXT,
    latency_ms INT,
    resolution_outcome TEXT,
    realized_pnl_usd NUMERIC(14,2),
    onchain_tx_hash TEXT,
    onchain_log_index INT,
    executed_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    UNIQUE(onchain_tx_hash, onchain_log_index, user_id)
);

CREATE INDEX idx_execution_logs_user_time ON execution_logs(user_id, executed_at DESC);
CREATE INDEX idx_wallets_status_tier ON wallets(status, tier);

-- FEE_CHARGES: performance-fee billing history (Phase 2)
CREATE TABLE fee_charges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    starting_high_water_mark_usd NUMERIC(14,2) NOT NULL,
    ending_value_usd NUMERIC(14,2) NOT NULL,
    profit_above_hwm_usd NUMERIC(14,2) NOT NULL,
    fee_pct NUMERIC(5,2) NOT NULL,
    fee_amount_usd NUMERIC(14,2) NOT NULL,
    charged_at TIMESTAMPTZ DEFAULT now()
);
