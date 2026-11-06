from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models


def get_settings(db: Session) -> models.Setting:
    """The single settings row, made on first use. On a brand-new database two first requests can both try to make
    it; the second takes the one the first made."""
    row = db.get(models.Setting, 1)
    if row is None:
        db.add(models.Setting(id=1, family_color="#7c3aed"))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        row = db.get(models.Setting, 1)
    return row
