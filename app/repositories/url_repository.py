from app.models.url import Url


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
    return Url.create(
        user_id=user_id,
        short_code=short_code,
        original_url=original_url,
        title=title,
        is_active=is_active,
        created_at=created_at,
        updated_at=updated_at,
    )


def update(url_id: int, **fields) -> bool:
    rows = Url.update(**fields).where(Url.id == url_id).execute()
    return rows > 0


def delete(url_id: int) -> bool:
    rows = Url.delete().where(Url.id == url_id).execute()
    return rows > 0
