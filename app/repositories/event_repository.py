from app.models.event import Event


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
    return Event.create(
        url_id=url_id,
        user_id=user_id,
        event_type=event_type,
        timestamp=timestamp,
        details=details,
    )


def update(event_id: int, **fields) -> bool:
    rows = Event.update(**fields).where(Event.id == event_id).execute()
    return rows > 0


def delete(event_id: int) -> bool:
    rows = Event.delete().where(Event.id == event_id).execute()
    return rows > 0
