"""Passwords and tokens: no HTTP, only cryptography."""

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from config import settings

ALGORITHM = "HS256"
ISSUER = "course-catalog-api"

password_hash = PasswordHash.recommended()  # Argon2id
# Hash of a “non-existent” password: verified when no user has this e-mail.
DUMMY_HASH = password_hash.hash("not-a-real-password")


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "iss": ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def read_access_token(token: str) -> int:
    """Returns the user id or raises jwt.InvalidTokenError."""
    claims = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[ALGORITHM],
        issuer=ISSUER,
        options={"require": ["exp", "sub", "iss"]},
    )
    try:
        return int(claims["sub"])
    except ValueError:
        raise jwt.InvalidTokenError("sub is not a user id") from None
