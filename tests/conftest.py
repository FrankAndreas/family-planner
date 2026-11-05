import base64
import os
import sys
import tempfile
from pathlib import Path

# Point the app at a throwaway database, data folder and key before it is imported, so tests never touch ./data
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["DATA_DIR"] = _tmp
os.environ["DEFAULT_LANGUAGE"] = "de"
os.environ["SYNC_DISABLED"] = "1"
_key = Path(_tmp) / "enc_key"
_key.write_text(base64.b64encode(os.urandom(32)).decode())
os.environ["ENC_KEY_FILE"] = str(_key)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import database, models  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Every test starts with an empty database and a data folder of its own."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    yield


@pytest.fixture
def db():
    with database.SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    return TestClient(app)


import fake_hub  # noqa: E402
from app import hub, hub_people  # noqa: E402
from helpers import ADMIN  # noqa: E402


@pytest.fixture(autouse=True)
def family_hub(monkeypatch):
    """A fake family hub instead of the real one (tests/fake_hub.py), with the parent Admin."""
    fake = fake_hub.FakeHub()
    monkeypatch.setattr(fake_hub, "current", fake)
    monkeypatch.setattr(hub, "fetch_session", fake.fetch_session)
    monkeypatch.setattr(hub, "fetch_people", fake.fetch_people)
    fake.add(ADMIN, "PARENT")
    yield fake
    hub.forget()
    hub_people.forget()
