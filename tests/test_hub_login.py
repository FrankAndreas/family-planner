import pytest
from fastapi import Depends

import fake_hub
from app import auth, models
from app.main import app
from helpers import ADMIN, bearer, login


# A parents-only route until the settings API brings real ones (removed in Task 9)
@app.get("/api/_test/parent")
def _parent(person: models.Person = Depends(auth.require_parent)):
    return {"id": person.id, "name": person.name}


@app.post("/api/_test/parent")
def _parent_change(person: models.Person = Depends(auth.require_parent)):
    return {"ok": True}


def code(response):
    return response.json()["detail"]


def test_no_login_401_not_logged_in(client):
    response = client.get("/api/_test/parent")
    assert response.status_code == 401 and code(response) == "not_logged_in"


def test_unknown_token_401(client):
    response = client.get("/api/_test/parent", headers=bearer("tok-nobody"))
    assert response.status_code == 401


def test_child_403_parents_only(client, family_hub):
    family_hub.add("Lea", "CHILD")
    response = client.get("/api/_test/parent", headers=login("Lea"))
    assert response.status_code == 403 and code(response) == "parents_only"


def test_parent_ok_and_person_row_has_hub_color(client, family_hub, db):
    family_hub.add("Mama", "PARENT", color="#e11d48")
    response = client.get("/api/_test/parent", headers=login("Mama"))
    assert response.status_code == 200 and response.json()["name"] == "Mama"
    row = db.query(models.Person).filter_by(name="Mama").one()
    assert row.color == "#e11d48" and row.is_active and row.hub_id is not None


def test_no_access_403(client, family_hub):
    family_hub.add("Gast", "PARENT", access=False)
    response = client.get("/api/_test/parent", headers=login("Gast"))
    assert response.status_code == 403 and code(response) == "no_access"


def test_hub_down_503_hub_unavailable(client, family_hub):
    family_hub.down = True
    response = client.get("/api/_test/parent", headers=login())
    assert response.status_code == 503 and code(response) == "hub_unavailable"


def test_cookie_change_without_header_403_csrf(client):
    client.cookies.set("hub_session", fake_hub.token(ADMIN))
    response = client.post("/api/_test/parent")
    assert response.status_code == 403 and code(response) == "csrf"


def test_cookie_change_with_header_x_requested_with_planner_ok(client):
    client.cookies.set("hub_session", fake_hub.token(ADMIN))
    response = client.post("/api/_test/parent", headers={"X-Requested-With": "planner"})
    assert response.status_code == 200


def test_cookie_read_needs_no_header(client):
    client.cookies.set("hub_session", fake_hub.token(ADMIN))
    assert client.get("/api/_test/parent").status_code == 200


def test_person_dropped_by_hub_becomes_inactive(client, family_hub, db):
    family_hub.add("Noah", "CHILD")
    client.get("/api/_test/parent", headers=login())
    family_hub.remove_access("Noah")
    client.get("/api/_test/parent", headers=login())
    assert db.query(models.Person).filter_by(name="Noah").one().is_active is False


@pytest.mark.parametrize("change", ["rename", "role"])
def test_hub_changes_follow(client, family_hub, db, change):
    family_hub.add("Lea", "CHILD")
    client.get("/api/_test/parent", headers=login())
    if change == "rename":
        family_hub.rename("Lea", "Lea M.")
        client.get("/api/_test/parent", headers=login())
        assert db.query(models.Person).filter_by(name="Lea M.").count() == 1
    else:
        family_hub.set_role("Lea", "PARENT")
        assert client.get("/api/_test/parent", headers=login("Lea")).status_code == 200
