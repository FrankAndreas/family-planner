"""The parents' settings (spec "Settings"): calendar sources and their credentials, which calendar is whose, colours.

A credential is tried before it is saved and never sent back: responses say only that one is stored."""

import json
import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import auth, caldav, crypto, database, google, importer, models
from .errors import api_error
from .settings_store import get_settings

router = APIRouter()

COLOR = re.compile(r"^#[0-9a-f]{6}$")
Name = Annotated[str, Field(min_length=1, max_length=100)]


class GoogleIn(BaseModel):
    kind: Literal["google_ical"]
    name: Name
    url: Annotated[str, Field(min_length=1, max_length=2000)]


class ICloudIn(BaseModel):
    kind: Literal["icloud_caldav"]
    name: Name
    apple_id: Annotated[str, Field(min_length=3, max_length=200)]
    password: Annotated[str, Field(min_length=1, max_length=200)]


class SourcePatch(BaseModel):
    name: Name | None = None
    url: Annotated[str, Field(min_length=1, max_length=2000)] | None = None
    apple_id: Annotated[str, Field(min_length=3, max_length=200)] | None = None
    password: Annotated[str, Field(min_length=1, max_length=200)] | None = None


class CalendarPatch(BaseModel):
    person_id: int | None = None
    color: str | None = None
    visible: bool | None = None
    enabled: bool | None = None


class SettingsPatch(BaseModel):
    family_color: str


def _source_out(source: models.Source) -> dict:
    return {
        "id": source.id,
        "kind": source.kind,
        "name": source.name,
        "has_credential": True,
        "last_success_at": source.last_success_at,
        "last_error": source.last_error,
        "calendars": [
            {"id": c.id, "name": c.name, "enabled": c.enabled, "visible": c.visible, "person_id": c.person_id,
             "color": c.color}
            for c in sorted(source.calendars, key=lambda c: (c.name, c.id))
        ],
    }


def _source(db: Session, source_id: int) -> models.Source:
    source = db.get(models.Source, source_id)
    if source is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "not_found")
    return source


def _color(value: str) -> str:
    value = value.strip().lower()
    if not COLOR.match(value):
        raise api_error(status.HTTP_422_UNPROCESSABLE_CONTENT, "bad_color")
    return value


def _tried(check, *args):
    """Run a source check; its failure becomes a 422 with the error code, nothing saved."""
    try:
        return check(*args)
    except importer.SourceError as error:
        raise api_error(status.HTTP_422_UNPROCESSABLE_CONTENT, error.code) from None


@router.get("/me")
def me(person: models.Person = Depends(auth.get_current_user)):
    return {"id": person.id, "name": person.name, "role": person.role.value, "language": person.language}


@router.get("/sources", dependencies=[Depends(auth.require_parent)])
def sources(db: Session = Depends(database.get_db)):
    return [_source_out(s) for s in db.query(models.Source).order_by(models.Source.name, models.Source.id).all()]


def _add(db: Session, body: GoogleIn | ICloudIn) -> dict:
    if isinstance(body, GoogleIn):
        _tried(google.check, body.url)
        source = models.Source(kind=body.kind, name=body.name, credential=crypto.encrypt(google.address(body.url)))
        db.add(source)
        db.commit()
        importer.sync_source(db, source, force=True)
    else:
        home, calendars = _tried(caldav.discover, body.apple_id.strip(), body.password)
        secret = json.dumps({"apple_id": body.apple_id.strip(), "password": body.password})
        source = models.Source(kind=body.kind, name=body.name, credential=crypto.encrypt(secret), base_url=home,
                               last_success_at=models.utcnow())
        db.add(source)
        db.flush()
        for found in calendars:
            db.add(models.Calendar(source_id=source.id, remote_id=found.href, name=found.name, enabled=False))
        db.commit()
    db.refresh(source)
    return _source_out(source)


@router.post("/sources", status_code=status.HTTP_201_CREATED, dependencies=[Depends(auth.require_parent)])
async def add_source(body: Annotated[GoogleIn | ICloudIn, Field(discriminator="kind")],
                     db: Session = Depends(database.get_db)):
    return await run_in_threadpool(_add, db, body)


