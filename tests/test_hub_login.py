import threading
import time

import pytest

import fake_hub
from app import database, hub, hub_people, models
from helpers import ADMIN, bearer, login

COLOR = {"family_color": "#112233"}


def code(response):
    return response.json()["detail"]


def test_no_login_401_not_logged_in(client):
    response = client.get("/api/sources")
    assert response.status_code == 401 and code(response) == "not_logged_in"


def test_unknown_token_401(client):
    response = client.get("/api/sources", headers=bearer("tok-nobody"))
    assert response.status_code == 401


def test_child_403_parents_only(client, family_hub):
    family_hub.add("Lea", "CHILD")
    response = client.get("/api/sources", headers=login("Lea"))
    assert response.status_code == 403 and code(response) == "parents_only"


def test_parent_ok_and_person_row_has_hub_color(client, family_hub, db):
    family_hub.add("Mama", "PARENT", color="#e11d48")
    response = client.get("/api/me", headers=login("Mama"))
    assert response.status_code == 200 and response.json()["name"] == "Mama"
    row = db.query(models.Person).filter_by(name="Mama").one()
    assert row.color == "#e11d48" and row.is_active and row.hub_id is not None


def test_no_access_403(client, family_hub):
    family_hub.add("Gast", "PARENT", access=False)
    response = client.get("/api/sources", headers=login("Gast"))
    assert response.status_code == 403 and code(response) == "no_access"


def test_hub_down_503_hub_unavailable(client, family_hub):
    family_hub.down = True
    response = client.get("/api/sources", headers=login())
    assert response.status_code == 503 and code(response) == "hub_unavailable"


def test_cookie_change_without_header_403_csrf(client):
    client.cookies.set("hub_session", fake_hub.token(ADMIN))
    response = client.patch("/api/settings", json=COLOR)
    assert response.status_code == 403 and code(response) == "csrf"


def test_cookie_change_with_header_x_requested_with_planner_ok(client):
    client.cookies.set("hub_session", fake_hub.token(ADMIN))
    response = client.patch("/api/settings", json=COLOR, headers={"X-Requested-With": "planner"})
    assert response.status_code == 200


def test_cookie_read_needs_no_header(client):
    client.cookies.set("hub_session", fake_hub.token(ADMIN))
    assert client.get("/api/sources").status_code == 200


def test_person_dropped_by_hub_becomes_inactive(client, family_hub, db):
    family_hub.add("Noah", "CHILD")
    client.get("/api/sources", headers=login())
    family_hub.remove_access("Noah")
    client.get("/api/sources", headers=login())
    assert db.query(models.Person).filter_by(name="Noah").one().is_active is False


@pytest.mark.parametrize("change", ["rename", "role"])
def test_hub_changes_follow(client, family_hub, db, change):
    family_hub.add("Lea", "CHILD")
    client.get("/api/sources", headers=login())
    if change == "rename":
        family_hub.rename("Lea", "Lea M.")
        client.get("/api/sources", headers=login())
        assert db.query(models.Person).filter_by(name="Lea M.").count() == 1
    else:
        family_hub.set_role("Lea", "PARENT")
        assert client.get("/api/sources", headers=login("Lea")).status_code == 200


def test_unknown_hub_role_counts_as_child(client, family_hub):
    family_hub.add("Gast", role="GUEST")
    response = client.get("/api/sources", headers=login("Gast"))
    assert response.status_code == 403 and response.json()["detail"] == "parents_only"
    assert "Gast" in [p["name"] for p in client.get("/api/people", headers=login()).json()]


# App integration review 2026-11-07: someone who only opens the planner never opens the hub, which renews a login. In
# its last week the hub says so, and the settings page sends the browser through the hub once (frontend api.ts)
def test_a_login_in_its_last_week_is_renewed_through_the_hub(client, family_hub):
    assert "X-Hub-Renew" not in client.get("/api/me", headers=login()).headers
    family_hub.renewing.add(ADMIN)
    hub.client.forget()
    assert client.get("/api/me", headers=login()).headers["X-Hub-Renew"] == "1"


# App integration review 2026-11-07 (as in the budget app): the first requests of someone given access come together;
# the one that finds another refreshing waits for it instead of answering "no access"
def test_a_new_persons_requests_at_the_same_moment(client, family_hub):
    family_hub.add("Mama", "PARENT")
    with hub_people._lock:
        hub_people._running = True

    def the_other_request():
        time.sleep(0.2)
        with database.SessionLocal() as db:
            hub_people._apply(db, hub.client.fetch_people(hub.Login(fake_hub.token("Mama"))))
        with hub_people._lock:
            hub_people._running = False
            hub_people._lock.notify_all()

    other = threading.Thread(target=the_other_request)
    other.start()
    try:
        assert client.get("/api/me", headers=login("Mama")).status_code == 200
    finally:
        other.join()
