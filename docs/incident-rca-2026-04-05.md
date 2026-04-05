# Incident RCA — Seed Endpoint 500 on Duplicate Username

**Incident ID:** INC-2026-04-05-001  
**Date:** 2026-04-05  
**Severity:** P2 — partial service degradation (seed endpoint unavailable; read/write API unaffected)  
**Status:** Resolved  
**Author:** on-call engineer  

---

Video demo: https://youtu.be/flEx7pPTJiA

## Summary

The `POST /seed/users` endpoint began returning HTTP 500 at 06:05 UTC on 2026-04-05. The failure was caused by `BulkLoader.load_users` calling `insert_many(...).execute()` without a conflict-resolution strategy. When the same CSV was uploaded a second time, Peewee attempted a plain `INSERT` for every row; the database rejected rows whose `username` values already existed, raising `peewee.IntegrityError` and surfacing as an unhandled 500.

The `HighErrorRate` alert fired within 3 minutes. The fix — adding `.on_conflict_ignore()` to the insert call — was deployed at 06:31 UTC. Total duration: **26 minutes**.

---

## Timeline

All times UTC.

| Time | Event |
|---|---|
| 05:58 | Operator re-uploads `users.csv` to refresh seed data after a staging reset. |
| 06:00 | First `POST /seed/users` request completes successfully (fresh database, no conflicts). |
| 06:03 | Operator uploads the same `users.csv` a second time after noticing missing URL records; intends to re-seed all entities. |
| 06:05:33 | First `IntegrityError` logged: `duplicate key value violates unique constraint "user_username"` for user `opalharvest72`. The entire batch fails; endpoint returns `500`. |
| 06:06 | `http_errors_total` begins incrementing. `HighErrorRate` enters pending state. |
| 06:08 | **`HighErrorRate` alert fires.** Discord notification received. On-call engineer acknowledges. |
| 06:09 | Engineer opens Grafana → *Error Rate* panel shows 100 % error ratio on `POST /seed/users`. All other endpoints healthy. |
| 06:11 | Engineer pulls structured logs from Loki: `{service="url-service", level="ERROR"}`. Full traceback identifies `bulk_loader.py:35` as the origin. |
| 06:14 | Root cause confirmed: plain `INSERT` with no conflict handling on a second upload of the same file. |
| 06:18 | Fix authored: `model.insert_many(records).on_conflict_ignore().execute()` in `app/utils/bulk_loader.py:35`. |
| 06:24 | Fix reviewed and merged. Docker image rebuilt. |
| 06:31 | New image deployed via `docker compose up -d url-service`. |
| 06:32 | Smoke test: `POST /seed/users` with duplicate CSV returns `200 {"loaded": 500, "model": "users"}`. |
| 06:33 | `HighErrorRate` alert resolves. Incident closed. |

---

## Root Cause

`BulkLoader._load` (`app/utils/bulk_loader.py:35`) used Peewee's `insert_many(...).execute()`, which generates a plain `INSERT INTO ... VALUES (...)` statement with no conflict clause. PostgreSQL enforces a `UNIQUE` constraint on `users.username`. When an already-present username was included in the upload, the database raised `UniqueViolation`; Peewee re-raised it as `IntegrityError`; the seed endpoint's unhandled-exception handler caught it and returned 500.

The immediate trigger was an operator re-uploading the same CSV file. The underlying defect was that the bulk loader provided no idempotency guarantee — a second upload of identical data was always going to fail.

```
POST /seed/users
  └─ seed_users()               app/api/seed.py:46
       └─ BulkLoader.load_users  app/utils/bulk_loader.py:51
            └─ _load              app/utils/bulk_loader.py:35
                 └─ insert_many(...).execute()
                      └─ psycopg2.errors.UniqueViolation  ← root cause
                           └─ peewee.IntegrityError
                                └─ HTTP 500
```

---

## Impact

| Dimension | Detail |
|---|---|
| Affected endpoint | `POST /seed/users` |
| Unaffected endpoints | All read/write API routes (`/users`, `/urls`, `/events`, `/health/*`) |
| User-facing impact | No production user impact; seed endpoint is an operator tool |
| Data impact | No data loss or corruption; the failed `insert_many` rolled back atomically |
| Duration | 26 minutes (06:05 – 06:31 UTC) |
| Alert-to-acknowledge | ~3 minutes (`HighErrorRate` fired at 06:08, acknowledged at 06:08) |
| Acknowledge-to-resolve | ~23 minutes |

---

## Detection

The incident was caught by the `HighErrorRate` Prometheus alert:

```yaml
expr: sum(rate(http_errors_total[2m])) / sum(rate(http_requests_total[2m])) > 0.05
for: 2m
```

Because the only traffic at that time was the failing seed call, the error ratio hit 100 %, well above the 5 % threshold. The alert entered a pending state ~1 minute after the first failure and fired after the 2-minute `for` period — a total detection lag of ~3 minutes, within the five-minute response objective.

Structured logs in Loki provided the full traceback within 2 minutes of the engineer acknowledging, eliminating any ambiguity about the root cause.

---

## Resolution

**Immediate fix** (`app/utils/bulk_loader.py:35`):

```python
# Before
model.insert_many(records).execute()

# After
model.insert_many(records).on_conflict_ignore().execute()
```

`ON CONFLICT DO NOTHING` instructs PostgreSQL to silently skip any row that would violate a unique constraint. The bulk loader is now idempotent: uploading the same CSV multiple times produces the same database state with no error.

---

## Contributing Factors

1. **No idempotency contract on seed endpoints.** The endpoint docs and code made no mention of whether re-uploading was safe. The operator had no reason to expect a failure.
2. **No pre-upload duplicate check.** The loader performed no existence check before inserting, relying entirely on the DB constraint to detect conflicts — but with no plan for handling the resulting error.
3. **Chunked transaction semantics.** The per-chunk `with db.atomic()` block meant the *entire first chunk* was rolled back on conflict, not just the offending row. Any rows in the same chunk that were not duplicates were also discarded.

---

## Action Items

| # | Action | Owner | Priority |
|---|---|---|---|
| 1 | ~~Add `.on_conflict_ignore()` to all `insert_many` calls in `BulkLoader`~~ | engineering | **Done** |
| 2 | Update `docs/error-handling.md` to note that `BulkLoader` is now idempotent and safe to re-run | engineering | low |
| 3 | Add an integration test: seed the same CSV twice, assert 200 on both calls and correct final row count | engineering | medium |
| 4 | Add a `409 Conflict` guard to the seed API documentation so callers understand the old behaviour was a defect, not a feature | engineering | low |

---

## Lessons Learned

- **Seed/import endpoints must be idempotent by design.** Operators will re-run them — during resets, retries, and debugging. Assuming a clean slate is an unsafe default.
- **Structured logs + Loki made diagnosis fast.** The full traceback was available in Grafana within seconds of searching `{level="ERROR"}`, reducing time-to-root-cause from what could have been tens of minutes to under 3.
- **Alert fired on time.** The `HighErrorRate` alert (2-minute `for`) notified within 3 minutes of the first failure, satisfying the five-minute response objective.
