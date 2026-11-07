import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import config, crypto, database, database_setup, hub, logs, public_api, scheduler, settings_api

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

logger.info(
    "Family hub: %s (logins at %s, app key %s)", hub.client.hub_url(), hub.client.public_url(), hub.client.app_key()
)



@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler.start()
    yield
    await scheduler.stop()


app = FastAPI(title="Family Planner API", version="0.1.0", lifespan=lifespan)

# Cloudflare sets this header on everything through its tunnel. The planner is for the home network only and has no
# tunnel route; should one appear by mistake, nothing but the health check answers through it
TUNNEL_HEADER = "Cf-Connecting-Ip"


def allowed_hosts() -> set[str]:
    """The names the planner answers under (ALLOWED_HOSTS, comma-separated, e.g. kalender.local.<domain>); empty: any.
    Viewing needs no login, so a web page that points a name of its own at the NAS (DNS rebinding) must get nothing."""
    return {host.strip().lower() for host in config.env("ALLOWED_HOSTS").split(",") if host.strip()}


@app.middleware("http")
async def home_only(request: Request, call_next):
    if request.url.path != "/health":
        if TUNNEL_HEADER in request.headers:
            return JSONResponse({"detail": "outside"}, status_code=403)
        hosts = allowed_hosts()
        host = request.headers.get("host", "").rsplit(":", 1)[0].strip("[]").lower()
        if hosts and host not in hosts:
            return JSONResponse({"detail": "bad_host"}, status_code=400)
    return await call_next(request)


app.include_router(public_api.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
