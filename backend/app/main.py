import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import crypto, database, database_setup, hub, logs, public_api, scheduler, settings_api

logs.configure()
logger = logging.getLogger(__name__)

# Without the key the stored calendar credentials can't be read: refuse to start, saying how to make one
try:
    crypto.load_key()
except crypto.KeyMissing as error:
    logger.error("%s", error)
    raise SystemExit(1) from None

# Create or upgrade the schema (Alembic migrations in app/migrations)
database_setup.setup(database.engine)

logger.info("Family hub: %s (logins at %s, app key %s)", hub.hub_url(), hub.public_url(), hub.app_key())



@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler.start()
    yield
    await scheduler.stop()


app = FastAPI(title="Family Planner API", version="0.1.0", lifespan=lifespan)

# Cloudflare sets this header on everything through its tunnel. The planner is for the home network only and has no
# tunnel route; should one appear by mistake, nothing but the health check answers through it
TUNNEL_HEADER = "Cf-Connecting-Ip"


@app.middleware("http")
async def home_only(request: Request, call_next):
    if TUNNEL_HEADER in request.headers and request.url.path != "/health":
        return JSONResponse({"detail": "outside"}, status_code=403)
    return await call_next(request)


app.include_router(public_api.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
