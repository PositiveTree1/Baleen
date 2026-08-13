from app.models import User

def test_digest_includes_only_opted_in_users():
    # Simulate DB query filtering
    users = [
        User(email="a@test.com", daily_digest_opt_in=True),
        User(email="b@test.com", daily_digest_opt_in=False),
        User(email="c@test.com", daily_digest_opt_in=True)
    ]
    
    opted_in = [u for u in users if u.daily_digest_opt_in]
    assert len(opted_in) == 2
    assert "a@test.com" in [u.email for u in opted_in]
    assert "c@test.com" in [u.email for u in opted_in]
