# Failure Modes and Recovery Expectations

This document describes how the application behaves under each class of failure and what recovery looks like — automatically or manually.

---

## 1. Database Outage (Total Connectivity Loss)

**Trigger:** Postgres container/host stops or is unreachable.

**What happens per request:**

1. `before_request` calls `_connect_with_retry()` (`app/database/__init__.py:20-33`).
2. It attempts to connect up to **3 times** with exponential back-off (0.5 s, 1 s).
3. All attempts fail → `OperationalError` propagates.
4. The hook catches it and returns `500 {"status": "error", "error": "database unavailable"}`.
5. The `db_up` Prometheus gauge is set to `0` on the next `/health/db` call.

**Readiness probe (`GET /health/db`):** Returns `503 {"status": "degraded", "database": "unreachable"}` — signals load balancers and Kubernetes to stop sending traffic.

**Recovery:** Automatic. Peewee closes the connection at the end of every request (`teardown_appcontext`). When the DB comes back, the next request opens a fresh connection via `_connect_with_retry()` and succeeds without a Flask restart.

**Logs emitted:**
```
WARNING  DB connect attempt 1/3 failed: <error>
WARNING  DB connect attempt 2/3 failed: <error>
WARNING  DB connect attempt 3/3 failed: <error>
ERROR    DB unavailable: <error>
```

**Metrics affected:** `db_up` → `0`, `http_errors_total` increments on each failed request.

See also: [Demo: Forced failure + recovery](demo-forced-failure-plus-recovery.md)

---

## 2. Database Connection Already Closed (Double-Close)

**Trigger:** An exception during a request causes the connection to be closed before `teardown_appcontext` runs.

**What happens:** The teardown hook checks `if not db.is_closed()` before calling `db.close()` (`app/database/__init__.py:73-75`). If already closed, `close()` is never called.

**Recovery:** Transparent — no secondary error is raised. The next request gets a fresh connection as normal.

---

## 3. Validation Failure (Bad Input)

**Trigger:** API request with missing required fields, blank strings, or disallowed field names.

**What happens:**

1. The service layer raises `ValueError` before any DB call is made.
2. The API handler catches it and returns `400 {"error": "<message>"}`.
3. No database interaction occurs; the process is unaffected.

**Recovery:** None needed — isolated to the request scope.

**Examples:**

| Input | Response |
|---|---|
| `POST /users/` with blank `username` | `400 {"error": "username is required"}` |
| `PATCH /urls/<id>` with no valid fields | `400 {"error": "no valid fields to update"}` |

---

## 4. Operation on Non-Existent Resource

**Trigger:** `PATCH` or `DELETE` on an ID that does not exist in the database.

**What happens:** The ORM `UPDATE`/`DELETE` query matches zero rows, returning `0`. The API handler checks `if not updated:` and returns `404 {"error": "Not found"}` instead of a misleading `200`.

**Recovery:** None needed — the caller receives an accurate error code.

---

## 5. Unexpected / Unhandled Exception

**Trigger:** Any exception not caught by service or API layer (e.g., unexpected ORM error, bug).

**What happens:**

1. Flask's global `@app.errorhandler(Exception)` catches it (`app/app.py:96-99`).
2. Returns `500 {"error": "internal server error"}`.
3. The exception is logged with full traceback via `logger.exception("unexpected_error")`.
4. `teardown_appcontext` still fires, releasing the DB connection.

**Recovery:** The process continues serving subsequent requests. The traceback appears in structured logs with `request_id` for correlation.

**Metrics affected:** `http_errors_total` increments for the endpoint.

---

## 6. Malformed / Partial CSV Upload

**Trigger:** `POST /seed/<entity>` with a CSV containing missing values, extra columns, or a chunk with a foreign key violation.

**What happens:**

1. Extra columns are dropped (whitelist applied).
2. `NaN` values in nullable fields are replaced with `None` before insert.
3. Rows are inserted in chunks of 1,000 inside `with db.atomic()`.
4. A failure in one chunk rolls back only that chunk; prior committed chunks are retained.

**Recovery:** Partial success — the API returns a count of rows actually inserted. Re-uploading only the failed rows is safe because each chunk is independent.

---

## 7. No File Provided to Seed Endpoint

**Trigger:** `POST /seed/<entity>` request missing the multipart file part.

**What happens:** Handler checks `if "file" not in request.files:` and immediately returns `400 {"error": "No file provided"}`. No DB interaction occurs.

---

## Summary Table

| Failure | HTTP Response | Auto-Recovery | Key Mechanism |
|---|---|---|---|
| DB total outage | `500` (data), `503` (/health/db) | Yes — next request reconnects | `_connect_with_retry()` + teardown close |
| DB double-close | — (transparent) | Yes | `if not db.is_closed()` guard |
| Validation error | `400` | N/A | `ValueError` → caught in API handler |
| Non-existent resource | `404` | N/A | Row count check after mutation |
| Unhandled exception | `500` | Yes — process continues | Global `errorhandler(Exception)` |
| Malformed CSV | Partial `201` | Partial — per-chunk atomicity | `with db.atomic()` + NaN substitution |
| Missing file | `400` | N/A | Early `request.files` check |
