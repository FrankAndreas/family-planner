"""iCalendar text into the series the planner keeps, and series back into the occurrences of a range.

A series is one UID: the event with its recurrence rules and its moved or cancelled occurrences (RECURRENCE-ID), kept
together as one small VCALENDAR with the time zones it uses, so it can be expanded later exactly as the source meant
it (spec "Sync rules"). Times keep their TZID; floating times count as the planner's zone (config.tz())."""

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import recurring_ical_events
import x_wr_timezone
from icalendar import Calendar

from . import config

logger = logging.getLogger(__name__)


class NotACalendar(Exception):
    """The text isn't an iCalendar (an HTML sign-in page, an empty answer)."""


@dataclass(frozen=True)
class SeriesData:
    uid: str
    ics: str
    # UTC, naive; None for last_end: repeats without an end
    first_start: datetime
    last_end: datetime | None


@dataclass(frozen=True)
class Occurrence:
    uid: str
    # Aware datetimes in the planner's zone, or dates for all-day events (end exclusive, as in iCalendar)
    start: datetime | date
    end: datetime | date
    all_day: bool
    title: str
    location: str
    description: str
    recurrence_id: str | None


def _is_date(value) -> bool:
    return isinstance(value, date) and not isinstance(value, datetime)


def _local(value: datetime | date) -> datetime | date:
    """A value as shown: dates stay dates, floating times are the planner's zone, the rest converted to it."""
    if _is_date(value):
        return value
    if value.tzinfo is None:
        return value.replace(tzinfo=config.tz())
    return value.astimezone(config.tz())


def _utc(value: datetime | date) -> datetime:
    """A start or end as naive UTC, for the range columns. A date is its midnight in the planner's zone."""
    if _is_date(value):
        value = datetime(value.year, value.month, value.day, tzinfo=config.tz())
    elif value.tzinfo is None:
        value = value.replace(tzinfo=config.tz())
    return value.astimezone(UTC).replace(tzinfo=None)


def _end(component, start):
    """DTEND, else DTSTART + DURATION, else one day for a date and no length for a time (RFC 5545 3.6.1)."""
    if "DTEND" in component:
        return component["DTEND"].dt
    if "DURATION" in component:
        return start + component["DURATION"].dt
    return start + timedelta(days=1) if _is_date(start) else start


def _text(component, name: str) -> str:
    value = component.get(name)
    return str(value) if value is not None else ""


def _unbounded(master) -> bool:
    rules = master.get("RRULE")
    if rules is None:
        return False
    for rule in rules if isinstance(rules, list) else [rules]:
        if "COUNT" not in rule and "UNTIL" not in rule:
            return True
    return False


def _read(text: str) -> Calendar:
    if not text.lstrip().upper().startswith("BEGIN:VCALENDAR"):
        raise NotACalendar()
    try:
        calendar = Calendar.from_ical(text)
    except ValueError:
        raise NotACalendar() from None
    # Google feeds may carry the calendar's zone as X-WR-TIMEZONE for times written without one
    return x_wr_timezone.to_standard(calendar)


def _series_calendar(components, timezones: dict) -> Calendar:
    calendar = Calendar()
    calendar.add("prodid", "-//family-planner//series//DE")
    calendar.add("version", "2.0")
    used = set()
    for component in components:
        for name in ("DTSTART", "DTEND", "RECURRENCE-ID", "EXDATE", "RDATE"):
            values = component.get(name)
            for value in values if isinstance(values, list) else [values]:
                if value is not None and "TZID" in getattr(value, "params", {}):
                    used.add(str(value.params["TZID"]))
    for tzid in sorted(used):
        if tzid in timezones:
            calendar.add_component(timezones[tzid])
    for component in components:
        calendar.add_component(component)
    return calendar


def parse(text: str, window: tuple[datetime, datetime]) -> list[SeriesData]:
    """The series of a VCALENDAR that touch the window; NotACalendar when the text isn't one."""
    calendar = _read(text)
    timezones = {str(tz["TZID"]): tz for tz in calendar.walk("VTIMEZONE")}
    groups: dict[str, list] = {}
    for event in calendar.walk("VEVENT"):
        if "UID" in event and "DTSTART" in event:
            groups.setdefault(str(event["UID"]), []).append(event)
    window_start, window_end = (_utc(edge) for edge in window)
    found = []
    for uid, components in groups.items():
        try:
            item = _series(uid, components, timezones, window, window_start, window_end)
        except Exception as error:  # one broken event (a bad date, a bad rule) must not hold up the whole calendar
            logger.warning("Skipped an event that can't be read (%s)", type(error).__name__)
            continue
        if item is not None:
            found.append(item)
    return found


def _series(uid: str, components, timezones: dict, window, window_start: datetime, window_end: datetime):
    series = _series_calendar(components, timezones)
    master = next((c for c in components if "RECURRENCE-ID" not in c), components[0])
    if _unbounded(master):
        first_start, last_end = _utc(master["DTSTART"].dt), None
        # Expanding it once proves the rule can be expanded later, when a screen asks
        recurring_ical_events.of(series).between(*window)
    else:
        spans = [
            (_utc(o["DTSTART"].dt), _utc(_end(o, o["DTSTART"].dt)))
            for o in recurring_ical_events.of(series).all()
        ]
        if not spans:
            return None
        first_start, last_end = min(s for s, _ in spans), max(e for _, e in spans)
    if first_start >= window_end or (last_end is not None and last_end < window_start):
        return None
    return SeriesData(uid, series.to_ical().decode(), first_start, last_end)


def expand(series_ics: str, start: datetime, end: datetime) -> list[Occurrence]:
    """The occurrences of a series that overlap [start, end), cancelled ones left out."""
    calendar = Calendar.from_ical(series_ics)
    found = []
    for event in recurring_ical_events.of(calendar).between(start, end):
        if _text(event, "STATUS").upper() == "CANCELLED":
            continue
        begin = event["DTSTART"].dt
        recurrence = event.get("RECURRENCE-ID")
        found.append(
            Occurrence(
                uid=_text(event, "UID"),
                start=_local(begin),
                end=_local(_end(event, begin)),
                all_day=_is_date(begin),
                title=_text(event, "SUMMARY"),
                location=_text(event, "LOCATION"),
                description=_text(event, "DESCRIPTION"),
                recurrence_id=recurrence.to_ical().decode() if recurrence is not None else None,
            )
        )
    return found
