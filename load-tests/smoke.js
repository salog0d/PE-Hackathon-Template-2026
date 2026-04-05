/**
 * Smoke test — minimal sanity check before any load test.
 *
 * Purpose:  Verify the API is reachable and all endpoints return expected
 *           status codes with a single virtual user. Run this after every
 *           deployment before promoting to load or stress tests.
 *
 * Duration: ~30 s
 * VUs:      1
 *
 * Run:
 *   k6 run load-tests/smoke.js
 */

import { sleep } from "k6";
import {
  SLO_THRESHOLDS,
  SEED_SHORT_CODES,
  SEED_USER_IDS,
  SEED_URL_IDS,
  randomItem,
  checkHealth,
  checkHealthDb,
  resolveShortCode,
  getUrl,
  getUser,
  createUrl,
  createUser,
  createEvent,
} from "./helpers.js";

export const options = {
  vus:      1,
  duration: "30s",
  thresholds: {
    ...SLO_THRESHOLDS,
    // Smoke must have zero failures
    http_req_failed: ["rate==0"],
  },
};

export default function () {
  // 1. Health probes
  checkHealth();
  sleep(0.2);

  checkHealthDb();
  sleep(0.2);

  // 2. Read seeded short code (hot path)
  resolveShortCode(randomItem(SEED_SHORT_CODES));
  sleep(0.2);

  // 3. Read seeded URL by ID
  getUrl(randomItem(SEED_URL_IDS));
  sleep(0.2);

  // 4. Read seeded user by ID
  getUser(randomItem(SEED_USER_IDS));
  sleep(0.2);

  // 5. Create a new user
  const userRes = createUser();
  const userId  = userRes.status === 201 ? userRes.json("id") : SEED_USER_IDS[0];
  sleep(0.2);

  // 6. Create a new URL owned by that user
  const urlRes = createUrl(userId);
  const urlId  = urlRes.status === 201 ? urlRes.json("id") : SEED_URL_IDS[0];
  sleep(0.2);

  // 7. Record a click event
  createEvent(urlId, userId);
  sleep(0.5);
}
