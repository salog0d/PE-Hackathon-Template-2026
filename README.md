# URL Shortener API

A production-ready REST API for shortening URLs and tracking click events, built for the MLH PE Hackathon 2026.

**Stack:** Flask 3.1 · Peewee ORM · PostgreSQL · uv · Flasgger (Swagger UI) · Pandas

---

## Prerequisites

- **Python 3.13+** (managed automatically by uv)
- **uv** — fast Python package manager
  ```bash
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Windows (PowerShell)
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **PostgreSQL** running locally or via Docker

---

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Create the database
createdb hackathon_db

# 3. Configure environment
cp .env.example .env   # edit if your DB credentials differ

# 4. Run migrations
python migrate.py run

# 5. (Optional) Seed the database from CSV files
python seed.py

# 6. Start the server
uv run run.py

# 7. Verify
curl http://localhost:5000/health
# → {"status": "ok"}
```

Swagger UI is available at **http://localhost:5000/apidocs**.

---

## Environment Variables

Copy `.env.example` to `.env` and adjust as needed:

| Variable            | Default        | Description              |
|---------------------|----------------|--------------------------|
| `DATABASE_NAME`     | `hackathon_db` | PostgreSQL database name |
| `DATABASE_HOST`     | `localhost`    | Database host            |
| `DATABASE_PORT`     | `5432`         | Database port            |
| `DATABASE_USER`     | `postgres`     | Database user            |
| `DATABASE_PASSWORD` | `postgres`     | Database password        |
| `FLASK_DEBUG`       | `true`         | Enable debug mode        |

---

## Project Structure

```
.
├── app/
│   ├── app.py                      # App factory — registers DB, routes, Swagger
│   ├── main.py                     # WSGI entry point
│   ├── database/
│   │   ├── __init__.py             # DatabaseProxy, BaseModel, connection lifecycle
│   │   └── migrations/
│   │       └── 001_init.py         # Initial schema migration
│   ├── models/
│   │   ├── user.py                 # User model
│   │   ├── url.py                  # Url model (FK → User)
│   │   └── event.py                # Event model (FK → Url, User)
│   ├── repositories/
│   │   ├── user_repository.py      # DB queries for User
│   │   ├── url_repository.py       # DB queries for Url
│   │   └── event_repository.py     # DB queries for Event
│   ├── services/
│   │   ├── user_service.py         # Business logic + validation for User
│   │   ├── url_service.py          # Business logic + validation for Url
│   │   └── event_service.py        # Business logic + validation for Event
│   ├── api/
│   │   ├── __init__.py             # Blueprint registration
│   │   ├── users.py                # CRUD endpoints for /users
│   │   ├── urls.py                 # CRUD endpoints for /urls
│   │   ├── events.py               # CRUD endpoints for /events
│   │   └── seed.py                 # CSV upload endpoints for /seed
│   └── utils/
│       ├── serializers.py          # Model → dict helpers
│       └── bulk_loader.py          # Pandas-backed CSV bulk importer
├── tests/
│   ├── conftest.py                 # Pytest fixtures (app, client, model factories)
│   ├── test_api_routes.py
│   ├── test_api_endpoints.py
│   ├── test_bootstrap.py
│   ├── test_repositories.py
│   ├── test_services.py
│   └── test_utils.py
├── seeds/
│   ├── users.csv
│   ├── urls.csv
│   └── events.csv
├── migrate.py                      # Migration CLI
├── seed.py                         # Seed loader CLI
├── run.py                          # Dev server entry point
├── pyproject.toml
└── .env.example
```

---

## Data Models

### User
| Column       | Type         | Constraints        |
|--------------|--------------|--------------------|
| `id`         | AutoField    | PK                 |
| `username`   | CharField    | max 255, unique    |
| `email`      | CharField    | max 255, unique    |
| `created_at` | DateTimeField|                    |

### Url
| Column         | Type          | Constraints          |
|----------------|---------------|----------------------|
| `id`           | AutoField     | PK                   |
| `user_id`      | ForeignKey    | → users.id           |
| `short_code`   | CharField     | max 20, unique       |
| `original_url` | CharField     | max 2048             |
| `title`        | CharField     | max 255, nullable    |
| `is_active`    | BooleanField  | default True         |
| `created_at`   | DateTimeField |                      |
| `updated_at`   | DateTimeField |                      |

