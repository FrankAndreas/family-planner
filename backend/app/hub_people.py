"""The planner's people come from the family hub, as in the sibling apps.

Everyone the hub lets use the planner gets a row here, linked by `hub_id`; name, role, colour and language follow the
hub. A row the hub no longer lists is hidden (`is_active` False). The wall has no login, so the list is refreshed with
the login of whoever uses the settings."""

import threading
import time

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import hub, models

REFRESH_SECONDS = 60
# After the hub failed to answer, the next try waits this long (requests go on with the people kept here)
BACKOFF_SECONDS = 10

# A condition, so a request can wait for a refresh that another one is running (wait_for_running)
_lock = threading.Condition()
# When the last refresh finished (time.monotonic()); None: not yet. Not 0.0: monotonic counts from the machine's start,
# so on a machine up for less than a minute 0.0 would look like a refresh a moment ago
_last: float | None = None
_running = False


def forget() -> None:
    """Refresh at the next chance (tests)."""
    global _last
    _last = None


def refresh(db: Session, login: hub.Login, force: bool = False) -> None:
    """Take the planner's people from the hub, at most every REFRESH_SECONDS unless forced. When the hub answers no one
    (the asking person has no access), nothing changes. One refresh at a time: other requests meanwhile go on with the
    people kept here instead of waiting for a slow hub."""
    global _last, _running
    with _lock:
        if _running or (not force and _last is not None and time.monotonic() - _last < REFRESH_SECONDS):
            return
        _running = True
    try:
        try:
            people = hub.client.fetch_people(login)
        except hub.HubUnavailable:
            with _lock:
                _last = time.monotonic() - REFRESH_SECONDS + BACKOFF_SECONDS
            raise
        if not people:
            return
        with _lock:
            try:
                _apply(db, people)
            except IntegrityError:
                # Another process got there first: start from what it wrote
                db.rollback()
                _apply(db, people)
            _last = time.monotonic()
    finally:
        with _lock:
            _running = False
            _lock.notify_all()


def wait_for_running(timeout: float) -> None:
    """Until a refresh another request is running has finished, at most `timeout` seconds. Only for a person the app
    doesn't know yet: their first requests often come together, and the one that didn't refresh would answer "no
    access" a moment before the other one adds them (app integration review 2026-11-07, as in the budget app).
    Everyone else goes on without waiting (one refresh at a time)."""
    with _lock:
        _lock.wait_for(lambda: not _running, timeout)


def _apply(db: Session, people: list[hub.HubPerson]) -> None:
    rows = {row.hub_id: row for row in db.query(models.Person).all()}
    listed = set()
    for person in people:
        row = rows.get(person.id)
        if row is None:
            row = models.Person(hub_id=person.id)
            db.add(row)
        row.name = person.name
        row.role = models.Role.from_hub(person.role)
        row.color = person.color
        row.language = person.language if person.language in ("de", "en") else None
        row.is_active = True
        listed.add(person.id)
    for hub_id, row in rows.items():
        if hub_id not in listed:
            row.is_active = False
    db.commit()
