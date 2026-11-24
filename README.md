# Course Catalog API

Backend of the course catalog: FastAPI, SQLAlchemy, PostgreSQL, Alembic migrations,
GraphQL on Strawberry, and JWT login with roles (Labs 4–9, “Advanced Web Technologies”).

## How to Run

You need Python 3.11 or newer and PostgreSQL 16 or newer.

Once, as the `postgres` superuser, create the role and the database:

```sql
CREATE ROLE catalog_app LOGIN PASSWORD 'change-me';
CREATE DATABASE course_catalog OWNER catalog_app;
```

Then, from the project folder:
```bash
python -m venv .venv
source .venv/bin/activate        # on Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env             # on Windows: copy .env.example .env
# Generate a 32-byte hex key and put it into SECRET_KEY in .env:
python -c "import secrets; print(secrets.token_hex(32))"

alembic upgrade head
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f seed.sql
python seed_users.py
fastapi dev main.py
```

REST docs: http://localhost:8000/docs. GraphQL: http://localhost:8000/graphql.  
The password `change-me` is for training; real projects don't commit passwords.

| E-mail | Role | Password |
| :--- | :--- | :--- |
| admin@example.com | admin | admin-demo-password |
| aigerim@example.com | student (student 1) | aigerim-demo-pass |
| daniyar@example.com | student (student 2) | daniyar-demo-pass |
| asel@example.com | student (student 3) | asel-demo-password |

`seed.sql` also clears `users`: after it, always run `python seed_users.py`.

## What was verified
- The following requests were tested and verified against the expected backend behavior:
- GET / — Returns {"message": "Course Catalog API is running"} confirming the server is alive.
- GET /courses — Returns all 6 courses sorted by popularity (likes descending); ai-integration first (32 likes) and api-design last (11 likes).
- GET /courses?is_elective=true — Returns only 2 elective courses (ai-integration and api-design).
- GET /courses?is_elective=false — Returns only 4 required courses (modern-frontend, web-security, backend-fastapi, databases-postgresql).
- GET /courses?sort=title — Returns all 6 courses sorted alphabetically by title (ai-integration to web-security).
- GET /courses?page=1&page_size=2 — Returns page 1 with 2 courses (ai-integration, modern-frontend).
- GET /courses?page=2&page_size=2 — Returns page 2 with 2 courses (web-security, backend-fastapi).
- GET /courses?page=3&page_size=2 — Returns page 3 with 2 courses (databases-postgresql, api-design).
- GET /courses?page=4&page_size=2 — Returns an empty list [] as there are no courses on page 4.
- GET /courses/web-security — Returns details for the single course Web Security Essentials.
- GET /courses/nope — Returns HTTP status 404 Not Found with {"detail": "Course not found"}.

## What changed (Lab 5)

- **CORS Middleware**: Configured `CORSMiddleware` with `allow_origins=["http://localhost:3000"]` to allow browser-based cross-origin requests from the Next.js frontend.
- **CamelCase JSON**: Configured Pydantic alias generator (`to_camel`) to output field names in camelCase (e.g., `isElective`, `studentName`) for Seamless integration with JavaScript.
- **New Endpoints**:
  - `POST /courses/{id}/like`: Increments the course like count and returns the updated course object.
  - `POST /enrollments`: Validates student enrollment requests and returns the newly created enrollment record.
  - `GET /enrollments`: Returns all recorded course enrollments.

## What changed (Lab 7)

- Database integration: Data is now stored in PostgreSQL using SQLAlchemy ORM (mapped models in models.py) instead of in-memory dictionaries. Data persists across server restarts.

- POST /enrollments: Updated to accept body matching the database schema (courseId and studentId).

- New routes:
  - GET /enrollments returns detailed enrollment records joined with course and student names.
  - GET /stats/courses returns enrollment statistics per course using func.count().

- level field: Added required level string field to courses (beginner, intermediate, advanced). The GET /courses endpoint supports filtering by ?level=.

