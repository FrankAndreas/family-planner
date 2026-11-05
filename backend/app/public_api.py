"""What the screens read, without a login (home only: main.py refuses requests from outside)."""

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import config, database, hub, models, occurrences
from .errors import api_error
from .settings_store import get_settings

router = APIRouter()

MAX_DAYS = 62


@router.get("/events")
def events(start: date = Query(alias="from"), end: date = Query(alias="to"), db: Session = Depends(database.get_db)):
    if end <= start:
        raise api_error(status.HTTP_422_UNPROCESSABLE_CONTENT, "bad_range")
    if (end - start).days > MAX_DAYS:
        raise api_error(status.HTTP_422_UNPROCESSABLE_CONTENT, "range_too_long")
    return occurrences.between(db, start, end)


def calendar_color(calendar: models.Calendar, family_color: str) -> str:
    """Its own colour, else its person's colour from the hub, else the family colour."""
    person = calendar.person if calendar.person is not None and calendar.person.is_active else None
    return calendar.color or (person.color if person is not None else None) or family_color


@router.get("/calendars")
def calendars(db: Session = Depends(database.get_db)):
    family_color = get_settings(db).family_color
    rows = (
        db.query(models.Calendar)
        .filter(models.Calendar.enabled.is_(True))
        .order_by(models.Calendar.name, models.Calendar.id)
        .all()
    )
    found = []
    for calendar in rows:
        person = calendar.person if calendar.person is not None and calendar.person.is_active else None
        found.append(
            {
                "id": calendar.id,
                "name": calendar.name,
                "color": calendar_color(calendar, family_color),
                "person": {"id": person.id, "name": person.name} if person is not None else None,
                "visible": calendar.visible,
                "ok": calendar.source.last_error is None,
                "last_success_at": calendar.source.last_success_at,
            }
        )
    return found


@router.get("/config")
def public_config(db: Session = Depends(database.get_db)):
    synced = db.query(func.max(models.Source.last_success_at)).scalar()
    return {"language": config.default_language(), "family_color": get_settings(db).family_color, "synced_at": synced}


@router.get("/hub")
def hub_links():
    """Where browsers log in (the family hub at home) and out (the hub's logout ends it for every family app)."""
    return {"login_url": hub.public_url(), "logout_url": f"{hub.public_url()}/logout"}
