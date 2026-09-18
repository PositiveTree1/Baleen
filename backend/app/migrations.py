import logging
from datetime import datetime
from typing import List, Tuple
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)

MIGRATION_TABLE_SQL_SQLITE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

MIGRATION_TABLE_SQL_POSTGRES = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

# Migration definitions: (version, name, [sqlite_sqls], [postgres_sqls])
MIGRATIONS: List[Tuple[int, str, List[str], List[str]]] = [
    (
        1,
        "base_schema",
        [],  # Base tables handled by Base.metadata.create_all
        [],
    ),
    (
        2,
        "metadata_columns",
        [
            "ALTER TABLE wallets ADD COLUMN pseudonym VARCHAR(255);",
            "ALTER TABLE wallets ADD COLUMN profile_image TEXT;",
            "ALTER TABLE execution_logs ADD COLUMN event_slug VARCHAR(255);",
            "ALTER TABLE execution_logs ADD COLUMN icon TEXT;",
            "ALTER TABLE execution_logs ADD COLUMN fee_usd FLOAT;",
            "ALTER TABLE execution_logs ADD COLUMN market_category VARCHAR(100);",
            "ALTER TABLE execution_logs ADD COLUMN resolution_outcome VARCHAR(255);",
            "ALTER TABLE execution_logs ADD COLUMN realized_pnl_usd FLOAT;",
            "ALTER TABLE execution_logs ADD COLUMN onchain_tx_hash VARCHAR(255);",
            "ALTER TABLE execution_logs ADD COLUMN onchain_log_index INTEGER;",
        ],
        [
            "ALTER TABLE wallets ADD COLUMN IF NOT EXISTS pseudonym VARCHAR(255);",
            "ALTER TABLE wallets ADD COLUMN IF NOT EXISTS profile_image TEXT;",
            "ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS event_slug VARCHAR(255);",
            "ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS icon TEXT;",
            "ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS fee_usd FLOAT;",
            "ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS market_category VARCHAR(100);",
            "ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS resolution_outcome VARCHAR(255);",
            "ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS realized_pnl_usd FLOAT;",
            "ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS onchain_tx_hash VARCHAR(255);",
            "ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS onchain_log_index INTEGER;",
        ],
    ),
    (
        3,
        "user_roles_and_admin",
        [
            "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user';",
        ],
        [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user';",
        ],
    ),
    (
        4,
        "live_wallet_encryption",
        [
            "ALTER TABLE live_wallet_links ADD COLUMN clob_api_secret_enc TEXT;",
            "ALTER TABLE live_wallet_links ADD COLUMN clob_api_passphrase_enc TEXT;",
            "ALTER TABLE live_wallet_links ADD COLUMN is_live_active BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE live_wallet_links ADD COLUMN live_balance_usdc FLOAT DEFAULT 0.0;",
            "ALTER TABLE live_wallet_links ADD COLUMN last_verified_at TIMESTAMP;",
        ],
        [
            "ALTER TABLE live_wallet_links ADD COLUMN IF NOT EXISTS clob_api_secret_enc TEXT;",
            "ALTER TABLE live_wallet_links ADD COLUMN IF NOT EXISTS clob_api_passphrase_enc TEXT;",
            "ALTER TABLE live_wallet_links ADD COLUMN IF NOT EXISTS is_live_active BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE live_wallet_links ADD COLUMN IF NOT EXISTS live_balance_usdc FLOAT DEFAULT 0.0;",
            "ALTER TABLE live_wallet_links ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMP WITH TIME ZONE;",
        ],
    ),
    (
        5,
        "ledger_and_execution_indexes",
        [
            "CREATE INDEX IF NOT EXISTS idx_exec_user_status ON execution_logs (user_id, status);",
            "CREATE INDEX IF NOT EXISTS idx_exec_market_cond ON execution_logs (market_condition_id);",
            "CREATE INDEX IF NOT EXISTS idx_snapshot_user_ts ON portfolio_snapshots (user_id, timestamp);",
        ],
        [
            "CREATE INDEX IF NOT EXISTS idx_exec_user_status ON execution_logs (user_id, status);",
            "CREATE INDEX IF NOT EXISTS idx_exec_market_cond ON execution_logs (market_condition_id);",
            "CREATE INDEX IF NOT EXISTS idx_snapshot_user_ts ON portfolio_snapshots (user_id, timestamp);",
        ],
    ),
    (
        6, "durable_security_state",
        [
            "CREATE TABLE IF NOT EXISTS revoked_access_tokens (token_hash VARCHAR(64) PRIMARY KEY, expires_at FLOAT NOT NULL)",
            "CREATE INDEX IF NOT EXISTS ix_revoked_access_tokens_expires_at ON revoked_access_tokens (expires_at)",
            "CREATE TABLE IF NOT EXISTS rate_limit_buckets (key VARCHAR(64) PRIMARY KEY, expires_at FLOAT NOT NULL, count INTEGER NOT NULL)",
            "CREATE INDEX IF NOT EXISTS ix_rate_limit_buckets_expires_at ON rate_limit_buckets (expires_at)",
        ],
        [
            "CREATE TABLE IF NOT EXISTS revoked_access_tokens (token_hash VARCHAR(64) PRIMARY KEY, expires_at DOUBLE PRECISION NOT NULL)",
            "CREATE INDEX IF NOT EXISTS ix_revoked_access_tokens_expires_at ON revoked_access_tokens (expires_at)",
            "CREATE TABLE IF NOT EXISTS rate_limit_buckets (key VARCHAR(64) PRIMARY KEY, expires_at DOUBLE PRECISION NOT NULL, count INTEGER NOT NULL)",
            "CREATE INDEX IF NOT EXISTS ix_rate_limit_buckets_expires_at ON rate_limit_buckets (expires_at)",
        ],
    ),
    (
        7, "canonical_ingestion_and_isolated_exposure",
        [
            "CREATE TABLE IF NOT EXISTS signal_inbox (id CHAR(32) PRIMARY KEY, source VARCHAR(50) NOT NULL, idempotency_key VARCHAR(255) NOT NULL UNIQUE, payload TEXT NOT NULL, status VARCHAR(50) NOT NULL DEFAULT 'PENDING', received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, processed_at TIMESTAMP, error_detail TEXT);",
            "CREATE INDEX IF NOT EXISTS ix_signal_inbox_status ON signal_inbox (status);",
            "CREATE TABLE IF NOT EXISTS canonical_source_events (id CHAR(32) PRIMARY KEY, chain_id INTEGER NOT NULL DEFAULT 137, emitting_contract VARCHAR(66), tx_hash VARCHAR(66) NOT NULL, log_index INTEGER, block_number BIGINT, block_hash VARCHAR(66), block_time TIMESTAMP, source_wallet_address VARCHAR(42) NOT NULL, maker_address VARCHAR(42), taker_address VARCHAR(42), condition_id VARCHAR(66), token_id VARCHAR(100), outcome VARCHAR(50), side VARCHAR(10) NOT NULL, price FLOAT NOT NULL, shares FLOAT NOT NULL, notional_usd FLOAT NOT NULL, status VARCHAR(50) NOT NULL DEFAULT 'CONFIRMED', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);",
            "CREATE INDEX IF NOT EXISTS ix_canonical_tx_log_wallet ON canonical_source_events (tx_hash, log_index, source_wallet_address);",
            "CREATE INDEX IF NOT EXISTS ix_canonical_tx_wallet ON canonical_source_events (tx_hash, source_wallet_address);",
            "ALTER TABLE execution_logs ADD COLUMN token_id VARCHAR(100);",
            "ALTER TABLE execution_logs ADD COLUMN mode VARCHAR(50) DEFAULT 'sandbox';",
            "ALTER TABLE execution_logs ADD COLUMN run_id CHAR(32);",
            "ALTER TABLE execution_logs ADD COLUMN source_event_id CHAR(32);",
            "CREATE TABLE IF NOT EXISTS exposure_ledger (id CHAR(32) PRIMARY KEY, wallet_address VARCHAR(66) NOT NULL, market_condition_id VARCHAR(100) NOT NULL, outcome VARCHAR(100) NOT NULL, asset_id VARCHAR(100), virtual_position_usd FLOAT NOT NULL DEFAULT 0.0, executed_position_usd FLOAT NOT NULL DEFAULT 0.0, last_whale_price FLOAT, market_question TEXT, status VARCHAR(50) NOT NULL DEFAULT 'accumulating', last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, user_id CHAR(32), mode VARCHAR(50) DEFAULT 'sandbox', run_id CHAR(32));",
            "ALTER TABLE exposure_ledger ADD COLUMN user_id CHAR(32);",
            "ALTER TABLE exposure_ledger ADD COLUMN mode VARCHAR(50) DEFAULT 'sandbox';",
            "ALTER TABLE exposure_ledger ADD COLUMN run_id CHAR(32);",
        ],
        [
            "CREATE TABLE IF NOT EXISTS signal_inbox (id UUID PRIMARY KEY, source VARCHAR(50) NOT NULL, idempotency_key VARCHAR(255) NOT NULL UNIQUE, payload JSONB NOT NULL, status VARCHAR(50) NOT NULL DEFAULT 'PENDING', received_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, processed_at TIMESTAMP WITH TIME ZONE, error_detail TEXT);",
            "CREATE INDEX IF NOT EXISTS ix_signal_inbox_status ON signal_inbox (status);",
            "CREATE TABLE IF NOT EXISTS canonical_source_events (id UUID PRIMARY KEY, chain_id INTEGER NOT NULL DEFAULT 137, emitting_contract VARCHAR(66), tx_hash VARCHAR(66) NOT NULL, log_index INTEGER, block_number BIGINT, block_hash VARCHAR(66), block_time TIMESTAMP WITH TIME ZONE, source_wallet_address VARCHAR(42) NOT NULL, maker_address VARCHAR(42), taker_address VARCHAR(42), condition_id VARCHAR(66), token_id VARCHAR(100), outcome VARCHAR(50), side VARCHAR(10) NOT NULL, price DOUBLE PRECISION NOT NULL, shares DOUBLE PRECISION NOT NULL, notional_usd DOUBLE PRECISION NOT NULL, status VARCHAR(50) NOT NULL DEFAULT 'CONFIRMED', created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);",
            "CREATE INDEX IF NOT EXISTS ix_canonical_tx_log_wallet ON canonical_source_events (tx_hash, log_index, source_wallet_address);",
            "CREATE INDEX IF NOT EXISTS ix_canonical_tx_wallet ON canonical_source_events (tx_hash, source_wallet_address);",
            "ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS token_id VARCHAR(100);",
            "ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS mode VARCHAR(50) DEFAULT 'sandbox';",
            "ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS run_id UUID;",
            "ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS source_event_id UUID;",
            "CREATE TABLE IF NOT EXISTS exposure_ledger (id UUID PRIMARY KEY, wallet_address VARCHAR(66) NOT NULL, market_condition_id VARCHAR(100) NOT NULL, outcome VARCHAR(100) NOT NULL, asset_id VARCHAR(100), virtual_position_usd DOUBLE PRECISION NOT NULL DEFAULT 0.0, executed_position_usd DOUBLE PRECISION NOT NULL DEFAULT 0.0, last_whale_price DOUBLE PRECISION, market_question TEXT, status VARCHAR(50) NOT NULL DEFAULT 'accumulating', last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, user_id UUID, mode VARCHAR(50) DEFAULT 'sandbox', run_id UUID);",
            "ALTER TABLE exposure_ledger ADD COLUMN IF NOT EXISTS user_id UUID;",
            "ALTER TABLE exposure_ledger ADD COLUMN IF NOT EXISTS mode VARCHAR(50) DEFAULT 'sandbox';",
            "ALTER TABLE exposure_ledger ADD COLUMN IF NOT EXISTS run_id UUID;",
        ],
    ),
    (
        8, "signal_retry_state",
        [
            "ALTER TABLE signal_inbox ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE signal_inbox ADD COLUMN retry_at TIMESTAMP",
        ],
        [
            "ALTER TABLE signal_inbox ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE signal_inbox ADD COLUMN IF NOT EXISTS retry_at TIMESTAMP",
        ],
    ),
    (
        9, "live_signer_identity",
        [
            "ALTER TABLE live_wallet_links ADD COLUMN signer_address VARCHAR(42)",
            "ALTER TABLE live_wallet_links ADD COLUMN signature_type INTEGER",
        ],
        [
            "ALTER TABLE live_wallet_links ADD COLUMN IF NOT EXISTS signer_address VARCHAR(42)",
            "ALTER TABLE live_wallet_links ADD COLUMN IF NOT EXISTS signature_type INTEGER",
        ],
    ),
    (10, "live_order_journal",
        ['CREATE TABLE IF NOT EXISTS live_execution_accounts (\n\tuser_id CHAR(32) NOT NULL, \n\trun_id CHAR(32) NOT NULL, \n\twallet_address VARCHAR(42) NOT NULL, \n\tcash NUMERIC(38, 18) NOT NULL, \n\treserved_cash NUMERIC(38, 18) NOT NULL, \n\treconciled_at DATETIME, \n\tenabled BOOLEAN NOT NULL, \n\tPRIMARY KEY (user_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)', 'CREATE TABLE IF NOT EXISTS live_order_intents (\n\tid CHAR(32) NOT NULL, \n\tuser_id CHAR(32) NOT NULL, \n\trun_id CHAR(32) NOT NULL, \n\tintent_key VARCHAR(255) NOT NULL, \n\ttoken_id VARCHAR(100) NOT NULL, \n\tside VARCHAR(4) NOT NULL, \n\tquantity NUMERIC(38, 18) NOT NULL, \n\tlimit_price NUMERIC(38, 18) NOT NULL, \n\tfee_budget NUMERIC(38, 18) NOT NULL, \n\tfilled_quantity NUMERIC(38, 18) NOT NULL, \n\treserved_cash NUMERIC(38, 18) NOT NULL, \n\tstate VARCHAR(24) NOT NULL, \n\tsigned_order_hash VARCHAR(66) NOT NULL, \n\tenvelope JSON NOT NULL, \n\tcreated_at DATETIME NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_live_copy_intent UNIQUE (user_id, run_id, intent_key), \n\tCONSTRAINT uq_live_signed_order UNIQUE (user_id, signed_order_hash), \n\tFOREIGN KEY(user_id) REFERENCES live_execution_accounts (user_id)\n)', 'CREATE TABLE IF NOT EXISTS live_positions (\n\tuser_id CHAR(32) NOT NULL, \n\ttoken_id VARCHAR(100) NOT NULL, \n\tquantity NUMERIC(38, 18) NOT NULL, \n\treserved_quantity NUMERIC(38, 18) NOT NULL, \n\tcost_basis NUMERIC(38, 18) NOT NULL, \n\tPRIMARY KEY (user_id, token_id), \n\tFOREIGN KEY(user_id) REFERENCES live_execution_accounts (user_id)\n)', 'CREATE TABLE IF NOT EXISTS live_confirmed_fills (\n\torder_id CHAR(32) NOT NULL, \n\ttrade_id VARCHAR(255) NOT NULL, \n\tquantity NUMERIC(38, 18) NOT NULL, \n\tprice NUMERIC(38, 18) NOT NULL, \n\tfee NUMERIC(38, 18) NOT NULL, \n\tconfirmed_at DATETIME NOT NULL, \n\tPRIMARY KEY (order_id, trade_id), \n\tFOREIGN KEY(order_id) REFERENCES live_order_intents (id)\n)'],
        ['CREATE TABLE IF NOT EXISTS live_execution_accounts (\n\tuser_id UUID NOT NULL, \n\trun_id UUID NOT NULL, \n\twallet_address VARCHAR(42) NOT NULL, \n\tcash NUMERIC(38, 18) NOT NULL, \n\treserved_cash NUMERIC(38, 18) NOT NULL, \n\treconciled_at TIMESTAMP WITHOUT TIME ZONE, \n\tenabled BOOLEAN NOT NULL, \n\tPRIMARY KEY (user_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)', 'CREATE TABLE IF NOT EXISTS live_order_intents (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\trun_id UUID NOT NULL, \n\tintent_key VARCHAR(255) NOT NULL, \n\ttoken_id VARCHAR(100) NOT NULL, \n\tside VARCHAR(4) NOT NULL, \n\tquantity NUMERIC(38, 18) NOT NULL, \n\tlimit_price NUMERIC(38, 18) NOT NULL, \n\tfee_budget NUMERIC(38, 18) NOT NULL, \n\tfilled_quantity NUMERIC(38, 18) NOT NULL, \n\treserved_cash NUMERIC(38, 18) NOT NULL, \n\tstate VARCHAR(24) NOT NULL, \n\tsigned_order_hash VARCHAR(66) NOT NULL, \n\tenvelope JSON NOT NULL, \n\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_live_copy_intent UNIQUE (user_id, run_id, intent_key), \n\tCONSTRAINT uq_live_signed_order UNIQUE (user_id, signed_order_hash), \n\tFOREIGN KEY(user_id) REFERENCES live_execution_accounts (user_id)\n)', 'CREATE TABLE IF NOT EXISTS live_positions (\n\tuser_id UUID NOT NULL, \n\ttoken_id VARCHAR(100) NOT NULL, \n\tquantity NUMERIC(38, 18) NOT NULL, \n\treserved_quantity NUMERIC(38, 18) NOT NULL, \n\tcost_basis NUMERIC(38, 18) NOT NULL, \n\tPRIMARY KEY (user_id, token_id), \n\tFOREIGN KEY(user_id) REFERENCES live_execution_accounts (user_id)\n)', 'CREATE TABLE IF NOT EXISTS live_confirmed_fills (\n\torder_id UUID NOT NULL, \n\ttrade_id VARCHAR(255) NOT NULL, \n\tquantity NUMERIC(38, 18) NOT NULL, \n\tprice NUMERIC(38, 18) NOT NULL, \n\tfee NUMERIC(38, 18) NOT NULL, \n\tconfirmed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, \n\tPRIMARY KEY (order_id, trade_id), \n\tFOREIGN KEY(order_id) REFERENCES live_order_intents (id)\n)'],
    ),
    (11, "live_reconciliation_evidence",
     ["CREATE TABLE IF NOT EXISTS live_reconciliations (id CHAR(32) PRIMARY KEY, user_id CHAR(32) NOT NULL REFERENCES live_execution_accounts(user_id), started_at DATETIME NOT NULL, finished_at DATETIME, status VARCHAR(24) NOT NULL, detail VARCHAR(255), observed_cash NUMERIC(38,18))",
      "CREATE INDEX IF NOT EXISTS ix_live_reconciliations_user_id ON live_reconciliations(user_id)"],
     ["CREATE TABLE IF NOT EXISTS live_reconciliations (id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES live_execution_accounts(user_id), started_at TIMESTAMP NOT NULL, finished_at TIMESTAMP, status VARCHAR(24) NOT NULL, detail VARCHAR(255), observed_cash NUMERIC(38,18))",
      "CREATE INDEX IF NOT EXISTS ix_live_reconciliations_user_id ON live_reconciliations(user_id)"]),
    (12, "account_owned_paper_runs",
     ["ALTER TABLE users ADD COLUMN active_paper_run_id CHAR(32)",
      "ALTER TABLE sandbox_runs ADD COLUMN user_id CHAR(32) REFERENCES users(id)",
      "ALTER TABLE sandbox_runs ADD COLUMN source_cutoff_at TIMESTAMP",
      "ALTER TABLE portfolio_snapshots ADD COLUMN run_id CHAR(32) REFERENCES sandbox_runs(id)",
      "CREATE UNIQUE INDEX IF NOT EXISTS uq_active_user_paper_run ON sandbox_runs(user_id) WHERE user_id IS NOT NULL AND status = 'ACTIVE'"],
     ["ALTER TABLE users ADD COLUMN IF NOT EXISTS active_paper_run_id UUID",
      "ALTER TABLE sandbox_runs ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id)",
      "ALTER TABLE sandbox_runs ADD COLUMN IF NOT EXISTS source_cutoff_at TIMESTAMP",
      "ALTER TABLE portfolio_snapshots ADD COLUMN IF NOT EXISTS run_id UUID REFERENCES sandbox_runs(id)",
      "CREATE UNIQUE INDEX IF NOT EXISTS uq_active_user_paper_run ON sandbox_runs(user_id) WHERE user_id IS NOT NULL AND status = 'ACTIVE'"]),
    (13, "durable_live_cancel_requests",
     ["ALTER TABLE live_order_intents ADD COLUMN cancel_requested_at TIMESTAMP"],
     ["ALTER TABLE live_order_intents ADD COLUMN IF NOT EXISTS cancel_requested_at TIMESTAMP"]),
    (14, "exact_settlement_cash",
     ["ALTER TABLE live_confirmed_fills ADD COLUMN cash_amount NUMERIC(38,18)"],
     ["ALTER TABLE live_confirmed_fills ADD COLUMN IF NOT EXISTS cash_amount NUMERIC(38,18)"]),
    (15, "scoped_runtime_and_copy_policy",
     ["CREATE TABLE IF NOT EXISTS live_signing_sessions (user_id CHAR(32) PRIMARY KEY REFERENCES users(id), wallet_address VARCHAR(42) NOT NULL, session_address VARCHAR(42) NOT NULL, encrypted_key TEXT NOT NULL, verified_at TIMESTAMP, valid_until TIMESTAMP, revoked_at TIMESTAMP)",
      "CREATE TABLE IF NOT EXISTS live_copy_policies (user_id CHAR(32) PRIMARY KEY REFERENCES users(id), revision INTEGER NOT NULL, source_wallets JSON NOT NULL, copy_ratio NUMERIC(38,18) NOT NULL, limits JSON NOT NULL, updated_at TIMESTAMP NOT NULL)",
      "CREATE TABLE IF NOT EXISTS live_source_positions (user_id CHAR(32) REFERENCES live_execution_accounts(user_id), source_wallet_address VARCHAR(42), token_id VARCHAR(100), quantity NUMERIC(38,18) NOT NULL DEFAULT 0, PRIMARY KEY(user_id, source_wallet_address, token_id))",
      "ALTER TABLE live_order_intents ADD COLUMN risk_context JSON",
      "ALTER TABLE live_confirmed_fills ADD COLUMN realized_pnl NUMERIC(38,18)"],
     ["CREATE TABLE IF NOT EXISTS live_signing_sessions (user_id UUID PRIMARY KEY REFERENCES users(id), wallet_address VARCHAR(42) NOT NULL, session_address VARCHAR(42) NOT NULL, encrypted_key TEXT NOT NULL, verified_at TIMESTAMP, valid_until TIMESTAMP, revoked_at TIMESTAMP)",
      "CREATE TABLE IF NOT EXISTS live_copy_policies (user_id UUID PRIMARY KEY REFERENCES users(id), revision INTEGER NOT NULL, source_wallets JSON NOT NULL, copy_ratio NUMERIC(38,18) NOT NULL, limits JSON NOT NULL, updated_at TIMESTAMP NOT NULL)",
      "CREATE TABLE IF NOT EXISTS live_source_positions (user_id UUID REFERENCES live_execution_accounts(user_id), source_wallet_address VARCHAR(42), token_id VARCHAR(100), quantity NUMERIC(38,18) NOT NULL DEFAULT 0, PRIMARY KEY(user_id, source_wallet_address, token_id))",
      "ALTER TABLE live_order_intents ADD COLUMN IF NOT EXISTS risk_context JSON",
      "ALTER TABLE live_confirmed_fills ADD COLUMN IF NOT EXISTS realized_pnl NUMERIC(38,18)"]),
    (16, "unique_scoped_wallet_owner",
     ["CREATE UNIQUE INDEX IF NOT EXISTS uq_live_session_wallet ON live_signing_sessions(lower(wallet_address))"],
     ["CREATE UNIQUE INDEX IF NOT EXISTS uq_live_session_wallet ON live_signing_sessions(lower(wallet_address))"]),
]


