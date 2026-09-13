import base64
import hashlib
import hmac
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)

import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User

# PBKDF2 Parameters
PBKDF2_ITERATIONS = 100_000
PBKDF2_ALGORITHM = "sha256"
JWT_ALGORITHM = "HS256"
DEFAULT_TOKEN_EXPIRE_HOURS = 72

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email(email: str) -> str:
    """Normalizes and validates email address consistently."""
    if not email or not isinstance(email, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid email address is required."
        )
    normalized = email.strip().lower()
    if len(normalized) < 5 or len(normalized) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address must be between 5 and 255 characters."
        )
    if not EMAIL_REGEX.match(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format."
        )
    return normalized


def validate_password_strength(password: str) -> None:
    """Enforces minimum password length."""
    if not password or len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )
    if len(password) > 256:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot exceed 256 characters."
        )


def hash_password(password: str) -> str:
    """Hashes password using NIST-standard salted PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS
    )
    return f"pbkdf2:{PBKDF2_ALGORITHM}:{PBKDF2_ITERATIONS}${salt.hex()}${key.hex()}"


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifies a password against PBKDF2 hash or legacy unsalted SHA-256 hash.
    Constant-time comparison used throughout.
    """
    if not plain or not hashed:
        return False

    if hashed.startswith(f"pbkdf2:{PBKDF2_ALGORITHM}:"):
        try:
            parts = hashed.split("$")
            if len(parts) != 3:
                return False
            meta, salt_hex, expected_hex = parts
            iterations = int(meta.split(":")[2])
            salt = bytes.fromhex(salt_hex)
            computed = hashlib.pbkdf2_hmac(
                PBKDF2_ALGORITHM,
                plain.encode("utf-8"),
                salt,
                iterations
            )
            return hmac.compare_digest(computed.hex(), expected_hex)
        except Exception:
            return False

    # Legacy SHA-256 fallback (for existing test and seed accounts)
    if len(hashed) == 64:
        legacy_hash = hashlib.sha256(plain.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy_hash, hashed)

    return False


def needs_rehash(hashed: str) -> bool:
    """Returns True if the hash is a legacy format and should be upgraded to PBKDF2."""
    return not str(hashed).startswith(f"pbkdf2:{PBKDF2_ALGORITHM}:")


