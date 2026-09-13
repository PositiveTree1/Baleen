"""Shared security state. Limits and logout survive workers and restarts."""
import hashlib
import time

from fastapi import HTTPException
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RateLimitBucket, RevokedAccessToken


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class DatabaseRateLimiter:
    """Fixed windows, shared across replicas; reject new keys at capacity.

    Call before business writes: each check commits its quota so rejected requests
    also consume it. Reuse the request session to avoid nested pool checkouts.
    At a window boundary up to twice the quota can occur in a short interval.
    """
    def __init__(self, namespace: str, requests_limit: int, window_seconds: int, max_keys: int = 10000):
        self.namespace = namespace
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.max_keys = max_keys

    async def check(self, db: AsyncSession, key: str, action_name: str = "request"):
        key_hash = token_hash(f"{self.namespace}:{key}")
        allowed = False
        retry_after = self.window_seconds
        if db.new or db.dirty or db.deleted:
            raise RuntimeError("Rate limiting must precede business writes")
        # Authentication may already hold a connection. Finish that read-only
        # transaction; never wait for a second connection from the same pool.
        if db.in_transaction():
            await db.commit()
        async with db.begin():
            if db.bind.dialect.name == "postgresql":
                await db.execute(text("SELECT pg_advisory_xact_lock(20260908, 2)"))
                now = float((await db.execute(text("SELECT EXTRACT(EPOCH FROM clock_timestamp())"))).scalar_one())
            else:
                await db.execute(text("BEGIN IMMEDIATE"))
                now = time.time()
            await db.execute(delete(RateLimitBucket).where(RateLimitBucket.expires_at <= now))
            bucket = await db.get(RateLimitBucket, key_hash)
            if bucket is None:
                size = (await db.execute(select(func.count()).select_from(RateLimitBucket))).scalar_one()
                if size < self.max_keys:
                    db.add(RateLimitBucket(key=key_hash, count=1, expires_at=now + self.window_seconds))
                    allowed = True
            elif bucket.count < self.requests_limit:
                bucket.count += 1
                allowed = True
            else:
                retry_after = max(1, int(bucket.expires_at - now) + 1)
        if not allowed:
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded for {action_name}.",
                                headers={"Retry-After": str(retry_after)})


async def persist_revocation(db: AsyncSession, token: str, expires_at: float):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    await db.execute(delete(RevokedAccessToken).where(RevokedAccessToken.expires_at <= time.time()))
    await db.execute(insert(RevokedAccessToken).values(token_hash=token_hash(token), expires_at=expires_at)
                     .on_conflict_do_nothing(index_elements=["token_hash"]))
    await db.commit()


async def token_is_revoked(db: AsyncSession, token: str) -> bool:
    # Never cache a negative answer: another worker may revoke at any time.
    row = await db.get(RevokedAccessToken, token_hash(token), populate_existing=True)
    return row is not None and row.expires_at > time.time()