async def run_versioned_migrations(conn: AsyncConnection) -> int:
    """
    Executes versioned migrations in order and updates schema_migrations.
    Returns the final schema version.
    """
    is_sqlite = "sqlite" in str(conn.engine.url)
    table_sql = MIGRATION_TABLE_SQL_SQLITE if is_sqlite else MIGRATION_TABLE_SQL_POSTGRES

    if not is_sqlite:
        # Serialize migration runners across API replicas for this transaction.
        await conn.execute(text("SELECT pg_advisory_xact_lock(20260908, 1)"))

    # 1. Ensure migrations table exists
    await conn.execute(text(table_sql))

    # 2. Query already applied migrations
    result = await conn.execute(text("SELECT version FROM schema_migrations ORDER BY version ASC;"))
    applied = {row[0] for row in result.fetchall()}

    # 3. Apply pending migrations
    for version, name, sqlite_sqls, pg_sqls in MIGRATIONS:
        if version not in applied:
            logger.info(f"Applying schema migration {version:03d}_{name}...")
            sqls = sqlite_sqls if is_sqlite else pg_sqls
            for sql in sqls:
                try:
                    await conn.execute(text(sql))
                except Exception as e:
                    # Idempotency guard if column already added in a previous startup
                    if is_sqlite and "duplicate column name:" in str(e).lower():
                        pass
                    else:
                        logger.exception("Migration %s failed; version will not be recorded", version)
                        raise

            # Record migration as applied
            await conn.execute(
                text("INSERT INTO schema_migrations (version, name, applied_at) VALUES (:v, :n, :ts);"),
                {"v": version, "n": name, "ts": datetime.utcnow()}
            )
            logger.info(f"✅ Schema migration {version:03d}_{name} applied successfully.")

    # 4. Get current max version
    ver_res = await conn.execute(text("SELECT COALESCE(MAX(version), 0) FROM schema_migrations;"))
    current_version = ver_res.scalar() or 0
    return int(current_version)


