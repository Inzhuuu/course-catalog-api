import httpx

BASE = "http://localhost:8000"
URL = BASE + "/graphql"


def login(email: str, password: str) -> str:
    form = {"username": email, "password": password}
    return httpx.post(f"{BASE}/auth/login", data=form).json()["access_token"]


def ask(query: str, token: str | None = None) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.post(URL, json={"query": query}, headers=headers)


# Functions that pick a short string from the response for comparison.
def first_error(response: httpx.Response) -> str:
    return response.json()["errors"][0]["message"]


def me_line(response: httpx.Response) -> str:
    return " ".join(response.json()["data"]["me"].values())


def students_count(response: httpx.Response) -> str:
    return str(len(response.json()["data"]["students"]))


def name_and_email(response: httpx.Response) -> str:
    student = response.json()["data"]["student"]
    return f"{student['name']}, email {student['email']}"


def email_only(response: httpx.Response) -> str:
    return response.json()["data"]["student"]["email"]


def emails_of_enrollments(response: httpx.Response) -> str:
    rows = [row["student"]["email"] for row in response.json()["data"]["enrollments"]]
    shown = sum(email is not None for email in rows)
    return f"{shown} shown, {len(rows) - shown} hidden"


def http_status(response: httpx.Response) -> str:
    return f"HTTP {response.status_code}"


student = login("aigerim@example.com", "aigerim-demo-pass")  # student 1
admin = login("admin@example.com", "admin-demo-password")

ME = "{ me { email role } }"
STUDENTS = "{ students { name } }"
STUDENT_2 = '{ student(id: "2") { name email } }'
STUDENT_1 = '{ student(id: "1") { email } }'
ENROLLMENTS = "{ enrollments(limit: 4) { student { email } } }"

# (description, query, token, how to read the response, expected string)
CASES = [
    ("me, no token", ME, None, first_error, "Authentication required"),
    ("me, student", ME, student, me_line, "aigerim@example.com student"),
    ("students, student", STUDENTS, student, first_error, "Admin role required"),
    ("students, admin", STUDENTS, admin, students_count, "3"),
    ("student(2).email, student", STUDENT_2, student, name_and_email,
     "Daniyar Bekov, email None"),
    ("student(1).email, student", STUDENT_1, student, email_only,
     "aigerim@example.com"),
    ("student(2).email, admin", STUDENT_2, admin, email_only, "daniyar@example.com"),
    ("enrollments → student.email", ENROLLMENTS, student, emails_of_enrollments,
     "2 shown, 2 hidden"),
    ("bad token", ME, "abc.def.ghi", http_status, "HTTP 401"),
]

failed = 0
for title, query, token, pick, expected in CASES:
    response = ask(query, token)
    try:
        actual = pick(response)
    except (KeyError, IndexError, TypeError):
        actual = "?"
    ok = actual == expected
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {title:<28} {actual}")
print(f"{len(CASES) - failed} of {len(CASES)} as expected")
