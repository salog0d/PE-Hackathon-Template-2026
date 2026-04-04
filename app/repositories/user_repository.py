from app.models.user import User


def get_all():
    return list(User.select())


def get_by_id(user_id: int):
    return User.get_or_none(User.id == user_id)


def create(username: str, email: str, created_at) -> User:
    return User.create(username=username, email=email, created_at=created_at)


def update(user_id: int, **fields) -> bool:
    rows = User.update(**fields).where(User.id == user_id).execute()
    return rows > 0


def delete(user_id: int) -> bool:
    rows = User.delete().where(User.id == user_id).execute()
    return rows > 0
