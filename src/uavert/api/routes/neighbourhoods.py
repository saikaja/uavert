import json

from fastapi import APIRouter, Path, Request

from uavert.api import live
from uavert.api.errors import ApiError

router = APIRouter(tags=["neighbourhoods"])

_COLUMNS = (
    "n.id, n.name, n.population, n.valid_year, ST_X(ST_PointOnSurface(n.geom)) AS lon,"
    " ST_Y(ST_PointOnSurface(n.geom)) AS lat, s.crime_score, s.reasons, s.details, s.computed_at"
)
_FROM = " FROM neighbourhoods n JOIN neighbourhood_scores s ON s.neighbourhood_id = n.id"


@router.get("/neighbourhoods", summary="All neighbourhoods with their scores, as GeoJSON")
async def list_neighbourhoods(request: Request):
    pool = request.app.state.pool
    ctx = await live.load(pool)
    rows = await pool.fetch(
        f"SELECT {_COLUMNS}, ST_AsGeoJSON(ST_SimplifyPreserveTopology(n.geom, 0.0001), 5) AS g {_FROM} ORDER BY n.name"
    )
    features = [
        {"type": "Feature", "geometry": json.loads(r["g"]),
         "properties": {"id": r["id"], "name": r["name"],
                        **ctx.score(r["lon"], r["lat"], r["crime_score"], json.loads(r["reasons"]),
                                    neighbourhood_id=r["id"]).to_dict(with_reasons=False)}}
        for r in rows
    ]
    return live.envelope({"type": "FeatureCollection", "features": features}, ctx)


@router.get("/neighbourhoods/{neighbourhood_id}", summary="One neighbourhood: score, reasons and crime details")
async def get_neighbourhood(request: Request, neighbourhood_id: int = Path(ge=1)):
    pool = request.app.state.pool
    r = await pool.fetchrow(f"SELECT {_COLUMNS} {_FROM} WHERE n.id = $1", neighbourhood_id)
    if r is None:
        raise ApiError(404, "not_found", f"No neighbourhood with id {neighbourhood_id}.")
    ctx = await live.load(pool)
    score = ctx.score(r["lon"], r["lat"], r["crime_score"], json.loads(r["reasons"]), neighbourhood_id=r["id"])
    details = json.loads(r["details"])
    return live.envelope({
        "id": r["id"], "name": r["name"], "population": r["population"], "population_year": r["valid_year"],
        "centre": {"lon": r["lon"], "lat": r["lat"]},
        "crime_details": details, "crime_computed_at": r["computed_at"].isoformat(), "odds": details.get("odds"),
        **score.to_dict(),
    }, ctx)
