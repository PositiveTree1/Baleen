"""Read-only audit of application logic using a disposable DB and mocked market I/O.
Run from repo root: python audit/2026-09-08/independent_checks.py
Writes no production state. Prints observations and exits nonzero for failed invariants.
These checks describe required behavior, not a specification of existing defects.
"""
import asyncio
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.update(TESTING='1', DATABASE_URL='sqlite+aiosqlite:///:memory:',
                  ENVIRONMENT='development', AUTH_SECRET='audit-only-not-a-production-secret')
from app.database import Base, engine, SessionLocal
from app.models import User, Wallet, ExecutionLog, PortfolioSnapshot
from app.main import app
from app.config import settings
from app.services.live_poller import LiveTradeMirrorService
from app.discovery.scanner import calculate_authentic_wallet_stats
from app.discovery.polymarket_client import PolymarketClient
from app.api.users import user_to_response
import httpx

logging.disable(logging.CRITICAL)
RESULTS = []

def record(name, observed, expected, passed):
    RESULTS.append(dict(check=name, observed=observed, expected=expected, passed=bool(passed)))

async def reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def main():
    settings.NETTED_LEDGER_ENABLED = False
    settings.LIVE_EXECUTION_ENABLED = False
    addr = '0x' + 'a' * 40
    cid = '0x' + 'b' * 64
    now = datetime.utcnow()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Marked equity already contains +$80 on a 200-share lot bought for $100.
    # Settlement changes the mark to $1, so correct equity becomes $10,100.
    uid = uuid.uuid4()
    async with SessionLocal() as db:
        db.add(Wallet(address=addr))
        db.add(User(id=uid, email='synthetic@audit.invalid', sandbox_starting_balance_usd=10000,
                    sandbox_balance_usd=10080, sandbox_high_water_mark_usd=10080))
        db.add(ExecutionLog(user_id=uid, source_wallet_address=addr, market_condition_id=cid,
                            side='BUY', status='FILLED', is_sandbox=True,
                            resolution_outcome='Yes', user_fill_price=.5,
                            whale_entry_price=.5, notional_usd=100, fee_usd=0))
        await db.commit()
    service = LiveTradeMirrorService()
    with patch('app.services.event_logger.log_event', new=AsyncMock()):
        await service.settle_market_resolution(cid, 'Yes')
        await service.settle_market_resolution(cid, 'Yes')
    async with SessionLocal() as db:
        u = await db.get(User, uid)
        record('settlement_after_MTM', {'equity':u.sandbox_balance_usd, 'hwm':u.sandbox_high_water_mark_usd},
               {'equity':10100, 'hwm':10100}, abs(u.sandbox_balance_usd-10100)<1e-6 and abs(u.sandbox_high_water_mark_usd-10100)<1e-6)

    # Direct unauthenticated account read, no external server/lifespan startup.
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://audit.local') as c:
        r = await c.get('/api/executions', params={'userId':str(uid)})
        record('private_executions_require_auth', {'http_status':r.status_code, 'rows':len(r.json()) if isinstance(r.json(),list) else None},
               '401 or 403', r.status_code in (401,403))
        r = await c.get('/api/users/' + str(uid))
        record('protected_settings_without_bearer', r.status_code, 401, r.status_code==401)
        r = await c.post('/api/live-trading/credentials',json={'user_id':str(uid),
            'polymarket_wallet_address':addr,'clob_api_key':'synthetic-key',
            'clob_api_secret':'synthetic-secret','clob_api_passphrase':'synthetic-passphrase'})
        record('credential_write_requires_auth',r.status_code,'401 or 403',r.status_code in (401,403))

    record('zero_balance_not_defaulted', user_to_response(User(id=uuid.uuid4(), email='zero@audit.invalid',
           sandbox_balance_usd=0, sandbox_starting_balance_usd=10000))['currentBalance'], 0,
           user_to_response(User(id=uuid.uuid4(), email='zero@audit.invalid', sandbox_balance_usd=0))['currentBalance']==0)

    # Both outcomes in the same condition must contribute to closed P&L.
    closed = [dict(asset='111', conditionId=cid, realizedPnl=50, curPrice=1, timestamp=int(time.time()), avgPrice=.5, totalBought=100),
              dict(asset='222', conditionId=cid, realizedPnl=-100, curPrice=0, timestamp=int(time.time()), avgPrice=.5, totalBought=200)]
    stats = calculate_authentic_wallet_stats(addr, [], [], profile={'pnl':-50}, trades=[], closed_positions=closed)
    record('both_outcomes_count_in_wallet_curve', stats['cumulative_pnl'], -50, stats['cumulative_pnl']==-50)

    # Duplicate redemption observation must not create extra money.
    trade = dict(asset='111', conditionId=cid, side='BUY', size=100, price=.5, timestamp=int(time.time())-100)
    redemption = dict(type='REDEEM', asset='111', conditionId=cid, size=100, usdcSize=100,
                      timestamp=int(time.time()), transactionHash='0x'+'c'*64)
    stats = calculate_authentic_wallet_stats(addr, [], [redemption,dict(redemption)], profile={'pnl':50}, trades=[trade])
    record('redemption_observation_idempotency', stats['cumulative_pnl'], 50, stats['cumulative_pnl']==50)

    # Unknown cost basis cannot be represented as a measured 50%-entry profit.
    stats = calculate_authentic_wallet_stats(addr, [], [redemption], profile=None, trades=[])
    record('missing_redemption_basis_not_invented', stats['cumulative_pnl'], 'unknown/excluded, not fabricated +50', stats['cumulative_pnl']!=50)

    # A rejected exit must preserve shares and cash.
    from app.backtesting.models import TradeSignal, ExecutionFill
    from app.backtesting.config import BacktestConfig
    from app.backtesting.portfolio import SimulatedPortfolio
    p=SimulatedPortfolio(BacktestConfig(initial_capital=1000,enable_fees=False))
    buy=TradeSignal(timestamp=100,whale_address=addr,market_id='m1',condition_id=cid,token_id='111',
                    side='BUY',whale_price=.5,whale_size_usd=50,whale_shares=100)
    p.open_position(ExecutionFill(order_id='buy',signal=buy,intended_size_usd=50,fill_price=.5,
        filled_size_usd=50,filled_shares=100,slippage_bps=0,fee_usd=0,latency_ms=0,status='FILLED',executed_at=100))
    sell=TradeSignal(timestamp=200,whale_address=addr,market_id='m1',condition_id=cid,token_id='111',
                     side='SELL',whale_price=.8,whale_size_usd=80,whale_shares=100)
    p.close_position_on_whale_sell(sell,ExecutionFill(order_id='rejected',signal=sell,intended_size_usd=80,
        fill_price=.8,filled_size_usd=0,filled_shares=0,slippage_bps=0,fee_usd=0,latency_ms=0,
        status='REJECTED_SLIPPAGE',executed_at=200))
    record('rejected_backtest_exit_has_no_fill',{'cash':p.cash,'open_positions':len(p.open_positions)},
           {'cash':950,'open_positions':1},p.cash==950 and len(p.open_positions)==1)

    # Wrong market responses must not be relabelled as the requested market.
    client = PolymarketClient()
    client._fetch_with_retry = AsyncMock(side_effect=[[], [dict(conditionId='0x'+'d'*64, outcomes=['Yes','No'], outcomePrices=['0.9','0.1'])]])
    prices = await client.fetch_batch_live_prices([cid])
    record('wrong_market_price_rejected', prices.get(cid), None, cid not in prices)
    await client.close()

    # A persisted genesis snapshot must not keep the guest summary at 10k forever.
    async with SessionLocal() as db:
        u = await db.get(User, uid)
        u.sandbox_balance_usd=10100
        db.add(PortfolioSnapshot(user_id=uid, timestamp=now-timedelta(days=1), balance=10000, total_pnl=0))
        await db.commit()
    from app.auth import create_access_token
    token_str = create_access_token(str(uid))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://audit.local') as c:
        r_anon = await c.get('/api/executions/summary', params={'userId': str(uid)})
        r = await c.get('/api/executions/summary', params={'userId': str(uid)}, headers={'Authorization': f'Bearer {token_str}'})
        record('summary_matches_settled_account', r.json().get('currentBalance'), 10100, r.json().get('currentBalance') == 10100 and r_anon.status_code == 401)
        r = await c.post('/api/executions/reset-sandbox', params={'userId': str(uid)})
        record('paper_reset_requires_auth', r.status_code, '401 or 403', r.status_code in (401, 403))

    # Actual BUY processing with no external I/O: repeated entries cannot borrow paper capital.
    await reset_db()
    settings.NETTED_LEDGER_ENABLED=True
    uid=uuid.uuid4()
    async with SessionLocal() as db:
        for i in range(10):
            db.add(Wallet(address=addr if i==0 else '0x'+f'{i:040x}', status='active', tier='gold_sniper',
                          dormant=False, is_hft=False, avg_trades_per_day=2, baleen_score=100-i,
                          all_time_pnl_usd=50000, win_rate_pct=90, wilson_lb=85))
        db.add(User(id=uid,email='budget@audit.invalid',sandbox_starting_balance_usd=100,
                    sandbox_balance_usd=100,sandbox_high_water_mark_usd=100))
        await db.commit()
    service=LiveTradeMirrorService()
    from sqlalchemy import select, func
    with patch('app.services.event_logger.log_event',new=AsyncMock()):
        for i in range(12):
            await service.process_trade_fill(wallet_address=addr, condition_id=cid, title='Audit General Question',
                side='BUY',price=.5,cash_usd=50000,dt=now,asset='111',event_slug='audit',icon='audit',
                tx_hash='0x'+f'{1000+i:064x}',log_index=i)
    async with SessionLocal() as db:
        invested=(await db.execute(select(func.sum(ExecutionLog.notional_usd)).where(ExecutionLog.user_id==uid,ExecutionLog.side=='BUY'))).scalar() or 0
        fees=(await db.execute(select(func.sum(ExecutionLog.fee_usd)).where(ExecutionLog.user_id==uid))).scalar() or 0
        record('paper_capital_conservation', {'starting_cash':100,'open_cost':invested,'fees':fees},
               'open_cost + fees <= 100 without borrowing', invested+fees<=100+1e-6)
    # Same real event through indexed chain and unindexed REST observations.
    # This is a separate invariant: the budget scenario above now exhausts
    # available cash correctly. Use a new funded fixture so deduplication must
    # still produce one effect, rather than passing/failing because of no funds.
    await reset_db()
    uid = uuid.uuid4()
    async with SessionLocal() as db:
        db.add(Wallet(address=addr, status='active', tier='gold_sniper', dormant=False,
                      is_hft=False, avg_trades_per_day=2, baleen_score=100,
                      all_time_pnl_usd=50000, win_rate_pct=90, wilson_lb=85))
        db.add(User(id=uid, email='dedup@audit.invalid', sandbox_starting_balance_usd=10000,
                    sandbox_balance_usd=10000, sandbox_high_water_mark_usd=10000))
        await db.commit()
    duplicate_tx='0x'+f'{9999:064x}'
    with patch('app.services.event_logger.log_event',new=AsyncMock()):
        for log_index in (7,None):
            await service.process_trade_fill(wallet_address=addr,condition_id=cid,title='Audit General Question',
                side='BUY',price=.5,cash_usd=50000,dt=now,asset='111',event_slug='audit',icon='audit',
                tx_hash=duplicate_tx,log_index=log_index)
    async with SessionLocal() as db:
        count=(await db.execute(select(func.count(ExecutionLog.id)).where(ExecutionLog.user_id==uid,
                                 ExecutionLog.onchain_tx_hash==duplicate_tx))).scalar()
        record('dual_provider_single_economic_event',count,1,count==1)
    await asyncio.sleep(0)
    await engine.dispose()
    print(json.dumps({'checks':RESULTS,'passed':sum(r['passed'] for r in RESULTS),'failed':sum(not r['passed'] for r in RESULTS)},indent=2))

if __name__=='__main__':
    asyncio.run(main())
    sys.exit(1 if any(not r['passed'] for r in RESULTS) else 0)
