import sqlite3

from sqlalchemy import create_engine

from app import backup, config, database_setup


def backups():
    folder = config.data_dir() / "backups"
    return sorted(p.name for p in folder.glob("planner-*.db")) if folder.exists() else []


def test_backup_is_a_readable_copy(db):
    path = backup.make("nightly")
    assert path.parent == config.data_dir() / "backups" and path.name.startswith("planner-nightly-")
    with sqlite3.connect(path) as conn:
        assert ("people",) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()


def test_backup_keeps_14():
    for _ in range(16):
        backup.make("nightly")
    backup.prune(keep=14)
    assert len(backups()) == 14


def test_backup_before_migration(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE something (id INTEGER)")
    database_setup.setup(create_engine(f"sqlite:///{path}"))
    assert [name for name in backups() if "before-migration" in name]


def test_no_backup_for_new_or_current_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/new.db")
    database_setup.setup(engine)
    database_setup.setup(engine)
    assert backups() == []


def test_last_nightly_day_from_the_newest_file():
    from datetime import date

    assert backup.last_nightly_day() is None
    backup.make("nightly")
    backup.make("before-migration")
    assert backup.last_nightly_day() == date.today()


def test_restart_after_3_does_not_back_up_again_the_same_day():
    from datetime import datetime

    from app import scheduler

    backup.make("nightly")
    now = datetime.now(config.tz()).replace(hour=22)
    assert scheduler.backup_due(now, backup.last_nightly_day()) is False
    assert scheduler.backup_due(now, None) is True
