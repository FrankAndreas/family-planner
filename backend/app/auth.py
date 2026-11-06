"""Who is logged in, for the settings: the family hub's login, as in the sibling apps.

Viewing needs no login. At home the browser sends the hub's cookie `hub_session` (set for local.<domain>, so every
family app gets it); tests and scripts may send the same token as `Authorization: Bearer`. Requests from outside never
get this far: main.py refuses everything that carries Cf-Connecting-Ip."""

import logging

from fastapi import Depends, Request, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from . import database, hub, hub_people, models
from .errors import api_error

logger = logging.getLogger(__name__)

COOKIE = "hub_session"
# With the cookie, a change must carry this header: another site can make the browser send the cookie (sibling apps
# share the site), but not a custom header without this app allowing it
CSRF_HEADER = "X-Requested-With"
CSRF_VALUE = "planner"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def request_login(request: Request) -> tuple[hub.Login | None, bool]:
    """The request's hub login, and whether it came as the cookie (then a change needs the header)."""
    scheme, _, value = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() == "bearer" and value.strip():
        return hub.Login(value.strip()), False
    cookie = request.cookies.get(COOKIE)
    return (hub.Login(cookie), True) if cookie else (None, False)


def _not_logged_in():
    error = api_error(status.HTTP_401_UNAUTHORIZED, "not_logged_in")
    error.headers = {"WWW-Authenticate": "Bearer"}
    return error


def _active(db: Session, hub_id: int) -> models.Person | None:
    return db.query(models.Person).filter(models.Person.hub_id == hub_id, models.Person.is_active.is_(True)).first()


def _resolve(request: Request, db: Session) -> models.Person:
    """The person behind the request's login. Blocking (the hub, the database): runs in a worker thread."""
    login, from_cookie = request_login(request)
    if login is None:
        raise _not_logged_in()
    if from_cookie and request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        raise api_error(status.HTTP_403_FORBIDDEN, "csrf")
    try:
        person, access = hub.session(login)
        if person is None:
            raise _not_logged_in()
        if not access:
            raise api_error(status.HTTP_403_FORBIDDEN, "no_access")
        hub_people.refresh(db, login)
        row = _active(db, person.id)
        # Given access a moment ago, or the role or name changed: the people kept here are older than that
        if row is None or row.role != models.Role.from_hub(person.role) or row.name != person.name:
            hub_people.refresh(db, login, force=True)
            row = _active(db, person.id)
    except hub.HubUnavailable as error:
        logger.warning("The family hub can't be reached (%s)", error)
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "hub_unavailable") from None
    if row is None:
        raise api_error(status.HTTP_403_FORBIDDEN, "no_access")
    return row


async def get_current_user(request: Request, db: Session = Depends(database.get_db)) -> models.Person:
    return await run_in_threadpool(_resolve, request, db)


def require_parent(person: models.Person = Depends(get_current_user)) -> models.Person:
    if person.role != models.Role.PARENT:
        raise api_error(status.HTTP_403_FORBIDDEN, "parents_only")
    return person