MIGRATIONS.append((17, 'owner_session_operation_journal', [
    "CREATE TABLE IF NOT EXISTS live_session_operations (id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL REFERENCES users(id), kind VARCHAR(16) NOT NULL, owner_address VARCHAR(42) NOT NULL, wallet_address VARCHAR(42) NOT NULL, session_address VARCHAR(42) NOT NULL, nonce VARCHAR(80) NOT NULL, deadline BIGINT NOT NULL, valid_until BIGINT, state VARCHAR(24) NOT NULL DEFAULT 'PREPARED', signature_hash VARCHAR(66), transaction_id VARCHAR(255), transaction_hash VARCHAR(66), created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE INDEX IF NOT EXISTS ix_live_session_operations_user_id ON live_session_operations(user_id)",
], [
    "CREATE TABLE IF NOT EXISTS live_session_operations (id UUID PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id), kind VARCHAR(16) NOT NULL, owner_address VARCHAR(42) NOT NULL, wallet_address VARCHAR(42) NOT NULL, session_address VARCHAR(42) NOT NULL, nonce VARCHAR(80) NOT NULL, deadline BIGINT NOT NULL, valid_until BIGINT, state VARCHAR(24) NOT NULL DEFAULT 'PREPARED', signature_hash VARCHAR(66), transaction_id VARCHAR(255), transaction_hash VARCHAR(66), created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE INDEX IF NOT EXISTS ix_live_session_operations_user_id ON live_session_operations(user_id)",
]))

