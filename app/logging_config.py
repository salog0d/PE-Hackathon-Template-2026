import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

SERVICE_NAME = os.environ.get("SERVICE_NAME", "url-service")

# Derive standard LogRecord attributes once so the formatter can exclude them.
_STANDARD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()

        log_entry: dict = {
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "logger": record.name,
            "message": record.message,
            "request_id": request_id_var.get(),
        }

        # Append any extra fields passed via the `extra=` kwarg.
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                log_entry[key] = value

        if record.exc_info:
            log_entry["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging() -> None:
    """Configure root logger: JSON → stdout, level from LOG_LEVEL env var."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(log_level)
    # Remove any handlers added before this call (e.g. Flask's default ones).
    root.handlers.clear()
    root.addHandler(handler)