- Error handling: PostgreSQL integrity constraint violations are intercepted during db.commit() and mapped to explicit HTTP error responses (409 Conflict, 404 Not Found) using CONSTRAINT_ERRORS.

## What changed in the API (Lab 8)

- **RFC 9457 Problem Details for REST errors:** Expected business-rule errors (duplicate enrollments, taken emails, missing courses or students) raise `ServiceError` in `services.py` and are converted by `problem.py` into `application/problem+json` responses with `type`, `title`, `status`, `detail`, and `instance`.
- **Parallel GraphQL endpoint at `/graphql`:** Built with Strawberry (`graphql_api.py`), allowing clients to fetch nested `Course`, `Student`, and `Enrollment` graphs in a single POST request. Unlike REST, GraphQL returns HTTP `200 OK` even when a query fails validation or execution, placing errors in a top-level `"errors"` list.
- **Mutations and `userErrors`:** Added `enroll` and `likeCourse` mutations that return expected business-rule failures inside `"data"` (`userErrors: [{ code, message }]`), leaving top-level `"errors"` for invalid GraphQL syntax/validation or unexpected server failures.
- **`X-SQL-Queries` header:** Added `ContextVars`-based SQLAlchemy event middleware (`counter.py`) that counts every SQL statement executed during an HTTP request and attaches the count in the `X-SQL-Queries` response header to benchmark N+1 vs. batched queries.
- **Server protection and introspection toggle:** Added `QueryDepthLimiter(max_depth=5)`, `MaxAliasesLimiter(max_alias_count=10)`, explicit argument validators (`check_limit` for `1..100` and `parse_id` for integer IDs), `MaskErrors` to hide unhandled database/Python exceptions behind `Unexpected error.`, and `DisableIntrospection` controlled via `GRAPHQL_INTROSPECTION` in `.env`.
- **New REST student routes:** Added `GET /students/{student_id}` and `GET /students/{student_id}/enrollments` powered by a shared `enrollment_details()` query builder in `main.py`.

## Example queries

The “My courses” query (in the GraphQL Variables panel: `{"id": "2"}`):

```graphql
query MyCourses($id: ID!) {
  student(id: $id) {
    name
    enrollments {
      id
      course {
        title
        credits
        level
      }
    }
  }
}
```

The `enroll` mutation and its answer on a repeated enrollment:

```graphql
mutation EnrollStudent {
  enroll(input: { courseId: "api-design", studentId: "1" }) {
    enrollment {
      id
      enrolledAt
    }
    userErrors {
      code
      message
    }
  }
}
```

```json
{
  "data": {
    "enroll": {
      "enrollment": null,
      "userErrors": [
        {
          "code": "ALREADY_ENROLLED",
          "message": "Student is already enrolled in this course"
        }
      ]
    }
  }
}
```

## Migrations

| Command | What it does |
|---|---|
| `alembic upgrade head` | Applies all missing migrations to bring the database up to date. |
| `alembic downgrade -1` | Rolls back the last applied migration. |
| `alembic current` | Shows the current revision of the database. |
| `alembic history` | Shows the full chain of migrations. |
| `alembic revision --autogenerate -m "text"` | Generates a draft migration based on ORM model changes. |
| `alembic check` | Verifies if models and live database schema are in sync. |
| `alembic upgrade 0001:0002 --sql` | Prints the raw SQL commands of a migration without executing them. |
| `alembic stamp head` | Marks the database as up to date without running migration scripts. |

## REST vs GraphQL comparison

The “My courses” screen of student 2; numbers from `measure.py`, starting data.

