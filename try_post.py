import sys

import httpx

name, email = sys.argv[1], sys.argv[2]
response = httpx.post(
    "http://localhost:8000/students", json={"name": name, "email": email}
)
print(response.status_code, response.headers["content-type"])
print(response.text)
