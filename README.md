# URL Shortener API

A production-ready REST API for shortening URLs and tracking click events, built for the MLH PE Hackathon 2026.

**Stack:** Flask 3.1 · Peewee ORM · PostgreSQL · uv · Flasgger (Swagger UI) · Pandas  
**Observability:** Prometheus · Grafana · Loki · Promtail · Alertmanager

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
- **Docker + Docker Compose** — required for the full stack (app + observability)

---

## Quick Start

### Full stack (recommended)

Runs the API, PostgreSQL, Prometheus, Grafana, Loki, Promtail, and Alertmanager in one command.

```bash
# 1. Configure environment
cp .env.example .env   # edit DB credentials / Grafana password if needed

# 2. Start everything
docker compose up --build -d

# 3. Run migrations
docker compose exec app python migrate.py run

# 4. (Optional) Seed the database
docker compose exec app python seed.py

# 5. Verify
curl http://localhost:5000/health
# → {"status": "ok"}
```

| Service | URL |
|---|---|
| API | http://localhost:5000 |
| Swagger UI | http://localhost:5000/apidocs |
| Grafana | http://localhost:3000 (admin / admin) |
| Prometheus | http://localhost:9090 |
| Alertmanager | http://localhost:9093 |
| Loki | http://localhost:3100 |

### Local dev (no Docker)

```bash
# 1. Install dependencies
uv sync

# 2. Create the database
createdb hackathon_db

# 3. Configure environment
cp .env.example .env

# 4. Run migrations
python migrate.py run

# 5. (Optional) Seed the database
python seed.py

# 6. Start the server
uv run run.py
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
| `LOG_LEVEL`         | `INFO`         | App log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `SERVICE_NAME`      | `url-service`  | Service name stamped on every log line |
| `GRAFANA_PASSWORD`  | `admin`        | Grafana admin password   |

---

## Project Structure

```
.
├── app/
│   ├── app.py                      # App factory — registers DB, routes, Swagger, metrics
│   ├── main.py                     # WSGI entry point
│   ├── metrics.py                  # Prometheus metric definitions
│   ├── logging_config.py           # JSON structured logging (JsonFormatter)
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
│       └── bulk_loader.py          # Pandas-backed idempotent CSV bulk importer
├── observability/
│   ├── prometheus/
│   │   ├── prometheus.yml          # Scrape config (url-service + alertmanager)
│   │   └── alert_rules.yml         # 6 alert rules (availability, latency, errors, saturation)
│   ├── alertmanager/
│   │   └── alertmanager.yml        # Discord webhook routing, severity-based repeat intervals
│   ├── grafana/
│   │   └── provisioning/
│   │       ├── dashboards/
│   │       │   ├── dashboards.yml  # Dashboard provider config
│   │       │   └── url-service.json# Pre-built dashboard (traffic, latency, errors, saturation, logs)
│   │       └── datasources/
│   │           └── datasources.yml # Prometheus + Loki datasources (auto-provisioned)
│   ├── loki/
│   │   └── loki-config.yml         # Loki storage and retention config
│   └── promtail/
│       └── promtail-config.yml     # Log scraping from Docker container labels
├── docs/
│   ├── observability.md            # Metrics reference, log format, alerting SLO
│   ├── runbook.md                  # Alert-response procedures for all 6 alerts
│   ├── incident-rca-2026-04-05.md  # RCA: duplicate username 500 on seed endpoint
│   ├── error-handling.md           # API error contracts, validation, failure modes
│   ├── failure-modes.md            # Per-failure-class behaviour and recovery
│   └── chaos-restart-demo.md       # Chaos/recovery demonstration guide
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
├── docker-compose.yml              # Full stack: app + DB + observability
├── Dockerfile
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

Accepts `multipart/form-data` with a `file` field. All seed endpoints are **idempotent** — uploading the same CSV multiple times is safe; duplicate rows are skipped via `ON CONFLICT DO NOTHING`.

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

## Observability

The full observability stack is provisioned automatically by `docker compose up`.

### Metrics — Prometheus + Grafana

The app exposes `GET /metrics` in Prometheus text format. Prometheus scrapes it every 15 seconds.