| Criterion | REST | GraphQL | Source |
| :--- | :--- | :--- | :--- |
| Requests and rounds per screen | 5 requests in 2 rounds | 1 request in 1 round | `measure.py`, step 8 |
| Bytes in the responses | 1160 bytes | 339 bytes | `measure.py`, step 8 |
| SQL queries per screen | 5 SQL queries | 3 SQL queries (batched) | `measure.py`, `X-SQL-Queries` |
| SQL growth with more students | Linear $O(N)$ without eager joins | Constant: 3 queries (1 per nesting level) | `try_n_plus_1.py`, experiments 4–5 |
| Error in the query text | HTTP 422 / 400 validation error | HTTP 200 OK with top-level `"errors"` array | experiments 1 and 8 |
| Expected rule error (repeated enrollment) | HTTP 409 Conflict (`application/problem+json`) | HTTP 200 OK with `data.enroll.userErrors` | steps 1 and 4 |
| HTTP cache | Built-in URL-based caching (`GET` + `Cache-Control`/`ETag`) | Not cacheable by HTTP intermediaries by default (`POST`) | lecture section 14 |
| Protection from “expensive” queries | Bounded by fixed route queries and pagination limits | Requires depth/alias limiters, input checks, and error masking | experiments 6 and 7 |

**Conclusion.** I would keep simple single-entity lookups, public catalog lists, and cache-heavy read endpoints on REST because URL-based HTTP caching works out of the box and query cost is fixed per route. I would choose GraphQL for composite screens like “My courses” that aggregate nested relations, as it reduces network traffic from 5 requests across 2 rounds (1160 bytes) to 1 request in 1 round (339 bytes) while keeping database load constant at 3 batched SQL queries via DataLoaders.

---

## Experiments Log

### Experiment 1: Why naming_convention matters
* **Changed:** Replaced the `"uq"` template in `NAMING_CONVENTION` inside `db.py` with `" %(table_name)s_%(column_0_name)s_unique"`.
* **Observed:** `python check_models.py` showed constraint name mismatches between models and the live database.
* **Reason:** SQLAlchemy generated constraint names using the new template, which differed from PostgreSQL's automatic naming during initial table creation.
* **Fix:** Restored the correct template `"%(table_name)s_%(column_0_N_name)s_key"`.

### Experiment 2: The database protected the data but answered wrongly
* **Changed:** Removed `Field(min_length=2)` validation from `StudentIn` schema in `schemas.py`.
* **Observed:** `POST /students` with `name: "N"` triggered database constraint `students_name_check` and returned `500 Internal Server Error`.
* **Reason:** `students_name_check` was unmapped in `CONSTRAINT_ERRORS`. Pydantic validation acts as the primary defense (422), while database `CHECK` acts as a fail-safe.
* **Fix:** Restored `Field(min_length=2)` to `StudentIn`.

### Experiment 3: A typo in a constraint name
* **Changed:** Replaced `"students_email_key"` with `"students_email_uniq"` in `CONSTRAINT_ERRORS`.
* **Observed:** `POST /students` with duplicate email returned `500 Internal Server Error`.
* **Reason:** PostgreSQL reported `students_email_key`. The unmapped key caused `raise_http_error` to re-raise the exception as 500.
* **Fix:** Restored key `"students_email_key"`.

### Experiment 4: A mismatch between the database and the models
* **Changed:** Dropped `NOT NULL` on `courses.title` and changed type to `VARCHAR(100)` in PostgreSQL.
* **Observed:** `alembic check` failed, flagging `modify_nullable` and `modify_type`.
* **Reason:** `alembic check` detects direct manual database modifications that diverge from ORM models.
* **Fix:** Restored column back to `TEXT NOT NULL`.

### Experiment 5: Adding a NOT NULL column to a non-empty table
* **Changed:** Added `level` as `nullable=False` directly to `Course` model.
* **Observed:** `alembic upgrade head` failed with `psycopg.errors.NotNullViolation`.
* **Reason:** Existing rows cannot satisfy a new `NOT NULL` column without default values or populating logic.
* **Fix:** Rewrote migration into 3 steps: add as `nullable=True`, run `UPDATE`, alter to `nullable=False`.

