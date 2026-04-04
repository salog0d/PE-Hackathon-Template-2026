import logging

import pandas as pd

from app.database import db
from app.models.event import Event
from app.models.url import Url
from app.models.user import User

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000


class BulkLoader:
    """Batch-loads seed CSV files into the database using Peewee insert_many.

    Load order matters due to foreign key constraints: Users → URLs → Events.
    Each model is processed in chunks to keep memory usage bounded regardless
    of file size.
    """

    @staticmethod
    def _load(filepath: str, model, transform=None) -> int:
        """Read a CSV in chunks and bulk-insert each chunk inside a transaction.

        Returns the total number of rows inserted.
        """
        total = 0
        for chunk in pd.read_csv(filepath, chunksize=CHUNK_SIZE):
            if transform:
                chunk = transform(chunk)
            records = chunk.to_dict("records")
            with db.atomic():
                model.insert_many(records).execute()
            total += len(records)
            logger.debug(
                "db_chunk_inserted",
                extra={"rows": len(records), "table": model._meta.table_name},
            )
        return total

    @classmethod
    def load_users(cls, filepath: str) -> int:
        """Load users.csv — columns: id, username, email, created_at."""

        def transform(df):
            df["created_at"] = pd.to_datetime(df["created_at"])
            return df[["id", "username", "email", "created_at"]]

        total = cls._load(filepath, User, transform)
        logger.info("bulk_users_loaded", extra={"count": total})
        return total

    @classmethod
    def load_urls(cls, filepath: str) -> int:
        """Load urls.csv — columns: id, user_id, short_code, original_url, title, is_active, created_at, updated_at."""

        def transform(df):
            df["created_at"] = pd.to_datetime(df["created_at"])
            df["updated_at"] = pd.to_datetime(df["updated_at"])
            df["is_active"] = (
                df["is_active"].map({"True": True, "False": False}).astype(bool)
            )
            return df[
                [
                    "id",
                    "user_id",
                    "short_code",
                    "original_url",
                    "title",
                    "is_active",
                    "created_at",
                    "updated_at",
                ]
            ]

        total = cls._load(filepath, Url, transform)
        logger.info("bulk_urls_loaded", extra={"count": total})
        return total

    @classmethod
    def load_events(cls, filepath: str) -> int:
        """Load events.csv — columns: id, url_id, user_id, event_type, timestamp, details."""

        def transform(df):
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["details"] = df["details"].where(df["details"].notna(), None)
            return df[["id", "url_id", "user_id", "event_type", "timestamp", "details"]]

        total = cls._load(filepath, Event, transform)
        logger.info("bulk_events_loaded", extra={"count": total})
        return total

    @classmethod
    def load_all(cls, users_path: str, urls_path: str, events_path: str) -> dict:
        """Load all three seed files in FK-safe order.

        Returns a summary dict with row counts per model.
        """
        logger.info("bulk_load_started")
        result = {
            "users": cls.load_users(users_path),
            "urls": cls.load_urls(urls_path),
            "events": cls.load_events(events_path),
        }
        logger.info("bulk_load_completed", extra={"summary": result})
        return result
