from datetime import UTC, datetime

from app.repositories import user_repository


def get_all():
    return user_repository.get_all()


def get_by_id(user_id: int):
    return user_repository.get_by_id(user_id)


def create(username: str, email: str):
    if not username or not username.strip():
        raise ValueError("username is required")
    if not email or not email.strip():
        raise ValueError("email is required")
    return user_repository.create(
        username=username.strip(),
        email=email.strip(),
        created_at=datetime.now(UTC),
    )


def update(user_id: int, **fields):
    allowed = {"username", "email"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        raise ValueError("no valid fields to update")
    if "username" in fields and not fields["username"].strip():
        raise ValueError("username cannot be empty")
    if "email" in fields and not fields["email"].strip():
        raise ValueError("email cannot be empty")
    return user_repository.update(user_id, **fields)


def delete(user_id: int):
    return user_repository.delete(user_id)
