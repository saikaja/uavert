"""FastAPI app: `/api/v1` endpoints and the web map."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from uavert import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    if getattr(app.state, "pool", None) is None:
        app.state.pool = await db.create_pool()
    yield
    await app.state.pool.close()


app = FastAPI(
    title="Uavert API",
    version="1.0",
    description="Location risk scores for Toronto from public data. All endpoints are public and read-only.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
v1 = APIRouter(prefix="/api/v1")


@v1.get("/health", tags=["system"])
async def health(request: Request):
    try:
        await request.app.state.pool.fetchval("SELECT 1")
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "database_unavailable", "message": "The database is not reachable.", "details": []}},
        )
    return {"data": {"status": "ok", "database": "ok"}}


app.include_router(v1)
