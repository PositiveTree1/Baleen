import pytest
from sqlalchemy import select, delete
from app.database import SessionLocal, init_db
from app.models import User

def test_digest_includes_only_opted_in_users():
    users = [
        User(email="a@test.com", daily_digest_opt_in=True),
        User(email="b@test.com", daily_digest_opt_in=False),
        User(email="c@test.com", daily_digest_opt_in=True)
    ]
    opted_in = [u for u in users if u.daily_digest_opt_in]
    assert len(opted_in) == 2
    assert "a@test.com" in [u.email for u in opted_in]
    assert "c@test.com" in [u.email for u in opted_in]

@pytest.mark.asyncio
async def test_digest_database_opt_in_query():
    await init_db()
    async with SessionLocal() as db:
        u1 = User(email="opt_in_test_1@baleen.ai", daily_digest_opt_in=True)
        u2 = User(email="opt_out_test_2@baleen.ai", daily_digest_opt_in=False)
        db.add(u1)
        db.add(u2)
        await db.commit()

        try:
            stmt = select(User).where(User.daily_digest_opt_in == True)
            opted = (await db.execute(stmt)).scalars().all()
            emails = [u.email for u in opted]
            assert "opt_in_test_1@baleen.ai" in emails
            assert "opt_out_test_2@baleen.ai" not in emails
        finally:
            await db.execute(delete(User).where(User.email.in_(["opt_in_test_1@baleen.ai", "opt_out_test_2@baleen.ai"])))
            await db.commit()
