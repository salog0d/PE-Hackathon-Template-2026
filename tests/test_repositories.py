from types import SimpleNamespace

import app.repositories.event_repository as event_repository
import app.repositories.url_repository as url_repository
import app.repositories.user_repository as user_repository


class _Field:
    def __eq__(self, other):
        return other


class _WhereExec:
    def __init__(self, rows):
        self._rows = rows

    def execute(self):
        return self._rows


class _UpdateDeleteBuilder:
    def __init__(self, rows):
        self._rows = rows

    def where(self, _expr):
        return _WhereExec(self._rows)


class _Selectable:
    def __init__(self, rows):
        self._rows = rows

    def where(self, _expr):
        return self._rows

    def __iter__(self):
        return iter(self._rows)


def test_user_repository_crud(monkeypatch):
    created = SimpleNamespace(id=1, username="alice")

    class FakeUser:
        id = _Field()

        @staticmethod
        def select():
            return [created]

        @staticmethod
        def get_or_none(_expr):
            return created

        @staticmethod
        def create(**_kwargs):
            return created

        @staticmethod
        def update(**_fields):
            return _UpdateDeleteBuilder(1)

        @staticmethod
        def delete():
            return _UpdateDeleteBuilder(1)

    monkeypatch.setattr(user_repository, "User", FakeUser)

    assert user_repository.get_all()[0].id == 1
    assert user_repository.get_by_id(1).username == "alice"
    assert user_repository.create("alice", "a@x.com", "ts").id == 1
    assert user_repository.update(1, username="b") is True
    assert user_repository.delete(1) is True


def test_url_repository_crud(monkeypatch):
    created = SimpleNamespace(id=2, short_code="code")

    class FakeUrl:
        id = _Field()
        user_id = _Field()
        short_code = _Field()

        @staticmethod
        def select():
            return _Selectable([created])

        @staticmethod
        def get_or_none(_expr):
            return created

        @staticmethod
        def create(**_kwargs):
            return created

        @staticmethod
        def update(**_fields):
            return _UpdateDeleteBuilder(1)

        @staticmethod
        def delete():
            return _UpdateDeleteBuilder(1)

    monkeypatch.setattr(url_repository, "Url", FakeUrl)

    assert url_repository.get_all()[0].id == 2
    assert url_repository.get_by_id(2).short_code == "code"
    assert url_repository.get_by_short_code("code").id == 2
    assert len(url_repository.get_by_user(1)) == 1
    assert url_repository.create(1, "c", "https://x", None, True, "ts", "ts").id == 2
    assert url_repository.update(2, short_code="new") is True
    assert url_repository.delete(2) is True


def test_event_repository_crud(monkeypatch):
    created = SimpleNamespace(id=3, event_type="click")

    class FakeEvent:
        id = _Field()
        url_id = _Field()
        user_id = _Field()

        @staticmethod
        def select():
            return _Selectable([created])

        @staticmethod
        def get_or_none(_expr):
            return created

        @staticmethod
        def create(**_kwargs):
            return created

        @staticmethod
        def update(**_fields):
            return _UpdateDeleteBuilder(1)

        @staticmethod
        def delete():
            return _UpdateDeleteBuilder(1)

    monkeypatch.setattr(event_repository, "Event", FakeEvent)

    assert event_repository.get_all()[0].id == 3
    assert event_repository.get_by_id(3).event_type == "click"
    assert len(event_repository.get_by_url(1)) == 1
    assert len(event_repository.get_by_user(1)) == 1
    assert event_repository.create(1, 1, "click", "ts", "{}").id == 3
    assert event_repository.update(3, details="x") is True
    assert event_repository.delete(3) is True
