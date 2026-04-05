import logging
import secrets
import string
from datetime import UTC, datetime

from app.repositories import url_repository

logger = logging.getLogger(__name__)


def get_all():
    return url_repository.get_all()


def get_by_id(url_id: int):
    return url_repository.get_by_id(url_id)


def get_by_short_code(short_code: str):
    return url_repository.get_by_short_code(short_code)


def get_by_user(user_id: int):
    return url_repository.get_by_user(user_id)


def _generate_short_code(length: int = 7) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create(
    user_id: int,
    original_url: str,
    short_code: str = None,
    title: str = None,
    is_active: bool = True,
):
    if not user_id:
        raise ValueError("user_id is required")
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive integer")
    if not short_code or not short_code.strip():
        short_code = _generate_short_code()
    if len(short_code.strip()) > 20:
        raise ValueError("short_code must be 20 characters or fewer")
    if not original_url or not original_url.strip():
        raise ValueError("original_url is required")
    if len(original_url.strip()) > 2048:
        raise ValueError("original_url must be 2048 characters or fewer")
    if not original_url.strip().startswith(("http://", "https://")):
        raise ValueError("original_url must start with http:// or https://")
    if title is not None and len(title) > 255:
        raise ValueError("title must be 255 characters or fewer")
    if not isinstance(is_active, bool):
        raise ValueError("is_active must be a boolean")

    now = datetime.now(UTC)
    logger.info("url_creating", extra={"user_id": user_id, "short_code": short_code})
    url = url_repository.create(
        user_id=user_id,
        short_code=short_code.strip(),
        original_url=original_url.strip(),
        title=title,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )
    logger.info(
        "url_created",
        extra={
            "url_id": getattr(url, "id", None),
            "user_id": user_id,
            "short_code": short_code,
        },
    )
    return url


def update(url_id: int, **fields):
    allowed = {"short_code", "original_url", "title", "is_active"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        raise ValueError("no valid fields to update")
    if "short_code" in fields and not fields["short_code"].strip():
        raise ValueError("short_code cannot be empty")
    if "original_url" in fields and not fields["original_url"].strip():
        raise ValueError("original_url cannot be empty")
    fields["updated_at"] = datetime.now(UTC)
    logger.info("url_updating", extra={"url_id": url_id, "fields": list(fields.keys())})
    result = url_repository.update(url_id, **fields)
    if result:
        logger.info("url_updated", extra={"url_id": url_id})
    else:
        logger.info("url_update_no_rows", extra={"url_id": url_id})
    return result


def delete(url_id: int):
    logger.info("url_deleting", extra={"url_id": url_id})
    result = url_repository.delete(url_id)
    if result:
        logger.info("url_deleted", extra={"url_id": url_id})
    else:
        logger.info("url_delete_no_rows", extra={"url_id": url_id})
    return result
