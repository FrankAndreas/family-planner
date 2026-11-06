from calendars import FUSSBALL, vcal, vevent
from helpers import add_calendar, add_person

WEEK = {"from": "2026-11-16", "to": "2026-11-23"}
INVITE = vcal(vevent("elternabend@test", "DTSTART;TZID=Europe/Zurich:20261119T190000",
                     "DTEND;TZID=Europe/Zurich:20261119T210000", summary="Elternabend"))


def events(client, **params):
    response = client.get("/api/events", params=params or WEEK)
    assert response.status_code == 200, response.text
    return response.json()


def test_week_range_returns_expanded_occurrences(client, db):
    calendar = add_calendar(db, FUSSBALL)
    (event,) = events(client)
    assert event["title"] == "Fussball (später)"
    assert (event["start"], event["end"]) == ("2026-11-19T17:30:00+01:00", "2026-11-19T19:00:00+01:00")
    assert event["all_day"] is False and event["calendar_ids"] == [calendar.id]
    assert event["key"] == "fussball@test|2026-11-19T17:30:00+01:00"


def test_needs_no_login(client, db):
    add_calendar(db, FUSSBALL)
    assert client.get("/api/events", params=WEEK).status_code == 200
    assert client.get("/api/calendars").status_code == 200


def test_sorted_by_start(client, db):
    add_calendar(db, FUSSBALL)
    add_calendar(db, INVITE, name="Papa")
    assert [e["title"] for e in events(client, **{"from": "2026-11-01", "to": "2026-12-01"})] == [
        "Fussball", "Fussball (später)", "Elternabend", "Fussball"]


def test_hidden_and_disabled_calendars_left_out(client, db):
    add_calendar(db, FUSSBALL, visible=False)
    add_calendar(db, INVITE, name="Papa", enabled=False)
    assert events(client) == []


def test_shared_invite_once_with_both_calendars(client, db):
    mama, papa = add_calendar(db, INVITE), add_calendar(db, INVITE, name="Papa")
    (event,) = events(client)
    assert event["calendar_ids"] == sorted([mama.id, papa.id])


def test_all_day_is_date_string(client, db):
    add_calendar(db, vcal(vevent("f@test", "DTSTART;VALUE=DATE:20261120", "DTEND;VALUE=DATE:20261122")))
    (event,) = events(client)
    assert (event["start"], event["end"], event["all_day"]) == ("2026-11-20", "2026-11-22", True)


def test_event_started_before_range_still_shown(client, db):
    add_calendar(db, vcal(vevent("lager@test", "DTSTART;VALUE=DATE:20261110", "DTEND;VALUE=DATE:20261118")))
    assert len(events(client)) == 1


def test_range_over_62_days_422(client):
    response = client.get("/api/events", params={"from": "2026-11-01", "to": "2027-01-03"})
    assert response.status_code == 422 and response.json()["detail"] == "range_too_long"


def test_range_backwards_422(client):
    assert client.get("/api/events", params={"from": "2026-11-10", "to": "2026-11-01"}).status_code == 422


def test_calendar_color_precedence(client, db):
    lea = add_person(db, "Lea", color="#16a34a")
    own = add_calendar(db, INVITE, name="Eigene", person=lea, color="#000000")
    persons = add_calendar(db, INVITE, name="Lea", person=lea)
    family = add_calendar(db, INVITE, name="Familie")
    colors = {c["id"]: c["color"] for c in client.get("/api/calendars").json()}
    assert colors == {own.id: "#000000", persons.id: "#16a34a", family.id: "#7c3aed"}


def test_inactive_person_counts_as_family(client, db):
    gone = add_person(db, "Gone", color="#16a34a", active=False)
    calendar = add_calendar(db, INVITE, person=gone)
    (item,) = client.get("/api/calendars").json()
    assert item["id"] == calendar.id and item["person"] is None and item["color"] == "#7c3aed"


def test_calendars_hide_error_details(client, db):
    calendar = add_calendar(db, INVITE)
    calendar.source.last_error = "source_auth"
    db.commit()
    (item,) = client.get("/api/calendars").json()
    assert item["ok"] is False and "last_error" not in item and "source" not in item
    assert set(item) == {"id", "name", "color", "person", "visible", "ok", "last_success_at"}


def test_config(client, db):
    add_calendar(db, INVITE)
    body = client.get("/api/config").json()
    assert body["language"] == "de" and body["family_color"] == "#7c3aed" and body["synced_at"]


def test_hub_links(client):
    body = client.get("/api/hub").json()
    assert body["login_url"] and body["logout_url"].endswith("/logout")


def test_a_bad_stored_series_does_not_break_the_wall(client, db):
    from app import models

    calendar = add_calendar(db, INVITE)
    broken = ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:bad@test\r\n"
              "DTSTART:20261101T090000Z\r\nRRULE:FREQ=FOO\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
    db.add(models.Series(calendar_id=calendar.id, uid="bad@test", ics=broken, first_start=models.utcnow().replace(year=2026, month=11, day=1)))
    db.commit()
    assert [e["title"] for e in events(client)] == ["Elternabend"]


def test_calendars_and_config_times_carry_utc(client, db):
    from calendars import FUSSBALL
    from helpers import add_calendar

    add_calendar(db, FUSSBALL)
    db.commit()
    [calendar] = client.get("/api/calendars").json()
    assert calendar["last_success_at"].endswith("+00:00")
    assert client.get("/api/config").json()["synced_at"].endswith("+00:00")
