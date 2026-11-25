import httpx

URL = "http://localhost:8000/graphql"

# Fields worth probing without a token. For mutations and lookups by number we take
# non-existent ids: the protection fires before the resolver, the data is unchanged.
FIELDS = [
    ("Query.courses", "{ courses(limit: 1) { id } }"),
    ("Query.course", '{ course(id: "nope") { id } }'),
    ("Query.me", "{ me { id } }"),
    ("Query.students", "{ students(limit: 1) { id } }"),
    ("Query.student", '{ student(id: "0") { id } }'),
    ("Query.enrollments", "{ enrollments(limit: 1) { id } }"),
    ("Course.enrollments", "{ courses(limit: 1) { enrollments { id } } }"),
    ("Student.enrollments", '{ student(id: "1") { enrollments { id } } }'),
    ("Student.email", '{ student(id: "1") { email } }'),
    (
        "Mutation.enroll",
        'mutation { enroll(input: {courseId: "nope", studentId: "0"}) '
        "{ userErrors { code } } }",
    ),
    (
        "Mutation.likeCourse",
        'mutation { likeCourse(id: "nope") { userErrors { code } } }',
    ),
]

print(f"{'field':<22}anonymous")
for name, query in FIELDS:
    answer = httpx.post(URL, json={"query": query}).json()
    errors = answer.get("errors")
    # A denial arrives in errors; if there is no errors, the field was executed.
    print(f"{name:<22}{errors[0]['message'] if errors else 'open'}")
