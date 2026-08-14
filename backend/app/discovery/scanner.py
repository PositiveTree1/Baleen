import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.discovery.polymarket_client import PolymarketClient
from app.models import Wallet

logger = logging.getLogger(__name__)

async def scan_for_wallets(db: AsyncSession) -> int:
    """
    Scans Polymarket for new active/high-volume wallets and adds them to the database as pending.
    Returns the number of new wallets discovered.
    """
    client = PolymarketClient()
    new_wallets_count = 0
    try:
        # 1. Fetch from leaderboard
        leaderboard = await client.fetch_leaderboard(limit=100)
        
        # 2. Fetch recent trades
        recent_trades = await client.fetch_recent_trades(limit=500)
        
        addresses = set()
        
        for entry in leaderboard:
            addr = entry.get("proxyWallet") or entry.get("address") or entry.get("user")
            if addr:
                addresses.add(addr.lower())
                
        for trade in recent_trades:
            maker = trade.get("maker_address") or trade.get("maker")
            if maker:
                addresses.add(maker.lower())
                
        # 3. Add to DB if they don't exist
        for address in addresses:
            stmt = select(Wallet).where(Wallet.address == address)
            result = await db.execute(stmt)
            existing_wallet = result.scalar_one_or_none()
            
            if not existing_wallet:
                wallet = Wallet(
                    address=address,
                    status="pending"
                )
                db.add(wallet)
                new_wallets_count += 1
                
        if new_wallets_count > 0:
            await db.commit()
            
    except Exception as e:
        logger.error(f"Error during scan: {e}")
        await db.rollback()
    finally:
        await client.close()
        
    return new_wallets_count
