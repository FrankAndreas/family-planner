import logging

import httpx
import pytest

from app import crypto, ics, importer, models
from calendars import FUSSBALL, vcal, vevent

URL = "https://calendar.google.com/calendar/ical/a%40example.com/private-s3cr3t/basic.ics"
ONE = vcal(vevent("one@test", "DTSTART;TZID=Europe/Zurich:20261105T090000", summary="Zahnarzt"))


def add_source(db, url=URL, name="Mama"):
    source = models.Source(kind="google_ical", name=name, credential=crypto.encrypt(url))
    db.add(source)
    db.commit()
    return source


def series_uids(db, source):
    return sorted(s.uid for c in source.calendars for s in c.series)


def test_first_import_creates_calendar_and_series(db, web):
    web.set(URL, FUSSBALL)
    source = add_source(db)
    importer.sync_source(db, source)
    (calendar,) = source.calendars
    assert (calendar.remote_id, calendar.name) == ("ics", "Mama")
    assert series_uids(db, source) == ["fussball@test"]
    assert source.last_success_at is not None and source.last_error is None


def test_unchanged_hash_skips_parse(db, web, monkeypatch):
    web.set(URL, FUSSBALL)
    source = add_source(db)
    importer.sync_source(db, source)
    monkeypatch.setattr(ics, "parse", lambda *a: pytest.fail("parsed an unchanged feed"))
    importer.sync_source(db, source)
    assert source.last_error is None


def test_changed_feed_replaces_events(db, web):
    web.set(URL, FUSSBALL)
    source = add_source(db)
    importer.sync_source(db, source)
    web.set(URL, ONE)
    importer.sync_source(db, source)
    assert series_uids(db, source) == ["one@test"]


def test_html_200_keeps_old_events_and_sets_source_invalid(db, web):
    web.set(URL, FUSSBALL)
    source = add_source(db)
    importer.sync_source(db, source)
    web.set(URL, "<html><body>Anmelden</body></html>")
    importer.sync_source(db, source)
    assert source.last_error == "source_invalid" and series_uids(db, source) == ["fussball@test"]


def test_empty_vcalendar_empties_calendar(db, web):
    web.set(URL, FUSSBALL)
    source = add_source(db)
    importer.sync_source(db, source)
    web.set(URL, vcal())
    importer.sync_source(db, source)
    assert series_uids(db, source) == [] and source.last_error is None


@pytest.mark.parametrize("status,code", [(404, "source_not_found"), (410, "source_not_found"), (401, "source_auth"),
                                         (403, "source_auth"), (500, "source_unreachable")])
def test_http_errors(db, web, status, code):
    web.set(URL, "nope", status=status)
    source = add_source(db)
    importer.sync_source(db, source)
    assert source.last_error == code and source.last_error_at is not None


def test_connect_error_source_unreachable(db, web):
    web.fail(URL)
    source = add_source(db)
    importer.sync_source(db, source)
    assert source.last_error == "source_unreachable"


def test_error_never_contains_secret(db, web, caplog):
    caplog.set_level(logging.DEBUG)
    web.fail(URL, httpx.ConnectError)
    source = add_source(db)
    importer.sync_source(db, source)
    with pytest.raises(importer.SourceError) as error:
        from app import google

        google.check(URL)
    assert "s3cr3t" not in source.last_error and "s3cr3t" not in caplog.text
    assert "s3cr3t" not in str(error.value) and error.value.__cause__ is None and error.value.__suppress_context__


def test_import_is_atomic(db, web):
    web.set(URL, FUSSBALL)
    source = add_source(db)
    importer.sync_source(db, source)
    (calendar,) = source.calendars
    twice = ics.SeriesData("dup@test", "x", models.utcnow(), None)
    with pytest.raises(Exception):
        importer.replace_series(db, calendar, [twice, twice])
    db.expire_all()
    assert series_uids(db, source) == ["fussball@test"]


def test_one_failing_source_others_sync(db, web):
    other = "https://calendar.google.com/calendar/ical/b%40example.com/private-x/basic.ics"
    web.fail(URL)
    web.set(other, ONE)
    broken, good = add_source(db), add_source(db, other, "Papa")
    importer.sync_all(db)
    assert broken.last_error == "source_unreachable" and series_uids(db, good) == ["one@test"]


def test_webcal_scheme(db, web):
    web.set(URL, ONE)
    source = add_source(db, URL.replace("https://", "webcal://"))
    importer.sync_source(db, source)
    assert series_uids(db, source) == ["one@test"]


def test_credential_with_other_key_gives_source_key(db, web):
    source = models.Source(kind="google_ical", name="Mama", credential="v1:AAAA")
    db.add(source)
    db.commit()
    importer.sync_source(db, source)
    assert source.last_error == "source_key"


def test_successful_sync_logs_no_secret(db, web, caplog):
    """httpx logs every request with its full URL at INFO: the secret address must not reach the log."""
    from app import logs

    logs.configure()
    caplog.set_level(logging.INFO)  # the root logger, as in the container; httpx keeps its own level
    web.set(URL, ONE)
    importer.sync_source(db, add_source(db))
    assert "s3cr3t" not in caplog.text
