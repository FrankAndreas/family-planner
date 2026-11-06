import asyncio
import threading
import time

from app import scheduler


def run_scheduler(monkeypatch, sync):
    monkeypatch.delenv("SYNC_DISABLED", raising=False)
    monkeypatch.setattr(scheduler, "_sync_all", sync)
    monkeypatch.setattr(scheduler, "backup_due", lambda now, last_day: False)


def test_stop_waits_for_a_running_sync(monkeypatch):
    entered, finished = threading.Event(), threading.Event()

    def sync():
        entered.set()
        time.sleep(0.3)
        finished.set()

    run_scheduler(monkeypatch, sync)

    async def main():
        scheduler.start()
        while not entered.is_set():
            await asyncio.sleep(0.01)
        await scheduler.stop()

    asyncio.run(main())
    assert finished.is_set()


def test_stop_gives_up_after_the_timeout(monkeypatch):
    entered = threading.Event()

    def sync():
        entered.set()
        time.sleep(2)

    run_scheduler(monkeypatch, sync)
    monkeypatch.setattr(scheduler, "STOP_TIMEOUT_SECONDS", 0.2)

    async def main():
        scheduler.start()
        while not entered.is_set():
            await asyncio.sleep(0.01)
        began = time.monotonic()
        await scheduler.stop()
        return time.monotonic() - began

    assert asyncio.run(main()) < 1


def test_a_stop_during_the_night_sync_skips_the_backup(monkeypatch):
    from app import backup

    entered, backups = threading.Event(), []

    def sync():
        entered.set()
        time.sleep(0.3)

    run_scheduler(monkeypatch, sync)
    monkeypatch.setattr(scheduler, "backup_due", lambda now, last_day: True)
    monkeypatch.setattr(backup, "nightly", lambda: backups.append("nightly"))

    async def main():
        scheduler.start()
        while not entered.is_set():
            await asyncio.sleep(0.01)
        await scheduler.stop()

    asyncio.run(main())
    assert backups == []


def test_stop_after_the_loop_died_doesnt_raise(monkeypatch):
    from app import backup

    run_scheduler(monkeypatch, lambda: None)

    def broken():
        raise OSError("disk")

    monkeypatch.setattr(backup, "last_nightly_day", broken)

    async def main():
        scheduler.start()
        await asyncio.sleep(0.05)
        await scheduler.stop()

    asyncio.run(main())