### Experiment 6: A forgotten import models
* **Changed:** Commented out `import models` in `alembic/env.py`.
* **Observed:** `alembic revision --autogenerate` generated `op.drop_table()` for all tables.
* **Reason:** `Base.metadata` was empty without model imports, making Alembic assume tables were deleted in code.
* **Fix:** Restored `import models` in `alembic/env.py` and removed draft migration.

### Experiment 7: The model changed, but there is no migration
* **Changed:** Added `phone: Mapped[str | None]` to `Student` model without generating a migration.
* **Observed:** `alembic check` failed with `FAILED: New upgrade operations detected`.
* **Reason:** Code changed without a corresponding database revision.
* **Fix:** Removed `phone` field from `Student` model.

### Experiment 8: Two heads and a merge
* **Changed:** Created two divergent migrations from `0002` using `--splice`.
* **Observed:** `alembic heads` listed 2 heads, and `alembic upgrade head` refused to run.
* **Reason:** History diverged into parallel branches.
* **Fix:** Merged branches via `alembic merge heads`, then cleaned up temporary migration files.

---

## Decisions

### 1. Why is the response chosen by the constraint name rather than by SQLSTATE?
The `SQLSTATE` code (e.g., `23505` for `UNIQUE_VIOLATION`) is generic across all unique constraints. It does not indicate *which* specific constraint failed (e.g., duplicate email vs duplicate enrollment). Mapping by exact `constraint_name` allows returning precise HTTP status codes and user-friendly error messages (such as 409 Conflict vs 404 Not Found).

### 2. Why is it better to catch the error after `commit()` than to check with a `SELECT` in advance?
Catching `IntegrityError` during `db.commit()` follows the EAFP principle (*Easier to ask for forgiveness than permission*) and prevents race conditions (TOCTOU). Checking with `SELECT` before `INSERT` leaves a window where concurrent requests can insert the same data, leading to unhandled errors.

---

## Migration 0002 self-check

| What to check | Result |
|---|---|
| Goal and steps | Clear goal (add required `level` column) split into 3 safe steps without data loss. |
| Data | Existing rows populated conditionally (`beginner` for electives, `intermediate` for others). |
| Renames and drops | No columns or tables renamed/dropped; purely additive schema change. |
| Rollback | Tested `alembic downgrade -1` and re-upgrade; rollback cleanly drops `level` column. |
| Verification | SQL generated via `--sql` inspected; tested on fresh database restart. |
| History | Single head (`0002`), linear migration chain from `0001`. |
| Application | `CourseOut` schema updated; `?level=` filter implemented in `GET /courses`; `seed.sql` updated. |

---

## Bonus Task 3: The N+1 Problem

### How to notice N+1 problem
1. **Enable SQL Logging:** Set `SQL_ECHO=true` in `.env` or set `echo=True` on the SQLAlchemy Engine to inspect all executed SQL queries in stdout.
2. **Count Repetitive Statements:** Look for identical `SELECT` statements executed multiple times in sequence with different primary key parameters (e.g., `SELECT ... FROM enrollments WHERE course_id = '...'`).
3. **Event Listeners / Profiling:** Attach a listener to `before_cursor_execute` event (as in `try_n_plus_1.py`) to programmatically track and count query executions per HTTP request.

### Difference between `selectinload` and `joinedload`
- **`selectinload`:** Executes **2 separate queries**. The first loads the parent objects (`SELECT ... FROM courses`), and the second loads all related child objects in a single batch using an `IN` clause (`SELECT ... FROM enrollments WHERE course_id IN ('id1', 'id2', ...)`). Best suited for one-to-many collections to avoid duplicating parent row data.
- **`joinedload`:** Executes **1 single query** using an explicit `LEFT OUTER JOIN` (`SELECT ... FROM courses LEFT OUTER JOIN enrollments ...`). Ideal for many-to-one or one-to-one relationships, but can produce large, duplicate Cartesian products when loading nested one-to-many collections.

---

## Bonus Task 4: A lost update in the ORM

