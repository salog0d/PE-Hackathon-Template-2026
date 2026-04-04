import runpy
from types import SimpleNamespace

import app.database as database_module


class _FakeApp:
    def __init__(self):
        self.before_request_handler = None
        self.teardown_handler = None

    def before_request(self, fn):
        self.before_request_handler = fn
        return fn

    def teardown_appcontext(self, fn):
        self.teardown_handler = fn
        return fn


class _FakeDBProxy:
    def __init__(self):
        self.initialized_with = None
        self.connect_kwargs = None
        self.closed = False
        self._is_closed = True

    def initialize(self, db_obj):
        self.initialized_with = db_obj

    def connect(self, **kwargs):
        self.connect_kwargs = kwargs

    def is_closed(self):
        return self._is_closed

    def close(self):
        self.closed = True
        self._is_closed = True


def test_init_db_registers_hooks_and_uses_config(monkeypatch):
    seen = {}
    app = _FakeApp()
    fake_db = _FakeDBProxy()
    fake_db._is_closed = False

    monkeypatch.setenv("DATABASE_NAME", "testdb")
    monkeypatch.setenv("DATABASE_HOST", "dbhost")
    monkeypatch.setenv("DATABASE_PORT", "5433")
    monkeypatch.setenv("DATABASE_USER", "dbuser")
    monkeypatch.setenv("DATABASE_PASSWORD", "dbpass")

    monkeypatch.setattr(
        database_module,
        "PostgresqlDatabase",
        lambda name, **kwargs: seen.setdefault("db_args", (name, kwargs)) or object(),
    )
    monkeypatch.setattr(database_module, "db", fake_db)

    database_module.init_db(app)
    app.before_request_handler()
    app.teardown_handler(None)

    name, kwargs = seen["db_args"]
    assert name == "testdb"
    assert kwargs == {
        "host": "dbhost",
        "port": 5433,
        "user": "dbuser",
        "password": "dbpass",
    }
    assert fake_db.initialized_with is not None
    assert fake_db.connect_kwargs == {"reuse_if_open": True}
    assert fake_db.closed is True


def test_init_db_does_not_close_if_already_closed(monkeypatch):
    app = _FakeApp()
    fake_db = _FakeDBProxy()

    monkeypatch.setattr(
        database_module, "PostgresqlDatabase", lambda *_args, **_kwargs: object()
    )
    monkeypatch.setattr(database_module, "db", fake_db)

    database_module.init_db(app)
    app.teardown_handler(None)

    assert fake_db.closed is False


def test_main_executes_run_when_module_is_main(monkeypatch):
    runner = {"called": False, "debug": None}
    fake_app = SimpleNamespace(
        run=lambda **kwargs: runner.update(called=True, debug=kwargs.get("debug")),
    )

    import app.app as app_module

    monkeypatch.setattr(app_module, "create_app", lambda: fake_app)
    runpy.run_module("app.main", run_name="__main__")

    assert runner["called"] is True
    assert runner["debug"] is True
