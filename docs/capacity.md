# Capacity Plan and Scalability Roadmap

This document describes the current system limits, the conditions under which they become binding, and a phased scalability plan that takes the service from a single-instance deployment to 500+ concurrent users using Redis caching.

---

## Current limits (single instance, no cache)

| Dimension | Current limit | Why it breaks |
|---|---|---|
| Concurrent requests | ~20–30 | One DB connection opened per request (no pool). Above ~30 in-flight, connections queue and P99 latency spikes. `HighRequestsInFlight` alerts at 50. |
| Sustained request rate | ~100 req/s | `flask run` is single-process, single-thread. CPU-bound work blocks the whole process. |
| Read-heavy endpoints | Degrades early | Every `GET /urls/<id>`, `GET /urls/code/<code>`, and `GET /events/` hits Postgres even for identical repeated lookups — no cache layer. |
| Database volume | Unbounded | Local Docker volume with no storage cap. Postgres stops accepting writes when the disk fills. |
| Prometheus retention | 7 days | Configured via `--storage.tsdb.retention.time=7d`. Older samples are dropped automatically. |
| Loki log retention | Unbounded | No retention period in `loki-config.yml`. Grows until manually pruned or the stack is torn down with `docker compose down -v`. |
| CSV seed file size | ~100 MB practical | Pandas loads the entire file into memory before chunking. Files > 500 MB risk OOM. |
| Migration rollback | One step at a time | `python migrate.py rollback` reverts one migration per invocation. |

---

## Scalability roadmap

The plan is structured in three phases. Each phase is independently deployable — later phases build on earlier ones but do not require rewriting previous work.

---

### Phase 1 — Multi-worker single host (~30 → ~150 concurrent users)

**Goal:** Eliminate the single-threaded bottleneck and add a connection pool without changing the application architecture.

**Changes:**

1. **Switch from `flask run` to Gunicorn.**
   Replace the Dockerfile `CMD` with:
   ```dockerfile
   CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app.main:app"]
   ```
   Four workers (rule of thumb: `2 × CPU cores + 1`) handle up to ~4× the current concurrent request count. Add `gunicorn` to `pyproject.toml`.

2. **Add a database connection pool via PgBouncer or `psycopg2` pool.**
   Peewee opens one connection per request. Under 4 workers each handling ~8 concurrent requests, the DB sees ~32 simultaneous connections — manageable, but a PgBouncer sidecar in `docker-compose.yml` will cap and reuse connections cheaply:
   ```yaml
   pgbouncer:
     image: edoburu/pgbouncer
     environment:
       DB_HOST: db
       DB_USER: ${DATABASE_USER}
       DB_PASSWORD: ${DATABASE_PASSWORD}
       POOL_MODE: transaction
       MAX_CLIENT_CONN: 200
       DEFAULT_POOL_SIZE: 20
   ```
   Point `DATABASE_HOST` in the `app` service at `pgbouncer` instead of `db`.

**Expected result:** Handles ~100–150 concurrent users before DB becomes the bottleneck.

**Documentation to add:** Update `docs/deployment.md` with the Gunicorn CMD and PgBouncer service block.

---

### Phase 2 — Redis read cache (~150 → ~500+ concurrent users)

**Goal:** Serve the highest-volume read endpoints from cache, dramatically reducing DB load and response latency for repeated lookups.

**Why Redis:** Short-code resolution (`GET /urls/code/<short_code>`) is the hottest read path in a URL shortener — the same short codes are resolved many times by many users. Caching these in Redis eliminates round-trips to Postgres for every redirect.

**Changes:**

1. **Add Redis to `docker-compose.yml`.**
   ```yaml
   redis:
     image: redis:7-alpine
     ports:
       - "6379:6379"
     command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
   ```
   `allkeys-lru` evicts the least-recently-used keys when the 256 MB limit is reached — appropriate for a URL cache where recent codes are hotter than old ones.

2. **Add `redis` env vars.**
   ```bash
   # .env.example additions
   REDIS_HOST=redis
   REDIS_PORT=6379
   REDIS_TTL_SECONDS=300
   ```

3. **Add `redis-py` dependency.**
   ```bash
   uv add redis
   ```