| Metric | Type | Description |
|---|---|---|
| `http_requests_total` | Counter | Total requests, labelled by `method`, `endpoint`, `status` |
| `http_request_duration_seconds` | Histogram | Request latency (buckets: 0.05 s → 10 s) |
| `http_requests_in_progress` | Gauge | Currently in-flight requests |
| `http_errors_total` | Counter | Total 5xx errors by `method` and `endpoint` |
| `db_up` | Gauge | Database reachability: `1` = up, `0` = down |
| `urls_created_total` | Counter | Short URLs successfully created |

The **URL Service** Grafana dashboard (auto-provisioned at startup) shows:
- Traffic: request rate and total counter
- Latency: p50 / p95 / p99 timeseries and a p95 gauge with red/yellow/green thresholds
- Errors: 5xx rate and error ratio (%)
- Saturation: in-flight requests and database health status
- Logs: live application and error log streams from Loki

### Logging — Loki + Promtail

Every log line is emitted as a JSON object to stdout and collected by Promtail via Docker container labels. Logs are queryable in Grafana using LogQL:

```
{service="url-service"}                    # all logs
{service="url-service", level="ERROR"}     # errors only
```

Each log line includes `timestamp`, `level`, `service`, `logger`, `message`, `request_id`, and optional `exc_info`.

### Alerting — Alertmanager → Discord

Six Prometheus alerting rules fire within **≤ 5 minutes** of a threshold breach (pending period + Alertmanager `group_wait` + routing overhead ≤ 5 min). Notifications are delivered to Discord.

| Alert | Severity | Condition |
|---|---|---|
| `ServiceDown` | critical | Service unreachable for 1 m |
| `DatabaseDown` | critical | `db_up == 0` for 1 m |
| `HighErrorRate` | critical | 5xx rate > 5 % for 2 m |
| `HighLatencyP99` | critical | P99 > 1 s for 1 m |
| `HighLatencyP95` | warning | P95 > 500 ms for 2 m |
| `HighRequestsInFlight` | warning | In-flight > 50 for 2 m |

See [`docs/runbook.md`](docs/runbook.md) for step-by-step response procedures and [`docs/observability.md`](docs/observability.md) for the full SLO breakdown.

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
- **Connection lifecycle**: `before_request` opens the connection with `reuse_if_open=True`; `teardown_appcontext` closes it even on errors, guarded against double-close.
- **Bulk loading**: `BulkLoader` processes CSVs in 1 000-row chunks inside atomic transactions. Duplicate rows are skipped via `ON CONFLICT DO NOTHING`, making all seed endpoints idempotent.
- **Structured logging**: Every log line is a JSON object with `request_id` for per-request correlation. Promtail ships logs to Loki; Grafana surfaces them alongside metrics.
- **Metrics instrumentation**: Request count, latency histogram, in-flight gauge, error counter, and DB health gauge are updated in `before_request` / `after_request` middleware hooks and the `/health/db` endpoint.
- **Observability stack**: All seven services (app, db, prometheus, alertmanager, loki, promtail, grafana) are defined in `docker-compose.yml`. Grafana datasources and the URL Service dashboard are auto-provisioned on first start — no manual setup required.
- **Interactive docs**: Flasgger generates Swagger 2.0 docs from inline docstrings. Visit `/apidocs` while the server is running.

---

## Documentation

| Doc | Contents |
|---|---|
| [`docs/deployment.md`](docs/deployment.md) | Deployment steps, rollback procedures, environment variables, health verification |
| [`docs/decisions.md`](docs/decisions.md) | Major technical decisions and rationale |
| [`docs/capacity.md`](docs/capacity.md) | Current limits, capacity assumptions, and scalability roadmap (single instance → Redis cache → 500+ users) |
| [`load-tests/README.md`](load-tests/README.md) | k6 load test suite — smoke, load, stress, and soak scenarios |
| [`docs/runbook.md`](docs/runbook.md) | Step-by-step alert response procedures for all 6 alerts |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Non-alert failures: startup crashes, migration errors, seed issues, missing metrics |
| [`docs/observability.md`](docs/observability.md) | Metrics reference, log format, alerting SLO, alert inventory |
| [`docs/error-handling.md`](docs/error-handling.md) | API error contracts, validation rules, failure mode catalogue |
| [`docs/failure-modes.md`](docs/failure-modes.md) | Per-failure-class behaviour, recovery mechanisms, and expected logs |
| [`docs/incident-rca-2026-04-05.md`](docs/incident-rca-2026-04-05.md) | RCA: duplicate username 500 on `/seed/users` |
