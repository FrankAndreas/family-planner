from app import database, models
from app.settings_store import get_settings


def test_two_first_requests_at_once_both_get_the_settings(db, monkeypatch):
    """A brand-new database: another request makes the row between this one's look and its insert."""
    real_get = db.get

    def get_after_the_other_request_inserted(model, ident):
        if model is models.Setting and not hasattr(get_after_the_other_request_inserted, "done"):
            get_after_the_other_request_inserted.done = True
            with database.SessionLocal() as other:
                other.add(models.Setting(id=1, family_color="#123456"))
                other.commit()
            return None
        return real_get(model, ident)

    monkeypatch.setattr(db, "get", get_after_the_other_request_inserted)
    assert get_settings(db).family_color == "#123456"
