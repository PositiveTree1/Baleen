"""Run inside the review image against a disposable local PostgreSQL database."""
import asyncio
import json
import os
import secrets
import re
import sys
from datetime import timedelta

sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app')
review_database = os.environ.get('BALEEN_SMOKE_DATABASE', 'baleen_a_acceptance')
if review_database != 'baleen_a_acceptance' and not re.fullmatch(r'baleen_smoke_[0-9a-f]{12}', review_database):
    raise ValueError('Expected a disposable local smoke database name')
os.environ.update({
    'ENVIRONMENT': 'production',
    'DATABASE_URL': 'postgresql+asyncpg://postgres@127.0.0.1:55432/' + review_database,
    'AUTH_SECRET': secrets.token_urlsafe(48),
    'SETTINGS_ENCRYPTION_KEY': secrets.token_urlsafe(48),
    'ADMIN_API_KEY': secrets.token_urlsafe(48),
    'LISTENER_SERVICE_KEY': secrets.token_urlsafe(48),
    'RUN_BACKGROUND_WORKERS': 'false',
    'LIVE_EXECUTION_ENABLED': 'false',
    'POLYGON_SETTLEMENT_RPC_URL': '',
    'POLYMARKET_BUILDER_API_KEY': '',
    'POLYMARKET_BUILDER_SECRET': '',
    'POLYMARKET_BUILDER_PASSPHRASE': '',
})
os.environ.pop('TESTING', None)
from httpx import AsyncClient, ASGITransport
from app.main import app, startup_event
from app.auth import create_access_token
from app.database import engine


async def main():
    await startup_event()
    results = {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        ready = await client.get('/ready')
        assert ready.status_code == 200, ready.text
        results['ready'] = ready.json()
        users = []
        for i in range(2):
            email = f'review-{secrets.token_hex(8)}@example.test'
            password = secrets.token_urlsafe(24)
            response = await client.post('/api/auth/signup', json={'email': email, 'password': password, 'startingBalance': 1234 + i})
            assert response.status_code == 200, response.text
            account = response.json()
            response = await client.post('/api/auth/login', json={'email': email, 'password': password})
            assert response.status_code == 200, response.text
            users.append(response.json())
        a, b = users
        auth = {'Authorization': 'Bearer ' + a['access_token']}
        session = await client.get('/api/live-trading/session', headers=auth)
        assert session.status_code == 200 and session.json()['status'] == 'not_configured'
        assert (await client.get('/api/live-trading/session')).status_code == 401
        assert (await client.post('/api/live-trading/session', headers=auth)).status_code == 409
        assert (await client.post('/api/live-trading/session/operations', headers=auth, json={'kind':'AUTHORIZE'})).status_code == 409
        assert (await client.post('/api/live-trading/initialize-account', headers=auth)).status_code == 409
        assert (await client.get('/api/me', headers=auth)).status_code == 200
        assert (await client.get('/api/users/' + a['id'])).status_code == 401
        assert (await client.get('/api/users/' + b['id'], headers=auth)).status_code == 403
        assert (await client.get('/api/admin/status', headers=auth)).status_code == 403
        assert (await client.patch('/api/users/' + a['id'], headers=auth, json={'risk_profile': 'Conservative'})).status_code == 200
        assert (await client.get('/api/users/' + a['id'], headers=auth)).json()['riskProfile'] == 'Conservative'
        expired = create_access_token(a['id'], expires_delta=timedelta(seconds=-10))
        assert (await client.get('/api/me', headers={'Authorization': 'Bearer ' + expired})).status_code == 401
        reset = await client.post('/api/executions/reset-sandbox', params={'userId': a['id']}, headers=auth)
        assert reset.status_code == 200, reset.text
        other = await client.get('/api/users/' + b['id'], headers={'Authorization': 'Bearer ' + b['access_token']})
        assert other.json()['currentBalance'] == 1235
        assert (await client.post('/api/auth/logout', headers=auth)).status_code == 200
        await engine.dispose()  # no in-process connection can retain the revocation
        assert (await client.get('/api/me', headers=auth)).status_code == 401
        assert (await client.get('/api/me', headers={'Authorization': 'Bearer ' + b['access_token']})).status_code == 200
        guest = await client.post('/api/auth/guest')
        assert guest.status_code == 200, guest.text
        guest_auth = {'Authorization': 'Bearer ' + guest.json()['access_token']}
        assert (await client.get('/api/me', headers=guest_auth)).status_code == 200
        assert (await client.post('/api/auth/login', json={'email': 'x@example.test', 'password': 'x' * 257})).status_code == 422
    await engine.dispose()
    results['passed'] = ['signup', 'login', 'settings_save', 'anonymous_rejection', 'cross_account_rejection',
                         'admin_rejection', 'expired_token', 'own_reset_isolation', 'persistent_logout', 'guest', 'payload_bound',
                         'session_account_auth', 'session_setup_gate', 'builder_setup_gate', 'wallet_funding_gate']
    print(json.dumps(results))


asyncio.run(main())
