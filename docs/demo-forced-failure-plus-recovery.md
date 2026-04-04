# Demo: Forced failure + recovery (Postgres Docker container)

This demo shows that the app handles a total database outage gracefully — retrying
on each request, reporting degraded health, and reconnecting automatically once the
database is back, **without restarting the Flask process**.

---

## Prerequisites

| What | Value |
|------|-------|
| Running container | `hackathon-postgres` (image: `postgres`) |
| App URL | `http://localhost:5000` |

---

## Step-by-step

### 1. Confirm everything is healthy

```bash
curl http://localhost:5000/health/db
```

Expected response (`HTTP 200`):

```json
{"database": "reachable", "status": "ok"}
```

---

### 2. Shut down the Postgres container

```bash
docker stop hackathon-postgres
```

The container exits immediately. The Flask process keeps running.

---

### 3. Hit a data endpoint — app retries 3×, then returns 500

```bash
curl -i http://localhost:5000/urls/
```

Expected response (`HTTP 500`):

```json
{"error": "database unavailable", "status": "error"}
```

What happens internally (`app/database/__init__.py`):

- `_connect_with_retry()` attempts to open a connection up to **3 times**
  (`_MAX_RETRIES = 3`), sleeping 0.5 s, 1 s between attempts.
- All three attempts fail with `OperationalError`.
- The `before_request` hook catches the final exception and returns `500`.
- Three `WARNING` lines appear in the Flask log:

  ```
  WARNING DB connect attempt 1/3 failed: ...
  WARNING DB connect attempt 2/3 failed: ...
  WARNING DB connect attempt 3/3 failed: ...
  ERROR   DB unavailable: ...
  ```

---

### 4. Confirm the readiness probe reports degraded

```bash
curl -i http://localhost:5000/health/db
```

Expected response (`HTTP 503`):

```json
{"database": "unreachable", "error": "...", "status": "degraded"}
```

> The `/health/db` endpoint (`check_db()`) runs `SELECT 1` directly against the
> proxy. With the container down the query raises an exception and the endpoint
> returns `503` — the correct signal for a Kubernetes/load-balancer readiness probe
> to stop sending traffic.

---

### 5. Restore the Postgres container

```bash
docker start hackathon-postgres
```

Wait a couple of seconds for Postgres to finish its startup sequence.

---

### 6. App reconnects automatically — no restart needed

```bash
curl http://localhost:5000/health/db
```

Expected response (`HTTP 200`):

```json
{"database": "reachable", "status": "ok"}
```

```bash
curl http://localhost:5000/urls/
```

Returns normal data. No Flask restart was required.

Demo video: https://youtu.be/aWo_z5aP880

---

## Why this works

Peewee's `teardown_appcontext` hook (`_db_close`) closes the connection at the end
of every request. The next request therefore always opens a **fresh** connection via
`_connect_with_retry()`. There is no long-lived connection that could be stuck in a
broken state — once the DB container is back up, the very next request succeeds.
