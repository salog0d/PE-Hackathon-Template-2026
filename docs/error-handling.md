# Error Handling Documentation

## Overview

The application is a Flask REST API backed by PostgreSQL, structured in three layers: API → Service → Repository. Error handling is enforced at every layer, ensuring that invalid input, missing resources, and unexpected states are caught and surfaced to callers with appropriate HTTP semantics.

---

## API-Level Validation and HTTP Status Codes

All endpoints follow a consistent contract:

| Scenario | Status Code | Response Body |
|---|---|---|
| Resource not found | `404` | `{"error": "Not found"}` |
| Validation failure | `400` | `{"error": "<validation message>"}` |
| Successful creation | `201` | Serialized resource object |
| Successful deletion | `204` | *(empty body)* |
| Successful list/read | `200` | Resource object or array |
| Health check | `200` | `{"status": "ok"}` |
| Missing file on upload | `400` | `{"error": "No file provided"}` |

**404 on mutations:** Update and delete endpoints check the repository return value (affected row count). If zero rows were affected, the endpoint returns `404` rather than `200`, preventing silent no-ops on non-existent IDs.

```python
# app/api/users.py:114-119
updated = user_service.update(id, data)
if not updated:
    return jsonify(error="Not found"), 404
```

**400 on validation errors:** The service layer raises `ValueError` for all validation failures. API endpoints catch this and return a `400` with the exception message verbatim, giving callers actionable feedback without leaking internals.

```python
# app/api/users.py:75-79
try:
    user = user_service.create(data)
except ValueError as e:
    return jsonify(error=str(e)), 400
```

---

## Service Layer Validation

Each service (`user_service`, `url_service`, `event_service`) performs input validation before any database interaction. Validation follows a consistent set of rules:

### Required Field Checks

String fields are checked for both `None` and blank/whitespace-only values. ID fields are checked for truthiness (rejecting `0`, `None`, or `False`).

```python
# app/services/user_service.py:15-20
if not username or not username.strip():
    raise ValueError("username is required")
if not email or not email.strip():
    raise ValueError("email is required")
```

### Field Whitelisting on Updates

Update operations explicitly define an allowed set of fields. Any payload key not in that set is silently discarded; if the remaining payload is empty, a `ValueError` is raised rather than executing a no-op query.

```python
# app/services/url_service.py:48-51
allowed = {"short_code", "original_url", "title", "is_active"}
filtered = {k: v for k, v in data.items() if k in allowed}
if not filtered:
    raise ValueError("no valid fields to update")
```

This prevents accidental mutation of system-managed fields (e.g., `created_at`, `id`) via the API.

### Automatic Timestamp Injection

`url_service.update()` injects `updated_at` with the current UTC time before calling the repository, ensuring the field is always accurate regardless of what the caller provides.

---

## Repository Layer

Repositories (`user_repository`, `url_repository`, `event_repository`) are thin wrappers around PeeWee ORM queries. They return objects or `None` on lookups, and row counts on mutations. No business logic lives here — repositories propagate database exceptions upward without swallowing them, allowing higher layers to decide how to respond.

The `get_or_none()` pattern is used throughout to avoid raising `DoesNotExist` exceptions from the ORM, keeping control flow explicit.

---

## Defensive Programming Patterns

### Database Connection Lifecycle Guard

The teardown hook checks whether the connection is already closed before attempting to close it, preventing errors in scenarios where a request-level exception might have already cleaned up the connection.

```python
# app/database/__init__.py:27-30
@app.teardown_appcontext
def close_db(exc):
    if not db.is_closed():
        db.close()
```

Flask's `teardown_appcontext` runs on every request regardless of whether an exception was raised, ensuring connections are always returned.

### Bulk CSV Import Resilience

The `BulkLoader` utility (`app/utils/bulk_loader.py`) applies several defensive transforms before inserting CSV data:

- **Column whitelisting:** Only expected columns are retained; extra columns in the uploaded file are dropped.
- **Boolean coercion:** String values `"True"` / `"False"` are explicitly converted to Python `bool` for the `is_active` field, preventing ORM type errors.
- **NaN → None substitution:** Pandas `NaN` values in nullable fields (e.g., `details` in the events table) are replaced with `None` before insertion, avoiding unexpected `float` values entering the database.
- **Chunked atomic transactions:** Rows are inserted in batches of 1,000 wrapped in `with db.atomic()`. A failure in one chunk does not roll back previously committed chunks, and memory usage is bounded regardless of file size.

---

## Test Coverage of Failure Scenarios

### Service Validation Tests (`tests/test_services.py`)

The following negative-path cases are exercised with `pytest.raises(ValueError)`:

| Test | Scenario Covered |
|---|---|
| `test_user_create_rejects_invalid_required_fields` | Empty username, whitespace-only username, empty email, whitespace-only email |
| `test_user_update_requires_valid_fields` | Payload with no allowed fields |
| `test_user_update_rejects_blank_username` | Blank username on update |
| `test_url_create_rejects_required_fields` | Missing `user_id`, `short_code`, `original_url` |
| `test_url_update_rejects_blank_short_code` | Blank `short_code` on update |
| `test_event_create_rejects_required_fields` | Missing `url_id`, `user_id`, `event_type` |
| `test_event_update_rejects_empty_event_type` | Empty `event_type` on update |
| `test_event_update_requires_any_valid_field` | Payload containing only unsupported fields |

### API Contract Tests (`tests/test_api_routes.py`)

HTTP-level error path coverage:

| Test | HTTP Assertion |
|---|---|
| `test_users_get_404_when_missing` | `GET /users/<id>` → `404`, body contains `"error"` key |
| `test_users_create_returns_400_on_validation_error` | `POST /users/` with bad payload → `400` |
| `test_users_update_returns_404_when_repo_has_no_row` | `PATCH /users/<id>` with no matching row → `404` |
| `test_urls_short_code_returns_404_when_missing` | `GET /urls/code/<code>` → `404` |
| `test_events_update_returns_400_for_invalid_payload` | `PATCH /events/<id>` with invalid payload → `400` |
| `test_seed_users_returns_400_without_file` | `POST /seed/users` with no file → `400` |

### Bootstrap Tests (`tests/test_bootstrap.py`)

- Verifies all five database environment variables are read and passed correctly to the ORM.
- Confirms the `before_request` hook calls `connect(reuse_if_open=True)`.
- Confirms `teardown_appcontext` does **not** call `close()` when the connection is already closed (double-close guard).

---

## CI Enforcement

The GitHub Actions pipeline (`.github/workflows/ci.yaml`) enforces two gates before any merge:

1. **Lint and format (`quality` job):** `ruff check` and `ruff format --check` must both pass. Failures block the `test` job entirely due to `needs: quality`.

2. **Tests with coverage (`test` job):**
   - Runs against a real PostgreSQL 16 container (health-checked with `pg_isready` before the job proceeds).
   - Requires ≥ 50% test coverage; the pipeline fails if coverage drops below this threshold.
   - An application smoke check runs before pytest: the Flask app is imported and its registered routes are counted, catching import-time errors and misconfigured blueprints before test execution begins.

Concurrent runs on the same branch are cancelled (`cancel-in-progress: true`), ensuring only the latest commit's checks are running at any given time.