MIGRATIONS.append((18, 'verified_live_wallet_baseline', [
    "CREATE TABLE IF NOT EXISTS live_wallet_baselines (user_id CHAR(32) PRIMARY KEY REFERENCES live_execution_accounts(user_id), run_id CHAR(32) NOT NULL, block_number BIGINT NOT NULL, block_hash VARCHAR(66) NOT NULL, block_time TIMESTAMP NOT NULL, starting_cash NUMERIC(38,18) NOT NULL, observed_tokens JSON NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)",
], [
    "CREATE TABLE IF NOT EXISTS live_wallet_baselines (user_id UUID PRIMARY KEY REFERENCES live_execution_accounts(user_id), run_id UUID NOT NULL, block_number BIGINT NOT NULL, block_hash VARCHAR(66) NOT NULL, block_time TIMESTAMP NOT NULL, starting_cash NUMERIC(38,18) NOT NULL, observed_tokens JSON NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)",
]))

MIGRATIONS.append((19, 'wallet_evidence', [
    "CREATE TABLE IF NOT EXISTS wallet_evidence (wallet_address VARCHAR PRIMARY KEY REFERENCES wallets(address), observed_at TIMESTAMP NOT NULL, payload JSON NOT NULL)"
], [
    "CREATE TABLE IF NOT EXISTS wallet_evidence (wallet_address VARCHAR PRIMARY KEY REFERENCES wallets(address), observed_at TIMESTAMP NOT NULL, payload JSON NOT NULL)"
]))

