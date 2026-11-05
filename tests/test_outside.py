from helpers import login

OUTSIDE = {"Cf-Connecting-Ip": "203.0.113.7"}


def test_outside_header_403_on_events_and_settings(client):
    for path in ("/api/events", "/api/sources", "/api/anything"):
        response = client.get(path, headers={**OUTSIDE, **login()})
        assert response.status_code == 403 and response.json()["detail"] == "outside", path


def test_health_answers_outside(client):
    assert client.get("/health", headers=OUTSIDE).status_code == 200


def test_foreign_host_refused_when_hosts_are_set(client, monkeypatch):
    """DNS rebinding: a web page that points its own name at the NAS gets nothing (the wall needs no login)."""
    monkeypatch.setenv("ALLOWED_HOSTS", "kalender.local.example.ch, localhost")
    assert client.get("/api/calendars", headers={"Host": "evil.example.com"}).status_code == 400
    assert client.get("/api/calendars", headers={"Host": "kalender.local.example.ch"}).status_code == 200
    assert client.get("/api/calendars", headers={"Host": "localhost:8090"}).status_code == 200
    assert client.get("/health", headers={"Host": "evil.example.com"}).status_code == 200


def test_any_host_when_not_set(client, monkeypatch):
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    assert client.get("/api/calendars", headers={"Host": "192.168.1.20:8090"}).status_code == 200
