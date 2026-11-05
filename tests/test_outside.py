from helpers import login

OUTSIDE = {"Cf-Connecting-Ip": "203.0.113.7"}


def test_outside_header_403_on_events_and_settings(client):
    for path in ("/api/events", "/api/sources", "/api/anything"):
        response = client.get(path, headers={**OUTSIDE, **login()})
        assert response.status_code == 403 and response.json()["detail"] == "outside", path


def test_health_answers_outside(client):
    assert client.get("/health", headers=OUTSIDE).status_code == 200
