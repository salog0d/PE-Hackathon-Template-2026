# Observability: Metrics & Structured Logging

## Structured Logging

Logs are emitted as JSON to stdout via a custom `JsonFormatter` (`app/logging_config.py`).

### Log format

Every log line is a JSON object with these fields:

| Field | Description |
|---|---|
| `timestamp` | ISO-8601 UTC timestamp |
| `level` | Log level (`INFO`, `WARNING`, `ERROR`, etc.) |
| `service` | Value of `SERVICE_NAME` env var (default: `url-service`) |
| `logger` | Logger name (Python module path) |
| `message` | Log message |
| `request_id` | UUID injected per request via `ContextVar`; `null` outside a request |
| `exc_info` | Exception traceback (only present on errors) |
| `...` | Any extra fields passed via `extra={}` in log calls |

### Configuration

| Env var | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Root log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `SERVICE_NAME` | `url-service` | Value stamped on every log line |

### Request lifecycle logs

The middleware in `app/app.py` emits two structured log events per request:

- `request_started` — logged before the handler runs, includes `method` and `path`
- `request_finished` — logged after the response is sent, includes `method`, `path`, `status`, and `latency_ms`

The `/metrics` endpoint is excluded from request logging to avoid noise.

---

## Prometheus Metrics

Metrics are exposed at `GET /metrics` in the Prometheus text exposition format.

### Available metrics

| Metric | Type | Labels | Description |
|---|---|---|---|
| `http_requests_total` | Counter | `method`, `endpoint`, `status` | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | `endpoint` | Request latency in seconds |
| `http_requests_in_progress` | Gauge | — | Requests currently being processed |
| `http_errors_total` | Counter | `method`, `endpoint` | Total 5xx server errors |
| `db_up` | Gauge | — | DB health: `1` = up, `0` = down |
| `urls_created_total` | Counter | — | Total short URLs successfully created |

### Latency buckets

`http_request_duration_seconds` uses API-tuned buckets (seconds):

```
0.05, 0.1, 0.25, 0.3, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0
```

### Endpoint label cardinality

The `endpoint` label uses the Flask route template (e.g. `/users/<id>`) rather than the raw path to keep cardinality bounded. Unmatched routes (404s) use `"unknown"`.

### Scraping

Point your Prometheus scrape config at:

```
http://<host>:<port>/metrics
```

---

## Alerting

Alerts are defined in `observability/prometheus/alert_rules.yml` and routed through Alertmanager (`observability/alertmanager/alertmanager.yml`) to Discord.

### Five-minute response objective

Every alert is tuned so that the total pipeline — from the moment a threshold is first breached to the moment a notification is dispatched — is **≤ 5 minutes**:

| Stage | Duration |
|---|---|
| Prometheus `for` pending period (max) | 2 min |
| Alertmanager `group_wait` | 30 s |
| Routing + delivery overhead | ~30 s |
| **Total (worst-case)** | **≈ 3 min** |

### Alert inventory

| Alert | Severity | Condition | Pending (`for`) |
|---|---|---|---|
| `ServiceDown` | critical | `up{job="url-service"} == 0` | 1 m |
| `DatabaseDown` | critical | `db_up == 0` | 1 m |
| `HighErrorRate` | critical | 5xx rate > 5 % of traffic | 2 m |
| `HighLatencyP99` | critical | P99 latency > 1 s | 1 m |
| `HighLatencyP95` | warning | P95 latency > 500 ms | 2 m |
| `HighRequestsInFlight` | warning | in-flight requests > 50 | 2 m |

Critical alerts repeat every 30 minutes; warnings repeat every 2 hours (see `alertmanager.yml` `repeat_interval`).
