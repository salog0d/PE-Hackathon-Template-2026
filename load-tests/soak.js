/**
 * Soak test — sustained moderate load over an extended period.
 *
 * Purpose:  Detect slow memory leaks, DB connection exhaustion, log file
 *           growth, or performance degradation that only appears after minutes
 *           or hours of continuous traffic. Not visible in a 3-minute load test.
 *
 * What to watch while this runs:
 *   - `docker stats` — container memory usage should stay flat
 *   - Grafana → Latency: P95/P99 should remain stable, not drift upward
 *   - Grafana → Errors: error rate should stay at 0 %
 *   - Grafana → Saturation: in-flight count should stay well under 50
 *   - `docker compose logs app | grep '"level": "ERROR"'` — no new errors
 *
 * Ramp profile:
 *   0 → 15 VUs over 1 min   (warm up — below the single-instance DB limit)
 *   15 VUs for    20 min     (sustained soak)
 *   15 → 0 VUs over 1 min   (cool down)
 *
 * Total duration: ~22 min
 *
 * Run:
 *   k6 run load-tests/soak.js
 *
 * To run a shorter soak (e.g., 5 min) for CI:
 *   k6 run -e SOAK_DURATION=5m load-tests/soak.js
 */

import { sleep } from "k6";
import {
  SLO_THRESHOLDS,
  SEED_SHORT_CODES,
  SEED_USER_IDS,
  SEED_URL_IDS,
  randomItem,
  checkHealth,
  resolveShortCode,
  getUrl,
  getUser,
  createUrl,
  createEvent,
} from "./helpers.js";

const SOAK_DURATION = __ENV.SOAK_DURATION || "20m";

export const options = {
  stages: [
    { duration: "1m",          target: 15 },   // ramp up
    { duration: SOAK_DURATION, target: 15 },   // soak
    { duration: "1m",          target: 0  },   // ramp down
  ],
  thresholds: {
    ...SLO_THRESHOLDS,
    // During a soak the service must stay fully healthy the entire time
    http_req_failed: ["rate<0.01"],
  },
};

export default function () {
  const roll = Math.random();

  if (roll < 0.05) {
    // Periodic health check — catches if the service silently degrades
    checkHealth();
    sleep(0.5);
    return;
  }

  if (roll < 0.70) {
    resolveShortCode(randomItem(SEED_SHORT_CODES));
  } else if (roll < 0.85) {
    createUrl(randomItem(SEED_USER_IDS));
  } else if (roll < 0.95) {
    getUrl(randomItem(SEED_URL_IDS));
  } else {
    createEvent(randomItem(SEED_URL_IDS), randomItem(SEED_USER_IDS));
  }

  // Slightly longer think time to keep VU count moderate
  sleep(0.3 + Math.random() * 0.4);
}
