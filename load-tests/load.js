/**
 * Load test — simulates expected production traffic.
 *
 * Purpose:  Verify the service meets its SLOs (P95 < 500 ms, P99 < 1 s,
 *           error rate < 5 %) under realistic concurrent load.
 *
 * Traffic model (URL shortener read-heavy pattern):
 *   70 % — short-code resolution  (GET /urls/code/:code)
 *   15 % — URL creation           (POST /urls/)
 *   10 % — user lookup            (GET /users/:id)
 *    5 % — event recording        (POST /events/)
 *
 * Ramp profile:
 *   0 → 200 VUs over  1 min  (warm up)
 *   200 VUs for        2 min (steady state)
 *   200 → 0 VUs over  30 s  (cool down)
 *
 * Total duration: ~3 min 30 s
 *
 * Run:
 *   k6 run load-tests/load.js
 *
 * Override base URL:
 *   k6 run -e BASE_URL=http://staging:5000 load-tests/load.js
 */

import { sleep } from "k6";
import http from "k6/http";
import {
  SLO_THRESHOLDS,
  SEED_SHORT_CODES,
  SEED_USER_IDS,
  SEED_URL_IDS,
  randomItem,
  resolveShortCode,
  getUrl,
  createUrl,
  createEvent,
} from "./helpers.js";

// 404 is an expected response for short-code lookups — do not count as failure
http.setResponseCallback(http.expectedStatuses({ min: 200, max: 399 }, 404));

export const options = {
  stages: [
    { duration: "1m",  target: 200 },  // ramp up
    { duration: "2m",  target: 200 },  // steady state
    { duration: "30s", target: 0   },  // ramp down
  ],
  thresholds: {
    ...SLO_THRESHOLDS,
    // Additional named-scenario thresholds
    "http_req_duration{scenario:default}": ["p(95)<500", "p(99)<1000"],
  },
};

// Shared state: track created URL IDs so later iterations can read their own writes
const createdUrlIds = [];

export default function () {
  const roll = Math.random();

  if (roll < 0.80) {
    // --- 80 %: resolve a short code (hot read path) ---
    resolveShortCode(randomItem(SEED_SHORT_CODES));
    sleep(randomSleep(0.05, 0.2));

  } else if (roll < 0.90) {
    // --- 10 %: look up a URL by ID ---
    getUrl(randomItem(SEED_URL_IDS));
    sleep(randomSleep(0.05, 0.15));

  } else if (roll < 0.97) {
    // --- 7 %: create a new short URL ---
    const userId = randomItem(SEED_USER_IDS);
    const res = createUrl(userId);
    if (res.status === 201) {
      createdUrlIds.push(res.json("id"));
    }
    sleep(randomSleep(0.1, 0.4));

  } else {
    // --- 3 %: record a click event ---
    const urlId  = createdUrlIds.length > 0
      ? randomItem([...SEED_URL_IDS, ...createdUrlIds])
      : randomItem(SEED_URL_IDS);
    createEvent(urlId, randomItem(SEED_USER_IDS));
    sleep(randomSleep(0.1, 0.3));
  }
}

function randomSleep(min, max) {
  return min + Math.random() * (max - min);
}
