import base64
import hashlib
import hmac
import os
import time

import jwt

ALGORITHM = "HS256"
TOKEN_LIFETIME_SECONDS = 3600  # a token works for one hour


def hash_password(password: str) -> str:
    """Return 'salt$hash'. The salt is random, so equal passwords get different hashes."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored 'salt$hash' value."""
    try:
        salt_b64, digest_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except ValueError:
        return False

    actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    # compare_digest compares in constant time, so timing cannot leak the hash
    return hmac.compare_digest(actual, expected)


def _secret() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if not secret:
        # Never run with an empty secret: anyone could forge tokens
        raise RuntimeError("JWT_SECRET is not set in .env")
    return secret


def create_token(email: str) -> str:
    """Create a signed token that says 'this is <email>' for one hour."""
    payload = {"sub": email, "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS}
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def read_token(token: str) -> str | None:
    """Return the email inside a valid token, or None if it is fake or expired."""
    try:
        data = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
        return data["sub"]
    except (jwt.PyJWTError, KeyError):
        return None