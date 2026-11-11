import httpx

URL = "http://localhost:8000/graphql"

QUERIES = [
    (
        "students → enrollments → course",
        "{ students { name enrollments { course { title } } } }",
    ),
    (
        "enrollments → course, student",
        "{ enrollments { id course { title } student { name } } }",
    ),
]

for title, query in QUERIES:
    response = httpx.post(URL, json={"query": query})
    response.raise_for_status()
    rows = len(next(iter(response.json()["data"].values())))
    queries = response.headers["x-sql-queries"]
    print(f"{title:<34} rows: {rows:<3} SQL queries: {queries}")
