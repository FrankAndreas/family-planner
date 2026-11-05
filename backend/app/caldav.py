"""iCloud calendars through CalDAV, read-only (spec "Calendar integration").

Discovery starts at caldav.icloud.com and follows the account's principal to its calendar home on a shard host
(pXX-caldav.icloud.com), which is kept on the source. Each sync lists the home once (names, ctags, new and removed
calendars) and fetches the events of an enabled calendar only when its ctag changed. The app-specific password never
reaches a log or an error."""

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC
from urllib.parse import urljoin

import httpx
from sqlalchemy.orm import Session

from . import config, fetch, ics, models
from .importer import SourceError, credential, http_error, replace_series

START = "https://caldav.icloud.com/"
NS = {"d": "DAV:", "c": "urn:ietf:params:xml:ns:caldav", "cs": "http://calendarserver.org/ns/"}


@dataclass(frozen=True)
class RemoteCalendar:
    href: str
    name: str
    ctag: str | None


def _body(props: str) -> str:
    return (f'<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:c="{NS["c"]}" xmlns:cs="{NS["cs"]}">'
            f"<d:prop>{props}</d:prop></d:propfind>")


def _request(client: httpx.Client, method: str, url: str, body: str, depth: str) -> list[tuple[str, ET.Element]]:
    """A WebDAV request; its <response>s as (absolute href, prop element)."""
    try:
        response = client.request(method, url, content=body.encode(),
                                  headers={"Depth": depth, "Content-Type": "application/xml; charset=utf-8"})
    except (httpx.HTTPError, ValueError):
        raise SourceError("source_unreachable") from None
    if response.status_code >= 400:
        raise http_error(response.status_code) from None
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError:
        raise SourceError("source_invalid") from None
    found = []
    for item in root.findall("d:response", NS):
        href = item.findtext("d:href", default="", namespaces=NS).strip()
        for propstat in item.findall("d:propstat", NS):
            if " 200 " in (propstat.findtext("d:status", default="", namespaces=NS) + " "):
                prop = propstat.find("d:prop", NS)
                if prop is not None:
                    found.append((urljoin(url, href), prop))
    return found


def _href(prop: ET.Element, path: str) -> str | None:
    element = prop.find(path, NS)
    return element.findtext("d:href", default="", namespaces=NS).strip() if element is not None else None


def _client(apple_id: str, password: str) -> httpx.Client:
    return fetch.client(auth=(apple_id, password))


def _home(client: httpx.Client) -> str:
    responses = _request(client, "PROPFIND", START, _body("<d:current-user-principal/>"), "0")
    principal = next((_href(p, "d:current-user-principal") for _, p in responses if _href(p, "d:current-user-principal")), None)
    if not principal:
        raise SourceError("source_invalid")
    principal = urljoin(START, principal)
    responses = _request(client, "PROPFIND", principal, _body("<c:calendar-home-set/>"), "0")
    home = next((_href(p, "c:calendar-home-set") for _, p in responses if _href(p, "c:calendar-home-set")), None)
    if not home:
        raise SourceError("source_invalid")
    return urljoin(principal, home)


def _calendars(client: httpx.Client, home: str) -> list[RemoteCalendar]:
    props = "<d:displayname/><d:resourcetype/><cs:getctag/><c:supported-calendar-component-set/>"
    found = []
    for href, prop in _request(client, "PROPFIND", home, _body(props), "1"):
        if prop.find("d:resourcetype/c:calendar", NS) is None:
            continue
        components = {c.get("name") for c in prop.findall("c:supported-calendar-component-set/c:comp", NS)}
        if components and "VEVENT" not in components:
            continue
        name = (prop.findtext("d:displayname", default="", namespaces=NS) or "").strip() or href.rstrip("/").rsplit("/", 1)[-1]
        ctag = prop.findtext("cs:getctag", default=None, namespaces=NS)
        found.append(RemoteCalendar(href, name, ctag.strip() if ctag else None))
    return found


def discover(apple_id: str, password: str) -> tuple[str, list[RemoteCalendar]]:
    """The account's calendar home (on its shard host) and its event calendars; tried before a source is saved."""
    with _client(apple_id, password) as client:
        home = _home(client)
        return home, _calendars(client, home)


def _events(client: httpx.Client, href: str) -> tuple[list[ics.SeriesData], dict[str, tuple[str, str]]]:
    start, end = (edge.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ") for edge in config.window())
    body = (f'<?xml version="1.0"?><c:calendar-query xmlns:d="DAV:" xmlns:c="{NS["c"]}">'
            "<d:prop><d:getetag/><c:calendar-data/></d:prop>"
            '<c:filter><c:comp-filter name="VCALENDAR"><c:comp-filter name="VEVENT">'
            f'<c:time-range start="{start}" end="{end}"/></c:comp-filter></c:comp-filter></c:filter>'
            "</c:calendar-query>")
    series: dict[str, ics.SeriesData] = {}
    hrefs: dict[str, tuple[str, str]] = {}
    for event_href, prop in _request(client, "REPORT", href, body, "1"):
        text = prop.findtext("c:calendar-data", default="", namespaces=NS)
        if not text.strip():
            continue
        try:
            items = ics.parse(text, config.window())
        except ics.NotACalendar:
            raise SourceError("source_invalid") from None
        for item in items:
            series[item.uid] = item
            hrefs[item.uid] = (event_href, prop.findtext("d:getetag", default="", namespaces=NS).strip())
    return list(series.values()), hrefs


def sync(db: Session, source: models.Source, force: bool = False) -> None:
    secret = json.loads(credential(source))
    with _client(secret["apple_id"], secret["password"]) as client:
        if not source.base_url:
            source.base_url = _home(client)
        remote = {c.href: c for c in _calendars(client, source.base_url)}
        kept = {c.remote_id: c for c in source.calendars}
        # An account without a single calendar is far more likely a hiccup at iCloud than the truth: keep everything
        # (and the parents' settings for each calendar) until it lists calendars again
        if kept and not remote:
            raise SourceError("source_invalid")
        for href, calendar in kept.items():
            if href not in remote:
                db.delete(calendar)
        for href, found in remote.items():
            calendar = kept.get(href)
            if calendar is None:
                db.add(models.Calendar(source_id=source.id, remote_id=href, name=found.name, ctag=None, enabled=False))
                continue
            calendar.name = found.name
            # With the window's first day: an unchanged calendar is still read once a day, as events far ahead move
            # into the window (and old ones out)
            marker = f"{found.ctag}|{config.window()[0].date()}" if found.ctag is not None else None
            if not calendar.enabled or (not force and marker is not None and marker == calendar.ctag):
                continue
            series, hrefs = _events(client, href)
            replace_series(db, calendar, series, ctag=marker or "", hrefs=hrefs)
        db.commit()
        db.refresh(source)
