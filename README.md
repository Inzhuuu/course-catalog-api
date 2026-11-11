Inzhu Rakhym, IT3-2301, labs 4–8

# course-catalog-api

Backend of the course catalog: FastAPI, SQLAlchemy 2.1, PostgreSQL, Alembic and
GraphQL on Strawberry as a second entrance (Labs 4–8, "Advanced Web Technologies").

## How to run

You need Python 3.11 or newer and PostgreSQL 16 or newer (checked on Python
3.13 and PostgreSQL 17.11).

Once, as the `postgres` superuser, create the role and the database:

```sql
CREATE ROLE catalog_app LOGIN PASSWORD 'change-me';
CREATE DATABASE course_catalog OWNER catalog_app;
```

Then, from the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # DATABASE_URL and GRAPHQL_INTROSPECTION
alembic upgrade head               # creates the tables (migrations 0001 and 0002)
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f seed.sql
alembic check                      # "No new upgrade operations detected."
fastapi dev main.py
```

In a second window, with the server running, the check scripts should print:
`python try_errors.py` — 5 of 5, `python try_graphql.py` — 8 of 8,
`python try_n_plus_1.py` — 3 and 3 SQL queries, `python measure.py` — REST
5 requests in 2 rounds, GraphQL 1 request in 1 round. `python print_schema.py`
prints the GraphQL schema.

REST docs: http://localhost:8000/docs. GraphiQL: http://localhost:8000/graphql.
The password `change-me` is for training; real projects don't commit passwords.

The “My courses” pages are in the frontend repository (course-catalog):
`/my-courses` (GraphQL) and `/my-courses-rest` (REST), run with `npm run dev`
while the API is running.

## What changed in the API

- **REST errors are Problem Details** (RFC 9457): rule errors come with the
  content type `application/problem+json` and a body with `type`, `title`,
  `status`, `detail`, `instance`, for example `type:
  https://example.com/problems/already-enrolled` with status 409. The rules live
  in `services.py` (they raise `ServiceError` with a code like
  `ALREADY_ENROLLED`), and `problem.py` translates the code into a status and a
  `type`. Unknown addresses and wrong methods also answer in this format
  (`about:blank`, 404 / 405 with `allow: GET`).
- **`/graphql`** is a second entrance to the same database and services: one
  POST with a query that lists the fields it needs. Opened in a browser (GET),
  it shows GraphiQL — an editor with hints and schema docs; a program sends
  POST requests with JSON `{"query", "variables"}` and gets JSON back. Types:
  `Course`, `Student`, `Enrollment`; queries: `courses`, `course`, `students`,
  `student`, `enrollments`.
- **Mutations `enroll` and `likeCourse`** take `input` / `id` and return an
  envelope with the result and `userErrors`. An expected rule error (already
  enrolled, unknown course or student) arrives in `data.…userErrors` with the
  same code the services give, status 200. Errors in the query text or
  unexpected failures arrive in the `errors` key.
- **The `X-SQL-Queries` header** on every response counts the SQL queries the
  request made (`counter.py`). It's how the N+1 problem was found (7 → 27
  queries) and checked after DataLoaders (3 queries regardless of the data).
- **Protection**: query depth at most 5, at most 10 aliases, `limit` must be
  1–100, `id` must be a number (clear `GraphQLError` messages), any other
  internal error is shown as `Unexpected error.` (the real text stays in the
  server log). Introspection is controlled by `GRAPHQL_INTROSPECTION` in `.env`
  (`true` by default, `false` turns it off).
- **New REST routes**: `GET /students/{id}` (404 Problem Details if there's no
  such student) and `GET /students/{id}/enrollments`.

## Example queries

The “My courses” query (in the GraphiQL Variables panel: `{"id": "2"}`):

```graphql
query MyCourses($id: ID!) {
  student(id: $id) {
    name
    enrollments {
      id
      course { title credits level }
    }
  }
}
```

The `enroll` mutation (Variables: `{"input": {"courseId": "web-security", "studentId": "3"}}`):

```graphql
mutation Enroll($input: EnrollInput!) {
  enroll(input: $input) {
    enrollment { id enrolledAt course { title } }
    userErrors { code message }
  }
}
```

