from prometheus_client import Counter, Gauge, Histogram

# API-tuned latency buckets: <50ms, <100ms, <250ms, <300ms, <500ms, <750ms, <1s
LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.3, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0)

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint"],
    buckets=LATENCY_BUCKETS,
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
)

http_errors_total = Counter(
    "http_errors_total",
    "Total HTTP server errors (5xx)",
    ["method", "endpoint"],
)

db_up = Gauge(
    "db_up",
    "Database health status (1 = up, 0 = down)",
)

urls_created_total = Counter(
    "urls_created_total",
    "Total short URLs successfully created",
)
