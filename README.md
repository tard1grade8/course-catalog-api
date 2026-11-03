# Course Catalog API

A FastAPI backend for a course catalog providing endpoints for filtering, sorting, and paginating courses.

## How to Run

1. **Create and activate a virtual environment:**
   - **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

**Start the development server:**
```bash
   fastapi dev main.py
   ```
- The API will be available at http://127.0.0.1:8000, and interactive documentation will be generated at /docs.

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

## Experiments Log

### Experiment 2: The database protected the data but answered wrongly
* **Changed:** Removed the `Field(min_length=2)` validation from `name` in `StudentIn` schema inside `schemas.py`.
* **Observed:** Sending a request with `name: "N"` to `POST /students` caused the database `CHECK` constraint (`students_name_check`) to fail, returning a `500 Internal Server Error` instead of `422 Unprocessable Entity`.
* **Reason:** `students_name_check` was not mapped in `CONSTRAINT_ERRORS`, so `raise_http_error` treated the unhandled `IntegrityError` as an unexpected server bug. Pydantic validation acts as the first line of defense (returning 422 before touching the database), while the database `CHECK` constraint serves as the final fail-safe.
* **Fix:** Restored `Field(min_length=2)` to `StudentIn`.

### Experiment 3: A typo in a constraint name
* **Changed:** Replaced `"students_email_key"` with `"students_email_uniq"` in `CONSTRAINT_ERRORS` inside `main.py`.
* **Observed:** Sending `POST /students` with an already registered email (`aigerim@example.com`) returned a `500 Internal Server Error`.
* **Reason:** PostgreSQL reported the constraint violation under the name `students_email_key`. Since the key was missing in `CONSTRAINT_ERRORS`, `raise_http_error` re-raised the exception, resulting in a 500 response.
* **Fix:** Restored the correct key `"students_email_key"`.

### 1. Why is the response chosen by the constraint name rather than by SQLSTATE?
The `SQLSTATE` code (e.g., `23505` for `UNIQUE_VIOLATION` or `23503` for `FOREIGN_KEY_VIOLATION`) is generic across all constraints of the same type in the database. It does not indicate *which specific field or relation* failed (e.g., whether a duplicate student email or a duplicate enrollment occurred). Identifying the exception by its exact `constraint_name` allows the API to return precise HTTP status codes and user-friendly error messages (such as returning 409 Conflict for an existing email vs 404 Not Found for a non-existent student ID).

### 2. Why is it better to catch the error after `commit()` than to check with a `SELECT` in advance?
Following the EAFP (*Easier to ask for forgiveness than permission*) principle avoids race conditions (Time-of-Check to Time-of-Use / TOCTOU). If the API checks availability via a `SELECT` query prior to an `INSERT`, a concurrent request could insert the same record in between the check and the write. The preliminary check would pass, but the insert would fail anyway. Catching `IntegrityError` during `db.commit()` delegates atomicity to PostgreSQL, ensuring thread-safe execution without extra database round-trips.

### Experiment 4: A mismatch between the database and the models
* **Changed:** Altered the `courses` table in PostgreSQL by dropping `NOT NULL` on `title` (`ALTER TABLE courses ALTER COLUMN title DROP NOT NULL;`) and changing its type to `VARCHAR(100)`.
* **Observed:** `alembic check` detected differences and failed with `Detected NOT NULL on column 'courses.title'` (`modify_nullable`) and `Detected type change from VARCHAR(100) to TEXT` (`modify_type`).
* **Reason:** `alembic check` compares the live database schema against the SQLAlchemy models metadata. Any manual schema alterations without corresponding model/migration updates are flagged as drift.
* **Fix:** Restored the column in PostgreSQL back to `TEXT NOT NULL` (`ALTER TABLE courses ALTER COLUMN title TYPE text;`).

### Experiment 5: Adding a NOT NULL column to a non-empty table
* **Changed:** Added `level: Mapped[str]` to `Course` model and generated a standard autogenerated migration (`op.add_column('courses', sa.Column('level', sa.Text(), nullable=False))`).
* **Observed:** Executing `alembic upgrade head` failed with `sqlalchemy.exc.IntegrityError: (psycopg.errors.NotNullViolation) column "level" of relation "courses" contains null values`.
* **Reason:** Alembic compares schemas, not data. Existing rows in the non-empty table cannot satisfy the `NOT NULL` constraint without a default value or manual population strategy.
* **Fix:** Implemented a three-step migration: 1) add `level` as `nullable=True`, 2) run `UPDATE` to set default values based on `is_elective`, 3) alter column to `nullable=False`.

### Experiment 6: A forgotten import models
* **Changed:** Commented out `import models` in `alembic/env.py` and ran `alembic revision --autogenerate -m "oops"`.
* **Observed:** Alembic generated a migration containing `op.drop_table()` for all project tables (`courses`, `students`, `enrollments`).
* **Reason:** Without importing the models module, SQLAlchemy's `Base.metadata` remains empty. Alembic assumes all existing database tables were deleted from the code and generates DDL commands to drop them.
* **Fix:** Deleted the generated migration file and un-commented `import models` in `alembic/env.py`.

### Experiment 7: The model changed, but there is no migration
* **Changed:** Added an optional `phone: Mapped[str | None]` field to the `Student` model in `models.py` without generating a migration.
* **Observed:** Running `alembic check` failed with `FAILED: New upgrade operations detected` (`add_column` for `students.phone`).
* **Reason:** `alembic check` verifies that the live database schema matches the current SQLAlchemy ORM models. Detecting unapplied model changes prevents deploying code without corresponding database migrations.
* **Fix:** Removed the `phone` field from `models.py`.

### Experiment 8: Two heads and a merge
* **Changed:** Created two conflicting migrations from `0002` using `--splice` (`0003` and `0004`).
* **Observed:** Running `alembic heads` displayed two active head revisions, and `alembic upgrade head` failed with `Multiple head revisions are present for given argument 'head'`.
* **Reason:** Concurrent branch development created divergent revision histories rooted at revision `0002`. Alembic cannot determine execution order without an explicit merge.
* **Fix:** Resolved by generating a merge revision (`alembic merge heads`), then deleted temporary experimental revision files (`0003`, `0004`, `0005`) to restore the linear history at `0002`.