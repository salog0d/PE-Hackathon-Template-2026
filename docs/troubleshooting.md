# Troubleshooting — Common Non-Alert Failures

Operational issues that do not necessarily trigger a Prometheus alert but require intervention. For alert-specific response procedures see [`docs/runbook.md`](runbook.md).

---

## App container fails to start

**Symptoms:** `docker compose ps` shows `app` as `Exit 1` or stuck in a restart loop.

**Steps:**

1. Read the exit logs:
   ```bash
   docker compose logs app
   ```
2. **Missing environment variable.** If you see `KeyError` or `ValueError` on startup, a required env var is not set. Verify `.env` contains all required variables (`DATABASE_NAME`, `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USER`, `DATABASE_PASSWORD`). See [`docs/deployment.md`](deployment.md) for the full list.
3. **Database not ready.** If you see `OperationalError: could not connect to server`, the DB container may not be healthy yet. Check:
   ```bash
   docker compose ps db
   docker compose logs db
   ```
   Wait for `db` to reach `healthy`, then restart the app:
   ```bash
   docker compose restart app
   ```
4. **Import error.** A Python syntax error or missing package causes an immediate exit. Read the full traceback in `docker compose logs app` and fix the offending module.

---

## Migrations fail or are out of sync

**Symptoms:** `python migrate.py run` exits with an error; API returns 500 because a table or column is missing.

**Steps:**

1. Check the migration error:
   ```bash
   docker compose exec app python migrate.py run
   ```
2. **Table already exists.** If a migration was partially applied, roll it back and re-run:
   ```bash
   docker compose exec app python migrate.py rollback
   docker compose exec app python migrate.py run
   ```
3. **Database unreachable.** Confirm `docker compose ps db` shows `healthy` before running migrations.
4. **Schema drift.** If the database schema was modified outside of migrations (e.g., manual `ALTER TABLE`), the migration state table (`migratehistory`) may be inconsistent. Inspect it:
   ```bash
   docker compose exec db psql -U postgres -d hackathon_db \
     -c "SELECT * FROM migratehistory ORDER BY id;"
   ```

---

## Seed upload returns 400 or partial count

**Symptoms:** `POST /seed/users` (or `/seed/urls`, `/seed/events`) returns `{"error": "No file provided"}` or a lower `loaded` count than expected.

**Steps:**

1. **Missing file part.** Ensure the `curl` or HTTP client sends `multipart/form-data` with field name `file`:
   ```bash
   curl -X POST http://localhost:5000/seed/users -F "file=@seeds/users.csv"
   ```
2. **Duplicate rows.** The seed endpoints are idempotent — duplicates are silently skipped via `ON CONFLICT DO NOTHING`. A lower count than the CSV row count is expected on re-upload.
3. **Foreign key violation.** URLs reference Users; Events reference both. Upload in order: users → urls → events. The CLI `python seed.py` enforces this order automatically.
4. **Malformed CSV.** Check that the CSV has the expected column headers. Extra columns are ignored; missing required columns cause a DB insert error. The response will show `loaded: 0` for the failed chunk.

---

## Grafana shows "No data" or Prometheus has no metrics

**Symptoms:** Grafana panels display "No data" or Prometheus shows no series for `http_requests_total`.

**Steps:**

1. **Confirm the app is exposing metrics:**
   ```bash
   curl http://localhost:5000/metrics | grep http_requests_total
   ```
2. **Check Prometheus scrape status.** Open http://localhost:9090/targets and verify `url-service` is `UP`.
3. **Check Prometheus config.** The scrape target must resolve. Inside Docker Compose, `app:5000` is the correct address. Outside Docker, use `localhost:5000`.
4. **Check Grafana datasource.** In Grafana → Connections → Data sources, confirm the Prometheus datasource URL is `http://prometheus:9090` (Docker internal) and the test passes.
5. **Check Loki for app logs.** If logs are missing, confirm Promtail is running:
   ```bash
   docker compose ps promtail
   docker compose logs promtail
   ```
   Promtail requires access to `/var/run/docker.sock` — if it is missing or permission-denied, no logs are collected.
