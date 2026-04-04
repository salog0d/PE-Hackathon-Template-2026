import logging
from datetime import UTC, datetime

from app.repositories import user_repository

logger = logging.getLogger(__name__)


def get_all():
    return user_repository.get_all()


def get_by_id(user_id: int):
    return user_repository.get_by_id(user_id)


def create(username: str, email: str):
    if not username or not username.strip():
        raise ValueError("username is required")
    if not email or not email.strip():
        raise ValueError("email is required")
    logger.info("user_creating", extra={"username": username})
    user = user_repository.create(
        username=username.strip(),
        email=email.strip(),
        created_at=datetime.now(UTC),
    )
    logger.info("user_created", extra={"user_id": user.id, "username": username})
    return user


def update(user_id: int, **fields):
    allowed = {"username", "email"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        raise ValueError("no valid fields to update")
    if "username" in fields and not fields["username"].strip():
        raise ValueError("username cannot be empty")
    if "email" in fields and not fields["email"].strip():
        raise ValueError("email cannot be empty")
    logger.info(
        "user_updating", extra={"user_id": user_id, "fields": list(fields.keys())}
    )
    result = user_repository.update(user_id, **fields)
    if result:
        logger.info("user_updated", extra={"user_id": user_id})
    else:
        logger.info("user_update_no_rows", extra={"user_id": user_id})
    return result


def delete(user_id: int):
    logger.info("user_deleting", extra={"user_id": user_id})
    result = user_repository.delete(user_id)
    if result:
        logger.info("user_deleted", extra={"user_id": user_id})
    else:
        logger.info("user_delete_no_rows", extra={"user_id": user_id})
    return result
