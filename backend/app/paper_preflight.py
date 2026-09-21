"""Read-only deployment checks. Run: python -m app.paper_preflight."""
import asyncio
import json
from sqlalchemy import select, func
from app.config import settings
from app.database import SessionLocal
from app.models import PaperCopyAccount, SignalInbox
from app.services.listener_health import listener_health
from app.migrations import check_schema_completeness


async def main():
    async with SessionLocal() as db:
        complete, version, detail = await check_schema_completeness(await db.connection())
        result = {'schema_complete': complete, 'schema_version': version, 'schema_detail': detail,
                  'background_workers_enabled': settings.RUN_BACKGROUND_WORKERS,
                  'envio_key_configured': bool(settings.ENVIO_API_KEY),
                  'dedicated_receipt_rpc_configured': bool(settings.POLYGON_SETTLEMENT_RPC_URL),
                  'live_execution_enabled': settings.LIVE_EXECUTION_ENABLED}
        if complete:
            result['listener'] = await listener_health(db)
            result['paper_accounts'] = dict((await db.execute(select(PaperCopyAccount.status, func.count()).group_by(PaperCopyAccount.status))).all())
            result['inbox'] = dict((await db.execute(select(SignalInbox.status, func.count()).group_by(SignalInbox.status))).all())
        result['operational_checks_passed'] = bool(complete and settings.RUN_BACKGROUND_WORKERS
            and result.get('listener', {}).get('status') == 'ONLINE'
            and not result.get('inbox', {}).get('FAILED', 0))
        result['strategy_profitability_verified'] = False
        print(json.dumps(result, indent=2, default=str))
        return 0 if result['operational_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
