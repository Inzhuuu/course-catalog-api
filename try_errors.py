import httpx

BASE = "http://localhost:8000"

# (description, path, request body, expected status)
CASES = [
    ("email already taken", "/students",
     {"name": "Aigerim Two", "email": "aigerim@example.com"}, 409),
    ("already enrolled", "/enrollments",
     {"courseId": "ai-integration", "studentId": 3}, 409),
    ("unknown course", "/enrollments",
     {"courseId": "nope", "studentId": 3}, 404),
    ("unknown student", "/enrollments",
     {"courseId": "web-security", "studentId": 999}, 404),
    ("name too short", "/students",
     {"name": "N", "email": "n@example.com"}, 422),
]

failed = 0
for title, path, body, expected in CASES:
    response = httpx.post(BASE + path, json=body)
    ok = response.status_code == expected
    failed += not ok
    mark = "ok  " if ok else "FAIL"
    print(f"{mark} {title:<20} {response.status_code}  {response.text[:48]}")
print(f"{len(CASES) - failed} of {len(CASES)} as expected")
