import threading

from app import database, google, importer, models
from test_google import ONE, add_source, series_uids


def test_two_syncs_of_one_source_run_one_after_the_other(db, monkeypatch):
    """A manual "Jetzt aktualisieren" while the scheduler syncs the same source: no false error, no duplicates."""
    source_id = add_source(db).id
    first_inside, release, events = threading.Event(), threading.Event(), []

    def slow_download(url):
        first = not first_inside.is_set()
        events.append("enter")
        if first:
            first_inside.set()
            release.wait(5)
        events.append("leave")
        return ONE

    monkeypatch.setattr(google, "download", slow_download)

    def run():
        with database.SessionLocal() as session:
            importer.sync_source(session, session.get(models.Source, source_id), force=True)

    scheduler_sync, manual_sync = threading.Thread(target=run), threading.Thread(target=run)
    scheduler_sync.start()
    assert first_inside.wait(5)
    manual_sync.start()
    manual_sync.join(0.3)
    release.set()
    scheduler_sync.join(5)
    manual_sync.join(5)
    assert not scheduler_sync.is_alive() and not manual_sync.is_alive()

    assert events == ["enter", "leave", "enter", "leave"]
    db.expire_all()
    source = db.get(models.Source, source_id)
    assert source.last_error is None
    assert len(source.calendars) == 1 and series_uids(db, source) == ["one@test"]
