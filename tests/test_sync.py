import threading

from app import database, google, importer, models
from test_google import ONE, add_source, series_uids


def test_a_sync_that_waited_for_another_uses_its_result(db, monkeypatch):
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

    # The manual sync waited, found the scheduler's fresh result and didn't download again
    assert events == ["enter", "leave"]
    db.expire_all()
    source = db.get(models.Source, source_id)
    assert source.last_error is None
    assert len(source.calendars) == 1 and series_uids(db, source) == ["one@test"]


def test_a_source_deleted_during_the_round_doesnt_stop_the_others(db, monkeypatch):
    first, second, third = (add_source(db, url=f"https://example.com/{n}.ics", name=n) for n in "abc")
    second_id = second.id

    def download(url):
        if url.endswith("/a.ics"):  # while the first source syncs, a parent deletes the second one
            with database.SessionLocal() as other:
                other.delete(other.get(models.Source, second_id))
                other.commit()
        return ONE

    monkeypatch.setattr(google, "download", download)
    importer.sync_all(db)
    db.expire_all()
    assert db.get(models.Source, third.id).last_success_at is not None
