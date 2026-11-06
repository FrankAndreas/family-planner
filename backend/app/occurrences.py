"""What the screens show for a range: every visible calendar's series expanded, one entry per event even when it is
in several calendars (an invite: same UID, same start), listing all of them so the screen shows each one's colour."""

import logging
from datetime import UTC, date, datetime, time

from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import config, ics, models

logger = logging.getLogger(__name__)


def _iso(value) -> str:
    return value.isoformat()


def between(db: Session, start: date, end: date) -> list[dict]:
    zone = config.tz()
    begin, finish = datetime.combine(start, time(), zone), datetime.combine(end, time(), zone)
    begin_utc, finish_utc = (moment.astimezone(UTC).replace(tzinfo=None) for moment in (begin, finish))
    rows = (
        db.query(models.Series)
        .join(models.Calendar)
        .filter(
            models.Calendar.visible.is_(True),
            models.Calendar.enabled.is_(True),
            models.Series.first_start < finish_utc,
            or_(models.Series.last_end.is_(None), models.Series.last_end >= begin_utc),
        )
        .all()
    )
    merged: dict[str, dict] = {}
    for row in rows:
        try:
            expanded = ics.expand(row.ics, begin, finish)
        except Exception as error:  # one series that can't be expanded must not leave the wall empty
            logger.warning("Calendar %s: skipped a series that can't be expanded (%s)", row.calendar_id, type(error).__name__)
            continue
        for occurrence in expanded:
            key = f"{occurrence.uid}|{_iso(occurrence.start)}"
            entry = merged.get(key)
            if entry is None:
                merged[key] = {
                    "key": key,
                    "uid": occurrence.uid,
                    "title": occurrence.title,
                    "start": _iso(occurrence.start),
                    "end": _iso(occurrence.end),
                    "all_day": occurrence.all_day,
                    "location": occurrence.location,
                    "description": occurrence.description,
                    "calendar_ids": [row.calendar_id],
                }
            elif row.calendar_id not in entry["calendar_ids"]:
                entry["calendar_ids"] = sorted(entry["calendar_ids"] + [row.calendar_id])

    def order(entry: dict):
        # All-day entries (dates) before the timed ones of their day, then by start
        start_value = entry["start"]
        moment = (datetime.combine(date.fromisoformat(start_value), time(), zone) if entry["all_day"]
                  else datetime.fromisoformat(start_value))
        return (moment, not entry["all_day"], entry["title"])

    return sorted(merged.values(), key=order)