The first time it answers with the enrollment and an empty `userErrors`:

```json
{"data": {"enroll": {"enrollment": {"id": "10", "enrolledAt": "2026-11-11T23:58:57.535912+05:00", "course": {"title": "Web Security Essentials"}}, "userErrors": []}}}
```

The same mutation again (a repeated enrollment):

```json
{"data": {"enroll": {"enrollment": null, "userErrors": [{"code": "ALREADY_ENROLLED", "message": "Student is already enrolled in this course"}]}}}
```

## REST vs GraphQL comparison

The “My courses” screen of student 2; numbers from `measure.py`, starting data.

| Criterion | REST | GraphQL | Source |
|-----------|------|---------|--------|
| Requests and rounds per screen | 5 requests, 2 rounds (the course codes are known only after round 1) | 1 request, 1 round | `measure.py`, step 8 |
| Bytes in the responses | 1145 (whole courses, names, times — more than the screen needs) | 339 (only the listed fields) | `measure.py`, step 8 |
| SQL queries per screen | 5 (one per course, grows with the number of courses) | 3 (DataLoaders: one per level) | `measure.py`, `X-SQL-Queries` |
| SQL growth with more students | constant per route: the shape is fixed, so one JOIN (`GET /enrollments` — 1 query) | without loaders 7 → 27 and 7 → 24 (3 → 20 students); with loaders 3 and 3 | `try_n_plus_1.py`, experiments 4–5 |
| Error in the query text | a real status: 404 for an unknown address, 422 for invalid parameters, Problem Details body | status 200, `data: null`, `errors` with `Did you mean …`; the client must check `errors` | experiments 1 and 8 |
| Expected rule error (repeated enrollment) | 409, `application/problem+json`, `type …/already-enrolled` | 200, `userErrors[0].code = ALREADY_ENROLLED` | steps 1 and 4 |
| HTTP cache | works out of the box: each resource has its own GET URL, so browsers, proxies and CDNs can cache by URL | almost all requests are POST to one `/graphql`, so HTTP caches don't help; caching moves to the client or to persisted queries | lecture section 14 |
| Protection from “expensive” queries | the route itself limits the cost (fixed query, `page_size` 1–100); a rate limiter counts requests | the client chooses depth and number of operations: needed depth ≤ 5, ≤ 10 aliases (12 likes in one POST without it), argument checks, error masking | experiments 6 and 7 |

**Conclusion.** For screens that combine several related objects, like “My
courses”, I'd choose GraphQL: one request in one round instead of 5 in 2, 339
bytes instead of 1145, and with DataLoaders a constant 3 SQL queries. For
simple resource screens and anything public that benefits from HTTP caching
(the course list, one course) I'd keep REST: each request is cheap (1 SQL
query), errors have real statuses, and the cost is limited by the route itself.
GraphQL needs extra work to stay safe and fast — DataLoaders against N+1 (27
queries without them) and limits against expensive queries.

## Experiment log

