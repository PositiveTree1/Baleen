import logging
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import LiveWalletLink, LiveSigningSession
from app.auth import decrypt_secret, encrypt_secret, is_legacy_secret

logger = logging.getLogger(__name__)


async def _secret_fields(db, *, lock=False):
    for model, fields, encrypted_only in (
        (LiveWalletLink, ('clob_api_key_enc', 'clob_api_secret_enc', 'clob_api_passphrase_enc'), False),
        (LiveSigningSession, ('encrypted_key',), True),
    ):
        query = select(model)
        if lock:
            query = query.with_for_update()
        for row in (await db.execute(query)).scalars():
            for field in fields:
                value = getattr(row, field)
                if value:
                    yield row, field, value, encrypted_only

async def scan_and_inventory_credentials(db: AsyncSession) -> Dict[str, Any]:
    """
    Inspects all live_wallet_links rows and tallies credentials by encryption status:
    - current: encrypted with current primary key
    - legacy_or_rotated: plaintext or encrypted with previous key
    - invalid: cannot be decrypted
    """
    result = await db.execute(select(LiveWalletLink))
    links = result.scalars().all()
    
    total = len(links)
    fields = ["clob_api_key_enc", "clob_api_secret_enc", "clob_api_passphrase_enc"]
    inventory = {
        "total_wallet_links": total,
        "current_key_count": 0,
        "needs_reencryption_count": 0,
        "unrecoverable_count": 0,
    }
    
    inventory['total_signing_sessions'] = len((await db.execute(select(LiveSigningSession))).scalars().all())
    async for _, _, val, encrypted_only in _secret_fields(db):
        if encrypted_only and not val.startswith('v1:'):
            inventory['unrecoverable_count'] += 1
        elif is_legacy_secret(val):
            if decrypt_secret(val) is not None:
                inventory['needs_reencryption_count'] += 1
            else:
                inventory['unrecoverable_count'] += 1
        else:
            inventory['current_key_count'] += 1
                
    return inventory


async def rotate_and_reencrypt_credentials(db: AsyncSession, *, migrate_plaintext: bool = False) -> Dict[str, int]:
    """
    Re-encrypts all stored credentials in live_wallet_links using the current primary key.
    Enables retirement of previous encryption keys. All changes roll back if any
    credential is unreadable. Plaintext migration requires an explicit operator
    choice and never changes the production credential-reading policy.
    """
    reencrypted_count = 0
    failed_count = 0
    
    async for row, field, val, encrypted_only in _secret_fields(db, lock=True):
        if encrypted_only and not val.startswith('v1:'):
            failed_count += 1  # Session keys never have a plaintext migration path.
        elif is_legacy_secret(val):
            decrypted = str(val).strip() if migrate_plaintext and not str(val).strip().startswith('v1:') else decrypt_secret(val)
            if decrypted is None:
                failed_count += 1
            else:
                setattr(row, field, encrypt_secret(decrypted))
                reencrypted_count += 1
            
    if failed_count:
        await db.rollback()
        raise ValueError(f"Rotation aborted: {failed_count} unreadable credential fields; no changes committed")
    await db.commit()
    logger.info(f"Credential rotation complete: {reencrypted_count} re-encrypted, {failed_count} failed.")
    return {"reencrypted": reencrypted_count, "failed": failed_count}


async def verify_all_credentials_decryptable(db: AsyncSession) -> bool:
    """
    Verifies that every stored secret in live_wallet_links decrypts without error.
    """
    async for _, _, val, encrypted_only in _secret_fields(db):
        if (encrypted_only and not val.startswith('v1:')) or decrypt_secret(val) is None:
            return False
    return True
