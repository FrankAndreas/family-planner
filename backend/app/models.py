"""The planner's tables (spec "Data"): people from the hub, calendar sources, their calendars and the cached events."""

import enum
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Role(str, enum.Enum):
    PARENT = "PARENT"
    CHILD = "CHILD"

    @classmethod
    def from_hub(cls, value: str) -> "Role":
        """The hub's role; one the planner doesn't know counts as a child (no settings)."""
        try:
            return cls(value)
        except ValueError:
            return cls.CHILD


class Person(Base):
    """A family member as the family hub lists them for the planner (a copy, refreshed by hub_people.py)."""

    __tablename__ = "people"

    id = Column(Integer, primary_key=True)
    hub_id = Column(Integer, unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    role = Column(Enum(Role), nullable=False)
    # The hub's colour for the person ("#rrggbb"), None when the hub has none
    color = Column(String(7))
    language = Column(String(2))
    # False: the hub no longer lists the person; their calendars count as "Familie" until a parent maps them again
    is_active = Column(Boolean, default=True, nullable=False)


class Source(Base):
    """Where calendars come from: one Google calendar's secret iCal address, or one iCloud account (CalDAV)."""

    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    # google_ical or icloud_caldav
    kind = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    # Encrypted (crypto.py): the secret URL, or JSON {"apple_id", "password"}. Never logged or sent to a browser
    credential = Column(Text, nullable=False)
    # iCloud: the calendar home found at discovery, on the account's shard host (pXX-caldav.icloud.com)
    base_url = Column(String(500))
    # Google: SHA-256 of the last downloaded feed; unchanged means nothing to import
    content_hash = Column(String(64))
    last_success_at = Column(DateTime)
    # An error code (source_auth, source_not_found, source_unreachable, source_invalid), never a message
    last_error = Column(String(40))
    last_error_at = Column(DateTime)

    calendars = relationship("Calendar", back_populates="source", cascade="all, delete-orphan", passive_deletes=True)


class Calendar(Base):
    """One calendar of a source. Google: the one feed ("ics"); iCloud: each calendar collection by its href."""

    __tablename__ = "calendars"
    __table_args__ = (UniqueConstraint("source_id", "remote_id"),)

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    remote_id = Column(String(500), nullable=False)
    name = Column(String(200), nullable=False)
    # iCloud: the collection's ctag at the last import; unchanged means nothing to import
    ctag = Column(String(200))
    # Whose calendar it is; None: "Familie"
    person_id = Column(Integer, ForeignKey("people.id", ondelete="SET NULL"))
    # Its own colour ("#rrggbb"), which wins over the person's
    color = Column(String(7))
    visible = Column(Boolean, default=True, nullable=False)
    # iCloud calendars are imported only once a parent ticks them
    enabled = Column(Boolean, default=True, nullable=False)

    source = relationship("Source", back_populates="calendars")
    person = relationship("Person")
    series = relationship("Series", cascade="all, delete-orphan", passive_deletes=True)


class Series(Base):
    """One event as the source has it: the master with its recurrence rules and moved occurrences (one UID), kept as
    iCalendar text and expanded for the range a screen asks for. first_start/last_end (UTC) find it quickly."""

    __tablename__ = "series"
    __table_args__ = (
        UniqueConstraint("calendar_id", "uid"),
        Index("ix_series_calendar_start", "calendar_id", "first_start"),
    )

    id = Column(Integer, primary_key=True)
    calendar_id = Column(Integer, ForeignKey("calendars.id", ondelete="CASCADE"), nullable=False)
    uid = Column(String(500), nullable=False)
    ics = Column(Text, nullable=False)
    first_start = Column(DateTime, nullable=False)
    # None: repeats without an end
    last_end = Column(DateTime)
    # CalDAV: the event's resource and its etag (for editing later)
    href = Column(String(500))
    etag = Column(String(200))


class Setting(Base):
    """The planner's settings: a single row (id 1)."""

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    family_color = Column(String(7), nullable=False, default="#7c3aed")
