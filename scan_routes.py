import re

import httpx

BASE = "http://localhost:8000"
# Login is open by design; GraphQL is checked by try_graphql_access.py.
SKIP = {"/auth/login", "/graphql"}


def login(email: str, password: str) -> str:
    form = {"username": email, "password": password}
    return httpx.post(f"{BASE}/auth/login", data=form).json()["access_token"]


ROLES = {
    "anonymous": None,
    "student": login("aigerim@example.com", "aigerim-demo-pass"),
    "admin": login("admin@example.com", "admin-demo-password"),
}

# Routes come from the API description, not from memory: a new route joins the table.
paths = httpx.get(f"{BASE}/openapi.json").json()["paths"]
routes = [
    (method.upper(), path)
    for path, methods in paths.items()
    for method in methods
    if path not in SKIP
]

open_routes = []
print(f"{'route':<42}" + "".join(f"{role:<11}" for role in ROLES))
for method, path in routes:
    # A non-existent id (0) and an empty body: the data does not change,
    # while the protection fires before the route.
    url = BASE + re.sub(r"\{[^}]+\}", "0", path)
    codes = []
    for role, token in ROLES.items():
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        body = {} if method == "POST" else None
        codes.append(httpx.request(method, url, json=body, headers=headers).status_code)
    if codes[0] not in (401, 403):
        open_routes.append(f"{method} {path}")
    print(f"{method + ' ' + path:<42}" + "".join(f"{code:<11}" for code in codes))

print("\nopen without a token:")
for route in open_routes:
    print("  " + route)