def _cipher_from_secret(secret: str) -> Fernet:
    """Derives a deterministic 32-byte Fernet key from a string secret."""
    key_bytes = hashlib.sha256(secret.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def _get_primary_cipher() -> Fernet:
    """Derives Fernet cipher from primary SETTINGS_ENCRYPTION_KEY or dev fallback."""
    secret = settings.SETTINGS_ENCRYPTION_KEY
    if not secret:
        if (settings.ENVIRONMENT or "").lower() != "production":
            secret = settings.AUTH_SECRET or "baleen_auth_secret_fallback_key_32b"
        else:
            raise RuntimeError("SETTINGS_ENCRYPTION_KEY is required in production.")
    return _cipher_from_secret(secret)


def _get_all_ciphers() -> list[Fernet]:
    """Returns primary cipher followed by any rotated previous ciphers for migration."""
    ciphers = [_get_primary_cipher()]
    prev = getattr(settings, "SETTINGS_ENCRYPTION_KEY_PREVIOUS", "").strip()
    if prev:
        ciphers.append(_cipher_from_secret(prev))
    return ciphers


def encrypt_secret(plaintext: Optional[str]) -> Optional[str]:
    """Encrypts sensitive plaintext (API keys, CLOB secrets) using Fernet authenticated encryption."""
    if not plaintext:
        return None
    cleaned = str(plaintext).strip()
    if not cleaned:
        return ""
    cipher = _get_primary_cipher()
    token = cipher.encrypt(cleaned.encode("utf-8")).decode("utf-8")
    return f"v1:{token}"


def decrypt_secret(ciphertext: Optional[str]) -> Optional[str]:
    """
    Decrypts ciphertext. Supports primary key, rotated previous keys,
    and legacy unencrypted plaintext with migration warnings.
    """
    if not ciphertext:
        return None
    cleaned = str(ciphertext).strip()
    if not cleaned:
        return ""

    if cleaned.startswith("v1:"):
        token = cleaned[3:]
        token_bytes = token.encode("utf-8")
        for cipher in _get_all_ciphers():
            try:
                return cipher.decrypt(token_bytes).decode("utf-8")
            except Exception:
                continue
        # If all ciphers failed, cannot decrypt
        return None

    # Legacy unencrypted storage - rejected in production, flagged with warning in development
    is_prod = (getattr(settings, "ENVIRONMENT", "") or "").lower() == "production"
    if is_prod:
        logger.error("Legacy unencrypted credential rejected in production environment.")
        return None

    logger.warning("Reading legacy unencrypted credential. Re-save to migrate to encrypted storage.")
    return cleaned


def is_legacy_secret(ciphertext: Optional[str]) -> bool:
    """Checks whether stored secret requires migration to current encryption."""
    if not ciphertext:
        return False
    cleaned = str(ciphertext).strip()
    if not cleaned:
        return False
    if not cleaned.startswith("v1:"):
        return True
    # If encrypted with an older rotated key, it needs re-encryption with primary
    token = cleaned[3:]
    try:
        _get_primary_cipher().decrypt(token.encode("utf-8"))
        return False
    except Exception:
        return True


from app.services.security_state import DatabaseRateLimiter, persist_revocation, token_is_revoked

guest_rate_limiter = DatabaseRateLimiter("guest", requests_limit=10, window_seconds=60)
copilot_rate_limiter = DatabaseRateLimiter("copilot", requests_limit=20, window_seconds=60)
auth_rate_limiter = DatabaseRateLimiter("auth", requests_limit=15, window_seconds=60)


async def revoke_token(token: str, db: AsyncSession) -> None:
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    payload = decode_access_token(token)
    if payload:
        await persist_revocation(db, token, float(payload["exp"]))


async def is_token_revoked(token: str, db: AsyncSession) -> bool:
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return await token_is_revoked(db, token)


def create_access_token(
    user_id_or_data: Union[str, Dict[str, Any]],
    role: str = "user",
    expires_delta: Optional[timedelta] = None,
    **extra_claims: Any
) -> str:
    """Generates a signed JWT bearer token supporting both string user_id and dict payload."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=DEFAULT_TOKEN_EXPIRE_HOURS))
    payload: Dict[str, Any] = {
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
    }
    if isinstance(user_id_or_data, dict):
        payload.update(user_id_or_data)
        if "sub" not in payload:
            derived_sub = user_id_or_data.get("sub") or user_id_or_data.get("id") or user_id_or_data.get("user_id") or user_id_or_data.get("email")
            if derived_sub:
                payload["sub"] = str(derived_sub)
        if "exp" not in user_id_or_data:
            payload["exp"] = expire
        if "iat" not in user_id_or_data:
            payload["iat"] = datetime.now(timezone.utc)
    else:
        payload["sub"] = str(user_id_or_data)
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.AUTH_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT bearer token."""
    try:
        payload = jwt.decode(
            token,
            settings.AUTH_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp"]}
        )
        return payload
    except jwt.PyJWTError:
        return None


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Resolves authenticated User from Authorization Bearer token without raising 401 if absent.
    Fails closed with 401 if an invalid or expired token is presented.
    """
    if not authorization:
        return None

    token = authorization.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    if not token:
        return None

    if await is_token_revoked(token, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = None
    user_id_str = payload.get("sub")
    if user_id_str:
        try:
            uid = uuid.UUID(str(user_id_str).strip())
            stmt = select(User).where(User.id == uid)
            user = (await db.execute(stmt)).scalar_one_or_none()
        except Exception:
            pass

    if not user and payload.get("email"):
        stmt = select(User).where(User.email == payload["email"])
        user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user account not found or deactivated.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


async def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """Requires verified user identity; raises HTTP 401 if missing or invalid."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return current_user


async def require_admin(
    authorization: Optional[str] = Header(None),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Requires verified administrator privileges via:
    1. Valid X-Admin-Key matching settings.ADMIN_API_KEY, or
    2. Valid User JWT bearer token where user.is_admin is True or user.role == 'admin'.
    """
    # 1. Check direct admin API key
    if x_admin_key and settings.ADMIN_API_KEY and hmac.compare_digest(x_admin_key.strip(), settings.ADMIN_API_KEY.strip()):
        return User(id=uuid.UUID(int=0), email="admin_system@baleen.internal", role="admin", is_admin=True)

    # If no credentials provided, return 401
    if not authorization and not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Administrator credentials needed.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 2. Check JWT Bearer
    user = await get_current_user_optional(authorization=authorization, db=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Invalid or expired bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    is_admin = getattr(user, "is_admin", False) or getattr(user, "role", "") == "admin"
    if is_admin:
        return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Administrator privileges required for this route."
    )


async def verify_listener_service_key(
    x_service_key: Optional[str] = Header(None, alias="X-Service-Key"),
    authorization: Optional[str] = Header(None)
) -> bool:
    """
    Authenticates ingestion requests from the Envio HyperSync listener service.
    Validates X-Service-Key or Authorization Bearer against LISTENER_SERVICE_KEY.
    In production, a configured LISTENER_SERVICE_KEY is strictly required.
    In non-production environments with no LISTENER_SERVICE_KEY set, falls back to open access for test suites.
    """
    configured_key = getattr(settings, "LISTENER_SERVICE_KEY", "").strip()
    is_prod = getattr(settings, "ENVIRONMENT", "").lower() == "production"

    if is_prod and not configured_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Listener service key is not configured in production."
        )

    if not is_prod and not configured_key:
        return True

    key_provided = None
    if x_service_key:
        key_provided = x_service_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        key_provided = authorization[7:].strip()

    if not key_provided or not hmac.compare_digest(key_provided, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing listener service authentication key."
        )
    return True
