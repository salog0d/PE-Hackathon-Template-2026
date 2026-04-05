# Technical Decisions and Architecture Rationale

---

## 1. Flask over FastAPI or Django

**Decision:** Flask 3.1 with manual route definitions and Flasgger for Swagger docs.

**Rationale:** This is a hackathon project with a straightforward CRUD surface. Flask is the lightest option that stays out of the way — no async runtime overhead (FastAPI), no ORM or admin bundled in (Django). Flasgger generates usable Swagger UI from inline docstrings with zero configuration.

**Trade-off:** No built-in data validation or serialization (FastAPI's Pydantic would handle this). Input validation is done manually in the service layer.

---

## 2. Peewee ORM over SQLAlchemy

**Decision:** Peewee as the ORM, `peewee-migrate` for migrations.

**Rationale:** Peewee is significantly smaller and simpler than SQLAlchemy. For a project of this scope (three models, straightforward relations) the reduced API surface reduces cognitive load. `peewee-migrate` auto-generates migration files from model diffs, which is fast enough for a hackathon timeline.

**Trade-off:** Peewee has a smaller ecosystem and less community support than SQLAlchemy. Advanced features (e.g., bulk upsert, window functions) are more awkward to express. The chosen design uses the repository pattern to isolate ORM calls, so swapping to SQLAlchemy later would be a contained change.

---

## 3. Repository pattern

**Decision:** `repositories/` layer mediates all ORM queries. Services never import Peewee models directly.

**Rationale:** Keeps business logic testable without a live database. Repositories return plain objects or `None`; services and API handlers make decisions. This split was validated immediately — the full test suite runs without a database connection using lightweight fakes (no mocking framework needed).

**Known limit:** Repositories are not transactional across multiple models. Operations that span multiple tables (e.g., "create URL and record event atomically") must either use a service-level `db.atomic()` block or be split into separate requests.

---

## 4. PostgreSQL 16

**Decision:** PostgreSQL as the only supported database.

**Rationale:** Peewee's `ON CONFLICT DO NOTHING` syntax (used for idempotent seed inserts) is PostgreSQL-specific. `pg_stat_statements` (referenced in the latency runbook for slow query diagnosis) is a Postgres extension. The CI pipeline spins up `postgres:16-alpine` so tests run against the same engine used in production.

**Capacity note:** The Docker Compose volume (`postgres_data`) is an unbounded local volume. No connection pool is configured — Peewee opens one connection per request via `before_request` and closes it in `teardown_appcontext`. This works correctly under low concurrency but will become a bottleneck under load (see [Capacity assumptions](#capacity-assumptions-and-known-limits) below).

---

## 5. uv for dependency management

**Decision:** `uv` (Astral) instead of pip/poetry/pipenv.

**Rationale:** `uv` resolves and installs dependencies significantly faster than pip. `uv.lock` pins the entire dependency graph (including transitive deps), giving reproducible installs in CI and Docker. The Dockerfile runs `uv pip install --system -r pyproject.toml` rather than creating a second virtualenv inside the container, keeping the image lean.

---

## 6. Prometheus + Grafana + Loki + Promtail + Alertmanager observability stack

**Decision:** Full self-hosted observability stack provisioned via Docker Compose.

**Rationale:** All five services (Prometheus, Grafana, Loki, Promtail, Alertmanager) are provisioned by `docker compose up` with no manual setup. Grafana datasources and the URL Service dashboard are auto-provisioned on first start. This provides metrics, logs, alerting, and dashboards in a single command — suitable for both the hackathon demo and as a template for a real deployment.

**Trade-off:** The stack is stateful (named volumes for Postgres, Loki, Grafana). Prometheus retains 7 days of TSDB data (`--storage.tsdb.retention.time=7d`). Loki has no explicit retention set — data grows unbounded until the volume is pruned manually or the stack is torn down.

**Alerting pipeline:** Alerts fire within ≤ 5 minutes of a threshold breach (2 min `for` + 30 s `group_wait` + ~30 s routing = ~3 min worst-case). Notifications route to Discord via Alertmanager webhook.

---

## 7. JSON structured logging

**Decision:** All log output is JSON (newline-delimited), with a `request_id` UUID per request.

**Rationale:** Promtail collects container stdout via Docker labels and ships it to Loki. Loki's LogQL parser can extract JSON fields for filtering and aggregation. The `request_id` field allows a single request to be traced across all log lines without a distributed tracing system.

**Implementation:** `JsonFormatter` in `app/logging_config.py` wraps Python's standard `logging` module. `request_id` is propagated via a `contextvars.ContextVar` set in `before_request`.

---

## 8. Pandas for bulk CSV import

**Decision:** `BulkLoader` (in `app/utils/bulk_loader.py`) uses Pandas to parse CSVs and insert rows in 1 000-row atomic chunks.

**Rationale:** Pandas handles type coercion edge cases (e.g., `NaN` → `None` for nullable fields, `"True"`/`"False"` strings → Python bools) that would otherwise require manual pre-processing. Chunked inserts bound memory usage so arbitrarily large CSVs don't exhaust container RAM. `ON CONFLICT DO NOTHING` makes every seed endpoint idempotent.

**Trade-off:** Pandas is a heavy dependency (~30 MB) justified only by the hackathon platform's CSV upload requirement. For a production service this functionality would likely be handled by PostgreSQL's native `COPY` command or a streaming CSV parser.

---

## Capacity assumptions and known limits

| Dimension | Assumed limit | Notes |
|---|---|---|
| Concurrent requests | ~20–30 | One DB connection per request; Peewee does not pool connections. Above ~30 concurrent requests, DB connections queue and P99 latency will spike. `HighRequestsInFlight` alerts at 50 in-flight. |
| Request rate | ~100 req/s | Flask dev server (`flask run`) is single-process and single-threaded. For higher throughput, run behind Gunicorn with multiple workers: `gunicorn -w 4 app.main:app`. |
| Database volume | Unbounded (local Docker volume) | No storage limit is set. Monitor with `df -h`; the `DatabaseDown` alert will fire if Postgres cannot write due to a full disk. |
| Prometheus retention | 7 days | Configured via `--storage.tsdb.retention.time=7d` in `docker-compose.yml`. Older samples are dropped automatically. |
| Loki log retention | Unbounded | `loki-config.yml` does not set a retention period. Logs accumulate until the volume is cleaned or the stack is restarted with `docker compose down -v`. |
| CSV seed file size | ~100 MB practical limit | Pandas loads the full file into memory before chunking. Very large CSVs (> 500 MB) may OOM the container (default Docker memory limit). |
| Migration rollback | One step at a time | `python migrate.py rollback` reverts the last migration only. Rolling back multiple versions requires running the command repeatedly. |
| Test coverage gate | 50 % line coverage | CI fails below this threshold (`--cov-fail-under=50`). The gate is intentionally low for a hackathon; raise it for a production codebase. |