4. **Implement a cache layer in `url_service.py`.**
   Cache short-code lookups on read and invalidate on update/delete:
   ```python
   # app/services/url_service.py
   import os, redis, json

   _redis = redis.Redis(
       host=os.getenv("REDIS_HOST", "localhost"),
       port=int(os.getenv("REDIS_PORT", 6379)),
       decode_responses=True,
   )
   _TTL = int(os.getenv("REDIS_TTL_SECONDS", 300))

   def get_by_short_code(short_code: str):
       key = f"url:code:{short_code}"
       cached = _redis.get(key)
       if cached:
           return json.loads(cached)
       url = url_repository.get_by_short_code(short_code)
       if url:
           _redis.setex(key, _TTL, json.dumps(serialize_url(url)))
       return url

   def update(id, data):
       url = url_repository.update(id, data)
       if url:
           _redis.delete(f"url:code:{url.short_code}")
       return url

   def delete(id):
       url = url_repository.get_by_id(id)
       if url:
           _redis.delete(f"url:code:{url.short_code}")
       return url_repository.delete(id)
   ```

5. **Cache `GET /urls/<id>` responses** using the same pattern with key `url:id:<id>`.

6. **Add Redis health to `/health/db`** (rename to `/health/dependencies` or add a separate `/health/cache` endpoint):
   ```python
   @app.route("/health/cache")
   def health_cache():
       try:
           _redis.ping()
           return jsonify(status="ok", cache="reachable")
       except Exception as e:
           return jsonify(status="degraded", cache="unreachable", error=str(e)), 503
   ```

7. **Add a Redis Prometheus metric.**
   Track cache hit/miss ratio to measure effectiveness:
   ```python
   cache_hits_total = Counter("cache_hits_total", "Cache hits", ["endpoint"])
   cache_misses_total = Counter("cache_misses_total", "Cache misses", ["endpoint"])
   ```

**Expected result:** Read latency for cached short-code lookups drops from ~5–20 ms (Postgres round-trip) to < 1 ms (Redis in-process lookup). The DB handles only cache misses and writes — typically < 20 % of traffic for an established URL shortener. This comfortably handles 500+ concurrent users on a single host.

**Documentation to add:**
- Update `docs/deployment.md` with the Redis service block and new env vars.
- Add a Redis section to `docs/observability.md` covering the new cache metrics.
- Update `docs/decisions.md` to record the Redis caching decision and TTL rationale.

---

### Phase 3 — Horizontal scaling (500+ → multi-thousand concurrent users)

**Goal:** Scale beyond what a single host can serve by running multiple app replicas behind a load balancer.

**Prerequisites:** Phase 2 must be complete. Redis must be a shared external instance (not a sidecar) so all replicas read from the same cache.

**Changes:**

1. **Externalize Redis** to a managed service (e.g., Redis Cloud, ElastiCache) or a standalone container not co-located with the app.

2. **Run multiple app replicas.**
   With Docker Compose:
   ```bash
   docker compose up --scale app=3 -d
   ```
   In production, use a container orchestrator (Kubernetes, ECS, Fly.io) to manage replicas and health checks.

3. **Add a load balancer** (nginx or Traefik) to distribute traffic across replicas:
   ```yaml
   # docker-compose.yml addition
   nginx:
     image: nginx:alpine
     ports:
       - "80:80"
     volumes:
       - ./observability/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
     depends_on:
       - app
   ```

4. **Ensure session-less request handling.** The current app is already stateless (no in-process session state; `request_id` uses `contextvars` scoped to the request). No changes needed here.

5. **Run a single migration process** (not one per replica). Gate app startup on a migration job completing, or run `python migrate.py run` as a one-off task before rolling out new replicas.

6. **Scale Postgres** to a managed instance (RDS, Supabase, Neon) with read replicas if write throughput becomes the bottleneck.

**Expected result:** Near-linear horizontal scaling. Each replica handles ~150 concurrent users (Phase 1 baseline), so three replicas handle ~450, five handle ~750, and so on. The shared Redis cache means cache hit rates improve as traffic increases across replicas.

---

## Summary

| Phase | Concurrent users | Key change | Status |
|---|---|---|---|
| Current | ~20–30 | Single Flask dev server, no pool, no cache | Deployed |
| Phase 1 | ~150 | Gunicorn multi-worker + PgBouncer connection pool | Not implemented |
| Phase 2 | ~500+ | Redis read cache for short-code and URL lookups | Not implemented |
| Phase 3 | 1 000+ | Multiple app replicas behind a load balancer | Not implemented |