| # | Experiment | What I saw | Cause | How I fixed it |
|---|------------|------------|-------|----------------|
| 1 | a typo in a field name, an argument name in `snake_case` | `titel`: status **200**, `data: null`, `Cannot query field 'titel' on type 'Course'. Did you mean 'title', 'level', or 'likes'?`; `is_elective`: `Unknown argument 'is_elective' on field 'Query.courses'. Did you mean 'isElective'?`. REST `/courses/no-such` gave a real 404 | GraphQL checks the query against the schema before running it and reports problems in `errors`, not with an HTTP status; argument names in the schema are camelCase | fixed the names (`title`, `isElective`); the client must check `errors`, not the status |
| 2 | `\| None` removed from the `course` query, a nonexistent course | schema `course(id: ID!): Course!`; `Cannot return null for non-nullable field Query.course.` with `data: null`; with two aliases `a` (exists) and `b` (nope) the whole `data` was `null` too, `path: ["b"]` | the `!` is a promise that the value is never null; a broken promise is a server error, and null propagates to the nearest nullable parent — here the whole `data` | put `\| None` back: `{"a": {...}, "b": null}` |
| 3 | a mutation with the GET method | the query via GET returned the course (likes 12); the mutation via GET: **400**, plain text `mutations are not allowed when using GET`; likes stayed 12 | GET must be safe (it can be repeated, prefetched, cached), so a link mustn't change data; mutations are POST only | nothing to fix — the refusal is correct |
| 4 | `more_students.sql`: 3 and 20 students, the SQL counter | `X-SQL-Queries`: 7 and 7 on 3 students, **27 and 24** on 20; the log showed 1 students query + 3 enrollments queries (`student_id = 1, 2, 3`) + 3 courses queries | lazy loading: each resolver loads its relation separately (1 + N + distinct courses); the client's single POST doesn't change, and neither the status nor the response time in GraphiQL shows it | DataLoaders in step 6 |
| 5 | a DataLoader batch function that doesn't sort rows by key | students query: `Received wrong number of results in dataloader, expected: 3, received: 6`; enrollments query: **no error**, but enrollments 2, 4, 5, 6 got the wrong course (e.g. 2 got Backend Foundations instead of AI/LLM Integration) | the loader hands out results by position; with `ORDER BY ... DESC` the rows came in a different order than the keys. The second case is more dangerous: wrong data with no error | `git restore graphql_api.py` — the original matches rows to keys by value through the `groups` dict |
| 6 | six dangerous queries without protection and with it | see the table below | without limits the server runs any depth and any number of aliases, and shows raw database errors | `QueryDepthLimiter`, `MaxAliasesLimiter`, `check_limit`, `parse_id`, `MaskErrors` |
| 7 | introspection off, a typo in a field name | `{ __schema … }` rejected: `GraphQL introspection has been disabled, but the requested query contained the field '__schema'.`; normal queries and `try_graphql.py` 8 of 8 still work; `{ cours { title } }` still says `Did you mean 'course' or 'courses'?` | introspection hides the schema map, but validation hints still reveal field names one by one, so it isn't security | put `GRAPHQL_INTROSPECTION` back to `true` (needed for GraphiQL); access must be restricted by permissions |
| 8 | client failures: a typo, no `errors` check, the API stopped | typo: `GraphQLRequestError: Cannot query field 'titel' on type 'Course'. Did you mean …`; no check: `TypeError: Cannot destructure property 'student' of '(intermediate value)' as it is null.`; API stopped: `TypeError: fetch failed` | GraphQL errors arrive with status 200, so only the `errors` check names the cause; without it only the consequence (`data: null`) is visible; a stopped API gives no answer at all | `git restore .` in the frontend and started the API again |

Experiment 6 in detail (`try_protection.py`, `flood_likes.py`):

| Query | Without protection | With protection |
|-------|--------------------|-----------------|
| a depth-6 cycle | executed, data arrived | `'Cycle' exceeds maximum operation depth of 5` |
| 12 aliases | executed; `flood_likes.py`: likes 12 → 23 in one POST, 24 SQL queries | `12 aliases found. Allowed: 10`, SQL queries: 0, likes unchanged |
| `limit: -1` | `(psycopg.errors.InvalidRowCountInLimitClause) LIMIT must not be negative` + the SQL text and parameters | `limit must be between 1 and 100` |
| `id: "abc"` | `invalid literal for int() with base 10: 'abc'` | `Invalid ID: 'abc'` (only `student` became null) |
| id of 20 digits | `(psycopg.errors.NumericValueOutOfRange) bigint out of range` + SQL | `Unexpected error.` (the real `DataError` stays in the server log) |
| introspection | the schema arrived | the schema arrived (switched off only in experiment 7) |

- **What the client learned without protection:** the driver (psycopg) and
  the database's error names, the table and column names, the full SQL text
  with parameter values, and the fact that the code calls `int()` on the id.
  (REST in my project answers `page_size=-1` with 422, because the Lab 4 bonus
  put `Query(ge=1, le=100)` on pagination; an unhandled REST error would be a
  bare 500 without the text.)
- **Why `check_limit` and `parse_id` and not only `MaskErrors`:** `Invalid ID:
  'abc'` tells the client what to fix; `Unexpected error.` only says that
  something broke. Expected mistakes get clear messages, and masking is a
  safety net for the unforeseen.
- **If `max_depth` were 2,** the “My courses” query (`student → enrollments →
  course`, depth 3) — the main screen of the app — would be rejected.

## Decisions

