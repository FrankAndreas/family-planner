import json

import pytest

from app import crypto, models
from calendars import FUSSBALL
from fake_sources import HOME
from helpers import add_calendar, add_person, login

URL = "https://calendar.google.com/calendar/ical/a%40example.com/private-s3cr3t/basic.ics"
APPLE_ID, PASSWORD = "familie@example.com", "abcd-efgh-ijkl-mnop"


def add_google(client, web, url=URL, name="Mama"):
    web.set(url, FUSSBALL)
    return client.post("/api/sources", json={"kind": "google_ical", "name": name, "url": url}, headers=login())


def walk(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)
    else:
        yield str(value)


def test_add_google_source_checks_url_first(client, db):
    response = client.post("/api/sources", json={"kind": "google_ical", "name": "Mama", "url": URL}, headers=login())
    assert response.status_code == 422 and response.json()["detail"] == "source_not_found"
    assert db.query(models.Source).count() == 0


def test_add_google_source_imports_once(client, web, db):
    response = add_google(client, web)
    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "google_ical" and body["has_credential"] is True and body["last_error"] is None
    (calendar,) = body["calendars"]
    assert calendar["name"] == "Mama" and calendar["enabled"] and calendar["visible"]
    assert db.query(models.Series).count() == 1


def test_stored_credential_is_encrypted(client, web, db):
    add_google(client, web)
    stored = db.query(models.Source).one().credential
    assert "s3cr3t" not in stored and crypto.decrypt(stored) == URL


def test_responses_never_contain_credentials(client, web):
    web.dav.calendar("home", "Familie")
    texts = []
    texts += walk(add_google(client, web).json())
    texts += walk(client.post("/api/sources", json={"kind": "icloud_caldav", "name": "iCloud", "apple_id": APPLE_ID,
                                                   "password": PASSWORD}, headers=login()).json())
    texts += walk(client.get("/api/sources", headers=login()).json())
    texts += walk(client.get("/api/calendars").json())
    texts += walk(client.get("/api/config").json())
    joined = " ".join(texts)
    assert "s3cr3t" not in joined and PASSWORD not in joined and "private-" not in joined


def test_add_icloud_lists_calendars_disabled(client, web, db):
    web.dav.calendar("home", "Familie")
    web.dav.calendar("work", "Arbeit")
    response = client.post("/api/sources", json={"kind": "icloud_caldav", "name": "iCloud", "apple_id": APPLE_ID,
                                                 "password": PASSWORD}, headers=login())
    assert response.status_code == 201
    assert sorted((c["name"], c["enabled"]) for c in response.json()["calendars"]) == [
        ("Arbeit", False), ("Familie", False)]
    source = db.query(models.Source).one()
    assert source.base_url == HOME and json.loads(crypto.decrypt(source.credential))["apple_id"] == APPLE_ID


def test_add_icloud_wrong_password_422(client, web, db):
    response = client.post("/api/sources", json={"kind": "icloud_caldav", "name": "iCloud", "apple_id": APPLE_ID,
                                                 "password": "falsch"}, headers=login())
    assert response.status_code == 422 and response.json()["detail"] == "source_auth"
    assert db.query(models.Source).count() == 0


def test_enabling_icloud_calendar_imports_it(client, web, db):
    web.dav.calendar("home", "Familie", {f"{HOME}home/a.ics": FUSSBALL})
    body = client.post("/api/sources", json={"kind": "icloud_caldav", "name": "iCloud", "apple_id": APPLE_ID,
                                             "password": PASSWORD}, headers=login()).json()
    calendar_id = body["calendars"][0]["id"]
    assert client.patch(f"/api/calendars/{calendar_id}", json={"enabled": True}, headers=login()).status_code == 200
    assert db.query(models.Series).count() == 1