### Why the first variant loses updates
In the first variant (`a.likes += 1`), Python reads the static integer value into memory (e.g., `11`), calculates `11 + 1 = 12`, and issues `UPDATE courses SET likes = 12`. Because both Alice and Bob read `11` before committing, both write hardcoded `12` back to the database. Bob's commit overwrites Alice's changes, causing a **Lost Update**.

### Why the second variant works
In the second variant (`a.likes = Course.likes + 1`), SQLAlchemy generates an SQL expression: `UPDATE courses SET likes = likes + 1`. The evaluation of `likes + 1` happens directly inside PostgreSQL during statement execution rather than in Python memory.

### Relationship to Row Locks (Lab 6)
In PostgreSQL, executing an `UPDATE` automatically acquires an exclusive row-level lock (`FOR UPDATE`) on the target row for the duration of the transaction. When Bob executes `UPDATE courses SET likes = likes + 1`, PostgreSQL forces Bob's transaction to wait until Alice's transaction completes. Once Alice commits (`likes` becomes `12`), Bob's `UPDATE` executes against the freshly committed value (`12 + 1 = 13`), preserving both updates without explicit manual locking.

## Experiment Log for Lab 8

| # | Experiment | What I saw | Cause | How I fixed it |
| :-: | :--- | :--- | :--- | :--- |
| 1 | a typo in a field name, an argument name in `snake_case` | HTTP `200 OK` with `"data": null` and `"errors"` (`Cannot query field 'titel'...`, unknown argument hint) | GraphQL validates syntax and schema at execution time and returns errors in JSON `"errors"` rather than HTTP `4xx` | Corrected field names to match schema (`title`) and used `camelCase` arguments (`isElective`) |
| 2 | `\| None` removed from the `course` query, a nonexistent course | Entire top-level `"data"` collapsed to `null`, even when aliased alongside a valid course | Under GraphQL Null Propagation, `null` in a non-nullable field (`!`) bubbles up to the nearest nullable parent (`Query` root) | Restored `CourseType \| None` return type on optional single-item resolvers |
| 3 | a mutation with the GET method | HTTP `400 Bad Request` (`mutations are not allowed when using GET`); read queries via GET returned `200 OK` | HTTP GET must stay safe and idempotent; Strawberry blocks mutations over GET | Sent all mutations via HTTP `POST` with `Content-Type: application/json` |
| 4 | `more_students.sql`: 3 and 20 students, the SQL counter | `X-SQL-Queries` jumped from `7` (3 students) to `27` and `24` (20 students) | SQLAlchemy lazy loading issued a separate `SELECT` for each nested relation on every row (N+1 problem) | Added per-request `DataLoader` instances in `Context` to batch lookups into single `WHERE ... IN (...)` queries (`3` queries total) |
| 5 | a DataLoader batch function that doesn't sort rows by key | `WrongNumberOfResultsReturned` (`expected: 3, received: 6`) on `students`; silent data mismatch on `enrollments` (4 of 6 wrong) | DataLoader maps returned items positionally by input key index; unsorted DB rows break length or misalign indices | Grouped fetched rows into a `defaultdict` by key value and returned results in `keys` order |
| 6 | six dangerous queries without protection and with it | Unprotected: depth-6 cycle & 12 aliases executed, invalid args leaked SQL/psycopg tracebacks. Protected: all 5 blocked cleanly | GraphQL allows arbitrary query depth/aliases and exposes unhandled exceptions unless guarded | Added `QueryDepthLimiter(5)`, `MaxAliasesLimiter(10)`, `check_limit`, `parse_id`, and `MaskErrors` |
| 7 | introspection off, a typo in a field name | `{ __schema ... }` was rejected; normal queries with typos still returned `Did you mean` hints | `DisableIntrospection` blocks `__schema`/`__type` meta-fields while keeping standard query validation active | Controlled via `GRAPHQL_INTROSPECTION` env setting (`false` for closed production, `true` for dev) |
| 8 | client failures: a typo, no `errors` check, the API stopped | 1) `GraphQLRequestError` with field hint; 2) `TypeError` reading `null` data; 3) `TypeError: fetch failed` | GraphQL returns HTTP `200 OK` on query errors, so checking `res.ok` alone passes `data: null` downstream | Checked `body.errors?.length` in `gql()` and threw `GraphQLRequestError` before returning `data` |