MIGRATIONS.append((20, 'wallet_research_reset_archives', [
    "CREATE TABLE IF NOT EXISTS wallet_reset_batches (reset_id VARCHAR PRIMARY KEY, created_at TIMESTAMP NOT NULL, wallet_count INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS wallet_evidence_archives (reset_id VARCHAR REFERENCES wallet_reset_batches(reset_id), wallet_address VARCHAR REFERENCES wallets(address), payload JSON NOT NULL, PRIMARY KEY (reset_id, wallet_address))"
], [
    "CREATE TABLE IF NOT EXISTS wallet_reset_batches (reset_id VARCHAR PRIMARY KEY, created_at TIMESTAMP NOT NULL, wallet_count INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS wallet_evidence_archives (reset_id VARCHAR REFERENCES wallet_reset_batches(reset_id), wallet_address VARCHAR REFERENCES wallets(address), payload JSON NOT NULL, PRIMARY KEY (reset_id, wallet_address))"
]))

MIGRATIONS.append((21, 'point_in_time_wallet_observations', [
    "CREATE TABLE IF NOT EXISTS wallet_evidence_observations (id VARCHAR PRIMARY KEY, wallet_address VARCHAR NOT NULL REFERENCES wallets(address), generation VARCHAR NOT NULL, observed_at TIMESTAMP NOT NULL, payload JSON NOT NULL)"
], [
    "CREATE TABLE IF NOT EXISTS wallet_evidence_observations (id VARCHAR PRIMARY KEY, wallet_address VARCHAR NOT NULL REFERENCES wallets(address), generation VARCHAR NOT NULL, observed_at TIMESTAMP NOT NULL, payload JSON NOT NULL)"
]))

