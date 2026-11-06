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
# How long stop() waits for a running sync (a download may take up to fetch.TIMEOUT_SECONDS per request); the
# compose file's stop_grace_period is longer
STOP_TIMEOUT_SECONDS = 30

_task: asyncio.Task | None = None
_stopping: asyncio.Event | None = None


def _sync_all() -> None:
    with database.SessionLocal() as db:
        importer.sync_all(db)


def backup_due(now: datetime, last_day) -> bool:
    return now.time() >= BACKUP_AT and now.date() != last_day


async def _loop(stopping: asyncio.Event) -> None:
    last_backup = backup.last_nightly_day()
    while not stopping.is_set():
        try:
            await run_in_threadpool(_sync_all)
        except Exception as error:  # never let the loop die; the type only, messages may carry addresses
            logger.error("Sync failed: %s", type(error).__name__)
        now = datetime.now(config.tz())
        # A stop during the night's sync leaves the backup to the next start (backup.last_nightly_day())
        if not stopping.is_set() and backup_due(now, last_backup):
            try:
                await run_in_threadpool(backup.nightly)
                last_backup = now.date()
            except Exception as error:
                logger.error("Backup failed: %s", type(error).__name__)
        try:
            await asyncio.wait_for(stopping.wait(), SYNC_SECONDS)
        except TimeoutError:
            pass


def start() -> None:
    global _task, _stopping
    if config.env("SYNC_DISABLED") != "1" and _task is None:
        _stopping = asyncio.Event()
        _task = asyncio.get_running_loop().create_task(_loop(_stopping))


async def stop() -> None:
    """Let a running sync finish (its import is one transaction either way), then end the loop."""
    global _task, _stopping
    if _task is None:
        return
    task, _task = _task, None
    _stopping.set()
    try:
        await asyncio.wait_for(asyncio.shield(task), STOP_TIMEOUT_SECONDS)
    except TimeoutError:
        task.cancel()
    except Exception as error:  # the loop had died already; shutting down goes on
        logger.error("The sync loop had stopped: %s", type(error).__name__)