## Decisions

- **Centralizing rules in `services.py` with separate error translators:** Keeping business validation and database integrity checks in `services.py` eliminates duplicate logic and guarantees identical behavior across both APIs. Each transport layer then translates `ServiceError` into its native contract—RFC 9457 HTTP 404/409 Problem Details for REST, and structured `userErrors` payloads inside HTTP 200 responses for GraphQL.
- **Per-request `Context` loaders and value-based key matching:** DataLoaders cache loaded entities by key, so creating them fresh per HTTP request in `Context` prevents stale reads and cross-user data leaks. Matching rows by key value using a dictionary (`defaultdict`) rather than database row position is required because SQL `IN (...)` does not guarantee row order and missing keys must resolve to `None` or `[]` at their exact index.
- **Two-layered protection (`check_limit`/`parse_id` + `MaskErrors`):** Predictable client input mistakes such as negative limits or non-numeric IDs are validated explicitly and raised as `GraphQLError` so callers receive actionable messages to fix their query. Meanwhile, `MaskErrors` acts as a fallback shield for unforeseen runtime or database faults (such as 20-digit `bigint` overflows), keeping full tracebacks in server logs while exposing only `Unexpected error.` to the client.

## Bonus Task 1 (Lab 8)

- **Validation errors as Problem Details (`422`):** Added a `RequestValidationError` handler in `problem.py` that extracts field-level validation failures from Pydantic's `exc.errors()` (mapping `loc` into `in` and dot-joined `field`, and `msg` into `detail`) and returns them as `application/problem+json` (`type: ".../validation-error"`). Under RFC 9457, only `type`, `title`, `status`, `detail`, and `instance` are standard members, while `errors` is a custom extension field included only when multiple per-field validation issues need to be reported at once so the client can fix them in a single pass.


## Lab 9

## Access matrix

The codes come from `python try_access.py` (14 of 14 as expected). The “—” cell: the
administrator has no student profile, so there is nobody to enroll “for yourself”.

| Request | Anonymous | Student | Administrator |
| :--- | :--- | :--- | :--- |
| `GET /courses` | 200 | 200 | 200 |
| `GET /me` | 401 | 200 | 200 |
| `GET /enrollments` | 401 | 403 | 200 |
| `POST /enrollments`, for yourself | 401 | 201 | — |
| `POST /enrollments`, for another | 401 | 403 | 403 |


## Open spots

Found by `scan_routes.py` and `scan_graphql.py`; not closed in this lab.

| Route or field | Verdict | How to close it |
| :--- | :--- | :--- |
| `GET /` | by design: root/health endpoint is public | no need to close it |
| `GET /courses` | by design: the catalog is open to everyone | no need to close it |
| `GET /courses/{id}` | by design: course details are public | no need to close it |
| `POST /courses/{id}/like` | hole: anonymous callers can increment likes without logging in | require `CurrentUser` and track one like per user in the service layer |
| `GET /students` | hole: anonymous callers can list all students and their e-mails | add `_: AdminUser` dependency to the route |
| `POST /students` | hole: anyone can create arbitrary student records | require `AdminUser` (or restrict to self-registration) |
| `GET /students/{id}` | hole: anonymous callers can inspect student profiles by ID | require `CurrentUser` and check `can_access_student` |
| `GET /students/{id}/enrollments` | hole: anyone can view any student's course enrollments | require `CurrentUser` and check `can_access_student(user, student_id)` |
| `GET /stats/courses` | by design: aggregate course statistics are public | no need to close it (or restrict to `AdminUser` if internal) |
| GraphQL `courses` | by design: the catalog is open to everyone | no need to close it |
| GraphQL `course` | by design: course details are public | no need to close it |
| GraphQL `student` | hole: anonymous callers can fetch student objects by ID | add `permission_classes=[IsAuthenticated]` (or `IsAdmin`) |
| GraphQL `enrollments` | hole: anonymous callers can list all enrollments | add `permission_classes=[IsAdmin]` |
| GraphQL `Course.enrollments` | hole: leaks enrollment records via nested course queries | add `permission_classes=[IsAdmin]` on `CourseType.enrollments` |
| GraphQL `Student.enrollments` | hole: leaks a student's enrollments to anonymous or other users | add `permission_classes=[IsSelfOrAdmin]` on `StudentType.enrollments` |
| GraphQL `enroll` | hole: anonymous callers can enroll any student into any course | require `IsAuthenticated` and check `can_access_student` in the service layer |
| GraphQL `likeCourse` | hole: anonymous callers can like courses without authentication | add `permission_classes=[IsAuthenticated]` |