- **The rules live in `services.py`, and each layer translates the code.** If
  REST and GraphQL each had their own copy of the constraint dictionary and the
  `try/except`, the copies would drift apart and the same mistake would give
  different answers. One rule in one place gives one code (`ALREADY_ENROLLED`),
  and only the presentation differs: 409 Problem Details in REST, `userErrors`
  in GraphQL.
- **Loaders are created per request in `Context`, and rows are matched to keys
  by value.** A loader caches results by key; one per application would show
  one request's (and one user's) data to another and never notice database
  changes. Matching by value is required because the database doesn't return
  rows in the order of the keys — experiment 5 showed that matching by position
  silently gives four enrollments someone else's course.
- **Two layers of protection.** For mistakes we can foresee (`limit` outside
  1–100, an id that isn't a number) we answer with a clear `GraphQLError`, so
  the client can fix the query. Everything we didn't foresee (a database
  failure, a 20-digit id, a bug) is hidden by `MaskErrors` as `Unexpected
  error.`, so internals like SQL text don't leak, while the full traceback
  stays in the server log for the developer.

## Bonus

### Task 1. Validation errors as Problem Details too

After step 1 the four rule errors were Problem Details, but a Pydantic
validation error still came in FastAPI's own format: `python try_post.py N bad`
gave `422 application/json` with `{"detail": [{"type": "string_too_short",
"loc": ["body", "name"], …}, …]}`, so a client had to parse two formats.

I added a `RequestValidationError` handler to `problem.install()`. Now the same
request gives `422 application/problem+json`:

```json
{"type": "https://example.com/problems/validation-error", "title": "Validation failed",
 "status": 422, "detail": "2 invalid value(s) in the request", "instance": "/students",
 "errors": [{"in": "body", "field": "name", "detail": "String should have at least 2 characters"},
            {"in": "body", "field": "email", "detail": "value is not a valid email address: An email address must have an @-sign."}]}
```

`try_errors.py` now shows `validation-error` in the fifth row instead of `-`,
and query parameters are covered too (`/courses?page_size=0` →
`"in": "query", "field": "page_size"`).

- **Where the list comes from:** FastAPI raises `RequestValidationError`
  before the route runs, and `exc.errors()` returns Pydantic's list — one
  dict per wrong value with `loc` (e.g. `["body", "name"]`), `msg` and service
  fields. The handler turns each into `{"in": loc[0], "field": the rest of loc
  joined with ".", "detail": msg}`. Both mistakes arrive at once, so the client
  can fix everything in one go.
- **Why `errors` is an extension:** RFC 9457 defines the five standard members
  (`type`, `title`, `status`, `detail`, `instance`) and explicitly allows
  problem types to add their own members. A list of invalid fields only makes
  sense for the `validation-error` type, so it's an extension of that type,
  not a required part of every problem; clients that don't know it can still
  read the standard fields.

## Lab 7 — SQLAlchemy and Alembic

### What changed in the API

- **The data lives in PostgreSQL**, not in Python lists: likes, students and
  enrollments survive a server restart. The database address comes from
  `.env` (`config.py`), and every request gets its own session (`get_db`).
- **`POST /enrollments` takes `studentId` instead of `studentName`**: body
  `{"courseId": "web-security", "studentId": 4}`, response 201 with `id`,
  `courseId`, `studentId` and `enrolledAt` (set by the database). The Lab 5
  enrollment form in the frontend still sends `studentName`, so it gets 422
  until the frontend is updated.
- **New routes**: `POST /students` (`{"name", "email"}` → 201 with `id`) and
  `GET /stats/courses` (enrollments per course, including courses with 0).
  `GET /enrollments` now also returns `courseTitle` and `studentName` (a JOIN
  with `courses` and `students`).
- **`level`**: every course has a required `level` (`beginner`,
  `intermediate`, `advanced`), and `GET /courses?level=beginner` filters by it.
  The other filters still work: `is_elective`, `sort=popular|title`, `q`
  (search in the title), `page` / `page_size`. `GET /stats` (Lab 4 bonus) is
  now computed by the database too.
