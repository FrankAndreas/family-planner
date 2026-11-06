import calendar
import os
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

Language = Literal["de", "en"]

# Events are kept and shown from this many months back to this many ahead (spec: "Range")
MONTHS_BACK = 3
MONTHS_AHEAD = 13


def env(name: str, default: str = "") -> str:
    """An environment variable, stripped; read on every call so tests can change it."""
    return (os.getenv(name) or default).strip()


def data_dir() -> Path:
    return Path(env("DATA_DIR", "./data"))


def default_language() -> Language:
    """The language of the screens (they have no login) and of people the hub has no language for."""
    return "en" if env("DEFAULT_LANGUAGE", "de").lower() == "en" else "de"


def tz() -> ZoneInfo:
    return ZoneInfo(env("TZ", "Europe/Zurich"))


def _add_months(moment: datetime, months: int) -> datetime:
    index = moment.year * 12 + moment.month - 1 + months
    year, month = divmod(index, 12)
    month += 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """The range of events the planner keeps: MONTHS_BACK before now to MONTHS_AHEAD after, in the planner's zone."""
    now = (now or datetime.now(tz())).astimezone(tz())
    return _add_months(now, -MONTHS_BACK), _add_months(now, MONTHS_AHEAD)
