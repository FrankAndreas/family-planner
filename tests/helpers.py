ADMIN = "Admin"


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(name: str = ADMIN) -> dict:
    """The headers of a hub login for that person (tests/fake_hub.py)."""
    import fake_hub

    return bearer(fake_hub.token(name))


def add_calendar(db, text: str, name: str = "Mama", person=None, color=None, visible=True, enabled=True,
                 kind="google_ical"):
    """A source with one calendar holding the events of `text` (an iCalendar), as an import would leave it."""
    from app import config, crypto, ics, importer, models

    source = models.Source(kind=kind, name=name, credential=crypto.encrypt("https://example.com/x.ics"),
                           last_success_at=models.utcnow())
    db.add(source)
    db.flush()
    calendar = models.Calendar(source_id=source.id, remote_id="ics", name=name, person_id=person.id if person else None,
                               color=color, visible=visible, enabled=enabled)
    db.add(calendar)
    db.flush()
    importer.replace_series(db, calendar, ics.parse(text, config.window()))
    return calendar


def add_person(db, name: str, color=None, role="CHILD", active=True):
    from app import models

    person = models.Person(hub_id=1000 + db.query(models.Person).count(), name=name, role=models.Role(role),
                           color=color, is_active=active)
    db.add(person)
    db.commit()
    return person
