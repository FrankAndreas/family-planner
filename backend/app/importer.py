"""Importing the sources (spec "Sync rules"): one calendar's events are replaced in one transaction, so no screen
sees a half-updated calendar; a failing source keeps its last good events and an error code, and the others go on.

Nothing here logs or stores a URL, a password or an exception's message: those can carry the secret address."""

import logging
import threading

from sqlalchemy.orm import Session

from . import crypto, models
from .ics import SeriesData

logger = logging.getLogger(__name__)

CODES = {"source_unreachable", "source_auth", "source_not_found", "source_invalid", "source_key"}


class SourceError(Exception):
    """A source failed; `code` says how, and the exception carries nothing else."""

    def __init__(self, code: str):
        assert code in CODES, code
        super().__init__(code)
        self.code = code


def http_error(status: int) -> SourceError:
    if status in (401, 403):
        return SourceError("source_auth")
    if status in (404, 410):
        return SourceError("source_not_found")
    return SourceError("source_unreachable")


def replace_series(db: Session, calendar: models.Calendar, series: list[SeriesData], ctag: str | None = None,
                   hrefs: dict[str, tuple[str, str]] | None = None) -> None:
    """Replace all of a calendar's series at once; on any failure nothing changes. hrefs: uid -> (href, etag)."""
    try:
        db.query(models.Series).filter(models.Series.calendar_id == calendar.id).delete()
        for item in series:
            href, etag = (hrefs or {}).get(item.uid, (None, None))
            db.add(
                models.Series(
                    calendar_id=calendar.id,
                    uid=item.uid,
                    ics=item.ics,
                    first_start=item.first_start,
                    last_end=item.last_end,
                    href=href,
                    etag=etag,
                )
            )
        if ctag is not None:
            calendar.ctag = ctag
        db.commit()
    except Exception:
        db.rollback()
        raise


def credential(source: models.Source) -> str:
    try:
        return crypto.decrypt(source.credential)
    except crypto.CannotDecrypt:
        raise SourceError("source_key") from None


_locks: dict[int, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock(source_id: int) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(source_id, threading.Lock())


def sync_source(db: Session, source: models.Source, force: bool = False) -> None:
    """Import one source now; its error code (or none) is stored on it. One sync per source at a time: a manual
    "Jetzt aktualisieren" during the scheduler's sync waits for it, then reads what that sync left."""
    with _lock(source.id):
        db.refresh(source)
        _sync_source(db, source, force)


def _sync_source(db: Session, source: models.Source, force: bool) -> None:
    from . import caldav, google

    module = google if source.kind == "google_ical" else caldav
    try:
        module.sync(db, source, force)
    except SourceError as error:
        code = error.code
    except Exception as error:  # a bug or a feed we can't read: say which kind, never the message
        db.rollback()
        logger.error("Source %s: unexpected %s", source.id, type(error).__name__)
        code = "source_invalid"
    else:
        source.last_success_at, source.last_error, source.last_error_at = models.utcnow(), None, None
        db.commit()
        return
    logger.warning("Source %s: %s", source.id, code)
    source.last_error, source.last_error_at = code, models.utcnow()
    db.commit()


def sync_all(db: Session, force: bool = False) -> None:
    for source in db.query(models.Source).order_by(models.Source.id).all():
        sync_source(db, source, force)
