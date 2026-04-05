# Load Tests

k6 load test suite for the URL Shortener API. Four scenarios cover the full testing pyramid from a quick smoke check to an extended soak.

## Prerequisites

Install k6:

```bash
# macOS
brew install k6

# Linux (Debian/Ubuntu)
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6

# Windows
winget install k6
# or: choco install k6
```

The API must be running before executing any test:

```bash
docker compose up -d
docker compose exec app python migrate.py run
docker compose exec app python seed.py
```

## Scenarios

| File | VUs | Duration | Purpose |
|---|---|---|---|
| `smoke.js` | 1 | ~30 s | Sanity check — run after every deployment |
| `load.js` | 25 | ~3 min | SLO validation under normal expected traffic |
| `stress.js` | up to 150 | ~4 min | Find the breaking point |
| `soak.js` | 15 | ~22 min | Detect memory leaks and slow degradation |

## Traffic model

All scenarios replicate a realistic URL shortener read-heavy pattern:

| Weight | Endpoint | Reason |
|---|---|---|
| 70 % | `GET /urls/code/:code` | Short-code resolution is the primary hot path |
| 15 % | `POST /urls/` | URL creation is the main write operation |
| 10 % | `GET /users/:id` | User lookups support the UI |
|  5 % | `POST /events/` | Click event recording |

## Running tests

```bash
# Smoke — quick sanity check
k6 run load-tests/smoke.js

# Load — SLO validation (~3 min)
k6 run load-tests/load.js

# Stress — find the breaking point (~4 min)
k6 run load-tests/stress.js

# Soak — memory/leak detection (~22 min)
k6 run load-tests/soak.js

# Soak with shorter duration (useful for CI)
k6 run -e SOAK_DURATION=5m load-tests/soak.js

# Target a non-default URL (e.g., staging)
k6 run -e BASE_URL=http://staging-host:5000 load-tests/load.js
```

## SLO thresholds

Thresholds are defined in `helpers.js` and mirror the Prometheus alert rules in `observability/prometheus/alert_rules.yml`:

| Threshold | Value | Corresponding alert |
|---|---|---|
| P99 latency | < 1 000 ms | `HighLatencyP99` (critical) |
| P95 latency | < 500 ms | `HighLatencyP95` (warning) |
| Error rate | < 5 % | `HighErrorRate` (critical) |

The smoke test additionally requires **zero errors** (`rate==0`).

## Reading results

k6 prints a summary after each run. Key metrics to check:

```
http_req_duration ......: avg=XX  p(95)=XX  p(99)=XX
http_req_failed ........: X.XX%
✓ / ✗ checks
```

For the stress test, watch Grafana in parallel:
- **Latency row** — when does P99 cross 1 s?
- **Saturation row** — at what VU count does in-flight hit 50?
- **Errors row** — at what VU count does the error rate cross 5 %?
- **Alertmanager** (http://localhost:9093) — which alerts fire and when?

These observations map directly to the capacity phases in `docs/capacity.md`.
