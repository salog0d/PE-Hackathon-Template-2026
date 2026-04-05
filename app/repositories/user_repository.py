import logging

from peewee import IntegrityError

from app.models.user import User

logger = logging.getLogger(__name__)


def get_all():
    return list(User.select())


def get_by_id(user_id: int):
    return User.get_or_none(User.id == user_id)


def create(username: str, email: str, created_at) -> User:
    logger.debug("db_user_insert", extra={"username": username})
    try:
        user = User.create(username=username, email=email, created_at=created_at)
    except IntegrityError:
        raise ValueError("username or email already exists")
    logger.debug("db_user_inserted", extra={"user_id": user.id})
    return user


def update(user_id: int, **fields) -> bool:
    logger.debug(
        "db_user_update", extra={"user_id": user_id, "fields": list(fields.keys())}
    )
    rows = User.update(**fields).where(User.id == user_id).execute()
    logger.debug("db_user_updated", extra={"user_id": user_id, "rows_affected": rows})
    return rows > 0


def delete(user_id: int) -> bool:
    logger.debug("db_user_delete", extra={"user_id": user_id})
    rows = User.delete().where(User.id == user_id).execute()
    logger.debug("db_user_deleted", extra={"user_id": user_id, "rows_affected": rows})
    return rows > 0
