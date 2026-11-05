import logging

from fastapi import FastAPI

from . import crypto, database, database_setup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Without the key the stored calendar credentials can't be read: refuse to start, saying how to make one
try:
    crypto.load_key()
except crypto.KeyMissing as error:
    logger.error("%s", error)
    raise SystemExit(1) from None

# Create or upgrade the schema (Alembic migrations in app/migrations)
database_setup.setup(database.engine)

app = FastAPI(title="Family Planner API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}
