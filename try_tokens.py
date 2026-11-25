import base64
import json
from datetime import datetime, timedelta, timezone

import httpx
import jwt

from config import settings

BASE = "http://localhost:8000"
now = datetime.now(timezone.utc)
claims = {
    "sub": "2",  # Aigerim
    "iss": "course-catalog-api",
    "iat": now,
    "exp": now + timedelta(minutes=15),
}


def encode(**changes) -> str:
    """Aigerim's token signed with our key; changes override payload fields."""
    return jwt.encode({**claims, **changes}, settings.secret_key, algorithm="HS256")


def b64(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


valid = encode()
header, payload, signature = valid.split(".")

# A payload the attacker writes by hand: sub = 1 is the administrator.
expires = int((now + timedelta(minutes=15)).timestamp())
as_admin = {"sub": "1", "iss": "course-catalog-api", "exp": expires}
no_exp = {k: v for k, v in claims.items() if k != "exp"}
none_header = b64({"alg": "none", "typ": "JWT"})

# (description, token, expected status)
CASES = [
    ("valid token", valid, 200),
    ("expired", encode(exp=now - timedelta(minutes=1)), 401),
    ("signed with another key", jwt.encode(claims, "x" * 32, algorithm="HS256"), 401),
    ("another issuer", encode(iss="evil"), 401),
    ("no exp", jwt.encode(no_exp, settings.secret_key, algorithm="HS256"), 401),
    ("sub is not a number", encode(sub="abc"), 401),
    ("sub of a missing user", encode(sub="999"), 401),
    ("payload edited, old signature", f"{header}.{b64(as_admin)}.{signature}", 401),
    ("alg none, no signature", f"{none_header}.{b64(as_admin)}.", 401),
]

failed = 0
for title, token, status in CASES:
    response = httpx.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
    ok = response.status_code == status
    failed += not ok
    who = response.json().get("email") or response.json().get("detail")
    print(f"{'ok  ' if ok else 'FAIL'} {title:<31} {response.status_code}  {who}")
print(f"{len(CASES) - failed} of {len(CASES)} as expected")