## Threat table

| Where | What can break | How it is covered | How I checked |
| :--- | :--- | :--- | :--- |
| The login form | User enumeration via different error messages or response times on unknown e-mails | Generic `"Invalid e-mail or password"` message and dummy Argon2id verification when e-mail is missing | `try_auth.py`, `try_timing.py` (Experiment 2) |
| Passwords and the key | Plaintext password leaks, weak JWT signing keys, or `alg: none` / algorithm confusion | Argon2id hashing (`pwdlib`), startup validation enforcing `SECRET_KEY` ≥ 32 bytes, pinned `HS256` algorithm | `check_users.py`, `try_tokens.py` (Experiments 1 & 3) |
| Token and role | Stale admin privileges remaining active after role downgrade in the database | JWT carries only `sub` (`user.id`); `role` and `student_id` are loaded fresh from PostgreSQL on every request | `try_access.py`, Experiment 4 |
| Permissions on objects | BOLA / IDOR: students reading other students' private data or enrolling others | `can_access_student` check in REST and `IsSelfOrAdmin` permission class with nullable `email: str \| None` in GraphQL | `try_access.py`, `try_graphql_access.py` (Experiments 5 & 6) |
| Cookie and Next.js | XSS stealing JWT from `localStorage` or forged `session` cookie bypassing middleware | JWT stored in an `httpOnly`, `Secure`, `SameSite=Lax` cookie; real verification via `verifySession()` (`GET /me`) in DAL | Browser DevTools check, Experiment 7 |
| Logout and lifetime | Stolen JWT remaining usable after the user clicks “Log out” | Short token lifetime (`15 min`) and automated route/field scanners catching unprotected endpoints | Experiment 8, `scan_routes.py`, `scan_graphql.py` |

Deliberately not closed:

- Limiting login attempts: the counter must live in shared storage such as Redis (not an in-memory Python dictionary, because multiple Uvicorn worker processes do not share RAM). Limiting solely by e-mail is dangerous because an attacker can intentionally lock out a victim's account (DoS) or spray one password across thousands of e-mails without hitting the per-account threshold, so rate limiting should combine IP address and account keys.
- The token after “Log out”: for this project, I would add a `token_version` integer column on the `users` table, include `ver` in the JWT payload, and increment `token_version` on logout. Because `get_optional_user` already queries the `User` row from PostgreSQL on every authenticated request, checking `claims["ver"] == user.token_version` requires zero extra database queries or external stores.

## Experiment log

