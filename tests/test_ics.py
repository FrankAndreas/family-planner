from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app import ics
from calendars import FUSSBALL, vcal, vevent

ZH = ZoneInfo("Europe/Zurich")
WINDOW = (datetime(2026, 8, 5, tzinfo=ZH), datetime(2027, 12, 5, tzinfo=ZH))
NOV = (datetime(2026, 11, 1, tzinfo=ZH), datetime(2026, 12, 1, tzinfo=ZH))


def occurrences(text, between=NOV):
    found = []
    for series in ics.parse(text, WINDOW):
        found += ics.expand(series.ics, *between)
    return sorted(found, key=lambda o: str(o.start))


def test_weekly_with_exdate_and_moved_occurrence():
    starts = [o.start for o in occurrences(FUSSBALL)]
    assert starts == [
        datetime(2026, 11, 5, 16, 0, tzinfo=ZH),
        datetime(2026, 11, 19, 17, 30, tzinfo=ZH),
        datetime(2026, 11, 26, 16, 0, tzinfo=ZH),
    ]
    assert [o.title for o in occurrences(FUSSBALL)][1] == "Fussball (später)"


def test_master_and_override_are_one_series():
    assert [s.uid for s in ics.parse(FUSSBALL, WINDOW)] == ["fussball@test"]


def test_cancelled_override_disappears():
    text = vcal(
        vevent("yoga@test", "DTSTART;TZID=Europe/Zurich:20261104T090000", "DTEND;TZID=Europe/Zurich:20261104T100000",
               "RRULE:FREQ=WEEKLY;COUNT=3"),
        vevent("yoga@test", "RECURRENCE-ID;TZID=Europe/Zurich:20261111T090000",
               "DTSTART;TZID=Europe/Zurich:20261111T090000", "DTEND;TZID=Europe/Zurich:20261111T100000",
               "STATUS:CANCELLED"),
    )
    assert [o.start.day for o in occurrences(text)] == [4, 18]


def test_cancelled_single_event_disappears():
    text = vcal(vevent("x@test", "DTSTART;TZID=Europe/Zurich:20261104T090000", "STATUS:CANCELLED"))
    assert occurrences(text) == []


def test_all_day_over_dst_change():
    text = vcal(vevent("ferien@test", "DTSTART;VALUE=DATE:20261024", "DTEND;VALUE=DATE:20261026"))
    (o,) = occurrences(text, (datetime(2026, 10, 19, tzinfo=ZH), datetime(2026, 11, 2, tzinfo=ZH)))
    assert (o.start, o.end, o.all_day) == (date(2026, 10, 24), date(2026, 10, 26), True)


def test_missing_dtend_and_duration():
    text = vcal(
        vevent("dur@test", "DTSTART;TZID=Europe/Zurich:20261105T080000", "DURATION:PT45M"),
        vevent("day@test", "DTSTART;VALUE=DATE:20261106"),
        vevent("point@test", "DTSTART;TZID=Europe/Zurich:20261107T100000"),
    )
    by_uid = {o.uid: o for o in occurrences(text)}
    assert by_uid["dur@test"].end - by_uid["dur@test"].start == timedelta(minutes=45)
    assert by_uid["day@test"].end == date(2026, 11, 7)
    assert by_uid["point@test"].end == by_uid["point@test"].start


def test_utc_times_shown_in_zurich():
    (o,) = occurrences(vcal(vevent("utc@test", "DTSTART:20261105T070000Z", "DTEND:20261105T080000Z")))
    assert o.start == datetime(2026, 11, 5, 8, 0, tzinfo=ZH) and o.start.tzinfo is not None


def test_floating_time_is_zurich():
    (o,) = occurrences(vcal(vevent("float@test", "DTSTART:20261105T090000", "DTEND:20261105T100000")))
    assert o.start == datetime(2026, 11, 5, 9, 0, tzinfo=ZH)


def test_windows_tzid_name():
    text = vcal(vevent("win@test", "DTSTART;TZID=W. Europe Standard Time:20261105T090000",
                       "DTEND;TZID=W. Europe Standard Time:20261105T100000"), timezones="")
    (o,) = occurrences(text)
    assert o.start == datetime(2026, 11, 5, 9, 0, tzinfo=ZH)


def test_unbounded_rrule_last_end_none():
    (series,) = ics.parse(FUSSBALL, WINDOW)
    assert series.last_end is None
    assert series.first_start == datetime(2026, 10, 1, 14, 0)  # UTC, naive


def test_count_rrule_has_last_end():
    text = vcal(vevent("c@test", "DTSTART;TZID=Europe/Zurich:20261104T090000",
                       "DTEND;TZID=Europe/Zurich:20261104T100000", "RRULE:FREQ=WEEKLY;COUNT=3"))
    (series,) = ics.parse(text, WINDOW)
    assert series.last_end == datetime(2026, 11, 18, 9, 0)  # 10:00 Zurich in UTC


def test_series_outside_window_dropped():
    text = vcal(
        vevent("old@test", "DTSTART;TZID=Europe/Zurich:20250105T090000", "DTEND;TZID=Europe/Zurich:20250105T100000"),
        vevent("far@test", "DTSTART;TZID=Europe/Zurich:20290105T090000", "DTEND;TZID=Europe/Zurich:20290105T100000"),
        vevent("old-weekly@test", "DTSTART;TZID=Europe/Zurich:20200105T090000",
               "RRULE:FREQ=WEEKLY;UNTIL=20210101T000000Z"),
        vevent("birthday@test", "DTSTART;VALUE=DATE:20100314", "RRULE:FREQ=YEARLY"),
        vevent("now@test", "DTSTART;TZID=Europe/Zurich:20261105T090000"),
    )
    assert sorted(s.uid for s in ics.parse(text, WINDOW)) == ["birthday@test", "now@test"]


def test_series_text_keeps_only_used_timezones():
    (series,) = ics.parse(FUSSBALL, WINDOW)
    assert "TZID:Europe/Zurich" in series.ics and series.ics.count("BEGIN:VEVENT") == 2


def test_text_fields():
    text = vcal(vevent("t@test", "DTSTART;TZID=Europe/Zurich:20261105T190000", "LOCATION:Schulhaus",
                       "DESCRIPTION:Zimmer 3\\, 1. Stock", summary="Elternabend"))
    (o,) = occurrences(text)
    assert (o.title, o.location, o.description) == ("Elternabend", "Schulhaus", "Zimmer 3, 1. Stock")


@pytest.mark.parametrize("body", ["<html><body>Sign in</body></html>", "", "   \n"])
def test_not_a_calendar_raises(body):
    with pytest.raises(ics.NotACalendar):
        ics.parse(body, WINDOW)


def test_empty_vcalendar_gives_empty_list():
    assert ics.parse(vcal(), WINDOW) == []


def test_one_broken_event_skipped_others_imported():
    text = vcal(
        vevent("bad-start@test", "DTSTART:2026111"),
        vevent("bad-rule@test", "DTSTART;TZID=Europe/Zurich:20261105T090000", "RRULE:FREQ=FOO;COUNT=3"),
        vevent("bad-open-rule@test", "DTSTART;TZID=Europe/Zurich:20261105T090000", "RRULE:FREQ=FOO"),
        vevent("good@test", "DTSTART;TZID=Europe/Zurich:20261105T090000", summary="Gut"),
    )
    assert [s.uid for s in ics.parse(text, WINDOW)] == ["good@test"]
