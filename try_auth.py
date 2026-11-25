import httpx

BASE = "http://localhost:8000"


def login(email: str, password: str) -> httpx.Response:
    # OAuth2PasswordRequestForm expects a form, not JSON: data=, not json=
    form = {"username": email, "password": password}
    return httpx.post(f"{BASE}/auth/login", data=form)


def me(token: str | None) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.get(f"{BASE}/me", headers=headers)


good = login("aigerim@example.com", "aigerim-demo-pass")
token = good.json().get("access_token")
wrong = login("aigerim@example.com", "wrong-password-123")
unknown = login("nobody@example.com", "wrong-password-123")

# (description, response, expected status, expected detail text or e-mail)
CASES = [
    ("login: right password", good, 200, "bearer"),
    ("login: wrong password", wrong, 401, "Incorrect email or password"),
    ("login: unknown e-mail", unknown, 401, "Incorrect email or password"),
    ("/me without a token", me(None), 401, "Not authenticated"),
    ("/me with a token", me(token), 200, "aigerim@example.com"),
    ("/me with a garbage token", me("abc.def.ghi"), 401, "Invalid or expired token"),
]

failed = 0
for title, response, status, text in CASES:
    ok = response.status_code == status and text in response.text
    failed += not ok
    mark = "ok  " if ok else "FAIL"
    challenge = response.headers.get("www-authenticate", "-")
    print(f"{mark} {title:<25} {response.status_code}  www-authenticate: {challenge}")
print(f"{len(CASES) - failed} of {len(CASES)} as expected")
