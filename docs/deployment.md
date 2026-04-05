# Deployment and Rollback

## Environment variables

Copy `.env.example` to `.env` before the first deploy. All variables have safe defaults for local/dev but **must** be overridden in any shared or production environment.

| Variable | Default | Required | Description |
|---|---|---|---|
| `DATABASE_NAME` | `hackathon_db` | yes | PostgreSQL database name |
| `DATABASE_HOST` | `localhost` | yes | Database hostname (use `db` inside Docker Compose) |
| `DATABASE_PORT` | `5432` | yes | Database port |
| `DATABASE_USER` | `postgres` | yes | Database user |
| `DATABASE_PASSWORD` | `postgres` | yes | Database password — **change in production** |
| `FLASK_DEBUG` | `true` | no | Set to `false` in production |
| `LOG_LEVEL` | `INFO` | no | Root log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `SERVICE_NAME` | `url-service` | no | Stamped on every structured log line; used as the Loki label |
| `GRAFANA_PASSWORD` | `admin` | no | Grafana admin password — **change in production** |

`DATABASE_HOST` is overridden to `db` inside `docker-compose.yml` so the app container can reach the Postgres container by service name. Do not set it to `localhost` when using Docker Compose.

---

## Initial deployment (full stack — recommended)

```bash
# 1. Clone the repo and enter the directory
git clone <repo-url>
cd PE-Hackathon-Template-2026

# 2. Configure environment
cp .env.example .env
# Edit .env — at minimum change DATABASE_PASSWORD and GRAFANA_PASSWORD

# 3. Build and start all services
docker compose up --build -d

# 4. Apply database migrations
docker compose exec app python migrate.py run

# 5. (Optional) Load seed data
docker compose exec app python migrate.py run   # idempotent; safe to re-run
docker compose exec app python -c "import seed; seed.run()"
# or use the CLI:
docker compose exec app python seed.py

# 6. Verify
curl http://localhost:5000/health
# → {"status": "ok"}

curl http://localhost:5000/health/db
# → {"status": "ok", "database": "reachable"}
```

| Service | URL | Default credentials |
|---|---|---|
| API | http://localhost:5000 | — |
| Swagger UI | http://localhost:5000/apidocs | — |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |
| Alertmanager | http://localhost:9093 | — |
| Loki | http://localhost:3100 | — |

---

## Deploying a new version

```bash
# 1. Pull the latest code
git pull origin main

# 2. Rebuild and restart only the app container (zero-downtime for DB + observability)
docker compose up --build -d app

# 3. Apply any new migrations
docker compose exec app python migrate.py run

# 4. Verify
curl http://localhost:5000/health
docker compose logs --tail=20 app
```

If the new image introduces breaking changes to other services (e.g., a new Prometheus scrape target), rebuild the full stack:

```bash
docker compose up --build -d
```

---

## Rollback

### Application rollback (code change)

```bash
# 1. Identify the last known-good commit
git log --oneline -10

# 2. Check out that commit (or a tag)
git checkout <commit-sha>

# 3. Rebuild and restart the app
docker compose up --build -d app

# 4. Verify
curl http://localhost:5000/health
```

To return to the main branch after investigation:

```bash
git checkout main
docker compose up --build -d app
```

### Database migration rollback

```bash
# Revert the most recent migration
docker compose exec app python migrate.py rollback

# Verify the schema is in the expected state by inspecting tables:
docker compose exec db psql -U postgres -d hackathon_db -c "\dt"
```

`rollback` reverts one migration at a time. Run it repeatedly to step back multiple versions.

### Full stack teardown and clean restart

This destroys all data volumes. Use only when recovering from an unrecoverable state.

```bash
# Stop everything and remove volumes
docker compose down -v

# Bring back up fresh
docker compose up --build -d
docker compose exec app python migrate.py run
```

---

## Health verification after deployment

Run the following checks after any deployment or rollback:

```bash
# 1. Process liveness
curl http://localhost:5000/health
# Expected: {"status": "ok"}

# 2. Database connectivity
curl http://localhost:5000/health/db
# Expected: {"status": "ok", "database": "reachable"}

# 3. Metrics endpoint (confirms Prometheus scraping will work)
curl -s http://localhost:5000/metrics | head -5

# 4. Container health
docker compose ps

# 5. Recent logs (look for ERROR lines)
docker compose logs --tail=50 app | grep '"level": "ERROR"'
```

If `health/db` returns `503`, the database container is not yet healthy — wait 10–15 seconds and retry, or check `docker compose ps db` and `docker compose logs db`.

---

## Local development (no Docker)

```bash
# 1. Install dependencies (creates .venv automatically)
uv sync

# 2. Create the local database
createdb hackathon_db

# 3. Configure environment
cp .env.example .env
# DATABASE_HOST defaults to localhost — correct for local dev

# 4. Apply migrations
python migrate.py run

# 5. (Optional) Seed data
python seed.py

# 6. Start the dev server
uv run run.py
```

The dev server runs with `FLASK_DEBUG=true` (hot reload on code changes). Observability tools (Prometheus, Grafana, Loki) are not started in local dev mode.

---

## CI pipeline

CI runs automatically on every push and pull request to `main` and `develop`.

```
push / pull_request
        │
        ▼
┌──────────────────┐
│   quality job    │  ruff check + ruff format --check
└──────────────────┘
        │ needs: quality (blocks on lint failure)
        ▼
┌──────────────────┐
│    test job      │  pytest + coverage ≥ 50 % against real Postgres 16
└──────────────────┘
```

To run CI checks locally before pushing:

```bash
# Lint
uvx ruff check . --output-format=github

# Format check
uvx ruff format --check .

# Fix all auto-fixable issues
uvx ruff check . --fix && uvx ruff format .

# Full test suite
PYTHONPATH=. uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=50
```
