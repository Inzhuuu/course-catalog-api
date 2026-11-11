import httpx

URL = "http://localhost:8000/graphql"


def enroll(course_id: str, student_id: str) -> str:
    return (
        "mutation { enroll(input: "
        f'{{courseId: "{course_id}", studentId: "{student_id}"}}) '
        "{ enrollment { id } userErrors { code } } }"
    )


def first_error(data) -> str:
    return data["errors"][0]["message"].split(". Did you")[0]


# (description, query, function that picks a short string from the answer, expected)
CASES = [
    ("courses(limit: 2)", "{ courses(limit: 2) { id } }",
     lambda d: ",".join(c["id"] for c in d["data"]["courses"]),
     "ai-integration,modern-frontend"),
    ('course(id: "api-design")', '{ course(id: "api-design") { title } }',
     lambda d: d["data"]["course"]["title"], "API Design: REST vs GraphQL"),
    ('course(id: "nope")', '{ course(id: "nope") { title } }',
     lambda d: str(d["data"]["course"]), "None"),
    ("student(id: 2) → courses", "{ student(id: 2) { enrollments { course { id } } } }",
     lambda d: str(len(d["data"]["student"]["enrollments"])), "3"),
    ("enroll twice", enroll("ai-integration", "3"),
     lambda d: d["data"]["enroll"]["userErrors"][0]["code"], "ALREADY_ENROLLED"),
    ("enroll: unknown course", enroll("nope", "3"),
     lambda d: d["data"]["enroll"]["userErrors"][0]["code"], "COURSE_NOT_FOUND"),
    ("enroll: unknown student", enroll("web-security", "999"),
     lambda d: d["data"]["enroll"]["userErrors"][0]["code"], "STUDENT_NOT_FOUND"),
    ("unknown field", '{ course(id: "api-design") { titel } }',
     first_error, "Cannot query field 'titel' on type 'Course'"),
]

failed = 0
for title, query, pick, expected in CASES:
    data = httpx.post(URL, json={"query": query}).json()
    try:
        actual = pick(data)
    except (KeyError, IndexError, TypeError):
        actual = "?"
    ok = actual == expected
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {title:<25} {actual}")
print(f"{len(CASES) - failed} of {len(CASES)} as expected")
