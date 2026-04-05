# Alert Runbook

Actionable response procedures for every alert defined in `observability/prometheus/alert_rules.yml`.

Alerts are delivered to Discord. The total pipeline from threshold breach to notification is ≤ 5 minutes (see `docs/observability.md` for the timing breakdown).

---

## Table of contents

| Alert | Severity | Section |
|---|---|---|
| `ServiceDown` | critical | [→](#servicedown) |
| `DatabaseDown` | critical | [→](#databasedown) |
| `HighErrorRate` | critical | [→](#higherrorrate) |
| `HighLatencyP99` | critical | [→](#highlatencyp99) |
| `HighLatencyP95` | warning | [→](#highlatencyp95) |
| `HighRequestsInFlight` | warning | [→](#highrequestsinflight) |

---

## ServiceDown

**Condition:** `up{job="url-service"} == 0` for 1 minute  
**Severity:** critical  
**Meaning:** Prometheus cannot scrape the `/metrics` endpoint. The service is either crashed, failing its health check, or unreachable on the network.

### Response steps

1. **Check container status.**
   ```bash
   docker compose ps url-service
   docker compose logs --tail=50 url-service
   ```
2. **Look for a crash or OOM.** If the container exited, the exit code and last log lines will indicate the cause (Python exception, OOM kill, etc.).
3. **Restart the service** if the cause is transient (e.g., startup race with the database).
   ```bash
   docker compose restart url-service
   ```
4. **Verify recovery.** Confirm `up{job="url-service"}` returns `1` in Prometheus and the alert resolves in Alertmanager within 2 minutes.
5. **If the container keeps crashing**, check `app/app.py` for import-time errors, verify all required environment variables are set (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`), and confirm the database is reachable.

---

## DatabaseDown

**Condition:** `db_up == 0` for 1 minute  
**Severity:** critical  
**Meaning:** The application's database health probe (`db_up` gauge) is reporting 0. The service is running but cannot reach PostgreSQL.

### Response steps

1. **Check the database container.**
   ```bash
   docker compose ps db
   docker compose logs --tail=50 db
   ```
2. **Verify connectivity from the app container.**
   ```bash
   docker compose exec url-service python -c \
     "import psycopg2, os; psycopg2.connect(host=os.environ['DB_HOST'], \
      port=os.environ['DB_PORT'], dbname=os.environ['DB_NAME'], \
      user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD']); print('ok')"
   ```
3. **Restart the database** if it is stopped or unhealthy.
   ```bash
   docker compose restart db
   ```
4. **Check disk space.** PostgreSQL will refuse connections if the volume is full.
   ```bash
   df -h
   ```
5. **Verify recovery.** Wait for `db_up` to return to `1` and confirm the alert resolves.

---

## HighErrorRate

**Condition:** `sum(rate(http_errors_total[2m])) / sum(rate(http_requests_total[2m])) > 0.05` for 2 minutes  
**Severity:** critical  
**Meaning:** More than 5 % of requests are returning HTTP 5xx responses.

### Response steps

1. **Identify the failing endpoints.** In Grafana open the *URL Service* dashboard → *Errors* row → *Error Rate (5xx/s)* panel, broken down by `method` and `endpoint`.
2. **Check application logs** for stack traces.
   ```bash
   docker compose logs --tail=100 url-service | grep '"level": "ERROR"'
   ```
   Or query Loki in Grafana: `{service="url-service", level="ERROR"}`.
3. **Check database connectivity.** A `DatabaseDown` alert firing simultaneously narrows the root cause to a DB issue — follow the [DatabaseDown](#databasedown) procedure first.
4. **Look for a recent deployment.** If a new image was deployed shortly before the alert fired, roll back.
   ```bash
   docker compose pull url-service   # pull known-good image tag
   docker compose up -d url-service
   ```
5. **Verify recovery.** The error ratio should drop below 5 % within 2 minutes. Confirm the alert resolves.

---

## HighLatencyP99

**Condition:** P99 `http_request_duration_seconds` > 1 s for 1 minute  
**Severity:** critical  
**Meaning:** The slowest 1 % of requests are taking longer than 1 second — severe tail latency affecting real users.

### Response steps

1. **Identify the slow endpoints.** In Grafana open the *URL Service* dashboard → *Latency* row → *Request Latency Percentiles* panel. Filter by endpoint label to find which route is slow.
2. **Correlate with in-flight requests.** If `HighRequestsInFlight` is also firing, the service may be saturated — see [HighRequestsInFlight](#highrequestsinflight).
3. **Check database query time.** Slow DB queries are the most common cause. Inspect `request_finished` log lines for high `latency_ms` values and cross-reference with the endpoint.
   ```bash
   docker compose logs url-service | grep request_finished | python3 -c \
     "import sys,json; [print(json.loads(l)) for l in sys.stdin if json.loads(l).get('latency_ms',0)>500]"
   ```
4. **Check for a missing index or table bloat** by connecting to the database:
   ```bash
   docker compose exec db psql -U $DB_USER -d $DB_NAME \
     -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
   ```
5. **Restart the service** to clear any connection pool saturation if queries look healthy.
6. **Verify recovery.** P99 should return below 1 s and the alert should resolve within 2 minutes.

---

## HighLatencyP95

**Condition:** P95 `http_request_duration_seconds` > 500 ms for 2 minutes  
**Severity:** warning  
**Meaning:** 5 % of requests are slower than 500 ms — a leading indicator of a deeper latency problem before it reaches P99.

### Response steps

1. **Monitor trend.** Open the *Request Latency Percentiles* panel in Grafana and check whether P95 is climbing toward P99 > 1 s territory. If it is escalating, treat it as [HighLatencyP99](#highlatencyp99) preemptively.
2. **Identify the affected endpoint** using the same Grafana panel.
3. **Check in-flight request count.** A rising `http_requests_in_progress` value alongside P95 latency suggests saturation.
4. **Inspect recent logs** for slow `request_finished` events (see step 3 of [HighLatencyP99](#highlatencyp99)).
5. **If stable and not worsening**, schedule a non-urgent investigation (slow query, missing cache, endpoint optimization). No immediate restart required.

---

## HighRequestsInFlight

**Condition:** `http_requests_in_progress > 50` for 2 minutes  
**Severity:** warning  
**Meaning:** More than 50 requests are being processed simultaneously. This can saturate the connection pool and cause latency to spike.

### Response steps

1. **Check whether latency is already degraded.** If `HighLatencyP95` or `HighLatencyP99` is also firing, prioritize those procedures.
2. **Identify the traffic source.** Look at the *Request Rate (req/s)* panel in Grafana for a sudden spike in a specific endpoint or method.
3. **Check for a runaway client or load test.** Inspect access logs for a single IP or user agent making an unusually high number of requests.
   ```bash
   docker compose logs url-service | grep request_started | \
     python3 -c "import sys,json,collections; c=collections.Counter(); \
     [c.update([json.loads(l).get('path')]) for l in sys.stdin]; \
     print(c.most_common(10))"
   ```
4. **Check database connection pool.** If the DB is slow, requests pile up waiting for a connection. Follow steps 3–4 from [HighLatencyP99](#highlatencyp99).
5. **If caused by legitimate traffic growth**, the service needs horizontal scaling or rate limiting — escalate to the engineering team.
6. **Verify recovery.** `http_requests_in_progress` should drop below 50 and the alert should resolve within 2 minutes.


For troubleshooting non-alert operational failures (startup crashes, migration errors, seed upload issues, missing Grafana/Prometheus data) see [`docs/troubleshooting.md`](troubleshooting.md).
