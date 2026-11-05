import json
import logging

import httpx

from app import caldav, crypto, importer, models
from calendars import FUSSBALL, vcal, vevent
from fake_sources import HOME

APPLE_ID, PASSWORD = "familie@example.com", "abcd-efgh-ijkl-mnop"
ONE = vcal(vevent("one@test", "DTSTART;TZID=Europe/Zurich:20261105T090000", summary="Zahnarzt"))


def add_source(db, password=PASSWORD):
    source = models.Source(kind="icloud_caldav", name="iCloud",
                           credential=crypto.encrypt(json.dumps({"apple_id": APPLE_ID, "password": password})))
    db.add(source)
    db.commit()
    return source


def enable_all(db, source):
    for calendar in source.calendars:
        calendar.enabled = True
    db.commit()


def test_discover_follows_shard_and_lists_event_calendars(web):
    web.dav.calendar("home", "Familie")
    web.dav.calendar("work", "Arbeit")
    web.dav.calendar("reminders", "Erinnerungen", component="VTODO")
    base, calendars = caldav.discover(APPLE_ID, PASSWORD)
    assert base == HOME
    assert sorted(c.name for c in calendars) == ["Arbeit", "Familie"]
    assert all(c.href.startswith("https://p42-caldav.icloud.com/") and c.ctag == "1" for c in calendars)


def test_first_sync_adds_calendars_disabled_and_imports_nothing(db, web):
    web.dav.calendar("home", "Familie", {f"{HOME}home/a.ics": FUSSBALL})
    source = add_source(db)
    importer.sync_source(db, source)
    assert source.base_url == HOME and source.last_error is None
    (calendar,) = source.calendars
    assert (calendar.name, calendar.enabled, calendar.series) == ("Familie", False, [])
    assert web.dav.reports == []


def test_enabled_calendar_imported_with_href_and_etag(db, web):
    href = web.dav.calendar("home", "Familie", {f"{HOME}home/a.ics": FUSSBALL})
    source = add_source(db)
    importer.sync_source(db, source)
    enable_all(db, source)
    importer.sync_source(db, source)
    (series,) = source.calendars[0].series
    assert (series.uid, series.href, series.etag) == ("fussball@test", f"{HOME}home/a.ics", f'"e-{len(FUSSBALL)}"')
    assert web.dav.reports == [href]


def test_unchanged_ctag_skips_report(db, web):
    web.dav.calendar("home", "Familie", {f"{HOME}home/a.ics": FUSSBALL})
    source = add_source(db)
    importer.sync_source(db, source)
    enable_all(db, source)
    importer.sync_source(db, source)
    importer.sync_source(db, source)
    assert len(web.dav.reports) == 1


def test_changed_ctag_replaces_events(db, web):
    href = web.dav.calendar("home", "Familie", {f"{HOME}home/a.ics": FUSSBALL})
    source = add_source(db)
    importer.sync_source(db, source)
    enable_all(db, source)
    importer.sync_source(db, source)
    web.dav.change(href, {f"{HOME}home/b.ics": ONE})
    importer.sync_source(db, source)
    assert [s.uid for s in source.calendars[0].series] == ["one@test"]


def test_new_remote_calendar_added_disabled_removed_one_deleted(db, web):
    old = web.dav.calendar("home", "Familie")
    source = add_source(db)
    importer.sync_source(db, source)
    del web.dav.calendars[old]
    web.dav.calendar("school", "Schule")
    importer.sync_source(db, source)
    db.expire_all()
    assert [(c.name, c.enabled) for c in source.calendars] == [("Schule", False)]


def test_401_source_auth_with_normal_password(db, web):
    source = add_source(db, password="mein-apple-passwort")
    importer.sync_source(db, source)
    assert source.last_error == "source_auth"


def test_unreachable(db, web, monkeypatch):
    def down(request):
        raise httpx.ConnectError(f"cannot connect to {request.url}", request=request)

    monkeypatch.setattr(web.dav, "handler", down)
    source = add_source(db)
    importer.sync_source(db, source)
    assert source.last_error == "source_unreachable"


def test_password_never_in_error_or_log(db, web, caplog):
    caplog.set_level(logging.DEBUG)
    source = add_source(db, password="geheim-1234")
    importer.sync_source(db, source)
    assert "geheim-1234" not in caplog.text and "geheim-1234" not in (source.last_error or "")
