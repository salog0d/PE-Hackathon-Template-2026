from datetime import datetime
from types import SimpleNamespace

import pandas as pd

from app.utils.bulk_loader import BulkLoader
from app.utils.serializers import serialize_event, serialize_url, serialize_user


def test_serialize_user_url_event_shapes():
    now = datetime(2026, 1, 1, 0, 0, 0)
    user = SimpleNamespace(id=1, username="u", email="u@example.com", created_at=now)
    url = SimpleNamespace(
        id=2,
        user_id=1,
        short_code="abc",
        original_url="https://example.com",
        title="t",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    event = SimpleNamespace(
        id=3,
        url_id=2,
        user_id=1,
        event_type="click",
        timestamp=now,
        details='{"x":1}',
    )

    assert serialize_user(user)["created_at"] == "2026-01-01 00:00:00"
    assert serialize_url(url)["short_code"] == "abc"
    assert serialize_event(event)["event_type"] == "click"


def test_bulk_loader_load_users_transforms_expected_columns(monkeypatch):
    captured = {}

    def _fake_load(filepath, model, transform=None):
        df = pd.DataFrame(
            [
                {
                    "id": 1,
                    "username": "alice",
                    "email": "alice@example.com",
                    "created_at": "2026-01-01T00:00:00Z",
                    "extra": "drop-me",
                }
            ]
        )
        transformed = transform(df)
        captured["filepath"] = filepath
        captured["columns"] = list(transformed.columns)
        captured["created_at_type"] = str(transformed["created_at"].dtype)
        return len(transformed)

    monkeypatch.setattr(BulkLoader, "_load", staticmethod(_fake_load))
    count = BulkLoader.load_users("users.csv")

    assert count == 1
    assert captured["filepath"] == "users.csv"
    assert captured["columns"] == ["id", "username", "email", "created_at"]
    assert "datetime64" in captured["created_at_type"]


def test_bulk_loader_load_urls_maps_booleans(monkeypatch):
    captured = {}

    def _fake_load(_filepath, _model, transform=None):
        df = pd.DataFrame(
            [
                {
                    "id": 1,
                    "user_id": 1,
                    "short_code": "a",
                    "original_url": "https://a",
                    "title": "A",
                    "is_active": "True",
                    "created_at": "2026-01-01",
                    "updated_at": "2026-01-02",
                },
                {
                    "id": 2,
                    "user_id": 1,
                    "short_code": "b",
                    "original_url": "https://b",
                    "title": "B",
                    "is_active": "False",
                    "created_at": "2026-01-01",
                    "updated_at": "2026-01-02",
                },
            ]
        )
        transformed = transform(df)
        captured["values"] = transformed["is_active"].tolist()
        return len(transformed)

    monkeypatch.setattr(BulkLoader, "_load", staticmethod(_fake_load))
    count = BulkLoader.load_urls("urls.csv")

    assert count == 2
    assert captured["values"] == [True, False]


def test_bulk_loader_load_events_replaces_nan_details_with_none(monkeypatch):
    captured = {}

    def _fake_load(_filepath, _model, transform=None):
        df = pd.DataFrame(
            [
                {
                    "id": 1,
                    "url_id": 5,
                    "user_id": 9,
                    "event_type": "click",
                    "timestamp": "2026-01-01",
                    "details": None,
                }
            ]
        )
        transformed = transform(df)
        captured["details"] = transformed["details"].iloc[0]
        return len(transformed)

    monkeypatch.setattr(BulkLoader, "_load", staticmethod(_fake_load))
    count = BulkLoader.load_events("events.csv")

    assert count == 1
    assert captured["details"] is None


def test_bulk_loader_load_all_preserves_fk_safe_order(monkeypatch):
    calls = []

    monkeypatch.setattr(
        BulkLoader,
        "load_users",
        classmethod(lambda cls, path: calls.append(("users", path)) or 1),
    )
    monkeypatch.setattr(
        BulkLoader,
        "load_urls",
        classmethod(lambda cls, path: calls.append(("urls", path)) or 2),
    )
    monkeypatch.setattr(
        BulkLoader,
        "load_events",
        classmethod(lambda cls, path: calls.append(("events", path)) or 3),
    )

    result = BulkLoader.load_all("users.csv", "urls.csv", "events.csv")

    assert calls == [
        ("users", "users.csv"),
        ("urls", "urls.csv"),
        ("events", "events.csv"),
    ]
    assert result == {"users": 1, "urls": 2, "events": 3}
