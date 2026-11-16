import time
import hashlib
import hmac
import os
import jwt
from typing import Optional, Dict, Any

from app.core.config import settings


# ── Password Hashing (Cryptographically Secure PBKDF2-SHA256) ─────
def hash_password(plain: str) -> str:
    """Return a PBKDF2-SHA256 hash with random 32-byte cryptographic salt."""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, 100_000)
    return salt.hex() + ":" + key.hex()


def check_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against its PBKDF2 hash using constant-time comparison."""
    try:
        salt_hex, key_hex = hashed.split(":")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(key_hex)
        actual = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(actual, expected)
    except (ValueError, AttributeError):
        return False


# ── JWT & Session Tokens ──────────────────────────────────────────
def create_access_token(user: Dict[str, Any], minutes: Optional[int] = None) -> str:
    """Issue a JWT access token carrying user claims."""
    ttl_minutes = minutes if minutes is not None else settings.jwt_expire_minutes
    now = int(time.time())
    payload = {
        "sub": str(user.get("_id") or user.get("id")),
        "email": user.get("email"),
        "name": user.get("name"),
        "role": user.get("role", "customer"),
        "token_type": "access",
        "iat": now,
        "exp": now + int(ttl_minutes * 60),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_session_token(user: Dict[str, Any], days: Optional[int] = None) -> str:
    """Issue a long-lived session token to keep mobile app persistent."""
    ttl_days = days if days is not None else settings.session_expire_days
    now = int(time.time())
    payload = {
        "sub": str(user.get("_id") or user.get("id")),
        "email": user.get("email"),
        "token_type": "session",
        "iat": now,
        "exp": now + int(ttl_days * 86400),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