### Event
| Column       | Type          | Constraints       |
|--------------|---------------|-------------------|
| `id`         | AutoField     | PK                |
| `url_id`     | ForeignKey    | → urls.id         |
| `user_id`    | ForeignKey    | → users.id        |
| `event_type` | CharField     | max 50            |
| `timestamp`  | DateTimeField |                   |
| `details`    | TextField     | nullable, JSON    |

---

## API Reference

All responses are JSON. Errors return `{"error": "<message>"}`.

### Health

| Method | Path      | Description  |
|--------|-----------|--------------|
| GET    | `/health` | Health check |

### Users — `/users`

| Method | Path              | Description        | Body / Params                      |
|--------|-------------------|--------------------|------------------------------------|
| GET    | `/users/`         | List all users     |                                    |
| GET    | `/users/<id>`     | Get user by ID     |                                    |
| POST   | `/users/`         | Create user        | `{"username": "", "email": ""}`    |
| PATCH  | `/users/<id>`     | Update user fields | `{"username": "", "email": ""}`    |
| DELETE | `/users/<id>`     | Delete user        |                                    |

### URLs — `/urls`

| Method | Path                     | Description             | Body / Params                                                      |
|--------|--------------------------|-------------------------|--------------------------------------------------------------------|
| GET    | `/urls/`                 | List all URLs           | `?user_id=<int>` to filter by user                                 |
| GET    | `/urls/<id>`             | Get URL by ID           |                                                                    |
| GET    | `/urls/code/<short_code>`| Get URL by short code   |                                                                    |
| POST   | `/urls/`                 | Create short URL        | `{"user_id": 1, "short_code": "abc", "original_url": "https://…", "title": "", "is_active": true}` |
| PATCH  | `/urls/<id>`             | Update URL fields       | `{"short_code": "", "original_url": "", "title": "", "is_active": true}` |
| DELETE | `/urls/<id>`             | Delete URL              |                                                                    |

### Events — `/events`

| Method | Path             | Description           | Body / Params                                            |
|--------|------------------|-----------------------|----------------------------------------------------------|
| GET    | `/events/`       | List all events       | `?url_id=<int>` or `?user_id=<int>` to filter           |
| GET    | `/events/<id>`   | Get event by ID       |                                                          |
| POST   | `/events/`       | Create event          | `{"url_id": 1, "user_id": 1, "event_type": "click", "details": "{}"}` |
| PATCH  | `/events/<id>`   | Update event fields   | `{"event_type": "", "details": ""}`                      |
| DELETE | `/events/<id>`   | Delete event          |                                                          |

### Seed — `/seed` (CSV Upload)

Accepts `multipart/form-data` with a `file` field.

| Method | Path           | CSV columns required                                                          |
|--------|----------------|-------------------------------------------------------------------------------|
| POST   | `/seed/users`  | `id, username, email, created_at`                                             |
| POST   | `/seed/urls`   | `id, user_id, short_code, original_url, title, is_active, created_at, updated_at` |
| POST   | `/seed/events` | `id, url_id, user_id, event_type, timestamp, details`                         |

Example:
```bash
curl -X POST http://localhost:5000/seed/users \
  -F "file=@seeds/users.csv"
```

---

## Migrations

```bash
# Apply all pending migrations
python migrate.py run

# Create a new migration (auto-detected from model changes)
python migrate.py create <name>

# Rollback the last migration
python migrate.py rollback
```

Migrations live in `app/database/migrations/`. The initial migration (`001_init.py`) creates the `users`, `urls`, and `events` tables.

---

## Seeding

**CLI (recommended for initial setup):**
```bash
python seed.py
```
Reads `seeds/users.csv`, `seeds/urls.csv`, and `seeds/events.csv` in FK-safe order (Users → URLs → Events). Uses chunked inserts (1 000 rows/batch) via Pandas for large datasets.

**HTTP endpoint:** See the `/seed` routes above — useful for uploading from the hackathon platform UI.

---

## Running Tests

```bash
# Run all tests
PYTHONPATH=. uv run pytest

# With coverage report (CI requires ≥ 50%)
PYTHONPATH=. uv run pytest --cov=app --cov-report=term-missing

# Run a single file
PYTHONPATH=. uv run pytest tests/test_services.py -v
```

No PostgreSQL instance is needed. Every test monkeypatches the service or repository layer so the real database is never touched.

### Test files

