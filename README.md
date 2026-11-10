# Course Catalog API

Backend of the course catalog: FastAPI, SQLAlchemy 2.1+, PostgreSQL, and Alembic migrations (Labs 4–7 of "Advanced Web Technologies").

## How to Run

You need Python 3.11 or newer and PostgreSQL 16 or newer.

Once, as the `postgres` superuser, create the role and the database:

```sql
CREATE ROLE catalog_app LOGIN PASSWORD 'change-me';
CREATE DATABASE course_catalog OWNER catalog_app;
```

Then, from the project folder:
```bash
# Set up environment variables
cp .env.example .env

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python -m alembic upgrade head

# Load initial seed data
psql -h localhost -U catalog_app -d course_catalog -v ON_ERROR_STOP=1 -f seed.sql

# Start the development server
python -m fastapi dev main.py
```

API documentation: http://localhost:8000/docs. The password change-me is for teaching; in a real project, passwords are never put into the repository.

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

### Experiment 1. Query Syntax Error Returns HTTP 200

* **Action:** Executed GraphQL queries containing typos in field names (e.g., `{ course(id: "api-design") { titel } }`) and using `snake_case` instead of `camelCase` for argument names (e.g., `{ courses(is_elective: true) { id } }`).
* **Result:** 
  * HTTP Status: **`200 OK`**.
  * Response Body: A JSON payload with `"data": null` alongside an `"errors"` array specifying error details (e.g., `"Cannot query field 'titel' on type 'Course'"` or hints for unknown arguments).
* **Explanation:** Per the GraphQL specification, syntax errors and schema validation failures do not trigger network-layer HTTP error codes (`4xx`/`5xx`), unlike REST APIs. The GraphQL engine processes the HTTP request successfully, returning `200 OK`, and encapsulates execution and validation errors inside the top-level `"errors"` key.
* **Resolution:** Corrected queries to adhere to the GraphQL schema conventions (using `camelCase` for arguments like `isElective` and exact schema field names like `title`).

---

### Experiment 2. Null Propagation Rule and Non-Nullable Types (`!`)

* **Action:** Temporarily removed `| None` from the `course` resolver return type annotation in `graphql_api.py` (changing the GraphQL field type from `Course` to non-nullable `Course!`). Queried a non-existent course individually and alongside a valid course using aliases (`{ a: course(id: "api-design") { title } b: course(id: "nope") { title } }`).
* **Result:**
  * Single query: Returned `"data": null` with the error `"Cannot return null for non-nullable field Query.course"`.
  * Aliased query: Even though field `a` was valid and could return data, the entire top-level `"data"` object collapsed to `null`.
* **Explanation:** Under GraphQL's Null Propagation Rule, if a non-nullable field (`!`) yields `null`, the error bubbles up to the nearest parent field that allows `null`. Since the top-level `Query` root cannot be `null`, the entire `"data"` payload is destroyed.
* **Resolution:** Reverted the resolver signature to `CourseType | None` for optional database entities, ensuring missing resources return `null` safely without wiping out valid data.

---

### Experiment 3. Blocking Mutations via HTTP GET

* **Action:** Attempted to execute both read queries and data-modifying mutations using URL query parameters via the HTTP GET method (e.g., `http://localhost:8000/graphql?query=mutation{likeCourse(id:"api-design"){course{likes}}}`).
* **Result:**
  * Read query (`query`) via GET returned **`200 OK`** with the requested data.
  * Mutation (`mutation`) via GET was rejected with **`400 Bad Request`** and the plain text message `mutations are not allowed when using GET`.
* **Explanation:** Standard HTTP semantics dictate that GET requests must be safe and idempotent (producing no side effects). Strawberry GraphQL enforces this standard by blocking mutations sent via GET requests to prevent accidental state modifications (e.g., from browser prefetching or search indexers).

---

### Experiment 4. N+1 Query Problem and Database Call Scaling

* **Action:** Utilized custom SQL counter middleware (`counter.py` injecting the `X-SQL-Queries` HTTP header) to benchmark database query counts for nested GraphQL queries under initial seed data (3 students) vs. expanded seed data (20 students via `more_students.sql`).
* **Benchmark Results:**

| Query | 3 Students | 20 Students | SQL Query Composition Breakdown |
| :--- | :---: | :---: | :--- |
| `students -> enrollments -> course` | 7 | 27 | $1 + N + \text{distinct courses} = 1 + 20 + 6$ |
| `enrollments -> course, student` | 7 | 24 | $1 + \text{distinct courses} + \text{distinct students} = 1 + 6 + 17$ |

* **Explanation:** Due to SQLAlchemy ORM lazy loading, GraphQL resolvers issue separate SQL queries for each nested relationship on every row. Increasing student rows by 6.6x caused total SQL queries to jump from 7 to 27 (the classic N+1 problem). While latency remains negligible in local GraphiQL testing, this pattern severely degrades performance in production environments under scale.