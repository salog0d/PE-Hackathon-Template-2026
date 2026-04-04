from datetime import UTC, datetime

from app.repositories import event_repository


def get_all():
    return event_repository.get_all()


def get_by_id(event_id: int):
    return event_repository.get_by_id(event_id)


def get_by_url(url_id: int):
    return event_repository.get_by_url(url_id)


def get_by_user(user_id: int):
    return event_repository.get_by_user(user_id)


def create(url_id: int, user_id: int, event_type: str, details: str = None):
    if not url_id:
        raise ValueError("url_id is required")
    if not user_id:
        raise ValueError("user_id is required")
    if not event_type or not event_type.strip():
        raise ValueError("event_type is required")
    return event_repository.create(
        url_id=url_id,
        user_id=user_id,
        event_type=event_type.strip(),
        timestamp=datetime.now(UTC),
        details=details,
    )


def update(event_id: int, **fields):
    allowed = {"event_type", "details"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        raise ValueError("no valid fields to update")
    if "event_type" in fields and not fields["event_type"].strip():
        raise ValueError("event_type cannot be empty")
    return event_repository.update(event_id, **fields)


def delete(event_id: int):
    return event_repository.delete(event_id)