MIGRATIONS.append((22, 'forward_wallet_book_observations', [
    "CREATE TABLE IF NOT EXISTS wallet_shadow_observations (id VARCHAR PRIMARY KEY, wallet_address VARCHAR NOT NULL REFERENCES wallets(address), generation VARCHAR NOT NULL, observed_at TIMESTAMP NOT NULL, payload JSON NOT NULL)"
], [
    "CREATE TABLE IF NOT EXISTS wallet_shadow_observations (id VARCHAR PRIMARY KEY, wallet_address VARCHAR NOT NULL REFERENCES wallets(address), generation VARCHAR NOT NULL, observed_at TIMESTAMP NOT NULL, payload JSON NOT NULL)"
]))

LATEST_SCHEMA_VERSION = max(v for v, _, _, _ in MIGRATIONS) if MIGRATIONS else 0


async def get_schema_version(conn: AsyncConnection) -> int:
    """Returns current schema migration version or 0 if uninitialized."""
    try:
        ver_res = await conn.execute(text("SELECT COALESCE(MAX(version), 0) FROM schema_migrations;"))
        return int(ver_res.scalar() or 0)
    except Exception:
        return 0


async def check_schema_completeness(conn: AsyncConnection) -> Tuple[bool, int, str]:
    """
    Checks whether the database schema is fully migrated up to LATEST_SCHEMA_VERSION.
    Returns (is_complete, current_version, details).
    """
    try:
        cur_version = await get_schema_version(conn)
        if cur_version < LATEST_SCHEMA_VERSION:
            return False, cur_version, f"Schema incomplete: current version v{cur_version} < required v{LATEST_SCHEMA_VERSION}"
        if cur_version != LATEST_SCHEMA_VERSION:
            return False, cur_version, "Schema version is newer than this application"
        applied = set((await conn.execute(text("SELECT version FROM schema_migrations"))).scalars())
        if applied != {v for v, _, _, _ in MIGRATIONS}:
            return False, cur_version, "Schema incomplete: migration history has gaps"

        # A stamped version does not prove the DDL succeeded in older releases.
        from app.database import Base
        def missing_columns(sync_conn):
            inspector = inspect(sync_conn)
            tables = set(inspector.get_table_names())
            missing = []
            for table in Base.metadata.sorted_tables:
                if table.name not in tables:
                    missing.append(table.name)
                    continue
                actual = {c["name"] for c in inspector.get_columns(table.name)}
                missing.extend(f"{table.name}.{c.name}" for c in table.columns if c.name not in actual)
            return missing
        missing = await conn.run_sync(missing_columns)
        if missing:
            return False, cur_version, "Schema incomplete: missing " + ", ".join(missing)
        return True, cur_version, f"Schema up to date at v{cur_version}"
    except Exception as e:
        return False, 0, f"Error checking schema version: {e}"
