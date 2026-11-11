import httpx

URL = "http://localhost:8000/graphql"

# twelve likeCourse mutations in one request: aliases a1 … a12
operations = " ".join(
    f'a{i}: likeCourse(id: "api-design") {{ course {{ likes }} }}'
    for i in range(1, 13)
)
response = httpx.post(URL, json={"query": "mutation { " + operations + " }"})
body = response.json()

print("HTTP status:", response.status_code)
if body.get("errors"):
    print("error:", body["errors"][0]["message"])
else:
    print("likes:", [body["data"][f"a{i}"]["course"]["likes"] for i in range(1, 13)])
print("SQL queries:", response.headers["x-sql-queries"])