| No. | Experiment | What I saw | Cause | How I fixed it |
| :--- | :--- | :--- | :--- | :--- |
| 1 | no key, a short key; two hashes of one password | `ValidationError` on missing/short `SECRET_KEY`; two different `$argon2id$...` strings for the same password | `Settings` enforces ≥ 32-byte key at startup; Argon2id generates a unique random salt per hash | Restored valid `SECRET_KEY` in `.env` |
| 2 | login time with and without `DUMMY_HASH` | Unknown e-mail took ~2 ms vs ~98 ms for known e-mail; with `DUMMY_HASH`, both took ~98 ms | Without `DUMMY_HASH`, missing users skipped Argon2id verification, leaking account existence via timing | Kept `verify_password(password, DUMMY_HASH)` on the unknown-user branch |
| 3 | nine forged tokens; signature check turned off | All 9 forged tokens rejected (`401`); disabling `verify_signature` accepted forged role/sub claims | PyJWT verifies HMAC signature, `exp`, and `iss` only when signature verification is enabled | Restored full `jwt.decode` verification |
| 4 | the role changes in the database, the token is the same | After `UPDATE users SET role='admin'`, old token immediately got `200` on `GET /enrollments` | Role is read from PostgreSQL on every request rather than cached inside the JWT payload | Reverted user role back to `student` in DB |
| 5 | the owner check in `POST /enrollments` removed | Student 1 enrolled Student 2 and received `201 Created` instead of `403` | Without `can_access_student`, any authenticated student could pass an arbitrary `student_id` | Restored `can_access_student` ownership check |
| 6 | the path closed, not the field; the closed field not nullable | Nested `student(id: "2") { email }` leaked email; non-nullable `email: str` crashed whole query with `null` data | Strawberry checks permissions per field, and a denied non-nullable field bubbles `null` up to `data` | Put `IsSelfOrAdmin` on `StudentType.email` and changed its return type to `str \| None` |
| 7 | a forged cookie; protection only in `proxy.ts` | With `verifySession()` removed, `Cookie: session=forged.token.value` returned `200` and secret page content | `proxy.ts` only checks whether a `session` cookie exists, without verifying its signature | Restored `verifySession()` in `app/account/page.tsx` |
| 8 | the token after “Log out” | Calling `GET /me` with the copied Bearer token still returned `200` and user JSON after clicking “Log out” | Logout only deletes the browser cookie; stateless JWTs remain valid until their 15-minute `exp` | Documented limitation in README and selected `token_version` for future revocation |

## Decisions

- **Reading the user's role from the database on every request:** You pay the cost of one primary-key `SELECT` on the `users` table per authenticated request. In return, role changes, account deactivation, or privilege downgrades take effect immediately without waiting for issued tokens to expire.
- **Nullable GraphQL field with field-level permission:** In GraphQL, `Student` can be reached through multiple paths (`Query.student`, `Enrollment.student`, etc.), so hanging the permission on `StudentType.email` protects all paths at once. Making the field `str | None` allows Strawberry to return `null` for that single restricted field plus an error entry while still returning the public parts of the response (`id`, `name`).
- **Why `proxy.ts` alone is not enough:** `proxy.ts` runs before rendering and only checks if a cookie named `session` is present, which anyone can forge in seconds. `verifySession()` sits next to the data in the Data Access Layer and validates the token's signature, expiration, and database user via `GET /me`, ensuring a page is never rendered with forged or revoked credentials.

### Bonus Task 1: Closed-by-default router (`APIRouter`)

To prevent forgetting authentication checks on new endpoints, routes should be grouped under `protected = APIRouter(dependencies=[Depends(get_current_user)])` by default, leaving only explicitly public endpoints on the root `app`:

- **Move into the `protected` router (require authentication by default):**
  - `POST /courses/{course_id}/like` — liking a course requires an authenticated user.
  - `GET /students` — student directory must not be anonymous (additionally requires `AdminUser`).
  - `POST /students` — creating student records must be restricted (additionally requires `AdminUser`).
  - `GET /students/{student_id}` — viewing a student profile requires authentication (plus `can_access_student` owner/admin check).
  - `GET /students/{student_id}/enrollments` — viewing a student's enrollments requires authentication (plus `can_access_student` owner/admin check).
- **Keep outside the `protected` router (deliberately public):**
  - `GET /` — root/health check endpoint.
  - `GET /courses` and `GET /courses/{course_id}` — the course catalog is public by design so prospective students can browse courses without logging in.
  - `GET /stats/courses` — public aggregate course statistics.