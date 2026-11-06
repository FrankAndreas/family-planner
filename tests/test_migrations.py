from sqlalchemy import create_engine, inspect

from app import database_setup, models


def _migrated(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/m.db")
    database_setup.setup(engine)
    return engine


def test_fresh_database_has_exactly_the_tables(tmp_path):
    engine = _migrated(tmp_path)
    assert set(inspect(engine).get_table_names()) == {
        "people", "sources", "calendars", "series", "settings", "alembic_version"
    }
    with engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar() == database_setup.HEAD


def test_setup_is_idempotent(tmp_path):
    engine = _migrated(tmp_path)
    database_setup.setup(engine)  # a second start must not fail


def test_migration_matches_models(tmp_path):
    """The migrations create exactly the columns the models declare (catches a forgotten migration)."""
    inspector = inspect(_migrated(tmp_path))
    for table in models.Base.metadata.sorted_tables:
        assert {c["name"] for c in inspector.get_columns(table.name)} == set(table.columns.keys()), table.name


def test_constraints_are_named(tmp_path):
    inspector = inspect(_migrated(tmp_path))
    for table in models.Base.metadata.sorted_tables:
        for unique in inspector.get_unique_constraints(table.name):
            assert unique["name"], table.name


def test_deleting_a_source_deletes_its_calendars_and_series(db):
    source = models.Source(kind="google_ical", name="Mama", credential="v1:x")
    db.add(source)
    db.flush()
    calendar = models.Calendar(source_id=source.id, remote_id="ics", name="Mama")
    db.add(calendar)
    db.flush()
    db.add(models.Series(calendar_id=calendar.id, uid="a", ics="", first_start=models.utcnow()))
    db.commit()
    db.delete(source)
    db.commit()
    assert db.query(models.Calendar).count() == 0 and db.query(models.Series).count() == 0
