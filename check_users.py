from sqlalchemy import select

from db import SessionLocal
from models import User
from seed_users import USERS
from security import password_hash

with SessionLocal() as db:
    users = {u.email: u for u in db.scalars(select(User))}


def roles_and_links_ok() -> bool:
    for email, role, student_id, _ in USERS:
        user = users.get(email)
        if user is None or (user.role, user.student_id) != (role, student_id):
            return False
    return True


def passwords_ok() -> bool:
    return all(
        email in users and password_hash.verify(password, users[email].password_hash)
        for email, _, _, password in USERS
    )


hashes_ok = all(u.password_hash.startswith("$argon2id$") for u in users.values())
checks = [  # (description, passed or not)
    (f"{len(USERS)} users in the table", len(users) == len(USERS)),
    ("every hash is argon2id", hashes_ok),
    ("roles and student links", roles_and_links_ok()),
    ("passwords match their hashes", passwords_ok()),
]

failed = 0
for title, ok in checks:
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {title}")
print(f"{len(checks) - failed} of {len(checks)} as expected")
