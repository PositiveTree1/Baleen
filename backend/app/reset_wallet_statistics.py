"""Run: python -m app.reset_wallet_statistics --reset-id <stable-id> [--apply --workers-stopped]."""
import argparse
import asyncio
import json
from sqlalchemy import select, func
from app.database import SessionLocal
from app.models import Wallet, WalletEvidence
from app.services.wallet_reset import reset_wallet_statistics, current_generation


async def run(args):
    async with SessionLocal() as db, db.begin():
        if not args.apply:
            print(json.dumps({"mode": "dry_run", "wallets": (await db.execute(select(func.count()).select_from(Wallet))).scalar(),
                              "evidence_rows": (await db.execute(select(func.count()).select_from(WalletEvidence))).scalar(),
                              "generation": await current_generation(db), "reset_id": args.reset_id}))
        else:
            if not args.workers_stopped:
                raise ValueError("Stop old discovery/scoring/API writers, then pass --workers-stopped")
            print(json.dumps(await reset_wallet_statistics(db, args.reset_id)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset-id", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--workers-stopped", action="store_true")
    asyncio.run(run(parser.parse_args()))
