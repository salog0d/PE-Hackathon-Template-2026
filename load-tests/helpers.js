/**
 * Shared helpers, constants, and threshold definitions for all k6 test scenarios.
 *
 * Thresholds are derived from the Prometheus alert rules in
 * observability/prometheus/alert_rules.yml:
 *   - HighLatencyP99  → P99 > 1 s   (critical)
 *   - HighLatencyP95  → P95 > 500 ms (warning)
 *   - HighErrorRate   → 5xx rate > 5 %
 */

import { check } from "k6";
import http from "k6/http";

// ---------------------------------------------------------------------------
// Base config
// ---------------------------------------------------------------------------

export const BASE_URL = __ENV.BASE_URL || "http://localhost:5000";

export const HEADERS = { "Content-Type": "application/json" };

// ---------------------------------------------------------------------------
// Thresholds — reused across all scenarios
// ---------------------------------------------------------------------------

/**
 * Standard SLO thresholds matching the Prometheus alert rules.
 * Import and spread these into your scenario's `options.thresholds`.
 */
export const SLO_THRESHOLDS = {
  // P99 must stay under 1 s (maps to HighLatencyP99 critical alert)
  http_req_duration: ["p(99)<1000", "p(95)<500"],
  // Error rate must stay under 5 % (maps to HighErrorRate critical alert)
  http_req_failed: ["rate<0.05"],
};

// ---------------------------------------------------------------------------
// Seed data — short codes and IDs present after running `python seed.py`
// ---------------------------------------------------------------------------

// A sample of short codes from seeds/urls.csv
export const SEED_SHORT_CODES = [
  "hcvbQ7", "ipA5VW", "jfN4UP", "VJ3ywj", "mK9pLx",
  "rT2qNs", "bX8wZd", "cY5vUe", "dZ3tSf", "eA6uRg",
];

// IDs assumed present after seeding (users 1–10, URLs 1–10)
export const SEED_USER_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
export const SEED_URL_IDS  = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

// ---------------------------------------------------------------------------
// Random helpers
// ---------------------------------------------------------------------------

export function randomItem(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

export function randomString(length = 6) {
  const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  let s = "";
  for (let i = 0; i < length; i++) {
    s += chars[Math.floor(Math.random() * chars.length)];
  }
  return s;
}

// ---------------------------------------------------------------------------
// Reusable request functions
// ---------------------------------------------------------------------------

/** GET /health — liveness probe */
export function checkHealth() {
  const res = http.get(`${BASE_URL}/health`);
  check(res, {
    "health: status 200":       (r) => r.status === 200,
    "health: body has status":  (r) => r.json("status") === "ok",
  });
  return res;
}

/** GET /health/db — readiness probe */
export function checkHealthDb() {
  const res = http.get(`${BASE_URL}/health/db`);
  check(res, {
    "health/db: status 200":    (r) => r.status === 200,
    "health/db: db reachable":  (r) => r.json("database") === "reachable",
  });
  return res;
}

/** GET /urls/code/:code — hottest read path in a URL shortener */
export function resolveShortCode(code) {
  const res = http.get(`${BASE_URL}/urls/code/${code}`);
  check(res, {
    "resolve short code: status 200 or 404": (r) =>
      r.status === 200 || r.status === 404,
  });
  return res;
}

/** GET /urls/:id */
export function getUrl(id) {
  const res = http.get(`${BASE_URL}/urls/${id}`);
  check(res, {
    "get url: status 200 or 404": (r) => r.status === 200 || r.status === 404,
  });
  return res;
}

/** GET /users/:id */
export function getUser(id) {
  const res = http.get(`${BASE_URL}/users/${id}`);
  check(res, {
    "get user: status 200 or 404": (r) => r.status === 200 || r.status === 404,
  });
  return res;
}

/** POST /urls/ — creates a short URL; returns the created object or null */
export function createUrl(userId) {
  const payload = JSON.stringify({
    user_id:      userId,
    short_code:   randomString(7),
    original_url: `https://example.com/${randomString(12)}`,
    title:        `Load test URL ${randomString(4)}`,
    is_active:    true,
  });
  const res = http.post(`${BASE_URL}/urls/`, payload, { headers: HEADERS });
  check(res, {
    "create url: status 201": (r) => r.status === 201,
    "create url: has id":     (r) => r.json("id") !== undefined,
  });
  return res;
}

/** POST /users/ — creates a user; returns the created object or null */
export function createUser() {
  const name = randomString(10);
  const payload = JSON.stringify({
    username: name,
    email:    `${name}@loadtest.io`,
  });
  const res = http.post(`${BASE_URL}/users/`, payload, { headers: HEADERS });
  check(res, {
    "create user: status 201": (r) => r.status === 201,
    "create user: has id":     (r) => r.json("id") !== undefined,
  });
  return res;
}

/** POST /events/ — records a click event */
export function createEvent(urlId, userId) {
  const payload = JSON.stringify({
    url_id:     urlId,
    user_id:    userId,
    event_type: "click",
    details:    JSON.stringify({ source: "load-test" }),
  });
  const res = http.post(`${BASE_URL}/events/`, payload, { headers: HEADERS });
  check(res, {
    "create event: status 201": (r) => r.status === 201,
  });
  return res;
}
