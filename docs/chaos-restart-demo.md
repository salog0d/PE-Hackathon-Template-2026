# Chaos Restart Demo

## Overview

This document describes how the application behaves under failure conditions — invalid inputs, missing resources, database connection edge cases, and malformed bulk imports. All scenarios described here are grounded in the actual implementation and are reproducible via the test suite.

---

## Simulated Failures and System Responses

### 1. Invalid or Missing Input (Service Layer)

**Scenario:** A `POST /users/` request is sent with a blank username.

**What happens:**
1. The API handler extracts the JSON body and calls `user_service.create()`.
2. `user_service.create()` checks `if not username or not username.strip()` — the condition is true.
3. A `ValueError("username is required")` is raised **before any database call is made**.
4. The API handler catches the `ValueError` and returns `400 {"error": "username is required"}`.
5. The application continues processing subsequent requests normally.

**Result:** The system does not crash. The error is isolated to the request scope.

---

### 2. Operation on Non-Existent Resource

**Scenario:** A `PATCH /users/9999` request is sent for a user ID that does not exist.

**What happens:**
1. `user_service.update(9999, data)` calls `user_repository.update(9999, data)`.
2. The PeeWee ORM `UPDATE` query matches zero rows and returns a row count of `0`.
3. The service propagates this falsy value back to the API handler.
4. The API handler checks `if not updated:` and returns `404 {"error": "Not found"}`.
5. No exception is raised; the database connection is cleanly released.

**Result:** The update silently matched nothing, but the caller receives an accurate `404` rather than a misleading `200`.

---

### 3. Mocked Repository Failures in Tests

The test suite injects fault conditions by mocking the repository layer with `unittest.mock.patch`. This allows verifying API-level error handling without a live database.

**Example — mocked 404 on update (`tests/test_api_routes.py:44-50`):**

```python
with patch("app.api.users.user_service.update", return_value=0):
    response = client.patch("/users/1", json={"username": "x"})
    assert response.status_code == 404
```

The mock simulates a repository that found no matching row. The test asserts the API returns `404`, confirming the not-found check in the handler is exercised.

**Example — mocked `ValueError` on create (`tests/test_api_routes.py:34-41`):**

```python
with patch("app.api.users.user_service.create", side_effect=ValueError("username is required")):
    response = client.post("/users/", json={"username": ""})
    assert response.status_code == 400
    assert "error" in response.get_json()
```

The service layer is bypassed entirely; the mock raises the exception directly, validating that the API handler's `except ValueError` branch is reachable and correct.

---

### 4. Database Connection Lifecycle Under Failure

**Scenario:** A request raises an unhandled exception mid-flight (e.g., an unexpected database error).

**What happens:**
- Flask's `teardown_appcontext` is registered during application startup (`app/database/__init__.py:27-30`).
- This hook fires on **every** request completion, including those terminated by an unhandled exception.
- The hook checks `if not db.is_closed():` before calling `db.close()`.

**Result:** The database connection is always released, even on a crash. The connection pool is not exhausted by failed requests. The double-close guard prevents the teardown hook itself from raising a secondary error.

**Test coverage (`tests/test_bootstrap.py:78-90`):**

```python
def test_init_db_does_not_close_if_already_closed(app, mock_db):
    mock_db.is_closed.return_value = True
    with app.app_context():
        pass
    mock_db.close.assert_not_called()
```

This test confirms that when the database proxy reports `is_closed() == True`, `close()` is never invoked — the defensive guard is verified to actually prevent the double-close.

---

### 5. Malformed CSV Upload

**Scenario:** A CSV file is uploaded to `POST /seed/events` where the `details` column contains missing values.

**What happens:**
1. Pandas reads the CSV; missing `details` cells become `NaN` (float).
2. `BulkLoader.load_events()` (`app/utils/bulk_loader.py:87`) applies `.where(pd.isna(...), None)`, substituting `NaN` with Python `None`.
3. The cleaned data is inserted via `with db.atomic()` in chunks of 1,000 rows.
4. If a chunk fails (e.g., a foreign key violation on `url_id`), only that chunk is rolled back. Prior committed chunks are retained.

**Result:** The import is partially successful rather than entirely lost. The API returns a summary of inserted rows.

---

### 6. No File Provided to Seed Endpoint

**Scenario:** A `POST /seed/users` request arrives without a multipart file.

**What happens:**
1. The seed handler checks `if "file" not in request.files:`.
2. Returns `400 {"error": "No file provided"}` immediately.
3. No database interaction occurs.

---

## Startup Validation

On every CI run, before the pytest suite executes, the following smoke check runs:

```bash
python -c "from app.app import create_app; app = create_app(); print(len(list(app.url_map.iter_rules())), 'routes registered')"
```

This validates:
- The app factory completes without error.
- All blueprints are registered and routes are resolvable.
- Environment defaults are accepted (no hard failures on missing env vars at startup).

If any import fails, any blueprint has a configuration error, or `init_db` raises, this step fails and the CI pipeline aborts before running tests — preventing a broken application from being evaluated.

Additionally, the CI test job uses a real PostgreSQL 16 container with a `pg_isready` health check. The job does not start until the database is confirmed ready, eliminating a class of flaky failures caused by race conditions during container startup.

---

## Evidence of Resilience

| Mechanism | Where | What It Prevents |
|---|---|---|
| `ValueError` catch in all API handlers | `app/api/*.py` | Validation failures crashing the process |
| `if not updated:` → 404 | `app/api/users.py:114`, `urls.py:157`, `events.py:135` | Silent no-ops masking missing resources |
| `reuse_if_open=True` on `connect()` | `app/database/__init__.py:24` | Duplicate connection errors on reused contexts |
| `if not db.is_closed()` guard | `app/database/__init__.py:29` | Double-close error in teardown |
| `with db.atomic()` per chunk | `app/utils/bulk_loader.py:34` | Full import rollback on large file partial failure |
| NaN → None substitution | `app/utils/bulk_loader.py:87` | Float type errors on nullable DB columns |
| Field whitelist on update | `app/services/*.py` | Accidental mutation of system fields |
| CI coverage gate (≥50%) | `.github/workflows/ci.yaml:111` | Untested failure paths reaching production |
| CI lint gate blocks test job | `.github/workflows/ci.yaml:56` | Broken code running tests and masking lint errors |
| App smoke check before pytest | `.github/workflows/ci.yaml:101` | Blueprint misconfiguration silently passing CI |