def _patch(db: Session, source: models.Source, body: SourcePatch) -> dict:
    if body.name is not None:
        source.name = body.name
        if source.kind == "google_ical":
            for calendar in source.calendars:
                calendar.name = body.name
    if source.kind == "google_ical" and body.url:
        _tried(google.check, body.url)
        source.credential, source.content_hash = crypto.encrypt(google.address(body.url)), None
    if source.kind == "icloud_caldav" and (body.apple_id or body.password):
        old = json.loads(importer.credential(source)) if not (body.apple_id and body.password) else {}
        apple_id = (body.apple_id or old["apple_id"]).strip()
        password = body.password or old["password"]
        home, _ = _tried(caldav.discover, apple_id, password)
        source.credential = crypto.encrypt(json.dumps({"apple_id": apple_id, "password": password}))
        source.base_url = home
    db.commit()
    if body.url or body.apple_id or body.password:
        importer.sync_source(db, source, force=True)
    db.refresh(source)
    return _source_out(source)


@router.patch("/sources/{source_id}", dependencies=[Depends(auth.require_parent)])
async def patch_source(source_id: int, body: SourcePatch, db: Session = Depends(database.get_db)):
    try:
        return await run_in_threadpool(_patch, db, _source(db, source_id), body)
    except importer.SourceError as error:  # the stored credential can't be read (source_key)
        raise api_error(status.HTTP_422_UNPROCESSABLE_CONTENT, error.code) from None


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(auth.require_parent)])
def delete_source(source_id: int, db: Session = Depends(database.get_db)):
    db.delete(_source(db, source_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _sync(db: Session, source: models.Source) -> dict:
    importer.sync_source(db, source, force=True)
    db.refresh(source)
    return _source_out(source)


@router.post("/sources/{source_id}/sync", dependencies=[Depends(auth.require_parent)])
async def sync_source(source_id: int, db: Session = Depends(database.get_db)):
    return await run_in_threadpool(_sync, db, _source(db, source_id))


def _patch_calendar(db: Session, calendar: models.Calendar, body: CalendarPatch) -> dict:
    fields = body.model_fields_set
    if "person_id" in fields:
        if body.person_id is not None:
            person = db.get(models.Person, body.person_id)
            if person is None or not person.is_active:
                raise api_error(status.HTTP_422_UNPROCESSABLE_CONTENT, "unknown_person")
        calendar.person_id = body.person_id
    if "color" in fields:
        calendar.color = _color(body.color) if body.color else None
    if body.visible is not None:
        calendar.visible = body.visible
    newly_enabled = body.enabled is True and not calendar.enabled
    if body.enabled is not None:
        calendar.enabled = body.enabled
    db.commit()
    if newly_enabled:
        importer.sync_source(db, calendar.source, force=True)
    db.refresh(calendar)
    return {"id": calendar.id, "name": calendar.name, "enabled": calendar.enabled, "visible": calendar.visible,
            "person_id": calendar.person_id, "color": calendar.color}


@router.patch("/calendars/{calendar_id}", dependencies=[Depends(auth.require_parent)])
async def patch_calendar(calendar_id: int, body: CalendarPatch, db: Session = Depends(database.get_db)):
    calendar = db.get(models.Calendar, calendar_id)
    if calendar is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "not_found")
    return await run_in_threadpool(_patch_calendar, db, calendar, body)


@router.get("/people", dependencies=[Depends(auth.require_parent)])
def people(db: Session = Depends(database.get_db)):
    rows = db.query(models.Person).filter(models.Person.is_active.is_(True)).order_by(models.Person.name).all()
    return [{"id": p.id, "name": p.name, "color": p.color} for p in rows]


@router.patch("/settings", dependencies=[Depends(auth.require_parent)])
def patch_settings(body: SettingsPatch, db: Session = Depends(database.get_db)):
    row = get_settings(db)
    row.family_color = _color(body.family_color)
    db.commit()
    return {"family_color": row.family_color}
