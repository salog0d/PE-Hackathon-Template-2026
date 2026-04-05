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
 *   0 → 25 VUs over  30 s  (warm up)
 *   25 VUs for        2 min (steady state)
 *   25 → 0 VUs over  30 s  (cool down)
 *
 * Total duration: ~3 min
 *
 * Run:
 *   k6 run load-tests/load.js
 *
 * Override base URL:
 *   k6 run -e BASE_URL=http://staging:5000 load-tests/load.js
 */

import { sleep } from "k6";
import {
  SLO_THRESHOLDS,
  SEED_SHORT_CODES,
  SEED_USER_IDS,
  SEED_URL_IDS,
  randomItem,
  resolveShortCode,
  getUrl,
  getUser,
  createUrl,
  createUser,
  createEvent,
} from "./helpers.js";

export const options = {
  stages: [
    { duration: "30s", target: 25 },   // ramp up
    { duration: "2m",  target: 25 },   // steady state
    { duration: "30s", target: 0  },   // ramp down
  ],
  thresholds: {
    ...SLO_THRESHOLDS,
    // Additional named-scenario thresholds
    "http_req_duration{scenario:default}": ["p(95)<500", "p(99)<1000"],
  },
};

// Shared state: track created IDs so later iterations can read their own writes
const createdUserIds = [];
const createdUrlIds  = [];

export default function () {
  const roll = Math.random();

  if (roll < 0.70) {
    // --- 70 %: resolve a short code (hot read path) ---
    const pool = createdUrlIds.length > 0
      ? [...SEED_SHORT_CODES, ...createdUrlIds.map((id) => `lt-${id}`)]
      : SEED_SHORT_CODES;
    resolveShortCode(randomItem(SEED_SHORT_CODES));
    sleep(randomSleep(0.05, 0.2));

  } else if (roll < 0.85) {
    // --- 15 %: create a new short URL ---
    const userId = createdUserIds.length > 0
      ? randomItem(createdUserIds)
      : randomItem(SEED_USER_IDS);
    const res = createUrl(userId);
    if (res.status === 201) {
      createdUrlIds.push(res.json("id"));
    }
    sleep(randomSleep(0.1, 0.4));

  } else if (roll < 0.95) {
    // --- 10 %: look up a user ---
    const userId = createdUserIds.length > 0
      ? randomItem([...SEED_USER_IDS, ...createdUserIds])
      : randomItem(SEED_USER_IDS);
    getUser(userId);
    sleep(randomSleep(0.05, 0.15));

  } else {
    // --- 5 %: record a click event ---
    const urlId  = createdUrlIds.length > 0
      ? randomItem([...SEED_URL_IDS, ...createdUrlIds])
      : randomItem(SEED_URL_IDS);
    const userId = createdUserIds.length > 0
      ? randomItem([...SEED_USER_IDS, ...createdUserIds])
      : randomItem(SEED_USER_IDS);
    createEvent(urlId, userId);
    sleep(randomSleep(0.1, 0.3));
  }
}

function randomSleep(min, max) {
  return min + Math.random() * (max - min);
}
