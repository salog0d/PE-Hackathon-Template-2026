import logging
import os
import time

from peewee import DatabaseProxy, Model, OperationalError
from playhouse.pool import PooledPostgresqlDatabase as PostgresqlDatabase

logger = logging.getLogger(__name__)

db = DatabaseProxy()

_MAX_RETRIES = 3
_RETRY_DELAY = 0.5  # seconds


class BaseModel(Model):
    class Meta:
        database = db


def _connect_with_retry():
    """Open a DB connection, retrying up to _MAX_RETRIES times on failure."""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            db.connect(reuse_if_open=True)
            return
        except OperationalError as exc:
            logger.warning(
                "DB connect attempt %d/%d failed: %s", attempt, _MAX_RETRIES, exc
            )
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY * attempt)
    # Final attempt — let the exception propagate so Flask returns a 500
    db.connect(reuse_if_open=True)


def check_db() -> dict:
    """
    Probe the database with a lightweight query.
    Returns {"ok": True} on success or {"ok": False, "error": "<msg>"} on failure.
    """
    from app.metrics import db_up

    try:
        db.execute_sql("SELECT 1")
        db_up.set(1)
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        db_up.set(0)
        return {"ok": False, "error": str(exc)}


def init_db(app):
    database = PostgresqlDatabase(
        os.environ.get("DATABASE_NAME", "hackathon_db"),
        host=os.environ.get("DATABASE_HOST", "localhost"),
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        user=os.environ.get("DATABASE_USER", "postgres"),
        password=os.environ.get("DATABASE_PASSWORD", "postgres"),
        max_connections=int(os.environ.get("DB_POOL_MAX", 20)),
        stale_timeout=300,
    )
    db.initialize(database)

    @app.before_request
    def _db_connect():
        try:
            _connect_with_retry()
        except OperationalError as exc:
            logger.error("DB unavailable: %s", exc)
            from flask import jsonify

            return jsonify(status="error", error="database unavailable"), 500

    @app.teardown_appcontext
    def _db_close(exc):
        if not db.is_closed():
            db.close()
