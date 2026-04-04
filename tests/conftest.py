from datetime import datetime
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def app(monkeypatch):
    import app.app as app_module

    monkeypatch.setattr(app_module, "init_db", lambda _app: None)
    flask_app = app_module.create_app()
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user():
    def _make_user(user_id=1, username="alice", email="alice@example.com"):
        return SimpleNamespace(
            id=user_id,
            username=username,
            email=email,
            created_at=datetime(2026, 1, 1, 0, 0, 0),
        )

    return _make_user


@pytest.fixture
def make_url():
    def _make_url(
        url_id=1, user_id=1, short_code="abc123", original_url="https://example.com"
    ):
        now = datetime(2026, 1, 1, 0, 0, 0)
        return SimpleNamespace(
            id=url_id,
            user_id=user_id,
            short_code=short_code,
            original_url=original_url,
            title="Example",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    return _make_url


@pytest.fixture
def make_event():
    def _make_event(event_id=1, url_id=1, user_id=1, event_type="click"):
        return SimpleNamespace(
            id=event_id,
            url_id=url_id,
            user_id=user_id,
            event_type=event_type,
            timestamp=datetime(2026, 1, 1, 0, 0, 0),
            details='{"ip":"127.0.0.1"}',
        )

    return _make_event
