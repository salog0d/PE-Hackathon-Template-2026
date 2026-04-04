import app.api.events as events_api
import app.api.seed as seed_api
import app.api.urls as urls_api
import app.api.users as users_api


def test_create_user_success(client, monkeypatch, make_user):
    monkeypatch.setattr(
        users_api.user_service,
        "create",
        lambda **_data: make_user(user_id=11, username="john"),
    )
    res = client.post("/users/", json={"username": "John", "email": "john@example.com"})
    assert res.status_code == 201
    assert res.get_json()["username"] == "john"


def test_create_url_success(client, monkeypatch, make_url):
    monkeypatch.setattr(
        urls_api.url_service, "create", lambda **_data: make_url(url_id=55)
    )
    res = client.post(
        "/urls/",
        json={"user_id": 1, "short_code": "code55", "original_url": "https://test.com"},
    )
    assert res.status_code == 201
    assert res.get_json()["id"] == 55


def test_get_urls_success(client, monkeypatch, make_url):
    monkeypatch.setattr(
        urls_api.url_service,
        "get_all",
        lambda: [make_url(url_id=1), make_url(url_id=2)],
    )
    res = client.get("/urls/")
    assert res.status_code == 200
    assert len(res.get_json()) == 2


def test_urls_update_success(client, monkeypatch, make_url):
    monkeypatch.setattr(urls_api.url_service, "update", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        urls_api.url_service,
        "get_by_id",
        lambda _id: make_url(url_id=_id, short_code="updated"),
    )
    res = client.patch("/urls/7", json={"short_code": "updated"})
    assert res.status_code == 200
    assert res.get_json()["short_code"] == "updated"


def test_urls_delete_not_found(client, monkeypatch):
    monkeypatch.setattr(urls_api.url_service, "delete", lambda _id: False)
    res = client.delete("/urls/404")
    assert res.status_code == 404


def test_create_event_success(client, monkeypatch, make_event):
    monkeypatch.setattr(
        events_api.event_service,
        "create",
        lambda **_data: make_event(event_id=42, event_type="click"),
    )
    res = client.post(
        "/events/", json={"url_id": 1, "user_id": 1, "event_type": "click"}
    )
    assert res.status_code == 201
    assert res.get_json()["id"] == 42


def test_get_events_success(client, monkeypatch, make_event):
    monkeypatch.setattr(
        events_api.event_service, "get_all", lambda: [make_event(event_id=1)]
    )
    res = client.get("/events/")
    assert res.status_code == 200
    assert len(res.get_json()) == 1


def test_events_get_not_found(client, monkeypatch):
    monkeypatch.setattr(events_api.event_service, "get_by_id", lambda _id: None)
    res = client.get("/events/999")
    assert res.status_code == 404


def test_events_delete_not_found(client, monkeypatch):
    monkeypatch.setattr(events_api.event_service, "delete", lambda _id: False)
    res = client.delete("/events/123")
    assert res.status_code == 404


def test_seed_urls_and_events_success(client, monkeypatch):
    monkeypatch.setattr(seed_api.BulkLoader, "load_urls", lambda _path: 2)
    monkeypatch.setattr(seed_api.BulkLoader, "load_events", lambda _path: 4)

    from io import BytesIO

    urls_res = client.post(
        "/seed/urls",
        data={
            "file": (
                BytesIO(
                    b"id,user_id,short_code,original_url,title,is_active,created_at,updated_at\n1,1,a,https://a,A,True,2026-01-01,2026-01-01"
                ),
                "urls.csv",
            )
        },
        content_type="multipart/form-data",
    )
    events_res = client.post(
        "/seed/events",
        data={
            "file": (
                BytesIO(
                    b"id,url_id,user_id,event_type,timestamp,details\n1,1,1,click,2026-01-01,{}"
                ),
                "events.csv",
            )
        },
        content_type="multipart/form-data",
    )

    assert urls_res.status_code == 200
    assert events_res.status_code == 200
    assert urls_res.get_json()["loaded"] == 2
    assert events_res.get_json()["loaded"] == 4
