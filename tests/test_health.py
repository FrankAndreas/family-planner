from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app import config


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_wal_mode(db):
    assert db.execute(text("PRAGMA journal_mode")).scalar() == "wal"


def test_window_is_3_months_back_13_ahead():
    start, end = config.window(datetime(2026, 11, 5, 12, tzinfo=ZoneInfo("Europe/Zurich")))
    assert (start.date(), end.date()) == (date(2026, 8, 5), date(2027, 12, 5))


def test_window_clamps_to_month_end():
    start, end = config.window(datetime(2026, 5, 31, tzinfo=ZoneInfo("Europe/Zurich")))
    assert (start.date(), end.date()) == (date(2026, 2, 28), date(2027, 6, 30))