| File | What it covers |
|---|---|
| `test_bootstrap.py` | `init_db` — verifies env vars are read, `PostgresqlDatabase` is constructed with the right arguments, `before_request` opens the connection with `reuse_if_open=True`, and `teardown_appcontext` closes it only when it is open. Also verifies `app.main` calls `app.run(debug=True)` when executed as `__main__`. |
| `test_repositories.py` | Repository CRUD functions — `get_all`, `get_by_id`, `get_by_short_code`, `get_by_user`, `create`, `update`, `delete` — for all three models using lightweight fake ORM classes instead of hitting the database. |
| `test_services.py` | Service-layer validation — blank/whitespace inputs are rejected with the correct `ValueError` messages, allowed fields are whitelisted on update, `created_at`/`updated_at`/`timestamp` are set to `datetime` objects, and `event_type` is trimmed before being saved. |
| `test_api_routes.py` | HTTP contract tests for every blueprint — status codes, JSON response shapes, 404 / 400 error bodies, the `?user_id=` filter on `/urls/`, the `url_id`-priority filter on `/events/`, and the `No file provided` guard on `/seed/users`. |
| `test_api_endpoints.py` | Additional endpoint integration checks — successful create/update/delete flows for URLs and Events, the seed CSV upload endpoints for URLs and Events returning the correct `loaded` count. |
| `test_utils.py` | `serialize_user/url/event` output shapes, and four `BulkLoader` transform tests: column whitelisting on users, `"True"`/`"False"` string → bool coercion on URLs, `NaN` → `None` replacement for nullable `details` on events, and FK-safe load order (`users → urls → events`) enforced by `load_all`. |

---

## CI

CI runs on every push and pull request to `main` and `develop`. Concurrent runs on the same ref are cancelled automatically (`concurrency: cancel-in-progress: true`).

### Pipeline overview

```
push / pull_request
        │
        ▼
┌──────────────────┐        fails fast — test job won't
│   quality job    │ ──────► start if linting fails
└──────────────────┘
        │ needs: quality
        ▼
┌──────────────────┐
│    test job      │
└──────────────────┘
```

### `quality` job — Lint and format checks

Runs on `ubuntu-latest`, timeout 10 min.

| Step | Tool | What it checks |
|---|---|---|
| Install deps | `uv sync --frozen` | Reproduces exact locked environment (`uv.lock`) |
| Lint | `uvx ruff check . --output-format=github` | PEP 8, import order, unused variables, common bugs |
| Format | `uvx ruff format --check .` | Consistent code style — fails if any file needs reformatting |

`UV_FROZEN=true` is set globally so any accidental `uv add` in CI fails rather than silently mutating the lock file.

### `test` job — Tests and smoke checks

Runs on `ubuntu-latest`, timeout 15 min. Requires `quality` to pass first.

Spins up a real **PostgreSQL 16** service container:

```yaml
image: postgres:16-alpine
POSTGRES_DB: hackathon_db
POSTGRES_USER: postgres
POSTGRES_PASSWORD: postgres
health-check: pg_isready (retries 5, interval 10s)
```

| Step | What it does |
|---|---|
| Import smoke check | `from app import create_app; app=create_app()` — verifies the app factory, Swagger setup, and all blueprint registrations succeed without errors |
| pytest + coverage | Runs the full suite with `--cov=app --cov-report=term-missing --cov-fail-under=50`; exit code 5 (no tests collected) is treated as a pass so an empty suite doesn't block PRs |

### Running CI checks locally

```bash
# Lint
uvx ruff check . --output-format=github

# Format check
uvx ruff format --check .

# Fix lint + format issues automatically
uvx ruff check . --fix && uvx ruff format .

# Full test run matching CI
PYTHONPATH=. uv run --with pytest --with pytest-cov pytest -q --cov=app --cov-report=term-missing --cov-fail-under=50
```

---

## uv Reference

| Command              | What it does                                  |
|----------------------|-----------------------------------------------|
| `uv sync`            | Install all dependencies (creates `.venv`)    |
| `uv run <script>`    | Run a script using the project's virtual env  |
| `uv add <package>`   | Add a dependency                              |
| `uv remove <package>`| Remove a dependency                           |

---

## Architecture Notes

- **Repository pattern**: `repositories/` handles all raw Peewee queries. Services never touch the ORM directly.
- **Service layer**: `services/` owns validation and business rules. Routes call services, not repositories.
- **Connection lifecycle**: `before_request` opens the connection; `teardown_appcontext` closes it even on errors.
- **Bulk loading**: `BulkLoader` processes CSVs in 1 000-row chunks inside transactions to bound memory and guarantee atomicity per batch.
- **Interactive docs**: Flasgger generates Swagger 2.0 docs from inline docstrings. Visit `/apidocs` while the server is running.
