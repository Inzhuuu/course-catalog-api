"""Demo accounts: an administrator and three students (linked to students 1–3)."""

from sqlalchemy import text

from db import SessionLocal
from models import User
from security import password_hash

USERS = [
    # (e-mail, role, student id, password)
    ("admin@example.com", "admin", None, "admin-demo-password"),
    ("aigerim@example.com", "student", 1, "aigerim-demo-pass"),
    ("daniyar@example.com", "student", 2, "daniyar-demo-pass"),
    ("asel@example.com", "student", 3, "asel-demo-password"),
]

if __name__ == "__main__":
    with SessionLocal() as db:
        # The script can be run again: user numbers start from 1 again.
        db.execute(text("TRUNCATE users RESTART IDENTITY"))
        for email, role, student_id, password in USERS:
            db.add(
                User(
                    email=email,
                    role=role,
                    student_id=student_id,
                    password_hash=password_hash.hash(password),
                )
            )
        db.commit()
    print(f"created users: {len(USERS)}")