def test_change_url_is_checked_and_resyncs(client, web, db):
    source_id = add_google(client, web).json()["id"]
    response = client.patch(f"/api/sources/{source_id}", json={"url": "https://example.com/gone.ics"}, headers=login())
    assert response.status_code == 422
    new = "https://calendar.google.com/calendar/ical/b%40example.com/private-neu/basic.ics"
    web.set(new, FUSSBALL)
    response = client.patch(f"/api/sources/{source_id}", json={"url": new, "name": "Mama neu"}, headers=login())
    assert response.status_code == 200 and response.json()["name"] == "Mama neu"
    assert crypto.decrypt(db.query(models.Source).one().credential) == new


def test_delete_source(client, web, db):
    source_id = add_google(client, web).json()["id"]
    assert client.delete(f"/api/sources/{source_id}", headers=login()).status_code == 204
    assert db.query(models.Calendar).count() == 0


def test_sync_now(client, web, db):
    source_id = add_google(client, web).json()["id"]
    web.set(URL, "<html></html>")
    body = client.post(f"/api/sources/{source_id}/sync", headers=login()).json()
    assert body["last_error"] == "source_invalid"


def test_patch_calendar_person_and_bad_color(client, web, db, family_hub):
    family_hub.add("Lea", "CHILD", color="#16a34a")
    calendar_id = add_google(client, web).json()["calendars"][0]["id"]
    lea = db.query(models.Person).filter_by(name="Lea").one()
    response = client.patch(f"/api/calendars/{calendar_id}", json={"person_id": lea.id, "visible": False},
                            headers=login())
    assert response.status_code == 200
    calendar = db.get(models.Calendar, calendar_id)
    assert (calendar.person_id, calendar.visible) == (lea.id, False)
    for bad in ("red", "#12345", "#GGGGGG"):
        response = client.patch(f"/api/calendars/{calendar_id}", json={"color": bad}, headers=login())
        assert response.status_code == 422 and response.json()["detail"] == "bad_color", bad
    assert client.patch(f"/api/calendars/{calendar_id}", json={"color": "#AABBCC"}, headers=login()).status_code == 200
    assert db.get(models.Calendar, calendar_id).color == "#aabbcc"


def test_patch_calendar_unknown_or_inactive_person(client, web, db):
    gone = add_person(db, "Gone", active=False)
    calendar_id = add_google(client, web).json()["calendars"][0]["id"]
    for person_id in (gone.id, 9999):
        response = client.patch(f"/api/calendars/{calendar_id}", json={"person_id": person_id}, headers=login())
        assert response.status_code == 422 and response.json()["detail"] == "unknown_person"


def test_people_lists_active(client, db, family_hub):
    family_hub.add("Lea", "CHILD", color="#16a34a")
    body = client.get("/api/people", headers=login()).json()
    assert sorted(p["name"] for p in body) == ["Admin", "Lea"]


def test_family_color(client):
    assert client.patch("/api/settings", json={"family_color": "#112233"}, headers=login()).status_code == 200
    assert client.get("/api/config").json()["family_color"] == "#112233"


@pytest.mark.parametrize("method,path", [("get", "/api/sources"), ("post", "/api/sources"), ("get", "/api/people"),
                                         ("patch", "/api/settings"), ("patch", "/api/calendars/1")])
def test_child_gets_parents_only(client, family_hub, method, path):
    family_hub.add("Lea", "CHILD")
    response = getattr(client, method)(path, headers=login("Lea"), **({} if method == "get" else {"json": {}}))
    assert response.status_code == 403 and response.json()["detail"] == "parents_only"


def test_me_for_a_child(client, family_hub):
    family_hub.add("Lea", "CHILD")
    assert client.get("/api/me", headers=login("Lea")).json()["role"] == "CHILD"


def test_inactive_person_falls_back_to_family(client, web, db, family_hub):
    family_hub.add("Lea", "CHILD", color="#16a34a")
    client.get("/api/people", headers=login())
    lea = db.query(models.Person).filter_by(name="Lea").one()
    calendar = add_calendar(db, FUSSBALL, person=lea)
    family_hub.remove_access("Lea")
    client.get("/api/people", headers=login())
    (item,) = client.get("/api/calendars").json()
    assert item["id"] == calendar.id and item["person"] is None
