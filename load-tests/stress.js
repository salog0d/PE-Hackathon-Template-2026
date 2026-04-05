/**
 * Stress test — find the service's breaking point.
 *
 * Purpose:  Push VUs well beyond the current single-instance capacity limit
 *           (~20–30 concurrent, see docs/capacity.md) to observe where P99
 *           latency exceeds 1 s, the error rate crosses 5 %, and the
 *           HighRequestsInFlight alert threshold (50 in-flight) is breached.
 *
 * What to watch while this runs:
 *   - Grafana → URL Service dashboard → Latency row: P95 and P99 curves
 *   - Grafana → Saturation row: in-flight request count
 *   - Grafana → Errors row: 5xx error rate
 *   - Alertmanager (http://localhost:9093): which alerts fire and when
 *
 * Ramp profile:
 *    0 →  20 VUs over 30 s  (baseline — should be healthy)
 *   20 →  50 VUs over 30 s  (approaches in-flight alert threshold)
 *   50 → 100 VUs over 1 min (expected saturation zone)
 *  100 → 150 VUs over 1 min (well past single-instance limit)
 *  150 →   0 VUs over 30 s  (recovery — watch if the service self-heals)
 *
 * Total duration: ~4 min
 *
 * Run:
 *   k6 run load-tests/stress.js
 *
 * NOTE: Thresholds intentionally use higher bounds here — the goal is to
 * observe degradation, not to pass at all costs. The test will report which
 * thresholds were breached.
 */

import { sleep } from "k6";
import {
  SEED_SHORT_CODES,
  SEED_USER_IDS,
  SEED_URL_IDS,
  randomItem,
  resolveShortCode,
  getUrl,
  createUrl,
  createEvent,
} from "./helpers.js";

export const options = {
  stages: [
    { duration: "30s", target: 20  },  // baseline
    { duration: "30s", target: 50  },  // approach alert threshold
    { duration: "1m",  target: 100 },  // saturation zone
    { duration: "1m",  target: 150 },  // well past capacity
    { duration: "30s", target: 0   },  // recovery
  ],
  thresholds: {
    // Relaxed — we expect these to be breached; the test is observational
    http_req_duration: ["p(99)<5000"],
    http_req_failed:   ["rate<0.30"],
  },
};

export default function () {
  const roll = Math.random();

  // Stress with the same realistic traffic mix as load.js
  if (roll < 0.70) {
    resolveShortCode(randomItem(SEED_SHORT_CODES));
    sleep(0.05);
  } else if (roll < 0.85) {
    createUrl(randomItem(SEED_USER_IDS));
    sleep(0.1);
  } else if (roll < 0.95) {
    getUrl(randomItem(SEED_URL_IDS));
    sleep(0.05);
  } else {
    createEvent(randomItem(SEED_URL_IDS), randomItem(SEED_USER_IDS));
    sleep(0.1);
  }
}
