from datetime import UTC, datetime

from app.repositories import url_repository


def get_all():
    return url_repository.get_all()


def get_by_id(url_id: int):
    return url_repository.get_by_id(url_id)


def get_by_short_code(short_code: str):
    return url_repository.get_by_short_code(short_code)


def get_by_user(user_id: int):
    return url_repository.get_by_user(user_id)


def create(
    user_id: int,
    short_code: str,
    original_url: str,
    title: str = None,
    is_active: bool = True,
):
    if not user_id:
        raise ValueError("user_id is required")
    if not short_code or not short_code.strip():
        raise ValueError("short_code is required")
    if not original_url or not original_url.strip():
        raise ValueError("original_url is required")
    now = datetime.now(UTC)
    return url_repository.create(
        user_id=user_id,
        short_code=short_code.strip(),
        original_url=original_url.strip(),
        title=title,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


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
    return url_repository.update(url_id, **fields)


def delete(url_id: int):
    return url_repository.delete(url_id)
