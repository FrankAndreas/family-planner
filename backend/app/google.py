"""Google calendars through their secret iCal address (spec "Calendar integration"): downloaded on every sync, and
parsed only when the feed changed. The address is a password: it never reaches a log or an error."""

import hashlib

import httpx
from sqlalchemy.orm import Session

from . import config, fetch, ics, models
from .importer import SourceError, credential, http_error, replace_series

REMOTE_ID = "ics"


def address(url: str) -> str:
    url = url.strip()
    return "https://" + url[len("webcal://"):] if url.lower().startswith("webcal://") else url


def download(url: str) -> str:
    try:
        with fetch.client() as client:
            response = client.get(address(url))
    except httpx.InvalidURL:  # not an httpx.HTTPError: an address that isn't one
        raise SourceError("source_invalid") from None
    except (httpx.HTTPError, ValueError):
        raise SourceError("source_unreachable") from None
    if response.status_code >= 400:
        raise http_error(response.status_code) from None
    return response.text


def _parse(text: str) -> list[ics.SeriesData]:
    try:
        return ics.parse(text, config.window())
    except ics.NotACalendar:
        raise SourceError("source_invalid") from None


def check(url: str) -> list[ics.SeriesData]:
    """Try an address before it is saved."""
    return _parse(download(url))


def sync(db: Session, source: models.Source, force: bool = False) -> None:
    text = download(credential(source))
    # With the window's first day in it, an unchanged feed is still read once a day as the window moves on
    digest = hashlib.sha256(f"{config.window()[0].date()}\n{text}".encode()).hexdigest()
    calendar = next((c for c in source.calendars if c.remote_id == REMOTE_ID), None)
    if calendar is not None and digest == source.content_hash and not force:
        return
    series = _parse(text)
    if calendar is None:
        calendar = models.Calendar(source_id=source.id, remote_id=REMOTE_ID, name=source.name)
        db.add(calendar)
        db.flush()
    replace_series(db, calendar, series)
    source.content_hash = digest
    db.commit()
