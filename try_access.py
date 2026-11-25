import httpx
from sqlalchemy import delete

from db import SessionLocal
from models import Enrollment

BASE = "http://localhost:8000"
COURSE = "web-security"  # nobody is enrolled in this course in the seed data


def login(email: str, password: str) -> str:
    form = {"username": email, "password": password}
    return httpx.post(f"{BASE}/auth/login", data=form).json()["access_token"]


def clean() -> None:
    """Removes enrollments for COURSE so the script can be run again."""
    with SessionLocal() as db:
        db.execute(delete(Enrollment).where(Enrollment.course_id == COURSE))
        db.commit()


ROLES = ["anonymous", "student", "admin"]
TOKENS = {
    "anonymous": None,
    "student": login("aigerim@example.com", "aigerim-demo-pass"),  # student 1
    "admin": login("admin@example.com", "admin-demo-password"),
}

# (request, method, path, body, statuses per role; None = the role has no such request)
ROWS = [
    ("GET /courses", "GET", "/courses", None, (200, 200, 200)),
    ("GET /me", "GET", "/me", None, (401, 200, 200)),
    ("GET /enrollments", "GET", "/enrollments", None, (401, 403, 200)),
    ("POST /enrollments, for yourself", "POST", "/enrollments",
     {"courseId": COURSE, "studentId": 1}, (401, 201, None)),
    ("POST /enrollments, for another", "POST", "/enrollments",
     {"courseId": COURSE, "studentId": 2}, (401, 403, 201)),
]

clean()
total = failed = 0
print(f"{'request':<34}" + "".join(f"{role:<15}" for role in ROLES))
for title, method, path, body, expected in ROWS:
    cells = []
    for role, want in zip(ROLES, expected):
        if want is None:
            cells.append("-")
            continue
        headers = {"Authorization": f"Bearer {TOKENS[role]}"} if TOKENS[role] else {}
        clean()  # every request starts with a clean slate
        got = httpx.request(method, BASE + path, json=body, headers=headers).status_code
        total += 1
        failed += got != want
        cells.append(str(got) if got == want else f"{got} (want {want})")
    print(f"{title:<34}" + "".join(f"{cell:<15}" for cell in cells))
clean()
print(f"{total - failed} of {total} as expected")