- **Database errors are API responses**: a violated constraint is recognized
  by its name — `students_email_key` and
  `enrollments_course_id_student_id_key` → 409, `enrollments_course_id_fkey` →
  404 Course not found, `enrollments_student_id_fkey` → 404 Student not found.
  An unknown violation stays a 500 (it's a bug). A too-short name gets 422 from
  Pydantic before it reaches the database.

### Migrations

| Command | What it does |
|---------|--------------|
| `alembic upgrade head` | applies all the missing migrations |
| `alembic downgrade -1` | rolls back the last migration |
| `alembic current` | shows the version of the database |
| `alembic history` | shows the chain of migrations |
| `alembic revision --autogenerate -m "text"` | writes a draft from models vs. database |
| `alembic check` | reports whether the models and the database have diverged |
| `alembic upgrade 0001:0002 --sql` | prints the SQL of a migration without running it |
| `alembic stamp head` | marks the database as up to date without running migrations |

The chain: `<base> -> 0001` (create catalog tables) `-> 0002` (add course
level). The database from Lab 6 already had the tables, so it was marked with
`alembic stamp head`; a new database gets both migrations with
`alembic upgrade head`.

### Experiment log

| # | Experiment | What I saw | Cause | How I fixed it |
|---|------------|------------|-------|----------------|
| 1 | the `uq` template in `naming_convention` changed | `check_models.py`: names only in models `['enrollments_course_id_unique', 'students_email_unique']`, only in database `['enrollments_course_id_student_id_key', 'students_email_key']` | with `%(column_0_name)s_unique` SQLAlchemy builds different names than the ones PostgreSQL chose in Lab 6; Alembic would want to recreate the constraints and the error mapping wouldn't find them | restored `%(table_name)s_%(column_0_N_name)s_key`, the check prints `none` twice |
| 2 | `min_length` removed from `StudentIn`, name `N` | `500 Internal Server Error`; in the server log `IntegrityError: (psycopg.errors.CheckViolation) new row for relation "students" violates check constraint "students_name_check"` | the request passed Pydantic, the database's CHECK rejected the row (the data is safe), but `students_name_check` isn't in `CONSTRAINT_ERRORS`, so it was treated as a bug → 500 | put back `Field(min_length=2)`: the 422 comes from Pydantic, CHECK stays as insurance; `try_errors.py` 5 of 5 |
| 3 | a typo in a constraint name in the dictionary | `500`; in the log `UniqueViolation ... unique constraint "students_email_key"` | the key was `students_email_uniq`, the real name is `students_email_key`; the lookup failed and the error was re-raised | restored the key `students_email_key`, 409 again |
| 4 | `title` without `NOT NULL` in the database, `alembic check` | `Detected NOT NULL on column 'courses.title'`, `FAILED: New upgrade operations detected: [[('modify_nullable', ...` ; after `TYPE varchar(100)`: `Detected type change from VARCHAR(length=100) to Text()`, `modify_type` | the database was changed by hand and no longer matches the models | `SET NOT NULL` and `TYPE text` back, `alembic check` clean |
| 5 | automatic migration `0002` on existing data | `IntegrityError: (psycopg.errors.NotNullViolation) column "level" of relation "courses" contains null values`, `[SQL: ALTER TABLE courses ADD COLUMN level TEXT NOT NULL]`; `alembic current` still `0001` | a NOT NULL column without a default can't be added to a table with rows; autogenerate compares schemas, not data | rewrote 0002 in three steps: add nullable → `UPDATE` by rule → `SET NOT NULL` |
| 6 | `import models` commented out in `env.py` | autogenerate: `Detected removed table 'students'`, `'courses'`, `'enrollments'`, `removed index 'enrollments_student_id_idx'`; the file had `op.drop_table(...)` for all three | without the import the models don't register in `Base.metadata`, so Alembic sees an empty target schema and wants to drop everything | didn't run upgrade; deleted `0003_oops.py`, put `import models` back |
| 7 | a `phone` field in the model without a migration | `Detected added column 'students.phone'`, `FAILED: New upgrade operations detected: [('add_column', None, 'students', Column('phone', Text() ...` | the model got ahead of the database | removed the field, `alembic check` clean (in real work: write a migration in the same commit) |
| 8 | two migrations from one revision | `alembic heads`: `0003 (head)` and `0004 (head)`; `upgrade head`: `FAILED: Multiple head revisions are present for given argument 'head'` | two branches started from `0002`, so the history has two heads | `alembic merge heads --rev-id 0005` → one head; then deleted 0003–0005, `alembic heads` = `0002 (head)` |

### Decisions

- **The response is chosen by the constraint name, and the error is caught
  after `commit`.** SQLSTATE says only the kind of violation: `23505` is the
  same for `students_email_key` and for the repeated enrollment, while the
  name says exactly which rule fired (and the message text depends on the
  version and language). Checking first with a `SELECT` (“is the email
  free?”) isn't reliable: between the check and the `INSERT` another request
  can take the same email, and the database would reject it anyway. So we just
  try and handle the refusal — the database's constraint is the single source
  of truth.
- **A like is `UPDATE courses SET likes = likes + 1`.** The database adds the
  one itself and locks the row while doing it, so two simultaneous likes give
  +2. If the program read the number and wrote `likes + 1` back, two requests
  could read the same 11 and both write 12 — one like lost. It's also one
  query (`UPDATE … RETURNING`) instead of two.
- **Migration `0002` has three steps.** The table already has six courses, and
  `ADD COLUMN level TEXT NOT NULL` fails because those rows would have no
  value (experiment 5). So: add the column as nullable, fill the existing rows
  with a rule (electives → `beginner`, the rest → `intermediate`), and only
  then make it `NOT NULL`. Everything runs in one transaction, so a failure
  leaves the database at `0001`.

### Migration 0002 self-check

| What to check | Result |
|---------------|--------|
| Goal and steps | yes — one change (a required `level` on `courses`) in three clear steps; nothing else is in the migration |
| Data | yes — existing rows get a value by a rule (`CASE WHEN is_elective THEN 'beginner' ELSE 'intermediate' END`) before `NOT NULL` is set |
| Renames and drops | yes — nothing is renamed or dropped in `upgrade`; only a column is added |
| Rollback | yes — `downgrade` drops `level`; it erases the level values, which is acceptable here because the rule recreates them, but not if users had set levels by hand |
| Verification | yes — read the SQL from `alembic upgrade 0001:0002 --sql`, ran `downgrade -1` → `upgrade head`, `alembic check` is clean, and the whole chain ran on an empty database |
| History | yes — `alembic heads` shows one head, `0002`; the migration is in the same commit as the model, schema, filter and `seed.sql` changes |
| Application | yes — `CourseOut` has `level`, `GET /courses?level=` filters by it, `seed.sql` inserts `level`; for clients, responses got a new field (nothing removed) |

### Bonus

#### Task 1. A CHECK that autogenerate does not see

I added `CheckConstraint("level IN ('beginner', 'intermediate', 'advanced')",
name="level")` to the `Course` model. `alembic check` printed `No new upgrade
operations detected.`, and `alembic revision --autogenerate` created a
migration with just `pass`: **Alembic doesn't compare CHECK constraints** (it
can't reliably compare SQL expressions — PostgreSQL even stores this one as
`level = ANY (ARRAY['beginner'::text, …])`), so such changes have to be
written by hand.

