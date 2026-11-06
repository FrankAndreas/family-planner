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
