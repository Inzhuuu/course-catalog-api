Inzhu Rakhym, IT3-2301, labs 4–7

# course-catalog-api

Backend of the course catalog: FastAPI, SQLAlchemy 2.1, PostgreSQL, and Alembic
migrations (Labs 4–7 of "Advanced Web Technologies").

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
cp .env.example .env               # the database address; edit it if yours differs
alembic upgrade head               # creates the tables (migrations 0001 and 0002)
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f seed.sql
alembic check                      # "No new upgrade operations detected."
fastapi dev main.py
```

In a second window, with the server running, `python try_errors.py` should
print `5 of 5 as expected`. Helper scripts: `python check_db.py` (connection),
`python check_models.py` (models vs. database). Add `SQL_ECHO=true` to `.env`
to see the SQL that SQLAlchemy sends (only on your own machine).

API documentation: http://localhost:8000/docs. The password `change-me` is for
teaching; in a real project, passwords are never put into the repository.

## What changed in the API

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

## Migrations

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

## Experiment log

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

## Decisions

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

## Migration 0002 self-check

| What to check | Result |
|---------------|--------|
| Goal and steps | yes — one change (a required `level` on `courses`) in three clear steps; nothing else is in the migration |
| Data | yes — existing rows get a value by a rule (`CASE WHEN is_elective THEN 'beginner' ELSE 'intermediate' END`) before `NOT NULL` is set |
| Renames and drops | yes — nothing is renamed or dropped in `upgrade`; only a column is added |
| Rollback | yes — `downgrade` drops `level`; it erases the level values, which is acceptable here because the rule recreates them, but not if users had set levels by hand |
| Verification | yes — read the SQL from `alembic upgrade 0001:0002 --sql`, ran `downgrade -1` → `upgrade head`, `alembic check` is clean, and the whole chain ran on an empty database |
| History | yes — `alembic heads` shows one head, `0002`; the migration is in the same commit as the model, schema, filter and `seed.sql` changes |
| Application | yes — `CourseOut` has `level`, `GET /courses?level=` filters by it, `seed.sql` inserts `level`; for clients, responses got a new field (nothing removed) |

## Bonus

### Task 1. A CHECK that autogenerate does not see

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
