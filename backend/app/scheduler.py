"""The background work, in the app's own process (spec: no separate worker): every source every 300 s, and the
nightly backup once the clock in the planner's zone passes 03:00."""

import asyncio
import logging
from datetime import datetime, time

from fastapi.concurrency import run_in_threadpool

from . import backup, config, database, importer

logger = logging.getLogger(__name__)

SYNC_SECONDS = 300
BACKUP_AT = time(3, 0)

_task: asyncio.Task | None = None


def _sync_all() -> None:
    with database.SessionLocal() as db:
        importer.sync_all(db)


def backup_due(now: datetime, last_day) -> bool:
    return now.time() >= BACKUP_AT and now.date() != last_day


async def _loop() -> None:
    last_backup = backup.last_nightly_day()
    while True:
        try:
            await run_in_threadpool(_sync_all)
        except Exception as error:  # never let the loop die; the type only, messages may carry addresses
            logger.error("Sync failed: %s", type(error).__name__)
        now = datetime.now(config.tz())
        if backup_due(now, last_backup):
            try:
                await run_in_threadpool(backup.nightly)
                last_backup = now.date()
            except Exception as error:
                logger.error("Backup failed: %s", type(error).__name__)
        await asyncio.sleep(SYNC_SECONDS)


def start() -> None:
    global _task
    if config.env("SYNC_DISABLED") != "1" and _task is None:
        _task = asyncio.get_running_loop().create_task(_loop())


async def stop() -> None:
    global _task
    if _task is not None:
        _task.cancel()
        _task = None
