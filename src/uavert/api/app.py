"""FastAPI app: `/api/v1` endpoints and the web map."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request

from uavert import db
from uavert.api import errors
from uavert.api.errors import error_response
from uavert.api.routes import cells, neighbourhoods, news, risk_scores, route_risks, sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    if getattr(app.state, "pool", None) is None:
        app.state.pool = await db.create_pool()
    yield
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
