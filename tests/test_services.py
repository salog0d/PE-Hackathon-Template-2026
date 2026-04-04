from datetime import datetime

import pytest

import app.services.event_service as event_service
import app.services.url_service as url_service
import app.services.user_service as user_service


def test_user_create_trims_input_and_sets_created_at(monkeypatch):
    captured = {}

    def _create(**kwargs):
        captured.update(kwargs)
        return kwargs

    monkeypatch.setattr(user_service.user_repository, "create", _create)
    created = user_service.create("  alice  ", "  alice@example.com  ")

    assert captured["username"] == "alice"
    assert captured["email"] == "alice@example.com"
    assert isinstance(captured["created_at"], datetime)
    assert created["username"] == "alice"


@pytest.mark.parametrize(
    ("username", "email", "expected"),
    [
        ("", "mail@example.com", "username is required"),
        ("   ", "mail@example.com", "username is required"),
        ("alice", "", "email is required"),
        ("alice", "   ", "email is required"),
    ],
)
def test_user_create_rejects_invalid_required_fields(username, email, expected):
    with pytest.raises(ValueError, match=expected):
        user_service.create(username, email)


def test_user_update_requires_valid_fields():
    with pytest.raises(ValueError, match="no valid fields to update"):
        user_service.update(1, unsupported="x")


def test_user_update_rejects_blank_username():
    with pytest.raises(ValueError, match="username cannot be empty"):
        user_service.update(1, username=" ")


def test_url_create_rejects_required_fields():
    with pytest.raises(ValueError, match="user_id is required"):
        url_service.create(0, "abc", "https://example.com")

    with pytest.raises(ValueError, match="short_code is required"):
        url_service.create(1, " ", "https://example.com")

    with pytest.raises(ValueError, match="original_url is required"):
        url_service.create(1, "abc", " ")


def test_url_update_sets_updated_at_and_filters_fields(monkeypatch):
    captured = {}

    def _update(url_id, **fields):
        captured["url_id"] = url_id
        captured["fields"] = fields
        return True

    monkeypatch.setattr(url_service.url_repository, "update", _update)
    updated = url_service.update(7, short_code="abc", unsupported="ignore-me")

    assert updated is True
    assert captured["url_id"] == 7
    assert captured["fields"]["short_code"] == "abc"
    assert "unsupported" not in captured["fields"]
    assert isinstance(captured["fields"]["updated_at"], datetime)


def test_url_update_rejects_blank_short_code():
    with pytest.raises(ValueError, match="short_code cannot be empty"):
        url_service.update(7, short_code=" ")


def test_event_create_rejects_required_fields():
    with pytest.raises(ValueError, match="url_id is required"):
        event_service.create(0, 1, "click")

    with pytest.raises(ValueError, match="user_id is required"):
        event_service.create(1, 0, "click")

    with pytest.raises(ValueError, match="event_type is required"):
        event_service.create(1, 1, " ")


def test_event_create_trims_event_type(monkeypatch):
    captured = {}

    def _create(**kwargs):
        captured.update(kwargs)
        return kwargs

    monkeypatch.setattr(event_service.event_repository, "create", _create)
    created = event_service.create(1, 2, "  click  ", details="{}")

    assert captured["url_id"] == 1
    assert captured["user_id"] == 2
    assert captured["event_type"] == "click"
    assert isinstance(captured["timestamp"], datetime)
    assert created["details"] == "{}"


def test_event_update_rejects_empty_event_type():
    with pytest.raises(ValueError, match="event_type cannot be empty"):
        event_service.update(8, event_type=" ")


def test_event_update_requires_any_valid_field():
    with pytest.raises(ValueError, match="no valid fields to update"):
        event_service.update(8, random_field="value")
