import json

from fastapi import APIRouter, Path, Query, Request

from uavert.api import live
from uavert.api.errors import ApiError
from uavert.api.timeofday import moment, neighbourhood_crime_at, time_info

router = APIRouter(tags=["neighbourhoods"])

_COLUMNS = (
    "n.id, n.name, n.population, n.valid_year, ST_X(ST_PointOnSurface(n.geom)) AS lon,"
    " ST_Y(ST_PointOnSurface(n.geom)) AS lat, s.crime_score, s.reasons, s.details, s.computed_at,"
    " s.crime_score_by_hour, s.move_by_hour"
)
_FROM = " FROM neighbourhoods n JOIN neighbourhood_scores s ON s.neighbourhood_id = n.id"
_HOUR = Query(None, ge=0, le=23, description="Hour of day in Toronto (0-23); omit for all day")


@router.get("/neighbourhoods", summary="All neighbourhoods with their scores, as GeoJSON")
async def list_neighbourhoods(request: Request, hour: int | None = _HOUR):
    pool = request.app.state.pool
    ctx = await live.load(pool)
    rows = await pool.fetch(
        f"SELECT {_COLUMNS}, ST_AsGeoJSON(ST_SimplifyPreserveTopology(n.geom, 0.0001), 5) AS g {_FROM} ORDER BY n.name"
    )
    at = moment(hour, ctx)
    features = [
        {"type": "Feature", "geometry": json.loads(r["g"]),
         "properties": {"id": r["id"], "name": r["name"],
                        **ctx.score(r["lon"], r["lat"], *neighbourhood_crime_at(r, hour, ctx),
                                    neighbourhood_id=r["id"], when=at).to_dict(with_reasons=False)}}
        for r in rows
    ]
    return live.envelope({"type": "FeatureCollection", "features": features, "time": time_info(hour)}, ctx)


@router.get("/neighbourhoods/{neighbourhood_id}", summary="One neighbourhood: score, reasons and crime details")
async def get_neighbourhood(request: Request, neighbourhood_id: int = Path(ge=1), hour: int | None = _HOUR):
    pool = request.app.state.pool
    r = await pool.fetchrow(f"SELECT {_COLUMNS} {_FROM} WHERE n.id = $1", neighbourhood_id)
    if r is None:
        raise ApiError(404, "not_found", f"No neighbourhood with id {neighbourhood_id}.")
    ctx = await live.load(pool)
    score = ctx.score(r["lon"], r["lat"], *neighbourhood_crime_at(r, hour, ctx), neighbourhood_id=r["id"],
                      when=moment(hour, ctx))
    details = json.loads(r["details"])
    return live.envelope({
        "id": r["id"], "name": r["name"], "population": r["population"], "population_year": r["valid_year"],
        "centre": {"lon": r["lon"], "lat": r["lat"]},
        "crime_details": details, "crime_computed_at": r["computed_at"].isoformat(), "odds": details.get("odds"),
        "trend": details.get("trend"),
        **score.to_dict(), "time": time_info(hour),
    }, ctx)
