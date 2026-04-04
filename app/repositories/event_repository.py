import logging

from app.models.event import Event

logger = logging.getLogger(__name__)


def get_all():
    return list(Event.select())


def get_by_id(event_id: int):
    return Event.get_or_none(Event.id == event_id)


def get_by_url(url_id: int):
    return list(Event.select().where(Event.url_id == url_id))


def get_by_user(user_id: int):
    return list(Event.select().where(Event.user_id == user_id))


def create(
    url_id: int, user_id: int, event_type: str, timestamp, details: str = None
) -> Event:
    logger.debug(
        "db_event_insert",
        extra={"url_id": url_id, "user_id": user_id, "event_type": event_type},
    )
    event = Event.create(
        url_id=url_id,
        user_id=user_id,
        event_type=event_type,
        timestamp=timestamp,
        details=details,
    )
    logger.debug("db_event_inserted", extra={"event_id": event.id})
    return event


def update(event_id: int, **fields) -> bool:
    logger.debug(
        "db_event_update", extra={"event_id": event_id, "fields": list(fields.keys())}
    )
    rows = Event.update(**fields).where(Event.id == event_id).execute()
    logger.debug(
        "db_event_updated", extra={"event_id": event_id, "rows_affected": rows}
    )
    return rows > 0


def delete(event_id: int) -> bool:
    logger.debug("db_event_delete", extra={"event_id": event_id})
    rows = Event.delete().where(Event.id == event_id).execute()
    logger.debug(
        "db_event_deleted", extra={"event_id": event_id, "rows_affected": rows}
    )
    return rows > 0