I wrote `0003_level_check.py` by hand with `op.create_check_constraint(
op.f("courses_level_check"), "courses", "level IN (...)")`. After `upgrade`,
`UPDATE courses SET level = 'expert'` failed with `violates check constraint
"courses_level_check"`. But `downgrade` with a plain string
`"courses_level_check"` failed: `constraint "courses_courses_level_check_check"
of relation "courses" does not exist`, and the database stayed at `0003`.

**Why `op.f` is needed:** Alembic passes every constraint name through
`naming_convention`. A plain string is treated as the short name (like
`name="level"` in the model), so the `ck` template added `courses_` and
`_check` again and doubled it. `op.f(...)` marks the name as final, so the
template isn't applied. With `op.f("courses_level_check")` in `downgrade` the
rollback worked (`0003 -> 0002`). After the task I deleted the migration file
and the `CheckConstraint` line, as the task asks.

## Labs 4–5 (history)

The sections below are from Labs 4 and 5, before the database. Some details
changed in Lab 7 (see “What changed in the API”): the data is in PostgreSQL,
and `POST /enrollments` takes `studentId`.

### Routes

- `GET /` — checks that the server is alive
- `GET /courses` — course list with filtering (`is_elective`), sorting
  (`sort=popular|title`) and pagination (`page`, `page_size` via `Depends`)
