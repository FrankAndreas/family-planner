"""Copies of the database (spec "Backup"): every night and before migrations run, kept in data/backups (the newest
14). VACUUM INTO writes a consistent copy while the app keeps running."""

import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import Engine

from . import config, database

logger = logging.getLogger(__name__)

KEEP = 14


def folder() -> Path:
    return config.data_dir() / "backups"


def make(reason: str, engine: Engine | None = None) -> Path:
    target = folder()
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"planner-{reason}-{datetime.now(config.tz()):%Y%m%d-%H%M%S-%f}.db"
    connection = (engine or database.engine).raw_connection()
    try:
        connection.driver_connection.execute("VACUUM INTO ?", (str(path),))
    finally:
        connection.close()
    logger.info("Backup written: %s", path.name)
    return path


def prune(keep: int = KEEP) -> None:
    """Keep the newest `keep` nightly backups; the ones made before migrations stay."""
    nightly = sorted(folder().glob("planner-nightly-*.db"))
    for old in nightly[:-keep] if keep else nightly:
        old.unlink()


def last_nightly_day():
    """The day of the newest nightly backup (from its name), so a restart doesn't make another one that day."""
    from datetime import date

    newest = max(folder().glob("planner-nightly-*.db"), default=None)
    if newest is None:
        return None
    stamp = newest.name.removeprefix("planner-nightly-")[:8]
    return date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:8]))


def nightly() -> None:
    make("nightly")
    prune()
