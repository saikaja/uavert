"""FastAPI app: `/api/v1` endpoints and the web map."""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from uavert import db
from uavert.config import get_settings
from uavert.ingest.steps import LIVE, run_steps
from uavert.api import errors
from uavert.api.errors import error_response
from uavert.api.routes import cells, neighbourhoods, news, risk_scores, route_risks, sources


log = logging.getLogger("uavert.api")


async def refresh_once(pool) -> list[str]:
    """One refresh of the live sources. Never raises: failures are recorded per source."""
    try:
        async with pool.acquire() as conn:
            return await run_steps(conn, LIVE, report=log.info)
    except Exception:
        log.exception("Live refresh failed")
        return LIVE


async def refresh_forever(pool, minutes: int) -> None:
    while True:
        failed = await refresh_once(pool)
        log.info("Live refresh done%s", f"; failed: {', '.join(failed)}" if failed else "")
        await asyncio.sleep(minutes * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if getattr(app.state, "pool", None) is None:
        app.state.pool = await db.create_pool()
    minutes = get_settings().refresh_minutes
    task = asyncio.create_task(refresh_forever(app.state.pool, minutes)) if minutes > 0 else None
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    await app.state.pool.close()
    if getattr(app.state, "http", None) is not None:
        await app.state.http.aclose()


app = FastAPI(
    title="Uavert API",
    version="1.0",
    description="Location risk scores for Toronto from public data. All endpoints are public and read-only. "
                "Scores run 0-100, higher means more reported risk; no area is ever labelled safe.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
errors.install(app)
v1 = APIRouter(prefix="/api/v1")
_pool_lock = asyncio.Lock()


@app.middleware("http")
async def database_and_noindex(request: Request, call_next):
    # Open the database pool on first use as well as at startup: hosted platforms may not run startup.
    if getattr(app.state, "pool", None) is None:
        async with _pool_lock:
            if getattr(app.state, "pool", None) is None:
                app.state.pool = await db.create_pool()
    response = await call_next(request)
    response.headers["X-Robots-Tag"] = "noindex, nofollow"  # keep the demo out of search engines
    return response


@app.get("/robots.txt", include_in_schema=False)
async def robots():
    return PlainTextResponse("User-agent: *\nDisallow: /\n")


@v1.get("/health", tags=["system"])
async def health(request: Request):
    try:
        await request.app.state.pool.fetchval("SELECT 1")
    except Exception:
        return error_response(503, "database_unavailable", "The database is not reachable.")
    return {"data": {"status": "ok", "database": "ok"}}


for module in (neighbourhoods, cells, risk_scores, route_risks, news, sources):
    v1.include_router(module.router)
app.include_router(v1)
app.mount("/", StaticFiles(directory=Path(__file__).parent.parent / "web", html=True), name="web")
