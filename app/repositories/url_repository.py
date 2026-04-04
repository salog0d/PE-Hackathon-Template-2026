import logging

from app.models.url import Url

logger = logging.getLogger(__name__)


def get_all():
    return list(Url.select())


def get_by_id(url_id: int):
    return Url.get_or_none(Url.id == url_id)


def get_by_short_code(short_code: str):
    return Url.get_or_none(Url.short_code == short_code)


def get_by_user(user_id: int):
    return list(Url.select().where(Url.user_id == user_id))


def create(
    user_id: int,
    short_code: str,
    original_url: str,
    title: str,
    is_active: bool,
    created_at,
    updated_at,
) -> Url:
    logger.debug("db_url_insert", extra={"user_id": user_id, "short_code": short_code})
    url = Url.create(
        user_id=user_id,
        short_code=short_code,
        original_url=original_url,
        title=title,
        is_active=is_active,
        created_at=created_at,
        updated_at=updated_at,
    )
    logger.debug("db_url_inserted", extra={"url_id": url.id})
    return url


def update(url_id: int, **fields) -> bool:
    logger.debug(
        "db_url_update", extra={"url_id": url_id, "fields": list(fields.keys())}
    )
    rows = Url.update(**fields).where(Url.id == url_id).execute()
    logger.debug("db_url_updated", extra={"url_id": url_id, "rows_affected": rows})
    return rows > 0


def delete(url_id: int) -> bool:
    logger.debug("db_url_delete", extra={"url_id": url_id})
    rows = Url.delete().where(Url.id == url_id).execute()
    logger.debug("db_url_deleted", extra={"url_id": url_id, "rows_affected": rows})
    return rows > 0
