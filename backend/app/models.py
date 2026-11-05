"""The planner's tables (spec "Data"): people from the hub, calendar sources, their calendars and the cached events."""

import enum
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String

from .database import Base


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Role(str, enum.Enum):
    PARENT = "PARENT"
    CHILD = "CHILD"


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
