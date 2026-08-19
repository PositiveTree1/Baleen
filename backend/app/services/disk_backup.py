import os
import json
import csv
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from sqlalchemy import select
from app.database import SessionLocal
from app.models import ExecutionLog

logger = logging.getLogger(__name__)

BACKUP_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "backups"

async def export_all_trades_to_disk() -> dict:
    """Exports all execution logs to disk in both JSON and CSV formats."""
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        
        async with SessionLocal() as db:
            stmt = select(ExecutionLog).order_by(ExecutionLog.executed_at.desc())
            logs = (await db.execute(stmt)).scalars().all()
            
            if not logs:
                return {"status": "empty", "count": 0}
                
            json_records = []
            csv_records = []
            
            for log in logs:
                rec = {
                    "id": str(log.id),
                    "timestamp": log.executed_at.isoformat() if log.executed_at else None,
                    "wallet_address": log.source_wallet_address,
                    "market_condition_id": log.market_condition_id,
                    "market_question": log.market_question,
                    "event_slug": log.event_slug,
                    "side": log.side,
                    "outcome": log.resolution_outcome,
                    "whale_entry_price": log.whale_entry_price,
                    "user_fill_price": log.user_fill_price,
                    "notional_usd": log.notional_usd,
                    "fee_usd": log.fee_usd,
                    "realized_pnl_usd": log.realized_pnl_usd,
                    "status": log.status,
                    "tx_hash": log.onchain_tx_hash
                }
                json_records.append(rec)
                csv_records.append(rec)
                
            json_path = BACKUP_DIR / "baleen_all_trades_backup.json"
            csv_path = BACKUP_DIR / "baleen_all_trades_backup.csv"
            
            # Write JSON backup
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "exported_at": datetime.utcnow().isoformat(),
                    "total_trades": len(json_records),
                    "trades": json_records
                }, f, indent=2)
                
            # Write CSV backup
            if csv_records:
                headers = list(csv_records[0].keys())
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(csv_records)
                    
            logger.info(f"💾 Successfully saved disk backup of {len(json_records)} trades to {BACKUP_DIR}")
            return {
                "status": "success",
                "count": len(json_records),
                "json_file": str(json_path),
                "csv_file": str(csv_path)
            }
    except Exception as e:
        logger.error(f"Failed to export trades to disk: {e}")
        return {"status": "error", "error": str(e)}

class DiskBackupService:
    def __init__(self):
        self.running = False

    async def start(self):
        if os.environ.get("TESTING") == "1":
            return
        self.running = True
        logger.info("Disk Backup Service initialized (interval: 15 minutes).")
        asyncio.create_task(self._backup_loop())

    async def stop(self):
        self.running = False
        await export_all_trades_to_disk()

    async def _backup_loop(self):
        # Initial backup after 30s warmup
        await asyncio.sleep(30)
        while self.running:
            try:
                await export_all_trades_to_disk()
            except Exception as e:
                logger.error(f"Backup loop error: {e}")
            await asyncio.sleep(900)  # 15 minutes

disk_backup_service = DiskBackupService()