- `GET /courses/{course_id}` — one course, or 404 if it doesn't exist
- `GET /stats` — catalog stats: total courses, total credits, electives
- `GET /docs` — interactive Swagger docs (generated by FastAPI)

### What was verified

| Request | Result |
| --- | --- |
| `/` | `{"message": "Course Catalog API is running"}` |
| `/courses` | 6 courses: ai-integration, modern-frontend, web-security, backend-fastapi, databases-postgresql, api-design |
| `/courses/web-security` | the Web Security Essentials course |
| `/courses/nope` | 404, `{"detail": "Course not found"}` |
| `/courses?is_elective=true` | 2 courses: ai-integration, api-design |
| `/courses?is_elective=false` | 4 courses: modern-frontend, web-security, backend-fastapi, databases-postgresql |
| `/courses?sort=title` | ai-integration, api-design, backend-fastapi, modern-frontend, databases-postgresql, web-security |
| `/courses?page=1&page_size=2` | ai-integration, modern-frontend |
| `/courses?page=2&page_size=2` | web-security, backend-fastapi |
| `/courses?page=3&page_size=2` | databases-postgresql, api-design |
| `/courses?page=4&page_size=2` | `[]` |

Also checked: `/docs` shows exactly three routes and the `Course` schema,
`/redoc` and `/openapi.json` open, and with `course_id: int` the request
`/courses/web-security` gives 422 (`Input should be a valid integer`), so the
type stays `str`.

### Bonus tasks

- `sort` is `Literal["popular", "title"]` — `/docs` shows a dropdown, and
  `?sort=banana` gives 422
- pagination params are checked with `Query`: `page >= 1`,
  `1 <= page_size <= 100`, so `?page=0` and `?page_size=1000` give 422
- search by title with `q` (case-insensitive): `?q=react` gives
  modern-frontend, `?q=api` gives backend-fastapi and api-design
- `GET /stats` with its own `Stats` model: `{"total": 6, "total_credits": 28, "electives": 2}`

### Lab 5 — What changed

#### CORS

`CORSMiddleware` allows exactly one origin: `http://localhost:3000` (the
Next.js frontend; scheme + host + port, no trailing slash). The browser needs
this permission to let the frontend's JavaScript read responses from
`localhost:8000` — it's a different origin. Requests from the Next.js server
(Server Components) don't need CORS at all. CORS doesn't protect data: the
server still answers any origin, it just doesn't give the browser permission.

```bash
curl -i -H "Origin: http://localhost:3000" http://localhost:8000/
# access-control-allow-origin: http://localhost:3000
# vary: Origin
curl -i -H "Origin: http://evil.example" http://localhost:8000/
# 200, but no access-control-allow-origin
```

#### camelCase in JSON

All models inherit from `CamelModel` (`alias_generator=to_camel`,
`validate_by_name=True`, `validate_by_alias=True`). Python keeps snake_case,
JSON uses camelCase: `is_elective` → `isElective`, `course_id` → `courseId`,
`student_name` → `studentName`. Query parameters don't change:
`/courses?is_elective=true` still returns 2 courses.

#### New routes

`POST /courses/{course_id}/like` — adds one like, returns the updated course
(`POST /courses/nope/like` → 404):

```json
{"id": "web-security", "title": "Web Security Essentials", "description": "JWT/OAuth2, XSS, CSRF, and SQL injection defense.", "credits": 4, "isElective": false, "likes": 22}
```

`POST /enrollments` — body `{"courseId": "web-security", "studentName": "Aigerim"}`,
answers 201:

```json
{"courseId": "web-security", "studentName": "Aigerim", "id": 1}
```

A one-letter name gives 422 (`"loc": ["body", "studentName"]`,
`"msg": "String should have at least 2 characters"`), an unknown course gives
404 `{"detail": "Course not found"}`.

`GET /enrollments` — all enrollments:

```json
[{"courseId": "web-security", "studentName": "Aigerim", "id": 1}]
```

Likes and enrollments live in memory, so they reset every time the server
restarts.
