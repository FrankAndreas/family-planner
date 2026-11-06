from sqlalchemy.orm import Session

from . import models


def get_settings(db: Session) -> models.Setting:
    """The single settings row, made on first use."""
    row = db.get(models.Setting, 1)
    if row is None:
        row = models.Setting(id=1, family_color="#7c3aed")
        db.add(row)
        db.commit()
    return row
