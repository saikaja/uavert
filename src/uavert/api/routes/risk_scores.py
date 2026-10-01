from fastapi import APIRouter, Query, Request

from uavert.api import live
from uavert.api.errors import ApiError
from uavert.api.locate import resolve, score_place
from uavert.api.ratelimit import limit_outside_calls
from uavert.sources.geocode import Place

router = APIRouter(tags=["destination and route"])


@router.get(
    "/risk-scores",
    summary="Where I'm going: the risk score for an address or a point",
)
async def risk_scores(
    request: Request,
    address: str | None = Query(None, min_length=3, max_length=200, description="A Toronto street address or place"),
    lat: float | None = Query(None, ge=-90, le=90),
    lon: float | None = Query(None, ge=-180, le=180),
    hour: int | None = Query(None, ge=0, le=23, description="Hour of day in Toronto (0-23); omit for all day"),
):
    if address:
        limit_outside_calls(request)  # only address lookups call the geocoding service
        place = await resolve(request, address)
    elif lat is not None and lon is not None:
        place = Place(f"{lat:.5f}, {lon:.5f}", lon, lat)
    else:
        raise ApiError(422, "validation_error", "Give an address, or both lat and lon.")
    pool = request.app.state.pool
    ctx = await live.load(pool)
    return live.envelope({"query": address or f"{lat},{lon}", **await score_place(pool, ctx, place, hour)}, ctx)
