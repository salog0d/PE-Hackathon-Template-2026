from io import BytesIO

import app.api.events as events_api
import app.api.seed as seed_api
import app.api.urls as urls_api
import app.api.users as users_api


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_users_list_returns_serialized_payload(client, monkeypatch, make_user):
    monkeypatch.setattr(
        users_api.user_service, "get_all", lambda: [make_user(user_id=10)]
    )
    response = client.get("/users/")
    assert response.status_code == 200
    body = response.get_json()
    assert len(body) == 1
    assert body[0]["id"] == 10
    assert body[0]["username"] == "alice"


def test_users_get_404_when_missing(client, monkeypatch):
    monkeypatch.setattr(users_api.user_service, "get_by_id", lambda _user_id: None)
    response = client.get("/users/999")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Not found"


def test_users_create_returns_400_on_validation_error(client, monkeypatch):
    def _raise(**_kwargs):
        raise ValueError("username is required")

    monkeypatch.setattr(users_api.user_service, "create", _raise)
    response = client.post("/users/", json={"username": " ", "email": "x@example.com"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "username is required"


def test_users_update_returns_404_when_repo_has_no_row(client, monkeypatch):
    monkeypatch.setattr(
        users_api.user_service, "update", lambda *_args, **_kwargs: False
    )
    response = client.patch("/users/123", json={"username": "new-name"})
    assert response.status_code == 404
    assert response.get_json()["error"] == "Not found"


def test_users_delete_success(client, monkeypatch):
    monkeypatch.setattr(users_api.user_service, "delete", lambda _user_id: True)
    response = client.delete("/users/1")
    assert response.status_code == 204
    assert response.data == b""


def test_urls_list_uses_user_filter_when_present(client, monkeypatch, make_url):
    called = {"by_user": 0, "all": 0}

    def _by_user(_user_id):
        called["by_user"] += 1
        return [make_url(url_id=2, user_id=7)]

    def _all():
        called["all"] += 1
        return [make_url(url_id=1, user_id=1)]

    monkeypatch.setattr(urls_api.url_service, "get_by_user", _by_user)
    monkeypatch.setattr(urls_api.url_service, "get_all", _all)

    response = client.get("/urls/?user_id=7")
    assert response.status_code == 200
    assert called == {"by_user": 1, "all": 0}
    assert response.get_json()[0]["user_id"] == 7


def test_urls_short_code_returns_404_when_missing(client, monkeypatch):
    monkeypatch.setattr(urls_api.url_service, "get_by_short_code", lambda _code: None)
    response = client.get("/urls/code/missing")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Not found"


def test_events_list_prioritizes_url_filter_over_user_filter(
    client, monkeypatch, make_event
):
    called = {"by_url": 0, "by_user": 0, "all": 0}

    def _by_url(_url_id):
        called["by_url"] += 1
        return [make_event(event_id=9, url_id=4, user_id=88)]

    def _by_user(_user_id):
        called["by_user"] += 1
        return [make_event(event_id=7, url_id=1, user_id=77)]

    def _all():
        called["all"] += 1
        return [make_event(event_id=1)]

    monkeypatch.setattr(events_api.event_service, "get_by_url", _by_url)
    monkeypatch.setattr(events_api.event_service, "get_by_user", _by_user)
    monkeypatch.setattr(events_api.event_service, "get_all", _all)

    response = client.get("/events/?url_id=4&user_id=88")
    assert response.status_code == 200
    assert called == {"by_url": 1, "by_user": 0, "all": 0}
    assert response.get_json()[0]["url_id"] == 4


def test_events_update_returns_400_for_invalid_payload(client, monkeypatch):
    def _raise(*_args, **_kwargs):
        raise ValueError("event_type cannot be empty")

    monkeypatch.setattr(events_api.event_service, "update", _raise)
    response = client.patch("/events/3", json={"event_type": " "})
    assert response.status_code == 400
    assert response.get_json()["error"] == "event_type cannot be empty"


def test_seed_users_returns_400_without_file(client):
    response = client.post("/seed/users", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json()["error"] == "No file provided"


def test_seed_users_accepts_csv_and_returns_count(client, monkeypatch):
    monkeypatch.setattr(seed_api.BulkLoader, "load_users", lambda _path: 3)
    payload = {
        "file": (
            BytesIO(b"id,username,email,created_at\n1,a,a@x.com,2026-01-01"),
            "users.csv",
        )
    }
    response = client.post(
        "/seed/users", data=payload, content_type="multipart/form-data"
    )
    assert response.status_code == 200
    assert response.get_json() == {"loaded": 3, "model": "users"}
